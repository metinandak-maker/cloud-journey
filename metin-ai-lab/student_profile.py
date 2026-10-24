import json
student_name = "Metin"
student_subject = "Linux"


print(student_name)
print(student_subject)

try:
    exam_score = int(input("Enter exam score: "))
except ValueError:
    print("Please enter a whole number!")
    raise SystemExit(1)

if exam_score < 0 or exam_score > 100:
    print("Invalid exam score!")
elif exam_score >= 80:
    student_level = "Advanced"
elif exam_score >= 50:
    student_level = "Intermediate"
else:
    student_level = "Beginner"

print("Exam Score:", exam_score)
if 0 <= exam_score <= 100:
    print("Student Level:", student_level)

if 0 <= exam_score <= 100:
    student_data = {
        "name": student_name,
        "subject": student_subject,
        "score": exam_score,
        "level": student_level
    }

    with open("student_data.json", "w") as file:
        json.dump(student_data, file, indent=4)


