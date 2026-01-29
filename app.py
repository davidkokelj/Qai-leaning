import streamlit as st
import google.generativeai as genai
import json
import os
import hashlib

# --- 1. TRAJNO SHRANJEVANJE ---
DB_FILE = "qai_users_data.json"

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if "users" not in d: d = {"users": {}, "folders": {}}
                return d
        except: return {"users": {}, "folders": {}}
    return {"users": {}, "folders": {}}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. NASTAVITVE IN STIL (Temno ozadje in čiste linije) ---
st.set_page_config(page_title="Qai - Študijski Tinder", layout="centered")

st.markdown("""
<style>
    /* Glavni gumbi */
    div.stButton > button {
        display: block; margin: 0 auto; width: 100% !important;
        min-height: 50px !important; border-radius: 10px;
        font-size: 16px !important; font-weight: bold;
        white-space: nowrap !important;
    }
    
    /* Kartica vprašanja */
    .flip-btn > button {
        height: 280px !important; white-space: normal !important;
        background-color: #1E1E1E !important; color: #FFFFFF !important;
        border: 1px solid #333 !important; font-size: 20px !important;
    }

    /* Kartica mape (brez belega ozadja) */
    .folder-container {
        display: flex; align-items: center; 
        background: transparent; /* Zlije se z ozadjem */
        border-radius: 12px; margin-bottom: 5px; padding: 10px;
        border: 1px solid #333;
    }
    .color-tab {
        width: 6px; height: 35px; border-radius: 3px; margin-right: 15px;
    }
    .folder-info { flex-grow: 1; }
    .folder-title { font-weight: bold; font-size: 18px; margin: 0; }
</style>
""", unsafe_allow_html=True)

# --- 3. INICIALIZACIJA ---
data = load_data()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = "login"
if 'edit_folder' not in st.session_state: st.session_state.edit_folder = None

MOJ_KLJUC = "AIzaSyCAcL8sBxKVyDW-QW6z06lm56WaQ-9tTUY"
genai.configure(api_key=MOJ_KLJUC)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- 4. STRANI ---

# PRIJAVA
if not st.session_state.logged_in:
    st.title("🔐 Qai Vstop")
    u = st.text_input("Uporabniško ime")
    p = st.text_input("Geslo", type="password")
