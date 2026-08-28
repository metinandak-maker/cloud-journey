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

print("=" * 50)
print("              METIN AI LAB")
print("=" * 50)

question = input("\nASK THE COUNCIL:\n> ")

print("\nThinking...\n")

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
        max_tokens=600,
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

print("\n" + "=" * 50)

print("\nATLAS:\n")
print(atlas_answer)

print("\n" + "-" * 50)

print("\nCLAUDE:\n")
print(claude_answer)

print("\n" + "-" * 50)

print("\nGROK:\n")
print(grok_answer)

print("\n" + "=" * 50)
