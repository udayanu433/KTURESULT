import json
import copy
import os

filepath = 'backend/credits_2019.json'
with open(filepath, 'r') as f:
    data = json.load(f)

has_it = any(d['department_name'] == 'Information Technology' for d in data['departments'])
if not has_it:
    cs_dept = next(d for d in data['departments'] if d['department_name'] == 'Computer Science and Engineering')
    it_dept = copy.deepcopy(cs_dept)
    it_dept['department_name'] = 'Information Technology'

    for sem in it_dept['semesters']:
        for course in sem['courses']:
            code = course['course_code']
            # Safely replace CS with IT for course codes
            new_code = code.replace('CST', 'ITT').replace('CSL', 'ITL').replace('CSD', 'ITD').replace('CSQ', 'ITQ')
            course['course_code'] = new_code

    data['departments'].append(it_dept)

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
    print("Successfully added Information Technology to credits_2019.json")
else:
    print("Information Technology already exists.")
