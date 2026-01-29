import streamlit as st
import google.generativeai as genai
import json
import os
import hashlib
import base64
from PIL import Image
from io import BytesIO

# --- 1. PODATKI IN VARNOST ---
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

# --- 2. NAPREDNI STIL (Temni/Svetli način & Sidebar) ---
st.set_page_config(page_title="Qai", layout="centered")

def apply_styles(dark_mode):
    if dark_mode:
        bg, txt, hover, card = "#0E1117", "#FFFFFF", "#1d232d", "#161B22"
    else:
        bg, txt, hover, card = "#FFFFFF", "#000000", "#f0f2f6", "#f9f9f9"
    
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {bg}; color: {txt}; }}
        
        /* Stranski meni brez okvirčkov */
        [data-testid="stSidebar"] div.stButton > button {{
            border: none !important;
            background: transparent !important;
            text-align: left !important;
            padding: 10px 15px !important;
            width: 100% !important;
            color: {txt} !important;
            border-radius: 0px !important;
        }}
        [data-testid="stSidebar"] div.stButton > button:hover {{
            background-color: {hover} !important;
        }}

        /* Profil v Sidebaru */
        .profile-header {{
            display: flex; align-items: center; gap: 12px; padding: 15px; margin-bottom: 10px;
        }}
        .profile-img {{
            width: 45px; height: 45px; border-radius: 50%; object-fit: cover; border: 1px solid #444;
        }}
        .profile-text {{ font-size: 14px; font-weight: 600; color: {txt}; }}

        /* Barvni zavihki za mape */
        .folder-header {{
            display: flex; align-items: center; gap: 10px; width: 100%;
        }}
        .color-pill {{
            width: 12px; height: 12px; border-radius: 50%;
        }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. INICIALIZACIJA ---
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
        u = st.text_input("Uporabnik", key="l_u")
        p = st.text_input("Geslo", type="password", key="l_p")
        if st.button("Vstop"):
            if u in data["users"] and data["users"][u] == hash_password(p):
                st.session_state.logged_in, st.session_state.user, st.session_state.page = True, u, "home"
                st.rerun()
    with t2:
        ur = st.text_input("Uporabniško ime", key="r_u")
        fn = st.text_input("Ime", key="r_fn")
        ln = st.text_input("Priimek", key="r_ln")
        pr = st.text_input("Geslo", type="password", key="r_p")
        if st.button("Ustvari račun"):
            if ur and pr:
                data["users"][ur] = hash_password(pr)
                data["folders"][ur] = {}
                data["user_settings"][ur] = {"dark_mode": True, "full_name": f"{fn} {ln}"}
                save_data(data); st.success("Registriran! Prijavi se.")

else:
    u_name = st.session_state.user
    # Osveži nastavitve
    settings = data["user_settings"].get(u_name, {"dark_mode": True})
    apply_styles(settings.get("dark_mode", True))

    # --- SIDEBAR ---
    with st.sidebar:
        pfp_data = settings.get("pfp", "https://www.w3schools.com/howto/img_avatar.png")
        full_name = settings.get("full_name", u_name)
        
        st.markdown(f"""
            <div class="profile-header">
                <img src="{pfp_data}" class="profile-img">
                <div class="profile-text">{full_name}</div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("🏠 Domov"): st.session_state.page = "home"; st.rerun()
        if st.button("⚙️ Profil"): st.session_state.page = "profile"; st.rerun()
        st.divider()
        if st.button("🚪 Odjava"): st.session_state.logged_in = False; st.rerun()

    # --- STRAN: DOMOV ---
    if st.session_state.page == "home":
        st.title("Moje mape")
        
        c1, c2 = st.columns(2)
        with c1.expander("✨ Ustvari z AI"):
            fn_ai = st.text_input("Ime mape")
            txt_ai = st.text_area("Snov")
            if st.button("Generiraj"):
                res = model.generate_content(f"Format: Q|A. Vir: {txt_ai}")
                cards = [{"q": l.split("|")[0], "a": l.split("|")[1], "known": False} for l in res.text.split('\n') if "|" in l]
                data["folders"][u_name][fn_ai] = {"cards": cards, "color": "#4A90E2"}
                save_data(data); st.rerun()
                
        with c2.expander("📁 Ustvari ročno"):
            fn_m = st.text_input("Ime ")
            if st.button("Ustvari"):
                data["folders"][u_name][fn_m] = {"cards": [], "color": "#9B59B6"}
                save_data(data); st.session_state.edit_folder, st.session_state.page = fn_m, "edit"; st.rerun()

        st.divider()
        
        user_folders = data["folders"].get(u_name, {})
        for f_name, f_data in user_folders.items():
            f_color = f_data.get("color", "#4A90E2")
            # Naslov z barvno piko
            header = f" {f_name}"
            with st.expander(f"📁 {header}"):
                st.markdown(f'<div style="height: 3px; background: {f_color}; border-radius: 2px; margin-bottom: 10px;"></div>', unsafe_allow_html=True)
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

    # --- STRAN: PROFIL (Sliko obrežemo in shranimo) ---
    elif st.session_state.page == "profile":
        st.header("Nastavitve profila")
        
        # 1. Dark mode preklop
        current_dm = settings.get("dark_mode", True)
        new_dm = st.toggle("Temni način", value=current_dm)
        if new_dm != current_dm:
            data["user_settings"][u_name]["dark_mode"] = new_dm
            save_data(data); st.rerun()

        st.divider()

        # 2. Profilna slika
        st.subheader("Profilna slika")
        col_img, col_up = st.columns([1, 2])
        with col_img:
            st.image(settings.get("pfp", "https://www.w3schools.com/howto/img_avatar.png"), width=100)
        
        with col_up:
            up_file = st.file_uploader("Izberi novo sliko", type=['jpg', 'png', 'jpeg'])
            if up_file:
                img = Image.open(up_file)
                # Avtomatsko "obrezovanje" na kvadrat (center crop)
                w, h = img.size
                min_dim = min(w, h)
                img = img.crop(((w - min_dim) // 2, (h - min_dim) // 2, (w + min_dim) // 2, (h + min_dim) // 2))
                img.thumbnail((200, 200))
                
                st.image(img, caption="Predogled", width=100)
                
                if st.button("💾 Shrani sliko"):
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    img_b64 = base64.b64encode(buf.getvalue()).decode()
                    data["user_settings"][u_name]["pfp"] = f"data:image/png;base64,{img_b64}"
                    save_data(data); st.success("Slika posodobljena!"); st.rerun()

        st.divider()

        # 3. Podatki
        new_fn = st.text_input("Ime in priimek", settings.get("full_name", ""))
        if st.button("Posodobi podatke"):
            data["user_settings"][u_name]["full_name"] = new_fn
            save_data(data); st.success("Shranjeno!")

    # --- STRAN: UREJANJE MAPE ---
    elif st.session_state.page == "edit":
        target = st.session_state.edit_folder
        f_obj = data["folders"][u_name][target]
        st.subheader(f"Urejanje: {target}")
        
        new_n = st.text_input("Ime mape", target)
        new_c = st.color_picker("Barva zavihka", f_obj.get("color", "#4A90E2"))
        
        for i, card in enumerate(f_obj["cards"]):
            c_q, c_a, c_d = st.columns([1, 1, 0.2])
            f_obj["cards"][i]["q"] = c_q.text_input(f"V", card["q"], key=f"q{i}")
            f_obj["cards"][i]["a"] = c_a.text_input(f"O", card["a"], key=f"a{i}")
            if c_d.button("🗑️", key=f"d{i}"): f_obj["cards"].pop(i); save_data(data); st.rerun()
            
        if st.button("➕ Dodaj kartico"):
            f_obj["cards"].append({"q": "", "a": "", "known": False})
            save_data(data); st.rerun()
        if st.button("💾 Shrani in nazaj"):
            data["folders"][u_name][new_n] = {"cards": f_obj["cards"], "color": new_c}
            if new_n != target: del data["folders"][u_name][target]
            save_data(data); st.session_state.page = "home"; st.rerun()
