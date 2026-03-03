from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import pandas as pd
import re
import io
import json
import base64
from collections import defaultdict

# ---------- CONSTANTS & HELPERS ----------
GRADE_POINTS = {
    'S': 10, 'A+': 9, 'A': 8.5, 'B+': 8, 'B': 7.5, 'C+': 7,
    'C': 6.5, 'D': 6, 'P': 5.5, 'PASS': 5.5,
    'F': 0, 'FE': 0, 'I': 0, 'ABSENT': 0, 'WITHHELD': 0
}

# register number regex: match PKD or LPKD prefix with two‑digit year,
# two letters dept code and three digits. used for filtering stray rows.
REG_NO_PATTERN = re.compile(r'(L?PKD\d{2}[A-Z]{2}\d{3})')
COURSE_GRADE_PATTERN = re.compile(r'([A-Z]{3,}\d{3})\s*\(([^)]+)\)')


def detect_metadata(text: str):
    """Return (semester, scheme, exam_name) detected from header text."""
    sem_match = re.search(r'\b(S[1-8])\b|SEMESTER\s+([IVX]+|[1-8])', text, re.IGNORECASE)
    semester = "S1"
    if sem_match:
        if sem_match.group(1):
            semester = sem_match.group(1).upper()
        else:
            roman = {"I":"S1","II":"S2","III":"S3","IV":"S4","V":"S5","VI":"S6","VII":"S7","VIII":"S8"}
            semester = roman.get(sem_match.group(2).upper(), semester)

    scheme = "2024" if "2024" in text else "2019"
    exam_name = "B.Tech Degree Examination" if "B.Tech" in text else "University Examination"
    return semester, scheme, exam_name


def get_course_credits(code: str, lookup: dict) -> int:
    """Look up credits for a given course code; supports X wildcard patterns."""
    clean = code.replace(" ", "")
    if clean in lookup:
        return lookup[clean]
    for pattern, val in lookup.items():
        if 'X' in pattern:
            regex = "^" + pattern.replace("X", "[A-Z0-9]") + "$"
            if re.match(regex, clean):
                return val
    return 0


app = FastAPI(title="KTU Result Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_and_analyze(pdf_bytes: bytes):
    departments_data = {}
    stats_data = []
    total_students = 0
    total_passed = 0
    missing_credit_courses = defaultdict(int)  # count of lookups that returned zero

    # will collect entire PDF text for metadata detection and SGPA logic
    full_text = ""
    
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        department = "Unknown"
        
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            full_text += text + "\n"
                
            lines = text.split('\n')
            current_student = None
            
            for line in lines:
                # 1. Match Department - Handle various KTU formats (e.g. Branch, Full Time, Generated on, etc.)
                # Often KTU headers look like: "INFORMATION TECHNOLOGY[Full Time] (Generated on ...)"
                # Or just the branch name before the date
                dept_match = re.match(r'^(.*?)(?:\[Full Time\]|\[Part Time\]|\(Generated on)', line)
                if dept_match and len(dept_match.group(1).strip()) > 5:
                    # Ignore lines that are definitely not departments
                    potential_dept = dept_match.group(1).strip()
                    if not potential_dept.startswith('APJ ABDUL KALAM') and not potential_dept.startswith('Exam Centre:'):
                        department = potential_dept
                        if department not in departments_data:
                            departments_data[department] = []
                        current_student = None
                        continue
                
                # Match Course string pattern globally: Any alphanumeric/hyphen/underscore string followed by (Grade)
                results_matches = re.findall(r'([A-Za-z0-9\-\_]+)\(([\w\+]+)\)', line)
                
                # 2. Match New Student Line
                student_match = re.match(r'^([A-Z0-9]{9,15})\s+(.*)', line)
                if student_match:
                    student_id = student_match.group(1)
                    
                    # Save previous student if exists
                    if current_student:
                        if department not in departments_data:
                            departments_data[department] = []
                        departments_data[department].append(current_student)
                        
                    current_student = {'Student ID': student_id}
                    
                    # Add courses on this line
                    for course, grade in results_matches:
                        current_student[course] = grade
                        
                # 3. Match continuation of student courses on next line
                elif current_student and len(results_matches) > 0:
                    for course, grade in results_matches:
                        current_student[course] = grade
                        
                # 4. If we hit empty line or something else, close the student block
                elif current_student and not line.strip():
                    if department not in departments_data:
                        departments_data[department] = []
                    departments_data[department].append(current_student)
                    current_student = None
                    
            # Add final student on page if exists
            if current_student:
                if department not in departments_data:
                    departments_data[department] = []
                departments_data[department].append(current_student)
                current_student = None

        # metadata detection & credit lookup
        detected_semester, detected_scheme, exam_name = detect_metadata(full_text)
        credits_file = f"credits_{detected_scheme}.json"
        # ensure we load from backend directory regardless of working directory
        import os
        base_dir = os.path.dirname(__file__)
        credits_path = os.path.join(base_dir, credits_file)
        try:
            with open(credits_path, "r") as f:
                credit_data = json.load(f)
        except FileNotFoundError:
            # if file missing, leave empty and later SGPA will be zero
            credit_data = {}
            print(f"WARNING: credit file not found at {credits_path}")

        # helper to extract entry year from register number
        def extract_year(reg: str):
            m = re.match(r'^L?PKD(\d{2})', reg, re.IGNORECASE)
            if m:
                return m.group(1)
            # fallback: look for any two-digit year at start
            m2 = re.match(r'.*?(\d{2})', reg)
            return m2.group(1) if m2 else None

        # separate regular vs supplementary students by year mismatch
        reg_dept = defaultdict(list)
        supp_dept = defaultdict(list)
        for dept, students in departments_data.items():
            # determine main year for this department - prefer the most frequent,
            # break ties by choosing the earliest year (lower number).
            year_counts = defaultdict(int)
            for s in students:
                yr = extract_year(s.get('Student ID', ''))
                if yr:
                    year_counts[yr] += 1
            main_year = None
            if year_counts:
                max_count = max(year_counts.values())
                candidates = [y for y, c in year_counts.items() if c == max_count]
                main_year = min(candidates)

            for s in students:
                yr = extract_year(s.get('Student ID', ''))
                # entries without a recognizable year go to supplementary
                if main_year and yr and yr != main_year:
                    supp_dept[dept].append(s)
                elif main_year and not yr:
                    supp_dept[dept].append(s)
                else:
                    reg_dept[dept].append(s)

        # remove any stray rows that lack a valid KTU register number
        # such as header lines like ELECTRICAL, ESSENTIALS etc. (lateral
        # students begin with LPKD so the regex now accepts an optional L)
        cleaned = {}
        for dept, studs in reg_dept.items():
            valid = [s for s in studs if REG_NO_PATTERN.match(s.get('Student ID',''))]
            if valid:
                cleaned[dept] = valid
        reg_dept = cleaned

        # also scrub supplementary bucket to avoid bogus rows lingering
        cleaned_supp = {}
        for dept, studs in supp_dept.items():
            valid = [s for s in studs if REG_NO_PATTERN.match(s.get('Student ID',''))]
            if valid:
                cleaned_supp[dept] = valid
        supp_dept = cleaned_supp

        # after cleaning, regular buckets are used for analysis; supplementary
        # students are kept in supp_dept to be written to a separate workbook if
        # any exist.
        dept_buckets = reg_dept
        departments_data = reg_dept

        # metadata and credit loading continues...
        # build semester_totals based on scheme
        if detected_scheme == "2024":
            semester_totals = credit_data.get("semester_total_credits", {})
        else:
            # 2019 structure: departments -> semesters each with total_credit
            semester_totals = {}
            for dept in credit_data.get("departments", []):
                for sem in dept.get("semesters", []):
                    key = f"S{sem.get('semester')}"
                    total = sem.get("total_credit", 0)
                    if key in semester_totals:
                        semester_totals[key] = max(semester_totals[key], total)
                    else:
                        semester_totals[key] = total
        semester_key = detected_semester
        if semester_key not in semester_totals:
            semester_key = detected_semester.replace("S", "")

        # build credit lookup: handles both JSON formats
        credit_lookup = {}
        if detected_scheme == "2024":
            credit_lookup = {
                c["code"].replace(" ", ""): c["credits"]
                for d in credit_data.get("curricula", [])
                for s in d.get("semesters", [])
                for c in s.get("courses", [])
            }
        else:
            # 2019 scheme: iterate departments and their semester courses
            for dept in credit_data.get("departments", []):
                for sem in dept.get("semesters", []):
                    for c in sem.get("courses", []):
                        code = c.get("course_code", "").replace(" ", "")
                        credit_lookup[code] = c.get("credit", 0)
        if not credit_lookup:
            print(f"WARNING: credit lookup is empty (scheme {detected_scheme}). check {credits_path}")

        # Calculate Results Post-Extraction
        for dept, students in departments_data.items():
            for student in students:
                passed_all = True
                total_weighted = 0
                total_creds = 0
                for course, grade in student.items():
                    if course in ['Student ID', 'Result', 'SGPA']:
                        continue
                    if grade in ['F', 'FE', 'Absent', 'Debarred', 'I']:
                        passed_all = False
                    gp = GRADE_POINTS.get(grade.upper(), 0)
                    creds = get_course_credits(course, credit_lookup)
                    if creds == 0:
                        missing_credit_courses[course] += 1
                    total_weighted += creds * gp
                    # 2019: include ALL courses in denominator (per official formula)
                    # 2024: only count passed courses for the denominator
                    if detected_scheme == "2019":
                        total_creds += creds
                    else:
                        if grade not in ['F', 'FE', 'Absent', 'Debarred', 'I']:
                            total_creds += creds
                # account for special 2024 S2 extra credit/activity
                if detected_scheme == "2024" and detected_semester == "S2":
                    total_creds += 1
                    total_weighted += 1 * 5.5
                # use different denominators based on scheme
                if detected_scheme == "2019":
                    # 2019 formula: SGPA = Σ(Ci×GPi)/ΣCi (sum of all course credits)
                    sgpa_denom = total_creds if total_creds > 0 else 1
                else:
                    # 2024: use official semester total
                    sgpa_denom = (
                        24 if detected_semester == "S2"
                        else semester_totals.get(semester_key, 21)
                    )
                sgpa = round(total_weighted / sgpa_denom, 2) if sgpa_denom else 0
                student['SGPA'] = sgpa
                student['Result'] = 'PASS' if passed_all else 'FAIL'

    if not departments_data:
        raise ValueError("Could not extract any results from the PDF.")

    # generate workbook for regular students only
    reg_excel = io.BytesIO()
    with pd.ExcelWriter(reg_excel, engine='openpyxl') as writer:
        for dept, students in dept_buckets.items():
            if not students:
                continue
            df = pd.DataFrame(students)

            # analytics for this department
            dept_total = len(df)
            dept_passed = len(df[df['Result'] == 'PASS'])
            dept_failed = dept_total - dept_passed
            dept_pass_percentage = round((dept_passed / dept_total) * 100, 2) if dept_total > 0 else 0

            # subject stats (exclude SGPA column)
            courses = [c for c in df.columns if c not in ['Student ID', 'Result', 'SGPA']]
            subject_stats = []
            for course in courses:
                course_grades = df[course].dropna()
                fails = course_grades.isin(['F', 'FE', 'Absent', 'Debarred']).sum()
                passes = len(course_grades) - fails
                subject_stats.append({
                    "subject": course,
                    "passed": int(passes),
                    "failed": int(fails)
                })

            total_students += dept_total
            total_passed += dept_passed
            stats_data.append({
                "name": dept.title(),
                "total": dept_total,
                "passed": dept_passed,
                "failed": dept_failed,
                "passPercentage": dept_pass_percentage,
                "subjectStats": subject_stats
            })

            cols = ['Student ID'] + courses + ['SGPA', 'Result']
            df = df[cols]
            df.to_excel(writer, sheet_name=dept[:31], index=False)
    reg_excel.seek(0)
    reg_base64 = base64.b64encode(reg_excel.read()).decode('utf-8')

    # if there are supplementary students create separate workbook
    supp_base64 = None
    if any(supp_dept.values()):
        supp_excel = io.BytesIO()
        with pd.ExcelWriter(supp_excel, engine='openpyxl') as writer:
            for dept, students in supp_dept.items():
                if not students:
                    continue
                df = pd.DataFrame(students)
                # build column list: always include Student ID and any course cols,
                # then append SGPA/Result only if they exist to avoid KeyErrors.
                courses = [c for c in df.columns if c not in ['Student ID', 'Result', 'SGPA']]
                cols = ['Student ID'] + courses
                if 'SGPA' in df.columns:
                    cols.append('SGPA')
                if 'Result' in df.columns:
                    cols.append('Result')
                df = df[cols]
                df.to_excel(writer, sheet_name=dept[:31], index=False)
        supp_excel.seek(0)
        supp_base64 = base64.b64encode(supp_excel.read()).decode('utf-8')

    overall_pass_percentage = round((total_passed / total_students) * 100, 2) if total_students > 0 else 0

    output = {
        "excelBase64": reg_base64,
        "stats": {
            "totalStudents": total_students,
            "passPercentage": overall_pass_percentage,
            "departments": stats_data
        }
    }
    # include supplementary workbook and summary if present
    supp_total = sum(len(v) for v in supp_dept.values())
    if supp_base64:
        output["supplementaryExcelBase64"] = supp_base64
    if supp_total:
        output["supplementaryCount"] = supp_total
    # also provide list of any courses for which we had no credit info
    if missing_credit_courses:
        output["missingCreditCourses"] = missing_credit_courses
    return output

@app.post("/api/convert")
async def convert_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
        
    try:
        contents = await file.read()
        analysis_result = extract_and_analyze(contents)
        return analysis_result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
