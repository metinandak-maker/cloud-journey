"""Local Teacher sessions. No SDK calls; each write atomically replaces a snapshot.

Use one running AI Lab instance per OS account. Paths follow the existing Council
history convention, so Windows Python and WSL Python have separate home folders.
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

from project_context import history_path


class TeacherHistoryError(Exception):
    pass


def teacher_path(project):
    return history_path(project).with_name("teacher_sessions.json")


def _load(project):
    path = teacher_path(project)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"version": 1, "project": project, "active_id": None, "sessions": []}
    except (ValueError, UnicodeError) as error:
        raise TeacherHistoryError("Teacher history is unreadable; the existing file was preserved.") from error
    if not isinstance(data, dict) or data.get("version") != 1 or data.get("project") != project:
        raise TeacherHistoryError("Teacher history format is invalid; the file was preserved.")
    sessions = data.get("sessions")
    if not isinstance(sessions, list):
        raise TeacherHistoryError("Teacher session list is invalid.")
    ids = set()
    for session in sessions:
        if (not isinstance(session, dict) or not isinstance(session.get("id"), str)
                or session["id"] in ids or not isinstance(session.get("created"), str)
                or not isinstance(session.get("turns"), list)
                or not all(isinstance(turn, str) for turn in session["turns"])):
            raise TeacherHistoryError("Teacher session data is invalid; the file was preserved.")
        ids.add(session["id"])
    if "active_id" not in data or (data["active_id"] is not None and data["active_id"] not in ids):
        raise TeacherHistoryError("Teacher active session is invalid.")
    return data


def _write(project, data):
    path = teacher_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".teacher-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_active_history(project):
    data = _load(project)
    for session in data["sessions"]:
        if session["id"] == data["active_id"]:
            return list(session["turns"])
    return []


def save_teacher_history(project, turns):
    """Save the entire active lesson, including turns retained after a write failure."""
    if not isinstance(turns, list) or not all(isinstance(turn, str) for turn in turns):
        raise ValueError("Teacher turns must be a list of strings")
    data = _load(project)
    session = next((s for s in data["sessions"] if s["id"] == data["active_id"]), None)
    if session is None:
        session = {"id": uuid4().hex, "created": datetime.now(timezone.utc).isoformat(), "turns": []}
        data["sessions"].append(session)
        data["active_id"] = session["id"]
    session["turns"] = list(turns)
    _write(project, data)


def start_new_lesson(project, current_turns):
    # Save first. If either write fails, the caller must keep its in-memory lesson.
    if current_turns:
        save_teacher_history(project, current_turns)
    data = _load(project)
    data["active_id"] = None
    _write(project, data)


def list_teacher_sessions(project):
    return list(reversed(_load(project)["sessions"]))


def resume_teacher_session(project, session_id):
    data = _load(project)
    session = next((s for s in data["sessions"] if s["id"] == session_id), None)
    if session is None:
        raise TeacherHistoryError("The selected lesson was not found.")
    data["active_id"] = session_id
    _write(project, data)
    return list(session["turns"])


def format_teacher_history(project, turns):
    return f"TEACHER — {project}\n\n" + "\n\n".join(turns)
