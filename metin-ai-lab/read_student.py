import json

with open("student_data.json", "r") as file:
    student = json.load(file)

print("Student:", student["name"])
print("Subject:", student["subject"])
print("Score:", student["score"])
print("Level:", student["level"])
