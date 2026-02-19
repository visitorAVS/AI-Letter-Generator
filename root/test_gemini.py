#!/usr/bin/env python3
"""
Test Gemini API Configuration
Run this to verify your API key and setup
"""

from dotenv import load_dotenv
import os
import sys

print("\n" + "="*60)
print("🧪 GEMINI API TEST")
print("="*60 + "\n")

# Step 1: Load .env
print("1️⃣  Loading .env file...")
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("   ❌ GEMINI_API_KEY not found in .env")
    print("   ℹ️  Make sure you have:")
    print("       GEMINI_API_KEY=your_key_here")
    sys.exit(1)

print(f"   ✅ API Key loaded: {api_key[:20]}...")

# Step 2: Import library
print("\n2️⃣  Importing google.generativeai...")
try:
    import google.generativeai as genai
    print("   ✅ Library imported successfully")
except ImportError:
    print("   ❌ google.generativeai not installed")
    print("   💡 Run: pip install google-generativeai==0.3.0")
    sys.exit(1)

# Step 3: Configure API
print("\n3️⃣  Configuring API...")
try:
    genai.configure(api_key=api_key)
    print("   ✅ API configured")
except Exception as e:
    print(f"   ❌ Configuration failed: {e}")
    sys.exit(1)

# Step 4: Initialize model
print("\n4️⃣  Loading gemini-1.5-flash model...")
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("   ✅ Model loaded")
except Exception as e:
    print(f"   ❌ Model load failed: {e}")
    sys.exit(1)

# Step 5: Test generation
print("\n5️⃣  Testing content generation...")
try:
    response = model.generate_content("Write a 2-line greeting.")
    if response and response.text:
        print("   ✅ Generation successful!")
        print(f"   Response: {response.text[:100]}...")
    else:
        print("   ⚠️  Empty response")
except Exception as e:
    error_str = str(e).lower()
    print(f"   ❌ Generation failed: {e}")
    
    if "quota" in error_str or "resource exhausted" in error_str:
        print("   💡 Rate limited. Wait 1 minute and try again.")
    elif "api key" in error_str or "authentication" in error_str:
        print("   💡 Invalid API key. Create a new one at:")
        print("      https://aistudio.google.com/apikey")
    elif "not found" in error_str or "not available" in error_str:
        print("   💡 Model not available. Try different model:")
        print("      - gemini-1.5-pro")
        print("      - gemini-pro")
    sys.exit(1)

# Step 6: Success
print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
print("\n🚀 Your setup is ready. Run:")
print("   python app.py")
print("\nThen open: http://localhost:5000\n")