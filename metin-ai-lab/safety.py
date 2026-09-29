from datetime import datetime


class SafetyManager:
    """
    Metin AI Lab - Agent Safety Layer

    Responsibilities:
    - Decide which actions are allowed.
    - Require human approval for sensitive actions.
    - Record security events.
    - Provide an emergency kill switch.
    """

    SAFE_ACTIONS = {
        "ask_model",
        "read_local_text",
        "generate_answer",
    }

    APPROVAL_REQUIRED = {
        "write_file",
        "delete_file",
        "run_command",
        "network_request",
        "send_message",
        "install_package",
    }

    def __init__(self):
        self.killed = False
        self.audit_log = []

    def log(self, action, decision, details=""):
        event = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "decision": decision,
            "details": details,
        }

        self.audit_log.append(event)
        return event

    def check_action(self, action):
        if self.killed:
            self.log(action, "BLOCKED", "Kill switch active")
            return {
                "allowed": False,
                "approval_required": False,
                "reason": "Agent system is disabled by kill switch.",
            }

        if action in self.SAFE_ACTIONS:
            self.log(action, "ALLOWED")
            return {
                "allowed": True,
                "approval_required": False,
                "reason": "Safe action.",
            }

        if action in self.APPROVAL_REQUIRED:
            self.log(action, "WAITING_APPROVAL")
            return {
                "allowed": False,
                "approval_required": True,
                "reason": "Human approval required.",
            }

        self.log(action, "BLOCKED", "Unknown action")
        return {
            "allowed": False,
            "approval_required": False,
            "reason": "Unknown action blocked by default.",
        }

    def activate_kill_switch(self):
        self.killed = True
        self.log("SYSTEM", "KILL_SWITCH_ON")

    def reset_kill_switch(self):
        self.killed = False
        self.log("SYSTEM", "KILL_SWITCH_OFF")

    def get_audit_log(self):
        return list(self.audit_log)


safety_manager = SafetyManager()
