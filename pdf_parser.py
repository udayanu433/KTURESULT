import pdfplumber
import pandas as pd
import re

def parse_pdf(pdf_path):
    import pdfplumber
    pdf = pdfplumber.open(pdf_path)
    department = 'Unknown'
    departments_data = {}
    
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue
            
        lines = text.split('\n')
        for line in lines:
            if '[Full Time]' in line or '[Part Time]' in line:
                dept_match = re.match(r'^(.*?)(?:\[Full Time\]|\[Part Time\])', line)
                if dept_match:
                    department = dept_match.group(1).strip()
                    if department not in departments_data:
                        departments_data[department] = []
            
            # Match student result line: Register No followed by Course(Grade)
            # Example: IDK20IT023 HUT300(B), ITT302(C), ITT304(C)
            if re.match(r'^[A-Z0-9]{10}\s', line) or re.match(r'^[A-Z]{3,4}\d{2}[A-Z]{2}\d{3}\s', line):
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    student_id = parts[0]
                    results_str = parts[1]
                    
                    # Extract pairs like HUT300(B)
                    results = re.findall(r'([A-Z0-9]+)\(([\w\+]+)\)', results_str)
                    
                    student_data = {'Student ID': student_id}
                    for course, grade in results:
                        student_data[course] = grade
                        
                    if department not in departments_data:
                        departments_data[department] = []
                    departments_data[department].append(student_data)
                    
    print(departments_data)

parse_pdf(r'D:\2019test.pdf')
