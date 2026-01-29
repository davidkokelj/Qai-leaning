import streamlit as st
import google.generativeai as genai
import json
import os
import hashlib
import base64
from PIL import Image
from io import BytesIO

# --- 1. PODATKI IN VARNOST (Popravek za KeyError/TypeError) ---
DB_FILE = "qai_users_data.json"

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                # Zagotovimo, da vsi glavni ključi obstajajo
                for key in ["users", "folders", "user_settings"]:
                    if key not in d: d[key] = {}
                return d
        except: return {"users": {}, "folders": {}, "user_settings": {}}
    return {"users": {}, "folders": {}, "user_settings": {}}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. STIL IN OBLIKOVANJE (Popravek za gumbe in gumbe v vrstici) ---
st.set_page_config(page_title="Qai", layout="centered")

def apply_styles(dark_mode):
    bg = "#0E1117" if dark_mode else "#FFFFFF"
    txt = "#FFFFFF" if dark_mode else "#000000"
    
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {bg}; color: {txt}; }}
        
        /* Popravek za gumb "Ustvari" (image_53a590) */
        div.stButton > button {{
            width: 100% !important;
            white-space: nowrap !important;
            word-break: keep-all !important;
        }}

        /* Sidebar brez okvirčkov */
        [data-testid="stSidebar"] div.stButton > button {{
            border: none !important;
            background: transparent !important;
            text-align: left !important;
        }}

        /* Barvna črta za mape */
        .folder-bar-ui {{
            height: 20px; width: 5px; border-radius: 2px; margin-right: 10px;
        }}
        .folder-container {{
            display: flex; align-items: center; margin-bottom: 5px;
        }}
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
    st.error("Napaka pri povezavi z AI.")

# --- 4. LOGIKA APLIKACIJE ---

if not st.session_state.logged_in:
    st.title("🚀 Qai")
    t1, t2 = st.tabs(["Prijava", "Registracija"])
    with t1:
        u = st.text_input("Uporabniško ime")
        p = st.text_input("Geslo", type="password")
        if st.button("Vstopi"):
            if u in data["users"] and data["users"][u] == hash_password(p):
                st.session_state.logged_in, st.session_state.user, st.session_state.page = True, u, "home"
                st.rerun()
    with t2:
        ur = st.text_input("Novo up. ime")
        fn = st.text_input("Ime")
        ln = st.text_input("Priimek")
        pr = st.text_input("Novo geslo", type="password")
        if st.button("Registriraj se"):
            if ur and pr:
                data["users"][ur] = hash_password(pr)
                data["folders"][ur] = {}
                data["user_settings"][ur] = {"dark_mode": True, "full_name": f"{fn} {ln}"}
                save_data(data); st.success("Registriran!")

else:
    u_name = st.session_state.user
    # Varno branje nastavitev (Popravek za image_52d353)
    settings = data.get("user_settings", {}).get(u_name, {"dark_mode": True, "full_name": u_name})
    apply_styles(settings.get("dark_mode", True))

    with st.sidebar:
        st.write(f"👤 **{settings.get('full_name', u_name)}**")
        if st.button("🏠 Domov"): st.session_state.page = "home"; st.rerun()
        if st.button("⚙️ Profil"): st.session_state.page = "profile"; st.rerun()
        st.divider()
        if st.button("🚪 Odjava"): st.session_state.logged_in = False; st.rerun()

    # --- STRAN: DOMOV ---
    if st.session_state.page == "home":
        st.title("Moje mape")
        c1, c2 = st.columns(2)
        with c1.expander("✨ Ustvari z AI"):
            fn_ai = st.text_input("Ime mape", key="ai_name")
            txt_ai = st.text_area("Vsebina za kartice", key="ai_txt")
            if st.button("Generiraj"):
                res = model.generate_content(f"Ustvari Q|A kartice iz: {txt_ai}")
                cards = [{"q": l.split("|")[0], "a": l.split("|")[1], "known": False} for l in res.text.split('\n') if "|" in l]
                data["folders"][u_name][fn_ai] = {"cards": cards, "color": "#4A90E2"}
                save_data(data); st.rerun()
        
        with c2.expander("📁 Ustvari ročno"):
            fn_m = st.text_input("Ime nove mape", key="m_name")
            if st.button("Ustvari"):
                data["folders"][u_name][fn_m] = {"cards": [], "color": "#9B59B6"}
                save_data(data); st.session_state.edit_folder, st.session_state.page = fn_m, "edit"; st.rerun()

        st.divider()
        
        # Prikaz map (Popravek za image_52c71a - brez HTML v naslovu)
        user_folders = data.get("folders", {}).get(u_name, {})
        for f_name, f_data in user_folders.items():
            color = f_data.get("color", "#4A90E2")
            
            # Namesto HTML-ja v expanderju uporabimo čisto besedilo, vizualno črto pa znotraj
            with st.expander(f"📁 {f_name}"):
                st.markdown(f'<div style="background:{color}; height:3px; width:100%; border-radius:2px; margin-bottom:10px;"></div>', unsafe_allow_html=True)
                
                # Popravek za TypeError (image_533812)
                cards = f_data.get("cards", [])
                znam = sum(1 for c in cards if c.get("known", False))
                total = len(cards)
                st.write(f"Napredek: {znam}/{total}")

                col1, col2, col3 = st.columns([1, 1, 0.5])
                if col1.button("📖 Uči", key=f"l_{f_name}"):
                    st.session_state.current_folder, st.session_state.page, st.session_state.card_index = f_name, "learning", 0
                    st.rerun()
                if col3.button("⋮", key=f"e_{f_name}"):
                    st.session_state.edit_folder, st.session_state.page = f_name, "edit"
                    st.rerun()

    # --- STRAN: PROFIL (Obrezovanje in shranjevanje slike) ---
    elif st.session_state.page == "profile":
        st.header("Nastavitve profila")
        new_name = st.text_input("Ime in priimek", settings.get("full_name", ""))
        
        up = st.file_uploader("Spremeni profilno sliko", type=['png', 'jpg', 'jpeg'])
        if up:
            img = Image.open(up)
            # Kvadratni izrez
            w, h = img.size
            min_dim = min(w, h)
            img = img.crop(((w-min_dim)//2, (h-min_dim)//2, (w+min_dim)//2, (h+min_dim)//2))
            img.thumbnail((200, 200))
            st.image(img, width=100)
            
            if st.button("Shrani sliko"):
                buf = BytesIO()
                img.save(buf, format="PNG")
                img_b64 = base64.b64encode(buf.getvalue()).decode()
                data["user_settings"][u_name]["pfp"] = f"data:image/png;base64,{img_b64}"
                save_data(data); st.success("Slika shranjena!"); st.rerun()

        if st.button("Shrani podatke"):
            data["user_settings"][u_name]["full_name"] = new_name
            save_data(data); st.success("Podatki posodobljeni!")

    # --- STRAN: UREJANJE MAPE ---
    elif st.session_state.page == "edit":
        target = st.session_state.edit_folder
        f_obj = data["folders"][u_name][target]
        st.subheader(f"Urejanje: {target}")
        
        new_n = st.text_input("Ime mape", target)
        new_c = st.color_picker("Barva", f_obj.get("color", "#4A90E2"))
        
        # Minimizirano urejanje kartic
        for i, card in enumerate(f_obj["cards"]):
            with st.expander(f"Kartica {i+1}: {card['q'][:20]}..."):
                f_obj["cards"][i]["q"] = st.text_input(f"Vprašanje {i}", card["q"])
                f_obj["cards"][i]["a"] = st.text_input(f"Odgovor {i}", card["a"])
                if st.button(f"🗑️ Izbriši", key=f"del{i}"):
                    f_obj["cards"].pop(i); save_data(data); st.rerun()
        
        if st.button("➕ Dodaj kartico"):
            f_obj["cards"].append({"q": "Novo", "a": "Odgovor", "known": False})
            save_data(data); st.rerun()

        st.divider()
        c_save, c_del = st.columns(2)
        if c_save.button("💾 Shrani"):
            data["folders"][u_name][new_n] = {"cards": f_obj["cards"], "color": new_c}
            if new_n != target: del data["folders"][u_name][target]
            save_data(data); st.session_state.page = "home"; st.rerun()
        if c_del.button("🗑️ IZBRIŠI MAPO"):
            del data["folders"][u_name][target]
            save_data(data); st.session_state.page = "home"; st.rerun()
