import tkinter as tk
from tkinter import scrolledtext, filedialog
import threading
import os
from datetime import datetime


from engine import run_council, ask_atlas, ask_claude, ask_grok


last_final_answer = ""
selected_mode = "COUNCIL"

selected_project = "General"

projects = [
    "General",
    "Cloud Journey",
    "Pip",
    "Website Client"
]

response_cache = {
    "COUNCIL": "",
    "ATLAS": "",
    "CLAUDE": "",
    "GROK": ""
}


thinking_after_id = None
thinking_mode = None
thinking_step = 0


def start_thinking_animation(mode):
    global thinking_after_id, thinking_mode, thinking_step

    stop_thinking_animation(set_ready=False)

    thinking_mode = mode
    thinking_step = 0

    def animate():
        global thinking_after_id, thinking_step

        if thinking_mode != mode:
            return

        dots = "." * ((thinking_step % 3) + 1)

        if selected_mode == mode:
            status_label.config(
                text=f"{mode}  ?  THINKING{dots}",
                fg="#38bdf8"
            )

        thinking_step += 1
        thinking_after_id = root.after(350, animate)

    animate()


def stop_thinking_animation(mode=None, set_ready=True):
    global thinking_after_id, thinking_mode, thinking_step

    if mode is not None and thinking_mode != mode:
        return

    finished_mode = thinking_mode

    if thinking_after_id is not None:
        try:
            root.after_cancel(thinking_after_id)
        except tk.TclError:
            pass

    thinking_after_id = None
    thinking_mode = None
    thinking_step = 0

    if set_ready and finished_mode and selected_mode == finished_mode:
        status_label.config(
            text=f"{finished_mode}  ?  READY",
            fg="#4ade80"
        )


def ask_council():
    question = question_box.get("1.0", tk.END).strip()

    if not question:
        results.delete("1.0", tk.END)
        results.insert(tk.END, "Please enter a question.")
        return

    ask_button.config(state="disabled")
    results.delete("1.0", tk.END)

    mode = selected_mode

    if mode == "COUNCIL":
        results.insert(tk.END, "Council is thinking...\n")
    else:
        results.insert(tk.END, f"{mode.title()} is thinking...\n")

    start_thinking_animation(mode)
    root.update_idletasks()

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

    stop_thinking_animation(mode)
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
    full_text = results.get("1.0", tk.END).strip()

    if not full_text:
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt")],
        initialfile="metin_ai_lab_result.txt"
    )

    if file_path:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(full_text)


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
    history_window.configure(bg="#f4f7fb")

    title = tk.Label(
        history_window,
        text="COUNCIL HISTORY",
        font=("Arial", 18, "bold"),
        fg="#10233f",
        bg="#f4f7fb"
    )
    title.pack(pady=(18, 10))

    history_box = scrolledtext.ScrolledText(
        history_window,
        wrap="word",
        font=("Consolas", 10),
        bg="#ffffff",
        fg="#172b4d",
        insertbackground="#2563eb",
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

    stop_thinking_animation("COUNCIL")
    last_final_answer = council.get("final", "")

    question = question_box.get("1.0", tk.END).strip()

    if last_final_answer:
        archive_result(question, last_final_answer)

    if "error" in council:
        error_output = str(council["error"])
        response_cache["COUNCIL"] = error_output

        if selected_mode == "COUNCIL":
            results.delete("1.0", tk.END)
            results.insert(tk.END, error_output)

        ask_button.config(state="normal")
        return

    output = f"""
==================================================
                 AI COUNCIL REPORT
==================================================

ATLAS  ?  ANALYSIS
--------------------------------------------------

{council["atlas"]}


CLAUDE  ?  ANALYSIS
--------------------------------------------------

{council["claude"]}


GROK  ?  ANALYSIS
--------------------------------------------------

{council["grok"]}


==================================================
                 COUNCIL REVIEW
==================================================

ATLAS  ?  REVIEW
--------------------------------------------------

{council["atlas_review"]}


CLAUDE  ?  REVIEW
--------------------------------------------------

{council["claude_review"]}


GROK  ?  REVIEW
--------------------------------------------------

{council["grok_review"]}


==================================================
              FINAL RECOMMENDATION
==================================================

{council["final"]}
"""

    response_cache["COUNCIL"] = output

    if selected_mode == "COUNCIL":
        results.delete("1.0", tk.END)
        results.insert(tk.END, output)
        results.see(tk.END)

    ask_button.config(state="normal")


root = tk.Tk()
root.title("METIN AI LAB v0.2 - AI COUNCIL")
root.geometry("1280x900")
root.minsize(640, 600)

# Open maximized while keeping the Windows taskbar visible
try:
    root.state("zoomed")
except tk.TclError:
    pass
root.configure(bg="#f4f7fb")

# Smooth professional startup
try:
    root.attributes("-alpha", 0.0)

    def fade_in(alpha=0.0):
        alpha += 0.08
        if alpha >= 1.0:
            root.attributes("-alpha", 1.0)
            return
        root.attributes("-alpha", alpha)
        root.after(18, lambda: fade_in(alpha))

    root.after(80, fade_in)
except tk.TclError:
    pass


# ---------- HEADER ----------
header = tk.Frame(root, bg="#f4f7fb")
header.pack(fill="x", padx=36, pady=(16, 8))

title = tk.Label(
    header,
    text="METIN AI LAB",
    font=("Segoe UI", 30, "bold"),
    fg="#0f2a4a",
    bg="#f4f7fb"
)
title.pack()

subtitle = tk.Label(
    header,
    text="v0.2  •  MULTI-AI COUNCIL",
    font=("Arial", 11, "bold"),
    fg="#8ea0ba",
    bg="#f4f7fb"
)
subtitle.pack(pady=(5, 0))

# ---------- MODE SELECTOR ----------
mode_frame = tk.Frame(root, bg="#f4f7fb")
mode_frame.pack(fill="x", padx=30, pady=(0, 10))

mode_buttons = {}

def set_mode(mode):
    global selected_mode
    selected_mode = mode

    for name, button in mode_buttons.items():
        if name == mode:
            button.config(bg="#2563eb", fg="white")
        else:
            button.config(bg="#e8eef6", fg="#10233f")

    status_label.config(text=f"{mode} • READY")
    ask_button.config(text=f"ASK {mode}")


for mode in ("COUNCIL", "ATLAS", "CLAUDE", "GROK"):
    btn = tk.Button(
        mode_frame,
        text=mode,
        command=lambda m=mode: set_mode(m),
        font=("Segoe UI", 10, "bold"),
        bg="#e8eef6",
        fg="#10233f",
        activebackground="#dce6f2",
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
    bg="#ffffff",
    highlightbackground="#d8e1ec",
    highlightthickness=1
)
question_frame.pack(fill="x", padx=36, pady=(6, 10))

question_label = tk.Label(
    question_frame,
    text="Ask the Council",
    font=("Arial", 12, "bold"),
    fg="#10233f",
    bg="#ffffff"
)
question_label.pack(anchor="w", padx=18, pady=(11, 5))

question_box = tk.Text(
    question_frame,
    height=3,
    wrap="word",
    font=("Arial", 12),
    bg="#ffffff",
    fg="#10233f",
    insertbackground="#2563eb",
    relief="flat",
    padx=12,
    pady=10
)
question_box.pack(fill="x", padx=18, pady=(0, 11))

# ---------- BUTTON BAR ----------
# ---------- PROJECT WORKSPACE ----------
project_frame = tk.Frame(root, bg="#f4f7fb")
project_frame.pack(fill="x", padx=36, pady=(0, 10))

project_label = tk.Label(
    project_frame,
    text="PROJECT",
    font=("Segoe UI", 9, "bold"),
    fg="#52657d",
    bg="#f4f7fb"
)
project_label.pack(side="left", padx=(0, 10))

project_var = tk.StringVar(value=selected_project)

project_menu = tk.OptionMenu(
    project_frame,
    project_var,
    *projects
)
project_menu.config(
    font=("Segoe UI", 10, "bold"),
    bg="#ffffff",
    fg="#10233f",
    activebackground="#e8eef6",
    activeforeground="#10233f",
    relief="flat",
    bd=0,
    highlightthickness=1,
    highlightbackground="#d8e1ec",
    padx=12,
    cursor="hand2"
)
project_menu["menu"].config(
    font=("Segoe UI", 10),
    bg="#ffffff",
    fg="#10233f"
)
project_menu.pack(side="left")

button_frame = tk.Frame(root, bg="#f4f7fb")
button_frame.pack(fill="x", padx=36, pady=(0, 10))

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
    font=("Segoe UI", 10, "bold"),
    bg="#e8eef6",
    fg="#10233f",
    activebackground="#dce6f2",
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
    font=("Segoe UI", 10, "bold"),
    bg="#e8eef6",
    fg="#10233f",
    activebackground="#dce6f2",
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
    font=("Segoe UI", 10, "bold"),
    bg="#e8eef6",
    fg="#10233f",
    activebackground="#dce6f2",
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
    font=("Segoe UI", 10, "bold"),
    bg="#e8eef6",
    fg="#10233f",
    activebackground="#dce6f2",
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
    font=("Segoe UI", 9, "bold"),
    fg="#4ade80",
    bg="#f4f7fb"
)
status_label.pack(side="right", pady=10)

# ---------- PROFESSIONAL BUTTON HOVER ----------

def add_hover_effect(button, normal_bg, hover_bg):
    button.bind(
        "<Enter>",
        lambda event: button.config(bg=hover_bg)
        if button.cget("state") != "disabled" else None
    )
    button.bind(
        "<Leave>",
        lambda event: button.config(bg=normal_bg)
        if button.cget("state") != "disabled" else None
    )


for widget in (
    copy_button,
    save_button,
    history_button,
    new_chat_button
):
    add_hover_effect(widget, "#e8eef6", "#d5e2f0")

add_hover_effect(ask_button, "#2563eb", "#3b82f6")


# ---------- RESULTS PANEL ----------
results_frame = tk.Frame(
    root,
    bg="#ffffff",
    highlightbackground="#d8e1ec",
    highlightthickness=1
)
results_frame.pack(
    fill="both",
    expand=True,
    padx=36,
    pady=(0, 18)
)

results_title = tk.Label(
    results_frame,
    text="AI RESPONSE",
    font=("Arial", 12, "bold"),
    fg="#10233f",
    bg="#ffffff"
)
results_title.pack(anchor="w", padx=18, pady=(14, 5))

results = scrolledtext.ScrolledText(
    results_frame,
    wrap="word",
    font=("Segoe UI", 11),
    bg="#ffffff",
    fg="#172b4d",
    insertbackground="#2563eb",
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


