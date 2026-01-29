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
    bg = "#0E1117" if dark_mode else "#FFFFFF"
    txt = "#FFFFFF" if dark_mode else "#000000"
    card_bg = "#161B22" if dark_mode else "#F0F2F6"
    
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {bg}; color: {txt}; }}
        
        /* Barvna črta pred mapo */
        .folder-item {{
            display: flex; align-items: center; gap: 10px; padding: 5px 0;
        }}
        .v-line {{
            width: 4px; height: 24px; border-radius: 2px;
        }}

        /* Stil za kartico učenja */
        .flashcard {{
            background-color: {card_bg};
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            min-height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            border: 1px solid #30363d;
            cursor: pointer;
            margin-bottom: 20px;
        }}
        
        /* Sidebar brez okvirčkov */
        [data-testid="stSidebar"] div.stButton > button {{
            border: none !important; background: transparent !important;
            text-align: left !important; width: 100% !important; color: {txt} !important;
        }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. INICIALIZACIJA ---
data = load_data()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = "login"
if 'card_index' not in st.session_state: st.session_state.card_index = 0
if 'flipped' not in st.session_state: st.session_state.flipped = False

genai.configure(api_key="AIzaSyCAcL8sBxKVyDW-QW6z06lm56WaQ-9tTUY")
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- 4. LOGIKA ---

if not st.session_state.logged_in:
    st.title("🚀 Qai")
    t1, t2 = st.tabs(["Prijava", "Registracija"])
    with t1:
        u = st.text_input("Uporabnik")
        p = st.text_input("Geslo", type="password")
        if st.button("Vstop"):
            if u in data["users"] and data["users"][u] == hash_password(p):
                st.session_state.logged_in, st.session_state.user, st.session_state.page = True, u, "home"
                st.rerun()
    with t2:
        ur = st.text_input("Novo up. ime")
        fn = st.text_input("Ime")
        ln = st.text_input("Priimek")
        pr = st.text_input("Novo geslo", type="password")
        if st.button("Ustvari"):
            if ur and pr:
                data["users"][ur] = hash_password(pr)
                data["folders"][ur] = {}
                data["user_settings"][ur] = {"dark_mode": True, "full_name": f"{fn} {ln}"}
                save_data(data); st.success("Registriran!")

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
        c1, c2 = st.columns(2)
        with c1.expander("✨ Ustvari z AI"):
            fn_ai = st.text_input("Ime mape", key="ai_name")
            txt_ai = st.text_area("Vpiši ali prilepi snov", key="ai_txt")
            if st.button("Generiraj kartice"):
                res = model.generate_content(f"Ustvari vprašanja in odgovore iz vira. Format: Vprašanje|Odgovor. Vir: {txt_ai}")
                cards = [{"q": l.split("|")[0], "a": l.split("|")[1], "known": False} for l in res.text.split('\n') if "|" in l]
                data["folders"][u_name][fn_ai] = {"cards": cards, "color": "#4A90E2"}
                save_data(data); st.rerun()
        with c2.expander("📁 Ustvari ročno"):
            fn_m = st.text_input("Ime nove mape", key="m_name")
            if st.button("Ustvari prazno"):
                data["folders"][u_name][fn_m] = {"cards": [], "color": "#9B59B6"}
                save_data(data); st.session_state.edit_folder, st.session_state.page = fn_m, "edit"; st.rerun()

        st.divider()
        for f_name, f_data in data["folders"].get(u_name, {}).items():
            color = f_data.get("color", "#4A90E2")
            # Vizualni prikaz: Črta | Ime
            st.markdown(f'''<div class="folder-item"><div class="v-line" style="background:{color}"></div><span>📁 {f_name}</span></div>''', unsafe_allow_html=True)
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

    # --- UREJANJE ---
    elif st.session_state.page == "edit":
        target = st.session_state.edit_folder
        f_obj = data["folders"][u_name][target]
        st.subheader(f"Urejanje: {target}")
        
        new_name = st.text_input("Ime mape", target)
        new_color = st.color_picker("Barva", f_obj.get("color", "#4A90E2"))
        
        st.write("### Kartice")
        for i, card in enumerate(f_obj["cards"]):
            with st.expander(f"Kartica {i+1}: {card['q'][:30]}..."):
                f_obj["cards"][i]["q"] = st.text_input(f"Vprašanje {i}", card["q"], key=f"eq{i}")
                f_obj["cards"][i]["a"] = st.text_input(f"Odgovor {i}", card["a"], key=f"ea{i}")
                if st.button(f"🗑️ Izbriši kartico {i+1}", key=f"del{i}"):
                    f_obj["cards"].pop(i); save_data(data); st.rerun()

        if st.button("➕ Dodaj novo kartico"):
            f_obj["cards"].append({"q": "Vprašanje", "a": "Odgovor", "known": False})
            save_data(data); st.rerun()
        
        st.divider()
        c_save, c_del = st.columns(2)
        if c_save.button("💾 Shrani in zapri"):
            data["folders"][u_name][new_name] = {"cards": f_obj["cards"], "color": new_color}
            if new_name != target: del data["folders"][u_name][target]
            save_data(data); st.session_state.page = "home"; st.rerun()
        if c_del.button("🔥 IZBRIŠI CELO MAPO"):
            del data["folders"][u_name][target]
            save_data(data); st.session_state.page = "home"; st.rerun()

    # --- UČENJE (Flashcards) ---
    elif st.session_state.page == "learning":
        cards = data["folders"][u_name][st.session_state.current_folder]["cards"]
        st.button("⬅️ Nazaj", on_click=lambda: setattr(st.session_state, 'page', 'home'))
        
        if st.session_state.card_index < len(cards):
            card = cards[st.session_state.card_index]
            display_text = card["a"] if st.session_state.flipped else card["q"]
            
            # Interaktivna kartica
            if st.button(display_text, key="card_flip", use_container_width=True):
                st.session_state.flipped = not st.session_state.flipped
                st.rerun()
            
            st.write(f"Kartica {st.session_state.card_index + 1} / {len(cards)}")
            col1, col2 = st.columns(2)
            if col1.button("✅ Znam"):
                st.session_state.card_index += 1
                st.session_state.flipped = False
                st.rerun()
            if col2.button("❌ Ne znam"):
                st.session_state.card_index += 1
                st.session_state.flipped = False
                st.rerun()
        else:
            st.success("Končano!")
            if st.button("Ponovi"): 
                st.session_state.card_index = 0
                st.rerun()

    # --- PROFIL ---
    elif st.session_state.page == "profile":
        st.header("Nastavitve")
        new_dm = st.toggle("Temni način", value=settings.get("dark_mode", True))
        if st.button("Shrani nastavitve"):
            data["user_settings"][u_name]["dark_mode"] = new_dm
            save_data(data); st.rerun()
