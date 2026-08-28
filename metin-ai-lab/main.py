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

print("=" * 35)
print("         METIN AI LAB")
print("=" * 35)

try:
    response = openai_client.responses.create(
        model="gpt-5.6",
        input="Reply with exactly: Atlas connected to METIN AI LAB."
    )
    print("Atlas :", response.output_text)

except Exception as error:
    print("Atlas : CONNECTION ERROR")
    print(error)

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

print("Grok  : waiting")
print("=" * 35)
