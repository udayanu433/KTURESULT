from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import pandas as pd
import re
import io
import base64

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
    
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        department = "Unknown"
        
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
                
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

        # Calculate Results Post-Extraction
        for dept, students in departments_data.items():
            for student in students:
                passed_all = True
                for course, grade in student.items():
                    if course == 'Student ID' or course == 'Result':
                        continue
                    if grade in ['F', 'FE', 'Absent', 'Debarred', 'I']:
                        passed_all = False
                student['Result'] = 'PASS' if passed_all else 'FAIL'

    if not departments_data:
        raise ValueError("Could not extract any results from the PDF.")

    excel_file = io.BytesIO()
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        for dept, students in departments_data.items():
            if not students:
                continue
                
            df = pd.DataFrame(students)
            
            # Analytics
            dept_total = len(df)
            dept_passed = len(df[df['Result'] == 'PASS'])
            dept_failed = dept_total - dept_passed
            dept_pass_percentage = round((dept_passed / dept_total) * 100, 2) if dept_total > 0 else 0
            
            # Subject-wise Pass/Fail Analytics
            courses = [c for c in df.columns if c not in ['Student ID', 'Result']]
            subject_stats = []
            
            for course in courses:
                # Count non-null grades (ignoring NaNs from pandas)
                course_grades = df[course].dropna()
                
                # A fail consists of grades like F, FE, Absent, Debarred
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
            
            # Format DataFrame
            cols = ['Student ID', 'Result'] + courses
            df = df[cols]
            
            sheet_name = dept[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
    excel_file.seek(0)
    excel_base64 = base64.b64encode(excel_file.read()).decode('utf-8')
    
    overall_pass_percentage = round((total_passed / total_students) * 100, 2) if total_students > 0 else 0
    
    return {
        "excelBase64": excel_base64,
        "stats": {
            "totalStudents": total_students,
            "passPercentage": overall_pass_percentage,
            "departments": stats_data
        }
    }

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
