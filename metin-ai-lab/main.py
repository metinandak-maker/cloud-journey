import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

print("=" * 35)
print("         METIN AI LAB")
print("=" * 35)

try:
    response = client.responses.create(
        model="gpt-5.6",
        input="Reply with exactly: Atlas connected to METIN AI LAB."
    )

    print("Atlas :", response.output_text)

except Exception as error:
    print("Atlas : CONNECTION ERROR")
    print(error)

print("Claude: waiting")
print("Grok  : waiting")
print("=" * 35)
