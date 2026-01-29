import streamlit as st
import google.generativeai as genai
import json
import os
import hashlib
import base64
from PIL import Image
from io import BytesIO

# --- 1. VARNO NALAGANJE PODATKOV ---
DB_FILE = "qai_users_data.json"

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                # Varnostni mehanizem: če ključi manjkajo, jih ustvari
                for key in ["users", "folders", "user_settings"]:
                    if key not in d: d[key] = {}
                return d
        except: return {"users": {}, "folders": {}, "user_settings": {}}
    return {"users": {}, "folders": {}, "user_settings": {}}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. STIL IN OBLIKOVANJE ---
st.set_page_config(page_title="Qai", layout="centered")

def apply_styles(dark_mode):
    bg = "#0E1117" if dark_mode else "#FFFFFF"
    txt = "#FFFFFF" if dark_mode else "#000000"
    hover = "#1d232d" if dark_mode else "#f0f2f6"
    
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {bg}; color: {txt}; }}
        
        /* Gumbi v sidebaru brez okvirčkov */
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

        /* Gumbi na glavni strani - prepreči prelom besed */
        div.stButton > button {{
            white-space: nowrap !important;
            word-break: keep-all !important;
        }}

        /* Profil v Sidebaru */
        .profile-header {{
            display: flex; align-items: center; gap: 15px; padding: 10px 0; margin-bottom: 20px;
        }}
        .profile-img {{
            width: 45px; height: 45px; border-radius: 50%; object-fit: cover;
            background: #333;
        }}
        .profile-text {{ font-size: 15px; font-weight: 600; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. INICIALIZACIJA ---
data = load_data()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = "login"

# AI Povezava
try:
    genai.configure(api_key="AIzaSyCAcL8sBxKVyDW-QW6z06lm56WaQ-9tTUY")
    model = genai.GenerativeModel('models/gemini-2.5-flash')
except:
    st.warning("AI trenutno ni dosegljiv.")

# --- 4. LOGIKA STRANI ---

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
            else: st.error("Napačni podatki.")
    with t2:
        ur = st.text_input("Novo up. ime", key="r_u")
        fname = st.text_input("Ime", key="r_fname")
        lname = st.text_input("Priimek", key="r_lname")
        pr = st.text_input("Novo geslo", type="password", key="r_p")
        if st.button("Registriraj se"):
            if ur and pr:
                data["users"][ur] = hash_password(pr)
                data["folders"][ur] = {}
                data["user_settings"][ur] = {"dark_mode": True, "pfp": None, "full_name": f"{fname} {lname}"}
                save_data(data); st.success("Zdaj se prijavi!")

else:
    u_name = st.session_state.user
    # Varna pridobitev nastavitev (prepreči KeyError)
    settings = data.get("user_settings", {}).get(u_name, {"dark_mode": True, "full_name": u_name})
    apply_styles(settings.get("dark_mode", True))

    with st.sidebar:
        pfp = settings.get("pfp", "https://www.w3schools.com/howto/img_avatar.png")
        full_name = settings.get("full_name", u_name)
        
        st.markdown(f"""
            <div class="profile-header">
                <img src="{pfp}" class="profile-img">
                <div class="profile-text">{full_name}</div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("🏠 Domov"): st.session_state.page = "home"; st.rerun()
        if st.button("⚙️ Nastavitve profila"): st.session_state.page = "profile"; st.rerun()
        st.divider()
        if st.button("🚪 Odjava"): st.session_state.logged_in = False; st.rerun()

    # STRAN: DOMOV
    if st.session_state.page == "home":
        st.title("Moje mape")
        
        c1, c2 = st.columns(2)
        with c1.expander("✨ Ustvari z AI"):
            fn = st.text_input("Ime mape")
            txt = st.text_area("Snov za učenje")
            if st.button("Generiraj"):
                with st.spinner("Qai razmišlja..."):
                    res = model.generate_content(f"Format: Q|A. Vir: {txt}")
                    cards = [{"q": l.split("|")[0], "a": l.split("|")[1], "known": False} for l in res.text.split('\n') if "|" in l]
                    data["folders"][u_name][fn] = {"cards": cards, "color": "#4A90E2"}
                    save_data(data); st.rerun()
                
        with c2.expander("📁 Ustvari ročno"):
            fn_m = st.text_input("Ime mape ")
            if st.button("Ustvari"):
                data["folders"][u_name][fn_m] = {"cards": [], "color": "#9B59B6"}
                save_data(data); st.session_state.edit_folder, st.session_state.page = fn_m, "edit"; st.rerun()

        st.divider()
        
        folders = data.get("folders", {}).get(u_name, {})
        for f_name, f_data in folders.items():
            # Čist naslov brez HTML-ja v expanderju (popravi sliko 52c71a)
            with st.expander(f"📁 {f_name}"):
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

    # STRAN: UREJANJE
    elif st.session_state.page == "edit":
        f_target = st.session_state.edit_folder
        f_obj = data["folders"][u_name].get(f_target, {"cards": []})
        st.subheader(f"Urejanje: {f_target}")
        
        for i, card in enumerate(f_obj["cards"]):
            cq, ca, cd = st.columns([1, 1, 0.2])
            f_obj["cards"][i]["q"] = cq.text_input(f"V", card["q"], key=f"q{i}")
            f_obj["cards"][i]["a"] = ca.text_input(f"O", card["a"], key=f"a{i}")
            if cd.button("🗑️", key=f"d{i}"): f_obj["cards"].pop(i); save_data(data); st.rerun()
            
        if st.button("➕ Dodaj"):
            f_obj["cards"].append({"q": "", "a": "", "known": False})
            save_data(data); st.rerun()
        if st.button("💾 Shrani in zapri"):
            st.session_state.page = "home"; st.rerun()

    # STRAN: PROFIL
    elif st.session_state.page == "profile":
        st.header("Nastavitve profila")
        new_name = st.text_input("Ime in priimek", settings.get("full_name", ""))
        dark = st.toggle("Temni način", value=settings.get("dark_mode", True))
        
        up = st.file_uploader("Spremeni sliko", type=['jpg', 'png'])
        if up:
            img = Image.open(up)
            img.thumbnail((150, 150))
            buf = BytesIO()
            img.save(buf, format="PNG")
            data["user_settings"][u_name]["pfp"] = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
            save_data(data); st.rerun()
            
        if st.button("Shrani vse"):
            data["user_settings"][u_name]["full_name"] = new_name
            data["user_settings"][u_name]["dark_mode"] = dark
            save_data(data); st.success("Shranjeno!"); st.rerun()
