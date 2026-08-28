import os
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic

load_dotenv()

# Atlas / OpenAI
openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# Claude / Anthropic
anthropic_client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Grok / xAI
grok_client = OpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1"
)

print("=" * 40)
print("           METIN AI LAB")
print("=" * 40)

# ATLAS
try:
    response = openai_client.responses.create(
        model="gpt-5.6",
        input="Reply with exactly: Atlas connected to METIN AI LAB."
    )
    print("Atlas :", response.output_text)

except Exception as error:
    print("Atlas : CONNECTION ERROR")
    print(error)

# CLAUDE
try:
    message = anthropic_client.messages.create(
        model="claude-sonnet-5",
        max_tokens=50,
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: Claude connected to METIN AI LAB."
            }
        ]
    )
    print("Claude:", message.content[0].text)

except Exception as error:
    print("Claude: CONNECTION ERROR")
    print(error)

# GROK
try:
    response = grok_client.chat.completions.create(
        model="grok-4.6",
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: Grok connected to METIN AI LAB."
            }
        ]
    )
    print("Grok  :", response.choices[0].message.content)

except Exception as error:
    print("Grok  : CONNECTION ERROR")
    print(error)

print("=" * 40)
