#!/usr/bin/env python3
"""
Test Gemini REST API directly (No SDK needed)
"""

from dotenv import load_dotenv
import os
import requests
import json

print("\n" + "="*70)
print("🧪 GEMINI REST API TEST")
print("="*70 + "\n")

# Step 1: Load API key
print("1️⃣  Loading API key from .env...")
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("   ❌ GEMINI_API_KEY not found")
    print("   Add to .env: GEMINI_API_KEY=your_key_here")
    exit(1)

print(f"   ✅ API Key: {api_key[:20]}...")

# Step 2: Test with each model
print("\n2️⃣  Testing available models...\n")

models_to_test = [
    "gemini-pro",
    "gemini-1.5-pro", 
    "gemini-1.5-flash",
]

api_url = "https://generativelanguage.googleapis.com/v1beta/models"

for model_name in models_to_test:
    print(f"   Testing {model_name}...")
    
    try:
        url = f"{api_url}/{model_name}:generateContent?key={api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "Say hello in one line"
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(
            url, 
            json=payload, 
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"      ✅ {model_name} is WORKING!")
            data = response.json()
            if "candidates" in data and data["candidates"]:
                reply = data["candidates"][0]["content"]["parts"][0]["text"]
                print(f"      Response: {reply[:50]}...")
            break
        elif response.status_code == 404:
            print(f"      ⚠️  {model_name} not found (404)")
        else:
            error = response.json().get("error", {}).get("message", "Unknown error")
            print(f"      ❌ {model_name}: {error[:50]}")
            
    except requests.exceptions.Timeout:
        print(f"      ⚠️  {model_name} timeout")
    except Exception as e:
        print(f"      ❌ {model_name}: {str(e)[:50]}")

print("\n" + "="*70)
print("💡 WHAT TO DO NEXT:")
print("="*70)
print("""
If one of the models worked:
1. Copy 'app_rest_api.py' to 'app.py'
2. Install: pip install Flask python-dotenv requests firebase-admin
3. Run: python app.py
4. Open: http://localhost:5000

If NO models worked:
1. Verify API key at: https://aistudio.google.com/apikey
2. Create a NEW API key
3. Update .env with the new key
4. Run this test again
""")
print("="*70 + "\n")