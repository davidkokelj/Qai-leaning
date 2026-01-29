import streamlit as st
import google.generativeai as genai
import json
import os
import hashlib
import base64
from PIL import Image
from io import BytesIO

# --- 1. TRAJNO SHRANJEVANJE ---
DB_FILE = "qai_users_data.json"

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if "users" not in d: d = {"users": {}, "folders": {}, "user_settings": {}}
                return d
        except: return {"users": {}, "folders": {}, "user_settings": {}}
    return {"users": {}, "folders": {}, "user_settings": {}}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. NASTAVITVE IN STIL ---
st.set_page_config(page_title="Qai", layout="centered")

# Dinamični CSS glede na Light/Dark mode
def apply_theme(dark_mode):
    bg = "#121212" if dark_mode else "#FFFFFF"
    txt = "#FFFFFF" if dark_mode else "#000000"
    card_bg = "#1E1E1E" if dark_mode else "#F9F9F9"
    border = "#333" if dark_mode else "#EEE"
    
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {bg}; color: {txt}; }}
        div.stButton > button {{
            width: 100% !important; min-height: 50px !important;
            border-radius: 10px; font-weight: bold; white-space: nowrap !important;
        }}
        .folder-container {{
            display: flex; align-items: center; background: {card_bg}; 
            border-radius: 12px; margin-bottom: 5px; padding: 10px; border: 1px solid {border};
        }}
        .color-tab {{ width: 6px; height: 35px; border-radius: 3px; margin-right: 15px; }}
        .flip-btn > button {{
            height: 280px !important; background-color: {card_bg} !important;
            color: {txt} !important; border: 1px solid {border} !important; font-size: 20px !important;
        }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. INICIALIZACIJA ---
data = load_data()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = "login"

# AI nastavitve
MOJ_KLJUC = "AIzaSyCAcL8sBxKVyDW-QW6z06lm56WaQ-9tTUY"
genai.configure(api_key=MOJ_KLJUC)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- 4. STRANI ---

if not st.session_state.logged_in:
    st.title("🔐 Dobrodošel v Qai")
    t_log, t_reg = st.tabs(["Prijava", "Registracija"])
    with t_log:
        u_l = st.text_input("Uporabnik")
        p_l = st.text_input("Geslo", type="password")
        if st.button("Vstopi"):
            if u_l in data["users"] and data["users"][u_l] == hash_password(p_l):
                st.session_state.logged_in, st.session_state.user, st.session_state.page = True, u_l, "home"
                st.rerun()
            else: st.error("Napačni podatki.")
    with t_reg:
        u_r = st.text_input("Novo ime")
        p_r = st.text_input("Novo geslo", type="password")
        if st.button("Registriraj"):
            if u_r and p_r and u_r not in data["users"]:
                data["users"][u_r] = hash_password(p_r)
                data["folders"][u_r] = {}
                data["user_settings"][u_r] = {"dark_mode": True, "pfp": None}
                save_data(data); st.success("Ustvarjeno!")

else:
    # Nalaganje nastavitev uporabnika
    user_settings = data["user_settings"].get(st.session_state.user, {"dark_mode": True, "pfp": None})
    apply_theme(user_settings.get("dark_mode", True))

    # --- DESNI PROFILNI MENI ---
    with st.sidebar:
        if user_settings.get("pfp"):
            st.image(user_settings["pfp"], width=100)
        st.title(f"👤 {st.session_state.user}")
        if st.button("🏠 Domov"): st.session_state.page = "home"; st.rerun()
        if st.button("⚙️ Nastavitve profila"): st.session_state.page = "profile"; st.rerun()
        st.divider()
        if st.button("🚪 Odjava"): 
            st.session_state.logged_in = False
            st.rerun()

    # --- STRAN PROFIL ---
    if st.session_state.page == "profile":
        st.header("⚙️ Nastavitve profila")
        
        # 1. Dark Mode
        dm = st.toggle("Dark Mode", value=user_settings.get("dark_mode", True))
        if dm != user_settings.get("dark_mode"):
            data["user_settings"][st.session_state.user]["dark_mode"] = dm
            save_data(data); st.rerun()

        # 2. Profilna slika
        img_file = st.file_uploader("Naloži profilno sliko", type=['png', 'jpg', 'jpeg'])
        if img_file:
            img = Image.open(img_file)
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            data["user_settings"][st.session_state.user]["pfp"] = f"data:image/png;base64,{img_str}"
            save_data(data); st.success("Slika posodobljena!"); st.rerun()

        # 3. Uporabniško ime in Geslo
        new_u = st.text_input("Novo uporabniško ime", st.session_state.user)
        new_p = st.text_input("Novo geslo (pusti prazno, če ne želiš menjati)", type="password")
        
        if st.button("Shrani spremembe profila"):
            if new_u != st.session_state.user:
                data["users"][new_u] = data["users"].pop(st.session_state.user)
                data["folders"][new_u] = data["folders"].pop(st.session_state.user)
                data["user_settings"][new_u] = data["user_settings"].pop(st.session_state.user)
                st.session_state.user = new_u
            if new_p:
                data["users"][st.session_state.user] = hash_password(new_p)
            save_data(data); st.success("Profil posodobljen!")

    # --- STRAN DOMOV ---
    elif st.session_state.page == "home":
        st.title("📂 Moje mape")
        col_a, col_b = st.columns(2)
        with col_a.expander("✨ AI"):
            fn_ai = st.text_input("Ime")
            vir_ai = st.text_area("Snov")
            if st.button("Generiraj"):
                res = model.generate_content(f"Format: Vprašanje|Odgovor. Vir: {vir_ai}")
                cards = [{"q": l.split("|")[0].strip(), "a": l.split("|")[1].strip(), "known": False} 
                         for l in res.text.strip().split('\n') if "|" in l]
                data["folders"][st.session_state.user][fn_ai] = {"cards": cards, "color": "#4A90E2"}
                save_data(data); st.rerun()
        with col_b.expander("📁 Ročno"):
            fn_m = st.text_input("Ime ")
            if st.button("Ustvari"):
                data["folders"][st.session_state.user][fn_m] = {"cards": [{"q":"", "a":""}], "color": "#9B59B6"}
                save_data(data); st.session_state.edit_folder = fn_m; st.session_state.page = "edit"; st.rerun()

        st.divider()
        user_folders = data["folders"].get(st.session_state.user, {})
        for f_name, folder in user_folders.items():
            st.markdown(f'<div class="folder-container"><div class="color-tab" style="background-color: {folder.get("color", "#4A90E2")};"></div><div><b>{f_name}</b></div></div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1, 1, 0.2])
            if c1.button("📖 Uči", key=f"l_{f_name}"):
                st.session_state.current_folder, st.session_state.page, st.session_state.card_index = f_name, "learning", 0
                st.rerun()
            if c2.button("📝 Test", key=f"t_{f_name}"):
                st.session_state.current_folder, st.session_state.page, st.session_state.card_index = f_name, "testing", 0
                st.rerun()
            if c3.button("⋮", key=f"o_{f_name}"):
                st.session_state.edit_folder, st.session_state.page = f_name, "edit"
                st.rerun()

    # --- STRAN ZA UREJANJE ---
    elif st.session_state.page == "edit":
        f_old = st.session_state.edit_folder
        folder = data["folders"][st.session_state.user][f_old]
        st.subheader(f"⚙️ {f_old}")
        new_n = st.text_input("Ime", f_old)
        new_c = st.color_picker("Barva", folder.get("color", "#4A90E2"))
        for i, card in enumerate(folder["cards"]):
            c_q, c_a, c_d = st.columns([1, 1, 0.2])
            folder["cards"][i]["q"] = c_q.text_input(f"V", card["q"], key=f"q{i}")
            folder["cards"][i]["a"] = c_a.text_input(f"O", card["a"], key=f"a{i}")
            if c_d.button("🗑️", key=f"d{i}"): folder["cards"].pop(i); save_data(data); st.rerun()
        if st.button("➕ Dodaj"): folder["cards"].append({"q":"","a":""}); save_data(data); st.rerun()
        if st.button("💾 Shrani"):
            del data["folders"][st.session_state.user][f_old]
            data["folders"][st.session_state.user][new_n] = {"cards": folder["cards"], "color": new_c}
            save_data(data); st.session_state.page = "home"; st.rerun()

    # --- STRAN ZA UČENJE ---
    elif st.session_state.page == "learning":
        cards = data["folders"][st.session_state.user][st.session_state.current_folder]["cards"]
        if st.button("🏠"): st.session_state.page = "home"; st.rerun()
        if st.session_state.card_index < len(cards):
            card = cards[st.session_state.card_index]
            st.markdown('<div class="flip-btn">', unsafe_allow_html=True)
            if st.button(card['a'] if st.session_state.get('flipped') else card['q']):
                st.session_state.flipped = not st.session_state.get('flipped', False)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✅"): st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
            if c2.button("❌"): st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
        else: st.success("Konec!"); st.button("Nazaj", on_click=lambda: setattr(st.session_state, 'page', 'home'))
