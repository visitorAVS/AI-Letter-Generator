from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta
import requests
from functools import wraps
from io import BytesIO
import jwt

load_dotenv()

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, make_response
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, auth
from fpdf import FPDF

# =========================
# Flask App Setup
# =========================
app = Flask(__name__)
IS_RENDER = bool(os.environ.get("RENDER", False))
SECRET_KEY = os.environ.get("SECRET_KEY", "smartchithi_super_secret_key_2024")
app.config["SECRET_KEY"] = SECRET_KEY
CORS(app, supports_credentials=True)

# =========================
# Gemini Configuration
# =========================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
AVAILABLE_MODELS = []

if GEMINI_API_KEY:
    print("✅ Gemini API Key found")
    try:
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "models" in data:
                for model in data["models"]:
                    name = model.get("name", "").replace("models/", "")
                    methods = model.get("supportedGenerationMethods", [])
                    method_names = [m.get("name", "") if isinstance(m, dict) else m for m in methods]
                    if "generateContent" in method_names:
                        AVAILABLE_MODELS.append(name)
                AVAILABLE_MODELS.sort()
                print(f"✅ Found {len(AVAILABLE_MODELS)} available models")
    except Exception as e:
        print(f"⚠️ Could not auto-detect models: {e}")

# =========================
# Firebase Setup
# =========================
try:
    firebase_creds = os.environ.get("FIREBASE_CREDENTIALS")
    if firebase_creds:
        print("📝 Loading Firebase credentials from environment variable...")
        cred_dict = json.loads(firebase_creds)
        cred = credentials.Certificate(cred_dict)
    else:
        print("📝 Loading Firebase credentials from file...")
        cred = credentials.Certificate("firebase-credentials.json")

    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase initialized successfully")
except Exception as e:
    print(f"⚠️ Firebase error: {e}")
    db = None

# =========================
# ✅ JWT Session — No filesystem, No Firestore dependency
# Cookie mein encrypted JWT store hoti hai
# Render restart safe, multi-worker safe
# =========================
SESSION_COOKIE_NAME = "sc_token"
SESSION_EXPIRY_DAYS = 7

def create_session(user_data):
    """JWT token banao"""
    try:
        payload = {
            "user": user_data,
            "exp": datetime.utcnow() + timedelta(days=SESSION_EXPIRY_DAYS),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return token
    except Exception as e:
        print(f"JWT create error: {e}")
        return None

def get_session(token):
    """JWT token decode karo"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("user")
    except jwt.ExpiredSignatureError:
        print("JWT expired")
        return None
    except Exception as e:
        print(f"JWT decode error: {e}")
        return None

def get_current_user():
    """Cookie se user nikalo"""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    return get_session(token)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# =========================
# Helper Functions
# =========================
def clean_subject(text):
    return text.replace("**", "").strip()

def save_to_firebase(letter_data, user_id):
    if db is None:
        return None
    try:
        letter_data["timestamp"] = datetime.utcnow()
        letter_data["created_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        letter_data["user_id"] = user_id
        ref = db.collection("users").document(user_id).collection("letters").add(letter_data)
        return ref[1].id
    except Exception as e:
        print("Firebase save error:", e)
        return None

def load_user_letters(user_id):
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
    if db is None:
        return False
    try:
        db.collection("users").document(user_id).collection("letters").document(letter_id).delete()
        return True
    except Exception as e:
        print("Firebase delete error:", e)
        return False

def generate_letter_with_gemini(letter_type, language, sender_name, receiver_name,
                                receiver_designation, subject, reason, tone, organization=""):
    if not GEMINI_API_KEY:
        return "Error: Gemini API key not configured."
    if not AVAILABLE_MODELS:
        return "Error: No available models found."

    reason_prompt = f"- Reason/Details: {reason}" if reason and reason.strip() else ""
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
2. Include date: {datetime.utcnow().strftime('%B %d, %Y')}
3. Proper subject, salutation, body, closing, signature
4. Professional spacing
5. NO explanations or preamble
6. NO ** or markdown symbols
7. If Hindi → use Devanagari script
8. Start directly with the letter content
"""

    for model_name in AVAILABLE_MODELS:
        try:
            full_url = f"{GEMINI_API_URL}/{model_name}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "topK": 40, "topP": 0.95, "maxOutputTokens": 2048}
            }
            response = requests.post(full_url, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and data["candidates"]:
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    return content.replace("**", "")
            elif response.status_code == 404:
                continue
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"⚠️ {model_name}: {e}")
            continue

    return "Error: No available models could generate the letter."

def create_pdf_from_letter(letter_content, subject, sender_name):
    try:
        pdf = FPDF()
        pdf.set_margins(20, 20, 20)
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=20)

        pdf.set_font("Helvetica", style="B", size=14)
        safe_subject = subject.encode("latin-1", "replace").decode("latin-1")
        pdf.cell(0, 10, safe_subject, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(4)

        pdf.set_draw_color(102, 126, 234)
        pdf.set_line_width(0.5)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)

        pdf.set_font("Helvetica", size=11)
        for line in letter_content.split("\n"):
            safe_line = line.encode("latin-1", "replace").decode("latin-1")
            if safe_line.strip():
                pdf.multi_cell(0, 7, safe_line)
            else:
                pdf.ln(4)

        pdf.ln(6)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(4)
        pdf.set_font("Helvetica", style="I", size=9)
        pdf.set_text_color(150, 150, 150)
        safe_sender = sender_name.encode("latin-1", "replace").decode("latin-1")
        pdf.cell(0, 6, f"Generated by: {safe_sender}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Generated on: {datetime.now().strftime('%B %d, %Y')}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, "Smart Chithi - AI Letter Generator", new_x="LMARGIN", new_y="NEXT")

        pdf_buffer = BytesIO()
        pdf.output(pdf_buffer)
        pdf_buffer.seek(0)
        return pdf_buffer
    except Exception as e:
        print(f"PDF creation error: {e}")
        return None

# =========================
# Routes
# =========================
@app.route("/")
def index():
    user = get_current_user()
    return redirect(url_for('home') if user else url_for('login'))

@app.route("/login")
def login():
    user = get_current_user()
    if user:
        return redirect(url_for('home'))
    return render_template("login.html")

@app.route("/auth/google", methods=["POST"])
def auth_google():
    try:
        data = request.get_json()
        id_token = data.get("token")
        if not id_token:
            return jsonify({"success": False, "error": "No token provided"}), 400

        print("🔍 Verifying token...")
        decoded_token = None

        # Firebase verify try karo
        try:
            decoded_token = auth.verify_id_token(id_token)
            print("✅ Firebase token verified!")
        except Exception as firebase_error:
            print(f"⚠️ Firebase verify failed: {firebase_error}")

        # Fallback: JWT manual decode
        if not decoded_token:
            try:
                import base64
                parts = id_token.split('.')
                if len(parts) == 3:
                    payload = parts[1]
                    padding = 4 - len(payload) % 4
                    if padding != 4:
                        payload += '=' * padding
                    decoded_bytes = base64.urlsafe_b64decode(payload)
                    decoded_token = json.loads(decoded_bytes)
                    print("✅ Token decoded manually (unverified)")
            except Exception as e:
                print(f"❌ Manual decode failed: {e}")
                return jsonify({"success": False, "error": "Token verification failed"}), 401

        uid = decoded_token.get('sub') or decoded_token.get('uid')
        email = decoded_token.get('email', '')
        name = decoded_token.get('name', 'User')

        if not uid:
            return jsonify({"success": False, "error": "No user ID in token"}), 401

        print(f"✅ User: {name} ({email})")

        # Firebase mein user save karo
        try:
            if db:
                user_ref = db.collection("users").document(uid)
                user_doc = user_ref.get()
                created_at = user_doc.get("created_at") if user_doc.exists else datetime.utcnow()
                user_ref.set({
                    "email": email, "name": name,
                    "last_login": datetime.utcnow(),
                    "created_at": created_at
                }, merge=True)
                print("✅ User saved to Firebase")
        except Exception as e:
            print(f"⚠️ DB error (non-fatal): {e}")

        # ✅ JWT token banao — no Firestore needed
        user_data = {"uid": uid, "email": email, "name": name}
        jwt_token = create_session(user_data)

        if not jwt_token:
            return jsonify({"success": False, "error": "Session creation failed"}), 500

        print(f"✅ JWT session created for {name}")

        resp = make_response(jsonify({
            "success": True,
            "message": "Login successful",
            "user": user_data
        }))
        resp.set_cookie(
            SESSION_COOKIE_NAME,
            jwt_token,
            max_age=SESSION_EXPIRY_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=IS_RENDER,
            samesite="Lax"
        )
        return resp

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for('login')))
    resp.delete_cookie(SESSION_COOKIE_NAME)
    return resp

@app.route("/auth/logout", methods=["POST"])
def auth_logout():
    resp = make_response(jsonify({"success": True}))
    resp.delete_cookie(SESSION_COOKIE_NAME)
    return resp

@app.route("/home")
@login_required
def home():
    return render_template("home.html")

@app.route("/api/check-auth")
def check_auth():
    user = get_current_user()
    print(f"🔍 check-auth: {'✅ ' + user['name'] if user else '❌ not logged in'}")
    if user:
        return jsonify({"authenticated": True, "name": user["name"], "email": user["email"], "uid": user["uid"]})
    return jsonify({"authenticated": False})

@app.route("/debug-session")
def debug_session():
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_current_user()
    return jsonify({
        "token_present": bool(token),
        "token_preview": token[:20] + "..." if token else None,
        "user_found": bool(user),
        "user": user,
        "is_render": IS_RENDER,
        "session_type": "JWT"
    })

@app.route("/generate", methods=["POST"])
@login_required
def generate():
    try:
        user = get_current_user()
        data = request.get_json()
        letter_content = generate_letter_with_gemini(
            data.get("letterType"), data.get("language"),
            data.get("senderName"), data.get("receiverName"),
            data.get("receiverDesignation"), data.get("subject"),
            data.get("reason", ""), data.get("tone"),
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
            "content": letter_content
        }
        letter_id = save_to_firebase(letter_data, user["uid"])
        return jsonify({"success": True, "letter": letter_content, "letterId": letter_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/history")
@login_required
def history():
    user = get_current_user()
    return jsonify(load_user_letters(user["uid"]))

@app.route("/history/<letter_id>")
@login_required
def get_letter(letter_id):
    user = get_current_user()
    letter = get_letter_from_firebase(user["uid"], letter_id)
    return jsonify(letter) if letter else jsonify({"error": "Not found"}), 404

@app.route("/delete/<letter_id>", methods=["DELETE"])
@login_required
def delete_letter(letter_id):
    user = get_current_user()
    if delete_from_firebase(user["uid"], letter_id):
        return jsonify({"success": True})
    return jsonify({"success": False}), 500

@app.route("/download-pdf/<letter_id>")
@login_required
def download_pdf(letter_id):
    try:
        user = get_current_user()
        letter = get_letter_from_firebase(user["uid"], letter_id)
        if not letter:
            return jsonify({"error": "Letter not found"}), 404
        pdf_buffer = create_pdf_from_letter(
            letter.get("content", ""),
            letter.get("subject", "Letter"),
            letter.get("senderName", "User")
        )
        if not pdf_buffer:
            return jsonify({"error": "PDF generation failed"}), 500
        filename = f"{letter.get('letterType', 'letter').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "firebase": db is not None,
        "gemini": GEMINI_API_KEY is not None,
        "models": len(AVAILABLE_MODELS),
        "is_render": IS_RENDER,
        "session_type": "JWT"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n" + "=" * 50)
    print("🚀 SMART CHITHI - AI LETTER GENERATOR")
    print("=" * 50)
    print(f"Gemini:  {'✅' if GEMINI_API_KEY else '❌'}")
    print(f"Models:  {len(AVAILABLE_MODELS)}")
    print(f"Firebase: {'✅' if db else '❌'}")
    print(f"Render:  {'✅' if IS_RENDER else '❌ localhost'}")
    print(f"Session: JWT ✅")
    print("=" * 50 + "\n")
    app.run(debug=True, host="0.0.0.0", port=port)