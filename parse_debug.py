import pdfplumber
import sys
import re

pdf_path = sys.argv[1]

with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages[:2]: # First two pages only
        text = page.extract_text()
        print("--- PAGE TEXT ---")
        print(text[:2000]) # Print first 2000 characters
        print("-----------------")
        
        lines = text.split('\n')
        for line in lines:
            if '[Full Time]' in line or '[Part Time]' in line:
                print(f"DEPT MATCH: {line}")
            elif re.match(r'^([A-Z0-9]{9,15})\s+(.*)', line):
                print(f"STUDENT MATCH: {line}")
