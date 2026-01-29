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
                # Varnostni mehanizem za manjkajoče ključe
                if "users" not in d: d["users"] = {}
                if "folders" not in d: d["folders"] = {}
                if "user_settings" not in d: d["user_settings"] = {}
                return d
        except: return {"users": {}, "folders": {}, "user_settings": {}}
    return {"users": {}, "folders": {}, "user_settings": {}}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. STIL (Temni/Svetli način in vizualni popravki) ---
st.set_page_config(page_title="Qai", layout="centered")

def apply_styles(dark_mode):
    bg, txt, card = ("#0E1117", "#FFFFFF", "#161B22") if dark_mode else ("#FFFFFF", "#000000", "#F0F2F6")
    st.markdown(f"""
    <style>
        .stApp {{ background-color: {bg}; color: {txt}; }}
        .folder-header-ui {{ display: flex; align-items: center; margin-bottom: -15px; margin-top: 10px; }}
        .v-line {{ width: 5px; height: 25px; border-radius: 10px; margin-right: 12px; }}
        .flashcard-ui {{
            background: {card}; padding: 40px; border-radius: 15px;
            text-align: center; border: 1px solid #30363d; font-size: 20px; margin-bottom: 20px;
        }}
        [data-testid="stSidebar"] div.stButton > button {{
            border: none !important; background: transparent !important;
            text-align: left !important; width: 100% !important; color: {txt} !important;
        }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. INICIALIZACIJA ---
data = load_data()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'page' not in st.session_state: st.session_state.page = "home"
if 'flipped' not in st.session_state: st.session_state.flipped = False
if 'card_index' not in st.session_state: st.session_state.card_index = 0

# AI Model
try:
    genai.configure(api_key="TVOJ_API_KLJUČ_TUKAJ") # Vstavi svoj ključ!
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("AI trenutno ni na voljo.")

# --- 4. LOGIKA ---

if not st.session_state.logged_in:
    st.title("🚀 Qai")
    t1, t2 = st.tabs(["Prijava", "Registracija"])
    with t1:
        u = st.text_input("Uporabnik", key="login_u")
        p = st.text_input("Geslo", type="password", key="login_p")
        if st.button("Vstop"):
            if u in data["users"] and data["users"][u] == hash_password(p):
                st.session_state.logged_in, st.session_state.user = True, u
                st.rerun()
    with t2:
        ur = st.text_input("Up. ime")
        fn = st.text_input("Ime")
        ln = st.text_input("Priimek")
        pr = st.text_input("Geslo", type="password")
        if st.button("Ustvari"):
            if ur and pr:
                data["users"][ur] = hash_password(pr)
                data["folders"][ur] = {}
                data["user_settings"][ur] = {"dark_mode": True, "full_name": f"{fn} {ln}"}
                save_data(data); st.success("Račun ustvarjen!")

else:
    u_name = st.session_state.user
    # Varen dostop do nastavitev
    u_settings = data["user_settings"].get(u_name, {"dark_mode": True, "full_name": u_name})
    apply_styles(u_settings.get("dark_mode", True))

    with st.sidebar:
        pfp = u_settings.get("pfp", "https://www.w3schools.com/howto/img_avatar.png")
        st.markdown(f'<img src="{pfp}" style="width:80px; height:80px; border-radius:50%; object-fit:cover; margin-bottom:10px;">', unsafe_allow_html=True)
        st.write(f"**{u_settings.get('full_name', u_name)}**")
        
        if st.button("🏠 Domov"): st.session_state.page = "home"; st.rerun()
        if st.button("⚙️ Profil"): st.session_state.page = "profile"; st.rerun()
        st.divider()
        if st.button("🚪 Odjava"): st.session_state.logged_in = False; st.rerun()

    # --- STRAN: DOMOV ---
    if st.session_state.page == "home":
        st.title("Moje mape")
        
        tab_ai, tab_img, tab_man = st.tabs(["✨ Avtomatsko", "📸 Dodaj z Qai", "📁 Ročno"])
        
        with tab_ai:
            f_name = st.text_input("Ime mape", key="ai_n")
            f_txt = st.text_area("Prilepi besedilo", key="ai_t")
            if st.button("Generiraj"):
                res = model.generate_content(f"Format: Vprašanje|Odgovor. Vir: {f_txt}")
                cards = [{"q": l.split("|")[0], "a": l.split("|")[1], "known": False} for l in res.text.split('\n') if "|" in l]
                data["folders"][u_name][f_name] = {"cards": cards, "color": "#4A90E2"}
                save_data(data); st.rerun()

        with tab_img:
            f_img_name = st.text_input("Ime mape", key="img_n")
            imgs = st.file_uploader("Naloži slike", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
            if st.button("Skeniraj z Qai"):
                all_c = []
                for f in imgs:
                    img = Image.open(f)
                    res = model.generate_content(["Ustvari vprašanja in odgovore iz slike. Format: Vprašanje|Odgovor.", img])
                    all_c += [{"q": l.split("|")[0], "a": l.split("|")[1], "known": False} for l in res.text.split('\n') if "|" in l]
                data["folders"][u_name][f_img_name] = {"cards": all_c, "color": "#FF4B4B"}
                save_data(data); st.rerun()

        st.divider()
        # Izris map s popravljeno barvno črto
        for name, f_data in data["folders"].get(u_name, {}).items():
            clr = f_data.get("color", "#4A90E2")
            st.markdown(f'<div class="folder-header-ui"><div class="v-line" style="background:{clr}"></div><b>📁 {name}</b></div>', unsafe_allow_html=True)
            with st.expander(""):
                c1, c2, c3 = st.columns([1, 1, 0.4])
                if c1.button("📖 Uči", key=f"l_{name}"):
                    st.session_state.current_folder, st.session_state.page, st.session_state.card_index = name, "learning", 0; st.rerun()
                if c3.button("⋮", key=f"e_{name}"):
                    st.session_state.edit_folder, st.session_state.page = name, "edit"; st.rerun()

    # --- STRAN: UREJANJE ---
    elif st.session_state.page == "edit":
        target = st.session_state.edit_folder
        f_obj = data["folders"][u_name][target]
        st.subheader(f"Urejanje: {target}")
        
        new_n = st.text_input("Ime", target)
        new_c = st.color_picker("Barva", f_obj.get("color", "#4A90E2"))
        
        for i, card in enumerate(f_obj.get("cards", [])):
            with st.expander(f"Kartica {i+1}"):
                f_obj["cards"][i]["q"] = st.text_input(f"V {i}", card.get("q", ""))
                f_obj["cards"][i]["a"] = st.text_input(f"O {i}", card.get("a", ""))
                if st.button(f"🗑️ Izbriši {i}"): f_obj["cards"].pop(i); save_data(data); st.rerun()
        
        if st.button("➕ Dodaj"): f_obj["cards"].append({"q":"", "a":"", "known":False}); save_data(data); st.rerun()
        
        col_s, col_d = st.columns(2)
        if col_s.button("💾 Shrani"):
            data["folders"][u_name][new_n] = {"cards": f_obj["cards"], "color": new_c}
            if new_n != target: del data["folders"][u_name][target]
            save_data(data); st.session_state.page = "home"; st.rerun()
        if col_d.button("🔥 IZBRIŠI MAPO"):
            del data["folders"][u_name][target]; save_data(data); st.session_state.page = "home"; st.rerun()

    # --- STRAN: UČENJE ---
    elif st.session_state.page == "learning":
        cards = data["folders"][u_name][st.session_state.current_folder].get("cards", [])
        if st.button("⬅️ Nazaj"): st.session_state.page = "home"; st.rerun()
        
        if st.session_state.card_index < len(cards):
            card = cards[st.session_state.card_index]
            txt = card.get("a", "") if st.session_state.flipped else card.get("q", "")
            st.markdown(f'<div class="flashcard-ui">{txt}</div>', unsafe_allow_html=True)
            if st.button("Obrni"): st.session_state.flipped = not st.session_state.flipped; st.rerun()
            
            c1, c2 = st.columns(2)
            if c1.button("✅ Znam"): 
                st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
            if c2.button("❌ Ne znam"): 
                st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
        else:
            st.success("Končano!")
            if st.button("Ponovi"): st.session_state.card_index = 0; st.rerun()

    # --- STRAN: PROFIL ---
    elif st.session_state.page == "profile":
        st.header("Profil")
        new_dm = st.toggle("Temni način", value=u_settings.get("dark_mode", True))
        up = st.file_uploader("Profilna slika", type=['png', 'jpg'])
        if up:
            img = Image.open(up)
            img.thumbnail((150, 150))
            buf = BytesIO()
            img.save(buf, format="PNG")
            data["user_settings"][u_name]["pfp"] = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
            save_data(data); st.success("Slika pripravljena!"); st.rerun()
        
        if st.button("Shrani vse"):
            data["user_settings"][u_name]["dark_mode"] = new_dm
            save_data(data); st.rerun()
