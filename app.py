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

# --- 2. STIL ---
st.set_page_config(page_title="Qai", layout="centered")

def apply_styles(dark_mode):
    bg, txt, card = ("#0E1117", "#FFFFFF", "#161B22") if dark_mode else ("#FFFFFF", "#000000", "#F0F2F6")
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {bg}; color: {txt}; }}
        [data-testid="stSidebar"] div.stButton > button {{
            border: none !important; background: transparent !important;
            text-align: left !important; width: 100% !important; color: {txt} !important;
        }}
        .folder-header-ui {{ display: flex; align-items: center; margin-bottom: -15px; }}
        .v-line {{ width: 5px; height: 25px; border-radius: 10px; margin-right: 12px; }}
        .flashcard-ui {{
            background: {card}; padding: 40px; border-radius: 15px;
            text-align: center; border: 1px solid #30363d; font-size: 20px;
            margin-bottom: 20px;
        }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. INICIALIZACIJA ---
data = load_data()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'page' not in st.session_state: st.session_state.page = "home"
if 'flipped' not in st.session_state: st.session_state.flipped = False

genai.configure(api_key="AIzaSyCAcL8sBxKVyDW-QW6z06lm56WaQ-9tTUY")
model = genai.GenerativeModel('gemini-1.5-flash') # Podpora za slike

# --- 4. LOGIKA ---

if not st.session_state.logged_in:
    st.title("🚀 Qai")
    t1, t2 = st.tabs(["Prijava", "Registracija"])
    with t1:
        u, p = st.text_input("Uporabnik"), st.text_input("Geslo", type="password")
        if st.button("Vstop"):
            if u in data["users"] and data["users"][u] == hash_password(p):
                st.session_state.logged_in, st.session_state.user = True, u
                st.rerun()
    with t2:
        ur, fn, ln, pr = st.text_input("Up. ime"), st.text_input("Ime"), st.text_input("Priimek"), st.text_input("Geslo ", type="password")
        if st.button("Ustvari"):
            if ur and pr:
                data["users"][ur] = hash_password(pr)
                data["folders"][ur], data["user_settings"][ur] = {}, {"dark_mode": True, "full_name": f"{fn} {ln}"}
                save_data(data); st.success("Račun ustvarjen!")

else:
    u_name = st.session_state.user
    settings = data["user_settings"].get(u_name, {"dark_mode": True})
    apply_styles(settings.get("dark_mode", True))

    with st.sidebar:
        st.write(f"👤 **{settings.get('full_name', u_name)}**")
        if st.button("🏠 Domov"): st.session_state.page = "home"; st.rerun()
        if st.button("⚙️ Profil"): st.session_state.page = "profile"; st.rerun()
        st.divider()
        if st.button("🚪 Odjava"): st.session_state.logged_in = False; st.rerun()

    # --- DOMOV ---
    if st.session_state.page == "home":
        st.title("Moje mape")
        
        tab_ai, tab_img, tab_man = st.tabs(["✨ Avtomatsko dodajanje", "📸 Dodaj z Qai", "📁 Ročno"])
        
        with tab_ai:
            fn_ai = st.text_input("Ime mape", key="ai_n")
            txt_ai = st.text_area("Prilepi snov (besedilo)", key="ai_t")
            if st.button("Generiraj iz besedila"):
                with st.spinner("Qai bere besedilo..."):
                    res = model.generate_content(f"Ustvari Q|A kartice. Format: Vprašanje|Odgovor. Vir: {txt_ai}")
                    cards = [{"q": l.split("|")[0], "a": l.split("|")[1], "known": False} for l in res.text.split('\n') if "|" in l]
                    data["folders"][u_name][fn_ai] = {"cards": cards, "color": "#4A90E2"}
                    save_data(data); st.rerun()

        with tab_img:
            fn_img = st.text_input("Ime mape", key="img_n")
            uploaded_images = st.file_uploader("Naloži slike snovi ali vprašanj", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
            if st.button("Skeniraj slike z Qai"):
                if uploaded_images:
                    with st.spinner("Qai analizira slike..."):
                        all_cards = []
                        for img_file in uploaded_images:
                            img = Image.open(img_file)
                            res = model.generate_content(["Iz te slike razberi snov in ustvari vprašanja in odgovore. Format: Vprašanje|Odgovor.", img])
                            cards = [{"q": l.split("|")[0], "a": l.split("|")[1], "known": False} for l in res.text.split('\n') if "|" in l]
                            all_cards.extend(cards)
                        data["folders"][u_name][fn_img] = {"cards": all_cards, "color": "#FF4B4B"}
                        save_data(data); st.rerun()

        with tab_man:
            fn_m = st.text_input("Ime nove mape", key="m_n")
            if st.button("Ustvari prazno mapo"):
                data["folders"][u_name][fn_m] = {"cards": [], "color": "#9B59B6"}
                save_data(data); st.session_state.edit_folder, st.session_state.page = fn_m, "edit"; st.rerun()

        st.divider()
        # Izris map s pokončno črto
        for f_name, f_data in data["folders"].get(u_name, {}).items():
            color = f_data.get("color", "#4A90E2")
            st.markdown(f'<div class="folder-header-ui"><div class="v-line" style="background:{color}"></div><b>📁 {f_name}</b></div>', unsafe_allow_html=True)
            with st.expander(""):
                c1, c2, c3 = st.columns([1, 1, 0.4])
                if c1.button("📖 Uči", key=f"l_{f_name}"):
                    st.session_state.current_folder, st.session_state.page, st.session_state.card_index = f_name, "learning", 0; st.rerun()
                if c2.button("📝 Test", key=f"t_{f_name}"):
                    st.session_state.current_folder, st.session_state.page, st.session_state.card_index = f_name, "testing", 0; st.rerun()
                if c3.button("⋮", key=f"e_{f_name}"):
                    st.session_state.edit_folder, st.session_state.page = f_name, "edit"; st.rerun()

    # --- UREJANJE ---
    elif st.session_state.page == "edit":
        target = st.session_state.edit_folder
        f_obj = data["folders"][u_name][target]
        st.subheader(f"Urejanje: {target}")
        new_name = st.text_input("Ime mape", target)
        new_color = st.color_picker("Barva črte", f_obj.get("color", "#4A90E2"))
        
        for i, card in enumerate(f_obj["cards"]):
            with st.expander(f"Kartica {i+1}: {card['q'][:30]}..."):
                f_obj["cards"][i]["q"] = st.text_input(f"Vprašanje {i}", card["q"])
                f_obj["cards"][i]["a"] = st.text_input(f"Odgovor {i}", card["a"])
                if st.button(f"🗑️ Izbriši kartico {i+1}"):
                    f_obj["cards"].pop(i); save_data(data); st.rerun()
        
        st.divider()
        if st.button("➕ Dodaj kartico"):
            f_obj["cards"].append({"q": "", "a": "", "known": False}); save_data(data); st.rerun()
        
        c_s, c_d = st.columns(2)
        if c_s.button("💾 Shrani"):
            data["folders"][u_name][new_name] = {"cards": f_obj["cards"], "color": new_color}
            if new_name != target: del data["folders"][u_name][target]
            save_data(data); st.session_state.page = "home"; st.rerun()
        if c_d.button("🔥 IZBRIŠI MAPO"):
            del data["folders"][u_name][target]; save_data(data); st.session_state.page = "home"; st.rerun()

    # --- UČENJE ---
    elif st.session_state.page == "learning":
        folder = data["folders"][u_name][st.session_state.current_folder]
        cards = folder["cards"]
        if st.button("⬅️ Nazaj"): st.session_state.page = "home"; st.rerun()
        
        if st.session_state.card_index < len(cards):
            card = cards[st.session_state.card_index]
            txt = card["a"] if st.session_state.flipped else card["q"]
            st.markdown(f'<div class="flashcard-ui">{txt}</div>', unsafe_allow_html=True)
            if st.button("Obrni"): st.session_state.flipped = not st.session_state.flipped; st.rerun()
            
            c1, c2 = st.columns(2)
            if c1.button("✅ Znam"):
                st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
            if c2.button("❌ Ne znam"):
                st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
        else:
            st.success("Mapa končana!")
            if st.button("Ponovi"): st.session_state.card_index = 0; st.rerun()
