"""Shared Council engine. SDK clients are created only when requested."""
import os
import math
from time import monotonic
from request_state import cancellable
from safety import safety_manager
from project_context import project_prompt


class ModelError(Exception):
    """A failed operation, never model-generated answer text."""
    def __init__(self, provider, code, message, diagnostics=None):
        self.provider = provider
        self.code = code
        self.diagnostics = diagnostics or {}
        super().__init__(f"{provider}: {message}")


PROVIDERS = {
    "ATLAS": ("OPENAI_API_KEY", "ATLAS_MODEL", "gpt-5.6"),
    "CLAUDE": ("ANTHROPIC_API_KEY", "CLAUDE_MODEL", "claude-sonnet-5"),
    "GROK": ("XAI_API_KEY", "GROK_MODEL", "grok-4.6"),
}


def configuration(provider):
    # dotenv is optional when credentials are supplied through the environment.
    try:
        from dotenv import load_dotenv
    except ImportError:
        pass
    else:
        load_dotenv()
    key_name, model_name, default_model = PROVIDERS[provider]
    key = os.getenv(key_name, "").strip()
    if not key:
        raise ModelError(provider, "configuration", f"Set {key_name} before using this mode.")
    model = os.getenv(model_name, default_model).strip()
    try:
        timeout = float(os.getenv("AI_TIMEOUT_SECONDS", "60"))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError()
    except ValueError:
        raise ModelError(provider, "configuration", "AI_TIMEOUT_SECONDS must be a positive finite number.") from None
    if not model:
        raise ModelError(provider, "configuration", f"{model_name} cannot be empty.")
    if provider == "CLAUDE":
        claude_max_tokens()  # Council preflight must fail before any provider spends.
    return key, model, timeout


def claude_max_tokens():
    try:
        value = int(os.getenv("CLAUDE_MAX_TOKENS", "1600"))
        if not 1 <= value <= 128000:
            raise ValueError()
        return value
    except ValueError:
        raise ModelError("CLAUDE", "configuration",
                         "CLAUDE_MAX_TOKENS must be an integer from 1 to 128000.") from None


def parse_claude_response(response, max_tokens):
    """Only fixed enums and numeric counts may enter diagnostics; never raw blocks."""
    reasons = {"end_turn", "max_tokens", "stop_sequence", "tool_use", "pause_turn",
               "refusal", "model_context_window_exceeded"}
    reason = getattr(response, "stop_reason", None)
    reason = reason if isinstance(reason, str) and reason in reasons else "unknown"
    content = getattr(response, "content", None)
    content = content if isinstance(content, (list, tuple)) else []
    known_types = {"text", "thinking", "redacted_thinking", "tool_use", "server_tool_use"}
    counts = {}
    texts = []
    for block in content:
        kind = getattr(block, "type", None)
        kind = kind if isinstance(kind, str) and kind in known_types else "other"
        counts[kind] = counts.get(kind, 0) + 1
        if kind == "text":
            text = getattr(block, "text", None)
            if isinstance(text, str) and text.strip():
                texts.append(text)
    usage = getattr(response, "usage", None)
    diagnostics = {"stop_reason": reason, "block_counts": counts, "max_tokens": max_tokens}
    for name in ("input_tokens", "output_tokens"):
        value = getattr(usage, name, None)
        if type(value) is int and value >= 0:
            diagnostics[name] = value
    summary = "; ".join(f"{key}={value}" for key, value in diagnostics.items())
    if reason == "max_tokens":
        code, message = "token_limit", "Output token limit reached; answer is incomplete. Consider CLAUDE_MAX_TOKENS or a shorter request."
    elif reason == "model_context_window_exceeded":
        code, message = "context_limit", "Context window limit reached; shorten the request."
    elif reason == "refusal":
        code, message = "refusal", "Provider declined this request."
    elif reason not in {"end_turn", "stop_sequence"}:
        code, message = "incomplete_response", "Provider did not complete a text answer. No automatic continuation was attempted."
    elif not texts:
        code, message = "empty_response", "Provider returned no text. No automatic retry was attempted."
    else:
        return "\n".join(texts)
    raise ModelError("CLAUDE", code, f"{message} Diagnostics: {summary}", diagnostics)


def make_client(provider, key, timeout):
    try:
        if provider == "CLAUDE":
            from anthropic import Anthropic
            return Anthropic(api_key=key, timeout=timeout, max_retries=0)
        from openai import OpenAI
        options = {"api_key": key, "timeout": timeout, "max_retries": 0}
        if provider == "GROK":
            options["base_url"] = "https://api.x.ai/v1"
        return OpenAI(**options)
    except ImportError:
        raise ModelError(provider, "configuration", "Required provider SDK is not installed.") from None


@cancellable
def ask_model(provider, prompt):
    try:
        check = safety_manager.check_action("ask_model")
    except OSError:
        raise ModelError(provider, "audit", "Cannot write the safety audit log; request blocked.") from None
    if not check["allowed"]:
        raise ModelError(provider, "blocked", check["reason"])
    key, model, timeout = configuration(provider)
    try:
        with make_client(provider, key, timeout) as client:
            if provider == "ATLAS":
                text = client.responses.create(model=model, input=prompt).output_text
            elif provider == "CLAUDE":
                max_tokens = claude_max_tokens()
                options = {}
                # Sonnet 5 defaults to adaptive thinking, which shares this budget.
                # Do not assume other model IDs accept the same thinking settings.
                if model == "claude-sonnet-5":
                    options["thinking"] = {"type": "disabled"}
                response = client.messages.create(
                    model=model, max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}], **options)
                text = parse_claude_response(response, max_tokens)
            else:
                response = client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": prompt}])
                text = response.choices[0].message.content
        if not isinstance(text, str) or not text.strip():
            raise ModelError(provider, "empty_response", "Provider returned no text.")
        return text
    except ModelError:
        raise
    except Exception as error:
        # Raw SDK errors can contain request data; do not display or archive them.
        status = getattr(error, "status_code", None)
        if isinstance(error, TimeoutError) or "timeout" in type(error).__name__.lower():
            code, message = "timeout", f"Request timed out (SDK timeout: {timeout:g}s; automatic retries disabled)."
        elif status in (401, 403):
            code, message = "authentication", "Check your API key and account permissions."
        elif provider == "CLAUDE" and status == 400:
            code, message = "invalid_request", "Request rejected. Check CLAUDE_MODEL, CLAUDE_MAX_TOKENS and model parameter limits."
        elif provider == "CLAUDE" and status == 404:
            code, message = "model_not_found", "Model or endpoint not found. Check CLAUDE_MODEL and account access."
        elif status == 429:
            code, message = "rate_limit", "Provider quota or rate limit reached. Try later."
        else:
            code, message = "provider_error", "Request failed. Check provider access and model configuration."
        raise ModelError(provider, code, message) from None


def ask_atlas(prompt):
    return ask_model("ATLAS", prompt)


def ask_claude(prompt):
    return ask_model("CLAUDE", prompt)


def ask_grok(prompt):
    return ask_model("GROK", prompt)


teacher_history = []
teacher_histories = {"General": teacher_history}
def ask_teacher(prompt, project="General", *, remember=True):
    # UI requests commit on the main thread only after cancellation checks.
    history = list(teacher_histories.setdefault(project, []))
    teacher_prompt = f"""
You are TEACHER MODE inside Metin AI Lab.

Teach interactively.

Rules:
1. Explain one concept at a time.
2. Give the student one small task at a time.
3. Let the student type commands or code themselves.
4. Do not immediately give the complete solution.
5. If the student makes a mistake, explain why and let them retry.
6. Ask short questions to check understanding.
7. Increase difficulty gradually.
8. When the lesson is complete, give a short summary and next step.

Previous conversation:
{chr(10).join(history)}

Student message:
{prompt}
"""

    answer = ask_atlas(teacher_prompt)
    if remember:
        teacher_histories.setdefault(project, []).append(f"Student: {prompt}\nTeacher: {answer}")
    return answer



COUNCIL_STAGES = (
    ("atlas", "ATLAS / ANALYSIS"), ("claude", "CLAUDE / ANALYSIS"),
    ("grok", "GROK / ANALYSIS"), ("atlas_review", "ATLAS / REVIEW"),
    ("claude_review", "CLAUDE / REVIEW"), ("grok_review", "GROK / REVIEW"),
    ("final", "ATLAS / FINAL"),
)


def _run_council(question, project=None, *, progress=None, partial=None):
    partial = partial if partial is not None else {}
    started = monotonic()

    def call(key, provider, prompt):
        index = next(i for i, stage in enumerate(COUNCIL_STAGES) if stage[0] == key)
        partial["stage"] = key
        if progress:
            progress({"stage": key, "label": COUNCIL_STAGES[index][1],
                      "number": index + 1, "total": 7, "started": started,
                      "stage_started": monotonic(),
                      "answers": {k: partial[k] for k, _ in COUNCIL_STAGES if k in partial}})
        answer = {"ATLAS": ask_atlas, "CLAUDE": ask_claude, "GROK": ask_grok}[provider](prompt)
        partial[key] = answer
        return answer


    if not question.strip():
        return {
            "error": "Please enter a question."
        }

    # -----------------------------
    # ROUND 1
    # -----------------------------

    # Capture evidence once, keeping all seven calls on the same project snapshot.
    contexts = {p: project_prompt(project, p, "") if project else "" for p in PROVIDERS}
    atlas_answer = call("atlas", "ATLAS", contexts["ATLAS"] + question)
    claude_answer = call("claude", "CLAUDE", contexts["CLAUDE"] + question)
    grok_answer = call("grok", "GROK", contexts["GROK"] + question)

    # -----------------------------
    # ROUND 2
    # -----------------------------

    atlas_review_prompt = f"""
Original question:

{question}

Claude answered:

{claude_answer}

Grok answered:

{grok_answer}

You are Atlas in an AI council.

Review Claude and Grok's answers.

Identify:
1. What they got right.
2. What they missed.
3. Where you disagree.
4. Your improved final position.

Be concise and practical.
"""

    claude_review_prompt = f"""
Original question:

{question}

Atlas answered:

{atlas_answer}

Grok answered:

{grok_answer}

You are Claude in an AI council.

Review Atlas and Grok's answers.

Identify:
1. What they got right.
2. What they missed.
3. Where you disagree.
4. Your improved final position.

Be concise and practical.
"""

    grok_review_prompt = f"""
Original question:

{question}

Atlas answered:

{atlas_answer}

Claude answered:

{claude_answer}

You are Grok in an AI council.

Review Atlas and Claude's answers.

Identify:
1. What they got right.
2. What they missed.
3. Where you disagree.
4. Your improved final position.

Be concise and practical.
"""

    atlas_review = call("atlas_review", "ATLAS", contexts["ATLAS"] + atlas_review_prompt)
    claude_review = call("claude_review", "CLAUDE", contexts["CLAUDE"] + claude_review_prompt)
    grok_review = call("grok_review", "GROK", contexts["GROK"] + grok_review_prompt)

    # -----------------------------
    # ROUND 3 - FINAL JUDGE
    # -----------------------------

    judge_prompt = f"""
You are the FINAL JUDGE of an AI council.

Original question:

{question}

ATLAS REVIEW:
{atlas_review}

CLAUDE REVIEW:
{claude_review}

GROK REVIEW:
{grok_review}

Analyze the debate and produce the strongest final answer.

Rules:
1. Identify where the council agrees.
2. Resolve important disagreements using reasoning.
3. Remove duplicated or weak arguments.
4. Preserve useful minority opinions where relevant.
5. Produce a practical and clear recommendation.
6. Mention important uncertainty when necessary.

Finish with:

FINAL RECOMMENDATION
"""

    final_answer = call("final", "ATLAS", contexts["ATLAS"] + judge_prompt)

    return {
        "atlas": atlas_answer,
        "claude": claude_answer,
        "grok": grok_answer,
        "atlas_review": atlas_review,
        "claude_review": claude_review,
        "grok_review": grok_review,
        "final": final_answer
    }


def run_council(question, project=None, *, progress=None):
    if not question.strip():
        return {"error": "Please enter a question.", "code": "input"}
    partial = {}
    try:
        # Validate all credentials before spending on the first round.
        for provider in PROVIDERS:
            configuration(provider)
        return _run_council(question, project, progress=progress, partial=partial)
    except ModelError as error:
        result = dict(partial, error=str(error), provider=error.provider, code=error.code)
        if error.diagnostics:
            result["diagnostics"] = error.diagnostics
        return result
