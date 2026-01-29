import streamlit as st
import google.generativeai as genai
import json
import os
import hashlib
import base64
from PIL import Image
from io import BytesIO

# --- 1. PODATKI ---
DB_FILE = "qai_users_data.json"

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                for key in ["users", "folders", "user_settings"]:
                    if key not in d: d[key] = {}
                return d
        except: return {"users": {}, "folders": {}, "user_settings": {}}
    return {"users": {}, "folders": {}, "user_settings": {}}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. POSODOBLJEN STIL (Brez okvirčkov) ---
st.set_page_config(page_title="Qai", layout="centered")

def apply_styles(dark_mode):
    bg = "#0E1117" if dark_mode else "#FFFFFF"
    txt = "#FFFFFF" if dark_mode else "#000000"
    hover = "#1d232d" if dark_mode else "#f0f2f6"
    
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {bg}; color: {txt}; }}
        
        /* Stranski meni - vrstice namesto okvirjev */
        [data-testid="stSidebar"] div.stButton > button {{
            border: none !important;
            background: transparent !important;
            text-align: left !important;
            justify-content: flex-start !important;
            padding: 10px 5px !important;
            width: 100% !important;
            color: {txt} !important;
            border-radius: 0px !important;
        }}
        [data-testid="stSidebar"] div.stButton > button:hover {{
            background-color: {hover} !important;
        }}

        /* Profilna vrstica v Sidebaru */
        .profile-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 10px 0;
            margin-bottom: 20px;
        }}
        .profile-img {{
            width: 50px;
            height: 50px;
            border-radius: 50%;
            object-fit: cover;
        }}
        .profile-text {{
            font-size: 16px;
            font-weight: 600;
        }}

        /* Expanderji map */
        .streamlit-expanderHeader {{
            border: none !important;
            background: transparent !important;
        }}
        .folder-row {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .color-bar {{
            width: 4px;
            height: 20px;
            border-radius: 2px;
        }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOGIKA ---
data = load_data()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = "login"

genai.configure(api_key="AIzaSyCAcL8sBxKVyDW-QW6z06lm56WaQ-9tTUY")
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- 4. STRANI ---

if not st.session_state.logged_in:
    st.title("🚀 Qai")
    t1, t2 = st.tabs(["Prijava", "Registracija"])
    with t1:
        u = st.text_input("Uporabniško ime", key="l_u")
        p = st.text_input("Geslo", type="password", key="l_p")
        if st.button("Vstopi"):
            if u in data["users"] and data["users"][u] == hash_password(p):
                st.session_state.logged_in, st.session_state.user, st.session_state.page = True, u, "home"
                st.rerun()
    with t2:
        ur = st.text_input("Uporabniško ime (za prijavo)", key="r_u")
        fname = st.text_input("Ime", key="r_fname")
        lname = st.text_input("Priimek", key="r_lname")
        pr = st.text_input("Geslo", type="password", key="r_p")
        if st.button("Registriraj se"):
            if ur and pr and fname:
                data["users"][ur] = hash_password(pr)
                data["folders"][ur] = {}
                data["user_settings"][ur] = {
                    "dark_mode": True, 
                    "pfp": None,
                    "full_name": f"{fname} {lname}"
                }
                save_data(data); st.success("Registracija uspela!")

else:
    u_name = st.session_state.user
    settings = data["user_settings"].get(u_name, {})
    apply_styles(settings.get("dark_mode", True))

    # --- SIDEBAR (Linijski dizajn) ---
    with st.sidebar:
        # Profilna vrstica: Slika + Ime in Priimek
        pfp = settings.get("pfp", "https://www.w3schools.com/howto/img_avatar.png")
        full_name = settings.get("full_name", u_name)
        
        st.markdown(f"""
            <div class="profile-header">
                <img src="{pfp}" class="profile-img">
                <div class="profile-text">{full_name}</div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("🏠 Domov"): st.session_state.page = "home"; st.rerun()
        if st.button("⚙️ Profil"): st.session_state.page = "profile"; st.rerun()
        st.divider()
        if st.button("🚪 Odjava"): st.session_state.logged_in = False; st.rerun()

    # --- DOMOV ---
    if st.session_state.page == "home":
        st.title("Moje mape")
        
        c1, c2 = st.columns(2)
        with c1.expander("✨ Ustvari z AI"):
            fn = st.text_input("Ime mape")
            txt = st.text_area("Snov")
            if st.button("Generiraj"):
                res = model.generate_content(f"Format: Q|A. Vir: {txt}")
                cards = [{"q": l.split("|")[0], "a": l.split("|")[1], "known": False} for l in res.text.split('\n') if "|" in l]
                data["folders"][u_name][fn] = {"cards": cards, "color": "#4A90E2"}
                save_data(data); st.rerun()
                
        with c2.expander("📁 Ustvari ročno"):
            fn_m = st.text_input("Ime nove mape")
            if st.button("Ustvari"):
                data["folders"][u_name][fn_m] = {"cards": [], "color": "#9B59B6"}
                save_data(data); st.session_state.edit_folder, st.session_state.page = fn_m, "edit"; st.rerun()

        st.divider()
        
        folders = data["folders"].get(u_name, {})
        for f_name, f_data in folders.items():
            color = f_data.get('color', '#4A90E2')
            header_html = f'<div class="folder-row"><div class="color-bar" style="background-color: {color};"></div><span>{f_name}</span></div>'
            
            with st.expander(header_html):
                col1, col2, col3 = st.columns([1, 1, 0.4])
                if col1.button("📖 Uči", key=f"l_{f_name}"):
                    st.session_state.current_folder, st.session_state.page, st.session_state.card_index = f_name, "learning", 0
                    st.rerun()
                if col2.button("📝 Test", key=f"t_{f_name}"):
                    st.session_state.current_folder, st.session_state.page, st.session_state.card_index = f_name, "testing", 0
                    st.rerun()
                if col3.button("⋮", key=f"e_{f_name}"):
                    st.session_state.edit_folder, st.session_state.page = f_name, "edit"
                    st.rerun()

    # --- PROFIL ---
    elif st.session_state.page == "profile":
        st.header("Nastavitve")
        new_fn = st.text_input("Ime in priimek", settings.get("full_name", ""))
        
        img_up = st.file_uploader("Spremeni profilno sliko", type=['jpg', 'png'])
        if img_up:
            img = Image.open(img_up)
            img.thumbnail((100, 100))
            buf = BytesIO()
            img.save(buf, format="PNG")
            data["user_settings"][u_name]["pfp"] = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
            save_data(data); st.rerun()
            
        if st.button("Shrani spremembe"):
            data["user_settings"][u_name]["full_name"] = new_fn
            save_data(data); st.success("Shranjeno!"); st.rerun()
