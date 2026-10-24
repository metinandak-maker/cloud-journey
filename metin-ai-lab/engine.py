"""Shared Council engine. SDK clients are created only when requested."""
import os
import math
from request_state import cancellable
from safety import safety_manager


class ModelError(Exception):
    """A failed operation, never model-generated answer text."""
    def __init__(self, provider, code, message):
        self.provider = provider
        self.code = code
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
    return key, model, timeout


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
                response = client.messages.create(
                    model=model, max_tokens=1600,
                    messages=[{"role": "user", "content": prompt}])
                text = "\n".join(block.text for block in response.content if block.type == "text")
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
            code, message = "timeout", "Request timed out. Please retry."
        elif status in (401, 403):
            code, message = "authentication", "Check your API key and account permissions."
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
def ask_teacher(prompt):
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
{chr(10).join(teacher_history)}

Student message:
{prompt}
"""

    answer = ask_atlas(teacher_prompt)
    teacher_history.append(f"Student: {prompt}\nTeacher: {answer}")
    return answer



def _run_council(question):

    if not question.strip():
        return {
            "error": "Please enter a question."
        }

    # -----------------------------
    # ROUND 1
    # -----------------------------

    atlas_answer = ask_atlas(question)
    claude_answer = ask_claude(question)
    grok_answer = ask_grok(question)

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

    atlas_review = ask_atlas(atlas_review_prompt)
    claude_review = ask_claude(claude_review_prompt)
    grok_review = ask_grok(grok_review_prompt)

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

    final_answer = ask_atlas(judge_prompt)

    return {
        "atlas": atlas_answer,
        "claude": claude_answer,
        "grok": grok_answer,
        "atlas_review": atlas_review,
        "claude_review": claude_review,
        "grok_review": grok_review,
        "final": final_answer
    }


def run_council(question):
    if not question.strip():
        return {"error": "Please enter a question.", "code": "input"}
    try:
        # Validate all credentials before spending on the first round.
        for provider in PROVIDERS:
            configuration(provider)
        return _run_council(question)
    except ModelError as error:
        return {"error": str(error), "provider": error.provider, "code": error.code}
