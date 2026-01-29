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

# --- 2. NASTAVITVE IN STIL (Brez lomljenja besed) ---
st.set_page_config(page_title="Qai - Študijski Tinder", layout="centered")

st.markdown("""
<style>
    div.stButton > button {
        display: block; margin: 0 auto; width: 100% !important;
        min-height: 50px !important; border-radius: 10px;
        font-size: 16px !important; font-weight: bold;
        white-space: nowrap !important; /* Fix za celo besedo */
    }
    .flip-btn > button {
        height: 280px !important; white-space: normal !important;
        background-color: #ffffff !important; color: #1f1f1f !important;
        border: 2px solid #e6e9ef !important; font-size: 20px !important;
    }
    .folder-container {
        display: flex; align-items: center; background: #ffffff;
        border-radius: 12px; margin-bottom: 5px; padding: 12px;
        border: 1px solid #eee; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .color-tab {
        width: 8px; height: 40px; border-radius: 4px; margin-right: 15px;
    }
    .folder-info { flex-grow: 1; }
    .folder-title { font-weight: bold; font-size: 17px; margin: 0; color: #333; }
</style>
""", unsafe_allow_html=True)

# --- 3. INICIALIZACIJA ---
data = load_data()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = "login"
if 'edit_folder' not in st.session_state: st.session_state.edit_folder = None

# POVEZAVA Z AI
MOJ_KLJUC = "AIzaSyCAcL8sBxKVyDW-QW6z06lm56WaQ-9tTUY"
genai.configure(api_key=MOJ_KLJUC)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- 4. STRANI ---

# STRAN ZA PRIJAVO
if not st.session_state.logged_in:
    st.title("🔐 Qai Vstop")
    tab1, tab2 = st.tabs(["Prijava", "Registracija"])
    with tab1:
        u = st.text_input("Uporabniško ime", key="l_u")
        p = st.text_input("Geslo", type="password", key="l_p")
        if st.button("Vstopi"):
            if u in data["users"] and data["users"][u] == hash_password(p):
                st.session_state.logged_in, st.session_state.user, st.session_state.page = True, u, "home"
                st.rerun()
            else: st.error("Napačni podatki.")
    with tab2:
        nu = st.text_input("Novo ime", key="r_u")
        np = st.text_input("Novo geslo", type="password", key="r_p")
        if st.button("Ustvari račun"):
            if nu and np and nu not in data["users"]:
                data["users"][nu], data["folders"][nu] = hash_password(np), {}
                save_data(data); st.success("Račun ustvarjen!")
            else: st.error("Ime je zasedeno ali polje prazno.")

# DOMOV
elif st.session_state.page == "home":
    st.title(f"👋 Shramba ({st.session_state.user})")
    if st.sidebar.button("Odjava"):
        st.session_state.logged_in = False
        st.rerun()

    user_folders = data["folders"].get(st.session_state.user, {})

    with st.expander("✨ Nova AI mapa"):
        fn = st.text_input("Ime mape")
        vir_ai = st.text_area("Snov za AI")
        if st.button("Ustvari"):
            with st.spinner("Qai razmišlja..."):
                res = model.generate_content(f"Format: Vprašanje|Odgovor. Vir: {vir_ai}")
                cards = [{"q": l.split("|")[0].strip(), "a": l.split("|")[1].strip(), "known": False} 
                         for l in res.text.strip().split('\n') if "|" in l]
                if cards:
                    data["folders"][st.session_state.user][fn] = {"cards": cards, "color": "#4A90E2", "source": vir_ai}
                    save_data(data); st.rerun()

    st.divider()
    
    for f_name in list(user_folders.keys()):
        folder = user_folders[f_name]
        
        # --- FIX ZA TYPEERROR: Samodejna pretvorba starih podatkov ---
        if isinstance(folder, list):
            folder = {"cards": folder, "color": "#4A90E2", "source": ""}
            data["folders"][st.session_state.user][f_name] = folder
            save_data(data)
        
        znam = sum(1 for c in folder["cards"] if c.get("known", False))
        
        st.markdown(f"""
            <div class="folder-container">
                <div class="color-tab" style="background-color: {folder.get('color', '#4A90E2')};"></div>
                <div class="folder-info">
                    <p class="folder-title">{f_name}</p>
                    <p style="margin:0; font-size:12px;">✅ {znam} / {len(folder['cards'])}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 1, 0.3])
        if c1.button("📖 Uči", key=f"l_{f_name}"):
            st.session_state.current_folder, st.session_state.page, st.session_state.card_index = f_name, "learning", 0
            st.rerun()
        if c2.button("📝 Test", key=f"t_{f_name}"):
            st.session_state.current_folder, st.session_state.page, st.session_state.card_index = f_name, "testing", 0
            st.rerun()
        if c3.button("⋮", key=f"opt_{f_name}"):
            st.session_state.edit_folder = f_name
            st.session_state.page = "edit"
            st.rerun()

# STRAN ZA UREJANJE
elif st.session_state.page == "edit":
    f_old = st.session_state.edit_folder
    folder = data["folders"][st.session_state.user][f_old]
    
    st.subheader(f"⚙️ Urejanje: {f_old}")
    new_n = st.text_input("Ime mape", f_old)
    new_c = st.color_picker("Barva zavihka", folder.get("color", "#4A90E2"))
    new_s = st.text_area("Izvorna snov", folder.get("source", ""))
    
    st.write("---")
    for i, card in enumerate(folder["cards"]):
        with st.container():
            col_q, col_a = st.columns(2)
            folder["cards"][i]["q"] = col_q.text_input(f"Vpr {i+1}", card["q"], key=f"eq_{i}")
            folder["cards"][i]["a"] = col_a.text_input(f"Odg {i+1}", card["a"], key=f"ea_{i}")

    if st.button("💾 Shrani spremembe"):
        folder["color"], folder["source"] = new_c, new_s
        del data["folders"][st.session_state.user][f_old]
        data["folders"][st.session_state.user][new_n] = folder
        save_data(data)
        st.session_state.page = "home"
        st.rerun()
    
    if st.button("🗑️ Izbriši celo mapo"):
        del data["folders"][st.session_state.user][f_old]
        save_data(data)
        st.session_state.page = "home"
        st.rerun()
    
    if st.button("⬅️ Prekliči"):
        st.session_state.page = "home"
        st.rerun()

# UČENJE
elif st.session_state.page == "learning":
    folder = data["folders"][st.session_state.user][st.session_state.current_folder]["cards"]
    if st.button("🏠 Nazaj"): st.session_state.page = "home"; st.rerun()
    if st.session_state.card_index < len(folder):
        card = folder[st.session_state.card_index]
        st.progress(st.session_state.card_index / len(folder))
        st.markdown('<div class="flip-btn">', unsafe_allow_html=True)
        if st.button(card['a'] if st.session_state.flipped else card['q'], key="f"):
            st.session_state.flipped = not st.session_state.flipped
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        if st.button("✅ ZNAM"):
            folder[st.session_state.card_index]['known'] = True
            save_data(data); st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
        if st.button("❌ NE ZNAM"):
            folder[st.session_state.card_index]['known'] = False
            save_data(data); st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
    else: st.success("Bravo!"); st.button("Domov", on_click=lambda: setattr(st.session_state, 'page', 'home'))
