import tkinter as tk
from tkinter import scrolledtext, filedialog
import threading
import os
from datetime import datetime


from engine import run_council, ask_atlas, ask_claude, ask_grok


last_final_answer = ""
selected_mode = "COUNCIL"

response_cache = {
    "COUNCIL": "",
    "ATLAS": "",
    "CLAUDE": "",
    "GROK": ""
}


def ask_council():
    question = question_box.get("1.0", tk.END).strip()

    if not question:
        results.delete("1.0", tk.END)
        results.insert(tk.END, "Please enter a question.")
        return

    ask_button.config(state="disabled")
    results.delete("1.0", tk.END)

    if selected_mode == "COUNCIL":
        results.insert(tk.END, "Council is thinking...\n")
    else:
        results.insert(tk.END, f"{selected_mode.title()} is thinking...\n")

    root.update_idletasks()

    mode = selected_mode

    thread = threading.Thread(
        target=run_selected_mode,
        args=(question, mode),
        daemon=True
    )
    thread.start()


def run_selected_mode(question, mode):
    try:
        if mode == "COUNCIL":
            response = run_council(question)
            root.after(0, show_results, response)
            return

        if mode == "ATLAS":
            answer = ask_atlas(question)
        elif mode == "CLAUDE":
            answer = ask_claude(question)
        elif mode == "GROK":
            answer = ask_grok(question)
        else:
            answer = "Unknown AI mode."

        root.after(0, show_single_result, mode, answer)

    except Exception as error:
        root.after(0, show_single_result, mode, f"ERROR: {error}")


def show_single_result(mode, answer):
    global last_final_answer

    last_final_answer = str(answer)

    output = (
        f"==============================\n"
        f"{mode}\n"
        f"==============================\n\n"
        f"{answer}"
    )

    response_cache[mode] = output

    if selected_mode == mode:
        results.delete("1.0", tk.END)
        results.insert(tk.END, output)
        results.see(tk.END)

    ask_button.config(state="normal")


def copy_final_answer():
    full_text = results.get("1.0", tk.END).strip()

    if full_text:
        root.clipboard_clear()
        root.clipboard_append(full_text)
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

    archive_dir = os.path.join(
        os.path.expanduser("~"),
        "Documents",
        "Metin AI Lab"
    )
    os.makedirs(archive_dir, exist_ok=True)

    archive_path = os.path.join(
        archive_dir,
        "council_archive.txt"
    )

    with open(archive_path, "a", encoding="utf-8") as file:
        file.write("\n" + "=" * 60 + "\n")
        file.write(f"DATE: {timestamp}\n")
        file.write(f"QUESTION: {question}\n\n")
        file.write("FINAL ANSWER:\n")
        file.write(final_answer)
        file.write("\n")


def new_chat():
    global last_final_answer

    last_final_answer = ""

    for mode in response_cache:
        response_cache[mode] = ""

    question_box.delete("1.0", tk.END)
    results.delete("1.0", tk.END)
    results.insert(tk.END, f"{selected_mode} ready. Ask a question.")

    question_box.focus_set()


def show_history():
    archive_dir = os.path.join(
        os.path.expanduser("~"),
        "Documents",
        "Metin AI Lab"
    )

    archive_path = os.path.join(
        archive_dir,
        "council_archive.txt"
    )

    history_window = tk.Toplevel(root)
    history_window.title("METIN AI LAB - HISTORY")
    history_window.geometry("900x650")
    history_window.configure(bg="#10131a")

    title = tk.Label(
        history_window,
        text="COUNCIL HISTORY",
        font=("Arial", 18, "bold"),
        fg="#f4f6fb",
        bg="#10131a"
    )
    title.pack(pady=(18, 10))

    history_box = scrolledtext.ScrolledText(
        history_window,
        wrap="word",
        font=("Consolas", 10),
        bg="#0f141c",
        fg="#dce3ee",
        insertbackground="#ffffff",
        relief="flat",
        padx=14,
        pady=12
    )
    history_box.pack(
        fill="both",
        expand=True,
        padx=20,
        pady=(0, 20)
    )

    if not os.path.exists(archive_path):
        history_box.insert(
            tk.END,
            "No archived Council results found yet."
        )
        return

    with open(archive_path, "r", encoding="utf-8") as file:
        history_box.insert(tk.END, file.read())

    history_box.see(tk.END)


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
root.title("METIN AI LAB v0.2 - AI COUNCIL")
root.geometry("1100x820")
root.minsize(900, 700)
root.configure(bg="#10131a")

# ---------- HEADER ----------
header = tk.Frame(root, bg="#10131a")
header.pack(fill="x", padx=30, pady=(24, 12))

title = tk.Label(
    header,
    text="METIN AI LAB",
    font=("Arial", 26, "bold"),
    fg="#f4f6fb",
    bg="#10131a"
)
title.pack()

subtitle = tk.Label(
    header,
    text="v0.2  •  MULTI-AI COUNCIL",
    font=("Arial", 11, "bold"),
    fg="#8ea0ba",
    bg="#10131a"
)
subtitle.pack(pady=(5, 0))

# ---------- MODE SELECTOR ----------
mode_frame = tk.Frame(root, bg="#10131a")
mode_frame.pack(fill="x", padx=30, pady=(0, 10))

mode_buttons = {}

def set_mode(mode):
    global selected_mode
    selected_mode = mode

    for name, button in mode_buttons.items():
        if name == mode:
            button.config(bg="#2563eb", fg="white")
        else:
            button.config(bg="#252c38", fg="#f4f6fb")

    status_label.config(text=f"{mode} • READY")
    ask_button.config(text=f"ASK {mode}")


for mode in ("COUNCIL", "ATLAS", "CLAUDE", "GROK"):
    btn = tk.Button(
        mode_frame,
        text=mode,
        command=lambda m=mode: set_mode(m),
        font=("Arial", 10, "bold"),
        bg="#252c38",
        fg="#f4f6fb",
        activebackground="#303947",
        activeforeground="white",
        relief="flat",
        bd=0,
        padx=18,
        pady=8,
        cursor="hand2"
    )
    btn.pack(side="left", padx=(0, 8))
    mode_buttons[mode] = btn


# ---------- QUESTION PANEL ----------
question_frame = tk.Frame(
    root,
    bg="#181d27",
    highlightbackground="#2a3342",
    highlightthickness=1
)
question_frame.pack(fill="x", padx=30, pady=(8, 12))

question_label = tk.Label(
    question_frame,
    text="Ask the Council",
    font=("Arial", 12, "bold"),
    fg="#f4f6fb",
    bg="#181d27"
)
question_label.pack(anchor="w", padx=18, pady=(15, 7))

question_box = tk.Text(
    question_frame,
    height=5,
    wrap="word",
    font=("Arial", 12),
    bg="#0f141c",
    fg="#f4f6fb",
    insertbackground="#ffffff",
    relief="flat",
    padx=12,
    pady=10
)
question_box.pack(fill="x", padx=18, pady=(0, 15))

# ---------- BUTTON BAR ----------
button_frame = tk.Frame(root, bg="#10131a")
button_frame.pack(fill="x", padx=30, pady=(0, 12))

ask_button = tk.Button(
    button_frame,
    text="ASK COUNCIL",
    command=ask_council,
    font=("Arial", 11, "bold"),
    bg="#2563eb",
    fg="white",
    activebackground="#1d4ed8",
    activeforeground="white",
    relief="flat",
    bd=0,
    padx=22,
    pady=10,
    cursor="hand2"
)
ask_button.pack(side="left", padx=(0, 10))

copy_button = tk.Button(
    button_frame,
    text="COPY ANSWER",
    command=copy_final_answer,
    font=("Arial", 10, "bold"),
    bg="#252c38",
    fg="#f4f6fb",
    activebackground="#303947",
    activeforeground="white",
    relief="flat",
    bd=0,
    padx=18,
    pady=10,
    cursor="hand2"
)
copy_button.pack(side="left", padx=(0, 10))

save_button = tk.Button(
    button_frame,
    text="SAVE",
    command=save_final_answer,
    font=("Arial", 10, "bold"),
    bg="#252c38",
    fg="#f4f6fb",
    activebackground="#303947",
    activeforeground="white",
    relief="flat",
    bd=0,
    padx=18,
    pady=10,
    cursor="hand2"
)
save_button.pack(side="left", padx=(0, 10))

history_button = tk.Button(
    button_frame,
    text="HISTORY",
    command=show_history,
    font=("Arial", 10, "bold"),
    bg="#252c38",
    fg="#f4f6fb",
    activebackground="#303947",
    activeforeground="white",
    relief="flat",
    bd=0,
    padx=18,
    pady=10,
    cursor="hand2"
)
history_button.pack(side="left", padx=(0, 10))

new_chat_button = tk.Button(
    button_frame,
    text="NEW CHAT",
    command=new_chat,
    font=("Arial", 10, "bold"),
    bg="#252c38",
    fg="#f4f6fb",
    activebackground="#303947",
    activeforeground="white",
    relief="flat",
    bd=0,
    padx=18,
    pady=10,
    cursor="hand2"
)
new_chat_button.pack(side="left")

status_label = tk.Label(
    button_frame,
    text="COUNCIL • READY",
    font=("Arial", 9, "bold"),
    fg="#67d391",
    bg="#10131a"
)
status_label.pack(side="right", pady=10)

# ---------- RESULTS PANEL ----------
results_frame = tk.Frame(
    root,
    bg="#181d27",
    highlightbackground="#2a3342",
    highlightthickness=1
)
results_frame.pack(
    fill="both",
    expand=True,
    padx=30,
    pady=(0, 25)
)

results_title = tk.Label(
    results_frame,
    text="AI RESPONSE",
    font=("Arial", 12, "bold"),
    fg="#f4f6fb",
    bg="#181d27"
)
results_title.pack(anchor="w", padx=18, pady=(14, 5))

results = scrolledtext.ScrolledText(
    results_frame,
    wrap="word",
    font=("Consolas", 10),
    bg="#0f141c",
    fg="#dce3ee",
    insertbackground="#ffffff",
    relief="flat",
    padx=14,
    pady=12
)
results.pack(
    padx=18,
    pady=(5, 18),
    fill="both",
    expand=True
)

results.insert(
    tk.END,
    "METIN AI LAB ready.\n\n"
    "Atlas, Claude and Grok are standing by.\n"
    "Enter a question above and press ASK COUNCIL."
)

set_mode("COUNCIL")

root.mainloop()
