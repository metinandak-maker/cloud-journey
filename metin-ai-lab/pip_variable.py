import os

pip_name = os.getenv("PIP_CHARACTER")
pip_world = os.getenv("PIP_WORLD")
pip_mood = os.getenv("PIP_MOOD")


print("Character:", pip_name)
print("World:", pip_world)
print("Mood:", pip_mood)


if pip_mood == "happy":
    print("Pip is smiling!")
elif pip_mood == "curious":
    print("Pip is exploring Wondernook!")
elif pip_mood == "scared":
    print("Pip is looking for a safe place!")
else:
    print("Pip is feeling something else.")



