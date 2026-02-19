#!/usr/bin/env python3
"""
Deep API Diagnostic Tool
Checks actual API permissions and quotas
"""

import os
import requests
import json
from dotenv import load_dotenv

print("\n" + "="*80)
print("🔬 DEEP API DIAGNOSTIC TOOL")
print("="*80 + "\n")

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("❌ No API key found in .env")
    exit(1)

print(f"API Key: {api_key[:25]}...\n")

# Test 1: Check if API key is valid at all
print("TEST 1: Validating API key format...")
print("─" * 80)

try:
    # Try to list models - this works if key is valid
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    response = requests.get(url, timeout=10)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ API Key is VALID")
        data = response.json()
        
        if "models" in data:
            print(f"✅ Found {len(data['models'])} models available:\n")
            for model in data['models']:
                model_name = model.get('name', 'Unknown').replace('models/', '')
                methods = [m.get('name', '') for m in model.get('supportedGenerationMethods', [])]
                print(f"   • {model_name}")
                print(f"     Methods: {', '.join(methods)}")
                print()
        else:
            print("⚠️  No models in response")
            print(json.dumps(data, indent=2))
    
    elif response.status_code == 400:
        print("❌ BAD REQUEST")
        print(json.dumps(response.json(), indent=2))
        print("\n💡 Possible issues:")
        print("   - API key format is wrong")
        print("   - API key is corrupted")
        print("   - There are extra spaces in .env")
    
    elif response.status_code == 401:
        print("❌ UNAUTHORIZED - API Key is invalid")
        print(json.dumps(response.json(), indent=2))
        print("\n💡 This means:")
        print("   - API key is wrong/expired/revoked")
        print("   - You need a NEW API key")
    
    elif response.status_code == 403:
        print("❌ FORBIDDEN - No permission to use API")
        print(json.dumps(response.json(), indent=2))
        print("\n💡 This means:")
        print("   - Generative Language API is NOT enabled")
        print("   - You need to enable it in Google Cloud Console")
    
    elif response.status_code == 404:
        print("⚠️  Not found - API endpoint issue")
        print(json.dumps(response.json(), indent=2))
    
    elif response.status_code == 429:
        print("⚠️  RATE LIMITED - Too many requests")
        print("   Wait a few minutes and try again")
    
    else:
        print(f"❌ Unexpected error: {response.status_code}")
        print(response.text)

except requests.exceptions.Timeout:
    print("❌ REQUEST TIMEOUT")
    print("   - Check your internet connection")
    print("   - Check if firewall is blocking requests")

except Exception as e:
    print(f"❌ ERROR: {e}")

# Test 2: Try a simpler endpoint
print("\n" + "="*80)
print("TEST 2: Testing basic connectivity...")
print("─" * 80)

try:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": "Hi"
            }]
        }]
    }
    
    response = requests.post(
        f"{url}?key={api_key}",
        json=payload,
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ API is working!")
    else:
        error_info = response.json() if response.text else {}
        error_msg = error_info.get("error", {}).get("message", response.text)
        print(f"❌ Error: {error_msg}")
        
        if "API" in error_msg and "not enabled" in error_msg:
            print("\n🚨 SOLUTION REQUIRED:")
            print("The Generative Language API is NOT enabled!")
            print("\nFollow these steps:")
            print("1. Go to: https://console.cloud.google.com/apis/library")
            print("2. Search for 'Generative Language API'")
            print("3. Click it and press 'ENABLE'")
            print("4. Wait 1-2 minutes")
            print("5. Run this test again")

except Exception as e:
    print(f"❌ Connection error: {e}")

# Test 3: Check .env file directly
print("\n" + "="*80)
print("TEST 3: Checking .env file...")
print("─" * 80)

if os.path.exists(".env"):
    with open(".env", "r") as f:
        content = f.read()
        lines = content.split("\n")
        
    print("✅ .env file found")
    print("\nContent:")
    for line in lines:
        if line.strip() and not line.startswith("#"):
            key, value = (line.split("=", 1) if "=" in line else (line, "???"))
            masked_value = value[:20] + "..." if len(value) > 20 else value
            print(f"   {key}={masked_value}")
            
            if key == "GEMINI_API_KEY":
                if value.startswith("AIzaSy"):
                    print(f"   ✅ Format looks correct")
                else:
                    print(f"   ❌ Format looks WRONG - should start with AIzaSy")
else:
    print("❌ .env file not found!")

# Test 4: Recommendation
print("\n" + "="*80)
print("💡 RECOMMENDED ACTION")
print("="*80)

print("""
Based on the results above, here's what to do:

OPTION 1: Enable the API (Most Likely Solution)
─────────────────────────────────────────────────
If you see "API is not enabled" error:

1. Go to: https://console.cloud.google.com/apis/library
2. Search for "Generative Language API"
3. Click and press "ENABLE"
4. Wait 1-2 minutes for it to activate
5. Run this diagnostic again

Then your API key should work!


OPTION 2: Get a Fresh API Key
──────────────────────────────
If the API is enabled but still doesn't work:

1. Go to: https://aistudio.google.com/apikey
2. Delete your old API key
3. Click "Create API Key"
4. Copy the NEW key
5. Replace in .env file
6. Run this diagnostic again


OPTION 3: Use Google Cloud Console
───────────────────────────────────
If neither works above:

1. Go to: https://console.cloud.google.com
2. Create a NEW project
3. Enable "Generative Language API"
4. Create API key from there
5. Use that new key


⚠️  IMPORTANT: Make sure your .env file has NO EXTRA SPACES!
   Correct:   GEMINI_API_KEY=AIzaSyCeviqt5vwtBpnMOtc66JRggbygrOrAy8Q
   Wrong:     GEMINI_API_KEY = AIzaSyCeviqt5vwtBpnMOtc66JRggbygrOrAy8Q (spaces!)
""")

print("="*80 + "\n")