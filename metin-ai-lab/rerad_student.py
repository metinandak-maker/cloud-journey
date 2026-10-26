import json

with open("student_data.json", "r") as file:
    student_data = json.load(file)

print(student_data)
