from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
print(f"Testing with key: {api_key[:20]}...")

try:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say hi"}],
        max_tokens=10
    )
    print("✅ SUCCESS! OpenAI is working!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ ERROR: {e}")