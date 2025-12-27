import streamlit as st
import requests
import uuid
import logging
from chat_history import save_session
from cookie_utils import get_cookie_manager
from datetime import datetime
import hashlib
# import os
# Logging
logging.basicConfig(filename="app.log", level=logging.DEBUG)

# Page Config
st.set_page_config(page_title="Login - HXAssist", page_icon="🔐", layout="centered")

# Custom CSS
st.markdown("""
    <style>
    .stApp { background-color: #f0f4f8; font-family: 'Inter', sans-serif; }
    .login-title { color: #006d77; font-size: 2em; text-align: center; margin-bottom: 0.5em; }
    .stTextInput > div > input { border-radius: 8px; border: 1px solid #83c5be; padding: 10px; }
    .stButton > button {
        background-color: #006d77; color: white; border-radius: 8px; padding: 8px 16px;
        transition: background-color 0.3s; display: block; margin: 10px auto;
    }
    .stButton > button:hover { background-color: #008b94; }
    .st-bs {
        background-color: rgb(231 231 231);
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------
# Always init cookies here
# -------------------------
cookies = get_cookie_manager()
if not cookies.ready():
    st.info("⏳ Initializing cookies... please wait.")
    st.stop()

# -------------------------
# Redirect if already logged in
# -------------------------
if st.session_state.get("authenticated", False):
    st.switch_page("app.py")

# -------------------------
# API Key Generation 
# -------------------------
def generate_api_key():
    date = datetime.now().strftime('%Y-%m-%d')
    base = f"click@hxa_ai{date}"
    inner_md5 = hashlib.md5(base.encode()).hexdigest()
    sha1_hash = hashlib.sha1(inner_md5.encode()).hexdigest()
    final_key = hashlib.md5(sha1_hash.encode()).hexdigest()
    return final_key

# -------------------------
# Login Form
# -------------------------
st.markdown('<div class="login-title">🔐 Login to HXAssist</div>', unsafe_allow_html=True)
API_LOGIN_URL = "https://qbizhub.sct-lb.net/ai_api/index.php?action=login"
# username = st.text_input("Username")
# password = st.text_input("Password", type="password")
# API_KEY = os.getenv("API_KEY")

def login():
    st.title("Login")
    API_KEY = generate_api_key()
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if not username or not password:
            st.warning("⚠️ Please enter both username and password.")
            return

        try:
            ACTION = "login"  # Optional: action identifier for backend

            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "API-Key": API_KEY,
                "action": ACTION,
                "Content-Type": "application/json"
            }

            response = requests.post(API_LOGIN_URL, json={
                "username": username,
                "password": password
            }, headers=headers)
            print("Response status:", response.status_code)
            print("Response text:", response.text)
            print(response.json())
            try:
                result = response.json()
            except ValueError:
                result = None  # set to None so we can still handle it safely

            # ✅ Success path
            if response.status_code == 200 and result:
                access_token = result.get("data", {}).get("access_token")

                if not access_token:
                    st.error("Login failed: No token returned.")
                    return

                # Store session info
                
                st.session_state["user"] = username
                st.session_state["access_token"] = access_token

                if "session_id" not in st.session_state:
                    st.session_state["session_id"] = str(uuid.uuid4())
                cookies["session_id"] = st.session_state["session_id"]
                cookies.save()

                st.session_state["authenticated"] = True
                st.rerun()

            else:
                error_message = result.get("error_info") or result.get("message") or "Unknown error occurred."
                st.error(f"❌ Login failed: {error_message}")

        except Exception as e:
            st.error(f"⚠️ Error during login: {e}")



login()