import tkinter as tk
from tkinter import scrolledtext, filedialog
import threading
from datetime import datetime


from engine import run_council


last_final_answer = ""


def ask_council():
    question = question_box.get("1.0", tk.END).strip()

    if not question:
        results.delete("1.0", tk.END)
        results.insert(tk.END, "Please enter a question.")
        return

    ask_button.config(state="disabled")
    results.delete("1.0", tk.END)
    results.insert(tk.END, "Council is thinking...\n")
    root.update_idletasks()

    thread = threading.Thread(
        target=run_council_thread,
        args=(question,),
        daemon=True
    )
    thread.start()


def run_council_thread(question):
    council = run_council(question)

    root.after(
        0,
        show_results,
        council
    )

def copy_final_answer():
    if last_final_answer:
        root.clipboard_clear()
        root.clipboard_append(last_final_answer)
        root.update()


def save_final_answer():
    if not last_final_answer:
        return


    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt")],
        initialfile="metin_ai_lab_result.txt"
    )

    if file_path:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(last_final_answer)


def archive_result(question, final_answer):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open("council_archive.txt", "a", encoding="utf-8") as file:
        file.write("\n" + "=" * 60 + "\n")
        file.write(f"DATE: {timestamp}\n")
        file.write(f"QUESTION: {question}\n\n")
        file.write("FINAL ANSWER:\n")
        file.write(final_answer)
        file.write("\n")


def show_results(council):
    global last_final_answer
    last_final_answer = council.get("final", "")

    question = question_box.get("1.0", tk.END).strip()

    if last_final_answer:
        archive_result(question, last_final_answer)

    results.delete("1.0", tk.END)

    if "error" in council:
        results.insert(tk.END, council["error"])
        ask_button.config(state="normal")
        return

    output = f"""
==============================
ATLAS
==============================

{council["atlas"]}


==============================
CLAUDE
==============================

{council["claude"]}


==============================
GROK
==============================

{council["grok"]}


==============================
ATLAS REVIEW
==============================

{council["atlas_review"]}


==============================
CLAUDE REVIEW
==============================

{council["claude_review"]}


==============================
GROK REVIEW
==============================

{council["grok_review"]}


==================================================
COUNCIL FINAL ANSWER
==================================================

{council["final"]}
"""

    results.insert(tk.END, output)
    results.see(tk.END)

    ask_button.config(state="normal")


root = tk.Tk()

root.title("METIN AI LAB - AI COUNCIL")
root.geometry("1050x780")

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
question_box.pack(
    padx=20,
    pady=10
)

ask_button = tk.Button(
    root,
    text="ASK COUNCIL",
    command=ask_council,
    font=("Arial", 12, "bold"),
    width=20
)
ask_button.pack(pady=10)
copy_button = tk.Button(
    root,
    text="COPY FINAL ANSWER",
    command=copy_final_answer,
    font=("Arial", 11, "bold"),
    width=20
)
copy_button.pack(pady=5)
save_button = tk.Button(
    root,
    text="SAVE RESULT",
    command=save_final_answer,
    font=("Arial", 11, "bold"),
    width=20
)
save_button.pack(pady=5)
results = scrolledtext.ScrolledText(
    root,
    width=115,
    height=28,
    font=("Consolas", 10)
)
results.pack(
    padx=20,
    pady=15,
    fill="both",
    expand=True
)

results.insert(
    tk.END,
    "METIN AI LAB ready.\n\n"
    "Ask a question and press ASK COUNCIL."
)

root.mainloop()
