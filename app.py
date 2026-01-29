import streamlit as st
import google.generativeai as genai
import json
import os
import hashlib
import base64
from PIL import Image
from io import BytesIO

# --- 1. FUNKCIJE ZA PODATKE ---
DB_FILE = "qai_users_data.json"

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                # Varnostni popravek: zagotovi, da vsi ključi obstajajo
                if "users" not in d: d["users"] = {}
                if "folders" not in d: d["folders"] = {}
                if "user_settings" not in d: d["user_settings"] = {}
                return d
        except: return {"users": {}, "folders": {}, "user_settings": {}}
    return {"users": {}, "folders": {}, "user_settings": {}}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. STIL IN TEMA ---
st.set_page_config(page_title="Qai", layout="centered")

def apply_custom_styles(dark_mode):
    bg = "#0E1117" if dark_mode else "#FFFFFF"
    txt = "#FFFFFF" if dark_mode else "#000000"
    card = "#161B22" if dark_mode else "#F0F2F6"
    
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {bg}; color: {txt}; }}
        /* Popravek za gumbe: celo besedilo brez lomljenja */
        div.stButton > button {{
            width: 100% !important; min-height: 45px !important;
            white-space: nowrap !important; overflow: hidden !important;
            text-overflow: ellipsis !important; display: block !important;
        }}
        .folder-box {{
            display: flex; align-items: center; background: {card}; 
            border-radius: 10px; padding: 12px; border: 1px solid #30363D; margin-bottom: 10px;
        }}
        .color-tab {{ width: 6px; height: 30px; border-radius: 3px; margin-right: 15px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOGIKA APLIKACIJE ---
data = load_data()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = "login"

# Povezava z AI
genai.configure(api_key="AIzaSyCAcL8sBxKVyDW-QW6z06lm56WaQ-9tTUY")
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- 4. STRANI ---

# --- PRIJAVA / REGISTRACIJA ---
if not st.session_state.logged_in:
    st.title("🚀 Qai Vstop")
    t1, t2 = st.tabs(["Prijava", "Registracija"])
    with t1:
        ul = st.text_input("Uporabniško ime", key="l_u")
        pl = st.text_input("Geslo", type="password", key="l_p")
        if st.button("Vstopi"):
            if ul in data["users"] and data["users"][ul] == hash_password(pl):
                st.session_state.logged_in, st.session_state.user = True, ul
                st.session_state.page = "home"
                st.rerun()
            else: st.error("Napačni podatki.")
    with t2:
        ur = st.text_input("Izberi ime", key="r_u")
        pr = st.text_input("Izberi geslo", type="password", key="r_p")
        if st.button("Ustvari račun"):
            if ur and pr and ur not in data["users"]:
                data["users"][ur] = hash_password(pr)
                data["folders"][ur] = {}
                data["user_settings"][ur] = {"dark_mode": True, "pfp": None}
                save_data(data); st.success("Račun ustvarjen! Zdaj se prijavi.")

# --- PRIJAVLJEN UPORABNIK ---
else:
    # Varno nalaganje nastavitev (Prepreči KeyError)
    u_name = st.session_state.user
    if u_name not in data["user_settings"]:
        data["user_settings"][u_name] = {"dark_mode": True, "pfp": None}
        save_data(data)
    
    settings = data["user_settings"][u_name]
    apply_custom_styles(settings.get("dark_mode", True))

    # Sidebar profil
    with st.sidebar:
        if settings.get("pfp"):
            st.image(settings["pfp"], width=80)
        st.write(f"**Uporabnik: {u_name}**")
        if st.button("🏠 Domov"): st.session_state.page = "home"; st.rerun()
        if st.button("⚙️ Nastavitve"): st.session_state.page = "profile"; st.rerun()
        st.divider()
        if st.button("🚪 Odjava"): st.session_state.logged_in = False; st.rerun()

    # STRAN: PROFIL
    if st.session_state.page == "profile":
        st.subheader("Uredi profil")
        
        # Dark mode preklop
        new_dm = st.toggle("Dark Mode", value=settings.get("dark_mode", True))
        if new_dm != settings.get("dark_mode"):
            data["user_settings"][u_name]["dark_mode"] = new_dm
            save_data(data); st.rerun()
            
        # Profilna slika
        img_up = st.file_uploader("Naloži sliko", type=['jpg', 'png'])
        if img_up:
            img = Image.open(img_up)
            img.thumbnail((150, 150))
            buf = BytesIO()
            img.save(buf, format="PNG")
            data["user_settings"][u_name]["pfp"] = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
            save_data(data); st.success("Slika shranjena!"); st.rerun()

        # Menjava gesla
        new_pass = st.text_input("Novo geslo", type="password")
        if st.button("Posodobi geslo") and new_pass:
            data["users"][u_name] = hash_password(new_pass)
            save_data(data); st.success("Geslo spremenjeno!")

    # STRAN: DOMOV
    elif st.session_state.page == "home":
        st.title("📂 Moje mape")
        
        c1, c2 = st.columns(2)
        with c1.expander("✨ AI Ustvari"):
            fn = st.text_input("Ime mape")
            txt = st.text_area("Snov")
            if st.button("Generiraj"):
                res = model.generate_content(f"Format: Q|A. Vir: {txt}")
                cards = [{"q": l.split("|")[0], "a": l.split("|")[1], "known": False} for l in res.text.split('\n') if "|" in l]
                data["folders"][u_name][fn] = {"cards": cards, "color": "#4A90E2"}
                save_data(data); st.rerun()
                
        with c2.expander("📁 Ročno Ustvari"):
            fn_m = st.text_input("Ime mape ")
            if st.button("Ustvari prazno"):
                data["folders"][u_name][fn_m] = {"cards": [], "color": "#9B59B6"}
                save_data(data); st.session_state.edit_folder = fn_m; st.session_state.page = "edit"; st.rerun()

        st.divider()
        
        # Prikaz map
        folders = data["folders"].get(u_name, {})
        for f_name, f_data in folders.items():
            st.markdown(f"""<div class="folder-box">
                <div class="color-tab" style="background-color: {f_data.get('color', '#4A90E2')};"></div>
                <div style="flex-grow:1"><b>{f_name}</b></div>
            </div>""", unsafe_allow_html=True)
            
            with st.expander("Odpri možnosti"):
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
        f_obj = data["folders"][u_name][f_target]
        st.subheader(f"Urejanje: {f_target}")
        
        new_name = st.text_input("Ime", f_target)
        new_col = st.color_picker("Barva", f_obj.get("color", "#4A90E2"))
        
        for i, card in enumerate(f_obj["cards"]):
            c_q, c_a, c_d = st.columns([1, 1, 0.2])
            f_obj["cards"][i]["q"] = c_q.text_input(f"Vpr {i}", card["q"], key=f"q{i}")
            f_obj["cards"][i]["a"] = c_a.text_input(f"Odg {i}", card["a"], key=f"a{i}")
            if c_d.button("🗑️", key=f"d{i}"): f_obj["cards"].pop(i); save_data(data); st.rerun()
            
        if st.button("➕ Dodaj kartico"):
            f_obj["cards"].append({"q": "", "a": "", "known": False})
            save_data(data); st.rerun()
            
        if st.button("💾 Shrani"):
            del data["folders"][u_name][f_target]
            data["folders"][u_name][new_name] = {"cards": f_obj["cards"], "color": new_col}
            save_data(data); st.session_state.page = "home"; st.rerun()
