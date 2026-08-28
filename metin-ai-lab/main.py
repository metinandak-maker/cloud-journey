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

print("=" * 60)
print("                 METIN AI LAB")
print("               BRAINSTORM V2")
print("=" * 60)

question = input("\nASK THE COUNCIL:\n> ").strip()

if not question:
    print("No question entered.")
    raise SystemExit

print("\nROUND 1: Independent thinking...\n")

# -----------------------------
# ROUND 1
# -----------------------------

# ATLAS
try:
    atlas_response = openai_client.responses.create(
        model="gpt-5.6",
        input=question
    )
    atlas_answer = atlas_response.output_text

except Exception as error:
    atlas_answer = f"CONNECTION ERROR: {error}"

# CLAUDE
try:
    claude_response = anthropic_client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": question
            }
        ]
    )
    claude_answer = claude_response.content[0].text

except Exception as error:
    claude_answer = f"CONNECTION ERROR: {error}"

# GROK
try:
    grok_response = grok_client.chat.completions.create(
        model="grok-4.6",
        messages=[
            {
                "role": "user",
                "content": question
            }
        ]
    )
    grok_answer = grok_response.choices[0].message.content

except Exception as error:
    grok_answer = f"CONNECTION ERROR: {error}"

print("\n" + "=" * 60)
print("ROUND 1 RESULTS")
print("=" * 60)

print("\nATLAS:\n")
print(atlas_answer)

print("\n" + "-" * 60)

print("\nCLAUDE:\n")
print(claude_answer)

print("\n" + "-" * 60)

print("\nGROK:\n")
print(grok_answer)

# -----------------------------
# ROUND 2
# -----------------------------

print("\n" + "=" * 60)
print("ROUND 2: Cross-evaluation...")
print("=" * 60)

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

# ATLAS REVIEW
try:
    atlas_review_response = openai_client.responses.create(
        model="gpt-5.6",
        input=atlas_review_prompt
    )
    atlas_review = atlas_review_response.output_text

except Exception as error:
    atlas_review = f"CONNECTION ERROR: {error}"

# CLAUDE REVIEW
try:
    claude_review_response = anthropic_client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1200,
        messages=[
            {
                "role": "user",
                "content": claude_review_prompt
            }
        ]
    )
    claude_review = claude_review_response.content[0].text

except Exception as error:
    claude_review = f"CONNECTION ERROR: {error}"

# GROK REVIEW
try:
    grok_review_response = grok_client.chat.completions.create(
        model="grok-4.6",
        messages=[
            {
                "role": "user",
                "content": grok_review_prompt
            }
        ]
    )
    grok_review = grok_review_response.choices[0].message.content

except Exception as error:
    grok_review = f"CONNECTION ERROR: {error}"

print("\n" + "=" * 60)
print("ROUND 2 RESULTS")
print("=" * 60)

print("\nATLAS REVIEW:\n")
print(atlas_review)

print("\n" + "-" * 60)

print("\nCLAUDE REVIEW:\n")
print(claude_review)

print("\n" + "-" * 60)

print("\nGROK REVIEW:\n")
print(grok_review)

print("\n" + "=" * 60)
print("BRAINSTORM V2 COMPLETE")
print("=" * 60)
# -----------------------------
# ROUND 3 - FINAL JUDGE
# -----------------------------

print("\n" + "=" * 60)
print("ROUND 3: Final Council Judgment...")
print("=" * 60)

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

Your task is NOT to simply summarize the three reviews.

Analyze the council debate and produce the strongest final answer.

Rules:
1. Identify where the council agrees.
2. Resolve important disagreements using reasoning.
3. Remove weak, duplicated, or unsupported arguments.
4. Preserve useful minority opinions when relevant.
5. Produce a practical and clear final recommendation.
6. Clearly mention important uncertainty if the council cannot resolve it.

Finish with a section called:
FINAL RECOMMENDATION
"""

try:
    judge_response = openai_client.responses.create(
        model="gpt-5.6",
        input=judge_prompt
    )

    final_answer = judge_response.output_text

except Exception as error:
    final_answer = f"JUDGE ERROR: {error}"

print("\n" + "=" * 60)
print("              COUNCIL FINAL ANSWER")
print("=" * 60)

print("\n")
print(final_answer)

print("\n" + "=" * 60)
print("BRAINSTORM V3 COMPLETE")
print("=" * 60)
