import tkinter as tk
from tkinter import scrolledtext

root = tk.Tk()
root.title("METIN AI LAB")
root.geometry("1000x750")

title = tk.Label(
    root,
    text="METIN AI LAB - AI COUNCIL",
    font=("Arial", 20, "bold")
)
title.pack(pady=15)

question_label = tk.Label(
    root,
    text="Ask the Council:",
    font=("Arial", 12, "bold")
)
question_label.pack()

question_box = tk.Text(
    root,
    height=4,
    width=100,
    font=("Arial", 11)
)
question_box.pack(padx=20, pady=10)

ask_button = tk.Button(
    root,
    text="ASK COUNCIL",
    font=("Arial", 12, "bold"),
    width=20
)
ask_button.pack(pady=10)

results = scrolledtext.ScrolledText(
    root,
    width=115,
    height=28,
    font=("Consolas", 10)
)
results.pack(padx=20, pady=15, fill="both", expand=True)

results.insert(
    tk.END,
    "METIN AI LAB ready.\n\n"
    "Atlas + Claude + Grok will appear here."
)

root.mainloop()
