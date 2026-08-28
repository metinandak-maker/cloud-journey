import os
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic

load_dotenv()

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

anthropic_client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

grok_client = OpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1"
)


def ask_atlas(prompt):
    try:
        response = openai_client.responses.create(
            model="gpt-5.6",
            input=prompt
        )
        return response.output_text

    except Exception as error:
        return f"ATLAS ERROR: {error}"


def ask_claude(prompt):
    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1600,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        text_parts = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)

        if not text_parts:
            return "CLAUDE ERROR: No text response returned."

        return "\n".join(text_parts)

    except Exception as error:
        return f"CLAUDE ERROR: {error}"


def ask_grok(prompt):
    try:
        response = grok_client.chat.completions.create(
            model="grok-4.6",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as error:
        return f"GROK ERROR: {error}"


def run_council(question):

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
