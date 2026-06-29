  KTU Result Analyser
An automated full-stack web application designed to parse official APJ Abdul Kalam Technological University (KTU) result PDFs and convert them into structured, highly readable Excel sheets. The tool automatically separates regular and supplementary examinations and calculates the Semester Grade Point Average ($SGPA$) for each student.
🚀 FeaturesPDF Parsing: 
Extracts raw text and tabular data directly from official university result PDFs.
Smart Categorization: Automatically identifies, filters, and splits results into distinct Regular and Supplementary sheets.
Automated SGPA Calculation: Programmatically calculates individual student $SGPA$ based on official KTU credit weights and grading schemes.
Excel Export: Generates clean, well-formatted .xlsx files ready for department analysis, sorting, and reporting.
🛠️ Tech StackFrontend: React.js, Tailwind CSS, Vercel (Deployment)Backend: Python FastAPI, Render (Deployment)
Libraries: PDF parsing engine (e.g., PyPDF/pdfplumber), Excel generation tools (e.g., pandas/openpyxl)
⚙️ How It Works1.
Upload PDF:
Step 1.Select and upload the official KTU B.Tech result PDF via the web interface.2.Processing & Extraction:
Step 2.The FastAPI backend parses the document, maps course codes, and identifies credit structures based on the academic scheme (e.g., 2019 or 2024 scheme).3.Metrics Computation:
Step 3.The application processes grades, separates regular attempts from supplementary ones, and calculates the exact $SGPA$ using the formula:$$SGPA = \frac{\sum (C_i \times G_i)}{\sum C_i}$$Where $C_i$ is the course credit and $G_i$ is the grade point.4.Download Report:
Step 4.The frontend serves a download link to pull the finalized, multi-sheet Excel spreadsheet.
