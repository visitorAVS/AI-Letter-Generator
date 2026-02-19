#!/usr/bin/env python3
"""
List all ACTUAL models available to your API key
This shows the REAL model names you can use
"""

import os
import requests
import json
from dotenv import load_dotenv

print("\n" + "="*80)
print("📋 LISTING ALL AVAILABLE MODELS")
print("="*80 + "\n")

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("❌ No API key found")
    exit(1)

print(f"API Key: {api_key[:20]}...\n")

try:
    # Call the listModels endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    print("Fetching models from Google API...\n")
    response = requests.get(url, timeout=10)
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.json())
        exit(1)
    
    data = response.json()
    
    if "models" not in data:
        print("❌ No models found in response")
        print(json.dumps(data, indent=2))
        exit(1)
    
    models = data["models"]
    print(f"✅ Found {len(models)} total models\n")
    
    print("="*80)
    print("MODELS THAT SUPPORT generateContent:")
    print("="*80 + "\n")
    
    working_models = []
    
    for model in models:
        name = model.get("name", "unknown").replace("models/", "")
        
        # Check if it supports generateContent
        methods = model.get("supportedGenerationMethods", [])
        
        # Handle both string and dict formats
        if methods:
            if isinstance(methods[0], dict):
                method_names = [m.get("name", "") for m in methods]
            else:
                method_names = methods
        else:
            method_names = []
        
        supports_generate = "generateContent" in method_names
        
        if supports_generate:
            print(f"✅ {name}")
            working_models.append(name)
            
            # Show details
            version = model.get("version", "unknown")
            input_tokens = model.get("inputTokenLimit", "unknown")
            print(f"   Version: {version}")
            print(f"   Max Input: {input_tokens} tokens")
            print()
    
    print("="*80)
    print(f"TOTAL WORKING MODELS: {len(working_models)}")
    print("="*80 + "\n")
    
    if working_models:
        print("✅ SUCCESS! Use one of these models:\n")
        
        # Sort by name
        working_models.sort()
        for i, model in enumerate(working_models, 1):
            print(f"{i}. {model}")
        
        print(f"\n💡 RECOMMENDED: {working_models[0]}")
        print(f"\nUpdate your app_rest_api.py to use:\n")
        print(f'   model_name = "{working_models[0]}"\n')
    else:
        print("❌ No working models found!")
        print("\nThis means:")
        print("1. API key might still be invalid")
        print("2. You might not have proper permissions")
        print("3. Try creating another API key\n")
    
    # Also show all models for reference
    print("\n" + "="*80)
    print("ALL AVAILABLE MODELS (including unsupported ones):")
    print("="*80 + "\n")
    
    for model in models:
        name = model.get("name", "unknown").replace("models/", "")
        methods = model.get("supportedGenerationMethods", [])
        
        if methods:
            if isinstance(methods[0], dict):
                method_names = [m.get("name", "") for m in methods]
            else:
                method_names = methods
        else:
            method_names = []
        
        supports = "generateContent" in method_names
        status = "✅" if supports else "⚠️"
        print(f"{status} {name}")
        print(f"   Methods: {', '.join(method_names)}")
        print()

except requests.exceptions.Timeout:
    print("❌ Request timeout - check internet connection")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("="*80 + "\n")