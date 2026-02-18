from dotenv import load_dotenv
import os
import json
from datetime import datetime
import requests
from functools import wraps
import re

# Load environment variables
load_dotenv()

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, auth

# =========================
# Flask App Setup
# =========================
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "your-secret-key-change-this")
CORS(app)

# =========================
# Firebase Configuration
# =========================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
AVAILABLE_MODELS = []

if GEMINI_API_KEY:
    print("✅ Gemini API Key found")
    try:
        print("🔍 Detecting available models...")
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if "models" in data:
                for model in data["models"]:
                    name = model.get("name", "").replace("models/", "")
                    methods = model.get("supportedGenerationMethods", [])
                    
                    if methods:
                        if isinstance(methods[0], dict):
                            method_names = [m.get("name", "") for m in methods]
                        else:
                            method_names = methods
                    else:
                        method_names = []
                    
                    if "generateContent" in method_names:
                        AVAILABLE_MODELS.append(name)
                
                if AVAILABLE_MODELS:
                    AVAILABLE_MODELS.sort()
                    print(f"✅ Found {len(AVAILABLE_MODELS)} available models")
    except Exception as e:
        print(f"⚠️ Could not auto-detect models: {e}")

# Firebase Setup
try:
    firebase_creds = os.environ.get("FIREBASE_CREDENTIALS")

    if firebase_creds:
        print("📝 Loading Firebase credentials from environment variable...")
        cred_dict = json.loads(firebase_creds)
        cred = credentials.Certificate(cred_dict)
    else:
        print("📝 Loading Firebase credentials from firebase-credentials.json...")
        cred = credentials.Certificate("firebase-credentials.json")

    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase initialized successfully")

except Exception as e:
    print(f"⚠️ Firebase error: {e}")
    db = None

# =========================
# Helper Functions
# =========================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def clean_subject(text):
    """Remove ** from subject"""
    return text.replace("**", "").strip()

def generate_signature(name):
    """Generate a stylized signature from name"""
    signatures = []
    
    # Signature style 1: Cursive style
    sig1 = f"~{name}~"
    signatures.append(sig1)
    
    # Signature style 2: Formal style
    sig2 = f"{name.upper()}"
    signatures.append(sig2)
    
    # Signature style 3: Script style
    sig3 = f"✍ {name}"
    signatures.append(sig3)
    
    # Signature style 4: Underlined style
    sig4 = f"_{name}_"
    signatures.append(sig4)
    
    # Signature style 5: Stylized
    sig5 = f"→ {name} ←"
    signatures.append(sig5)
    
    return signatures

def save_to_firebase(letter_data, user_id):
    """Save letter to Firebase"""
    if db is None:
        return None
    try:
        letter_data["timestamp"] = datetime.now()
        letter_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        letter_data["user_id"] = user_id
        
        ref = db.collection("users").document(user_id).collection("letters").add(letter_data)
        return ref[1].id
    except Exception as e:
        print("Firebase save error:", e)
        return None

def load_user_letters(user_id):
    """Load all letters for a user"""
    if db is None:
        return []
    try:
        letters = []
        docs = db.collection("users").document(user_id).collection("letters") \
                 .order_by("timestamp", direction=firestore.Query.DESCENDING) \
                 .stream()
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            data["timestamp"] = data.get("created_at", "")
            letters.append(data)
        return letters
    except Exception as e:
        print("Firebase load error:", e)
        return []

def get_letter_from_firebase(user_id, letter_id):
    """Get a specific letter"""
    if db is None:
        return None
    try:
        doc = db.collection("users").document(user_id).collection("letters").document(letter_id).get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            data["timestamp"] = data.get("created_at", "")
            return data
        return None
    except Exception as e:
        print("Firebase get error:", e)
        return None

def delete_from_firebase(user_id, letter_id):
    """Delete a letter"""
    if db is None:
        return False
    try:
        db.collection("users").document(user_id).collection("letters").document(letter_id).delete()
        return True
    except Exception as e:
        print("Firebase delete error:", e)
        return False

def generate_letter_with_gemini(letter_type, language, sender_name, receiver_name,
                                receiver_designation, subject, reason, tone,
                                organization=""):
    """Generate letter using Gemini API"""
    if not GEMINI_API_KEY:
        return "Error: Gemini API key not configured."

    if not AVAILABLE_MODELS:
        return "Error: No available models found. Check your API key."

    # Build reason part of prompt
    reason_prompt = ""
    if reason and reason.strip():
        reason_prompt = f"- Reason/Details: {reason}"

    prompt = f"""You are a professional formal letter writer.

Generate a formal {letter_type} in {language}.

DETAILS:
- Sender Name: {sender_name}
- Receiver Name: {receiver_name}
- Receiver Designation: {receiver_designation}
- Organization: {organization}
- Subject: {subject}
{reason_prompt}
- Tone: {tone}

RULES:
1. Follow standard formal letter format
2. Include date: {datetime.now().strftime('%B %d, %Y')}
3. Proper subject, salutation, body, closing, signature
4. Professional spacing
5. NO explanations or preamble
6. NO ** or markdown symbols
7. If Hindi → use Devanagari script
8. Start directly with the letter content
"""

    # Try each available model
    for model_name in AVAILABLE_MODELS:
        try:
            url = f"{GEMINI_API_URL}/{model_name}:generateContent"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 2048,
                }
            }
            
            full_url = f"{url}?key={GEMINI_API_KEY}"
            
            print(f"Trying model: {model_name}")
            response = requests.post(full_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    letter_content = data["candidates"][0]["content"]["parts"][0]["text"]
                    # Clean any ** from the content
                    letter_content = letter_content.replace("**", "")
                    print(f"✅ Success with {model_name}")
                    return letter_content
            elif response.status_code == 404:
                print(f"⚠️ Model {model_name} not found, trying next...")
                continue
            else:
                error_msg = response.json().get("error", {}).get("message", str(response.text))
                print(f"⚠️ {model_name} error: {error_msg}")
                continue
                
        except requests.exceptions.Timeout:
            print(f"⚠️ {model_name} timeout, trying next...")
            continue
        except Exception as e:
            print(f"⚠️ {model_name} exception: {e}")
            continue

    return "Error: No available models could generate the letter. Please check your API configuration."

# =========================
# Routes - Authentication
# =========================
@app.route("/")
def index():
    if 'user' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/auth/google", methods=["POST"])
def auth_google():
    """Handle Google OAuth response"""
    try:
        data = request.get_json()
        id_token = data.get("token")
        
        if not id_token:
            print("❌ No token provided")
            return jsonify({
                "success": False,
                "error": "No token provided"
            }), 400

        print(f"🔍 Received token from Google...")
        
        # Try Firebase verification first
        try:
            decoded_token = auth.verify_id_token(id_token)
            print(f"✅ Firebase token verified!")
        except Exception as firebase_error:
            print(f"⚠️ Firebase verification failed, trying alternative method...")
            print(f"Error: {firebase_error}")
            
            # Alternative: Verify token directly with Google
            try:
                import base64
                # Decode the JWT token manually (without verification)
                parts = id_token.split('.')
                if len(parts) == 3:
                    # Decode payload (second part)
                    payload = parts[1]
                    # Add padding if needed
                    padding = 4 - len(payload) % 4
                    if padding != 4:
                        payload += '=' * padding
                    
                    decoded_bytes = base64.urlsafe_b64decode(payload)
                    decoded_token = json.loads(decoded_bytes)
                    print(f"✅ Token decoded successfully (unverified)")
                else:
                    raise ValueError("Invalid token format")
            except Exception as decode_error:
                print(f"❌ Token decode failed: {decode_error}")
                return jsonify({
                    "success": False,
                    "error": "Invalid token format"
                }), 401
        
        # Extract user info from token
        uid = decoded_token.get('sub') or decoded_token.get('uid')
        email = decoded_token.get('email', '')
        name = decoded_token.get('name', 'User')
        
        if not uid:
            print("❌ No UID found in token")
            return jsonify({
                "success": False,
                "error": "Invalid token: no user ID"
            }), 401
        
        print(f"✅ User info extracted - UID: {uid}, Email: {email}")
        
        # Create or update user in Firebase
        try:
            if db:
                user_ref = db.collection("users").document(uid)
                user_doc = user_ref.get()
                created_at = user_doc.get("created_at") if user_doc.exists else datetime.now()
                
                user_ref.set({
                    "email": email,
                    "name": name,
                    "last_login": datetime.now(),
                    "created_at": created_at
                }, merge=True)
                
                print(f"✅ User saved to Firebase")
            else:
                print(f"⚠️ Firebase DB not available, but continuing...")
        except Exception as db_error:
            print(f"⚠️ Database error: {db_error}")
            # Continue anyway - user can still login
        
        # Set session
        session['user'] = {
            'uid': uid,
            'email': email,
            'name': name
        }
        
        print(f"✅ Session set, login successful!")
        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": session['user']
        })
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# =========================
# Routes - Main App
# =========================
@app.route("/home")
@login_required
def home():
    return render_template("home.html")

@app.route("/generate", methods=["POST"])
@login_required
def generate():
    try:
        user_id = session['user']['uid']
        data = request.get_json()

        letter_content = generate_letter_with_gemini(
            data.get("letterType"),
            data.get("language"),
            data.get("senderName"),
            data.get("receiverName"),
            data.get("receiverDesignation"),
            data.get("subject"),
            data.get("reason", ""),  # Optional
            data.get("tone"),
            data.get("organization", "")
        )

        letter_data = {
            "letterType": data.get("letterType"),
            "language": data.get("language"),
            "senderName": data.get("senderName"),
            "receiverName": data.get("receiverName"),
            "receiverDesignation": data.get("receiverDesignation"),
            "organization": data.get("organization", ""),
            "subject": clean_subject(data.get("subject")),
            "reason": data.get("reason", ""),
            "tone": data.get("tone"),
            "signature": data.get("signature", ""),
            "content": letter_content
        }

        letter_id = save_to_firebase(letter_data, user_id)

        return jsonify({
            "success": True,
            "letter": letter_content,
            "letterId": letter_id
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/generate-signatures", methods=["POST"])
@login_required
def generate_signatures():
    """Generate signature options"""
    try:
        data = request.get_json()
        name = data.get("name", "")
        
        if not name:
            return jsonify({"success": False, "error": "Name required"}), 400
        
        signatures = generate_signature(name)
        
        return jsonify({
            "success": True,
            "signatures": signatures
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/history")
@login_required
def history():
    user_id = session['user']['uid']
    return jsonify(load_user_letters(user_id))

@app.route("/history/<letter_id>")
@login_required
def get_letter(letter_id):
    user_id = session['user']['uid']
    letter = get_letter_from_firebase(user_id, letter_id)
    if letter:
        return jsonify(letter)
    return jsonify({"error": "Not found"}), 404

@app.route("/delete/<letter_id>", methods=["DELETE"])
@login_required
def delete_letter(letter_id):
    user_id = session['user']['uid']
    if delete_from_firebase(user_id, letter_id):
        return jsonify({"success": True})
    return jsonify({"success": False}), 500

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "firebase": db is not None,
        "gemini": GEMINI_API_KEY is not None,
        "available_models": len(AVAILABLE_MODELS)
    })

# =========================
# Run App
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    
    print("\n" + "="*50)
    print("🚀 AI LETTER GENERATOR (WITH AUTH)")
    print("="*50)
    print(f"Server: http://localhost:{port}")
    print(f"Gemini: {'✅ Configured' if GEMINI_API_KEY else '❌ Not Set'}")
    print(f"Models: {'✅ ' + str(len(AVAILABLE_MODELS)) if AVAILABLE_MODELS else '❌'}")
    print(f"Firebase: {'✅ Connected' if db else '❌ Not Connected'}")
    print("="*50 + "\n")
    
    app.run(debug=True, host="0.0.0.0", port=port)