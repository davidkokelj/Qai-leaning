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

# --- 2. NASTAVITVE IN STIL ---
st.set_page_config(page_title="Qai - Študijski Tinder", layout="centered")

st.markdown("""
<style>
    /* Gumbi brez lomljenja besed */
    div.stButton > button {
        display: block; margin: 0 auto; width: 100% !important;
        min-height: 50px !important; border-radius: 10px;
        font-size: 16px !important; font-weight: bold;
        white-space: nowrap !important;
    }
    
    /* Kartica vprašanja */
    .flip-btn > button {
        height: 280px !important; white-space: normal !important;
        background-color: #1E1E1E !important; color: #FFFFFF !important;
        border: 1px solid #333 !important; font-size: 20px !important;
    }

    /* Kartica mape - zlije se z ozadjem */
    .folder-container {
        display: flex; align-items: center; 
        background: transparent; 
        border-radius: 12px; margin-bottom: 5px; padding: 10px;
        border: 1px solid #333;
    }
    .color-tab {
        width: 6px; height: 35px; border-radius: 3px; margin-right: 15px;
    }
    .folder-info { flex-grow: 1; }
    .folder-title { font-weight: bold; font-size: 18px; margin: 0; }
</style>
""", unsafe_allow_html=True)

# --- 3. INICIALIZACIJA ---
data = load_data()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = "login"
if 'edit_folder' not in st.session_state: st.session_state.edit_folder = None

MOJ_KLJUC = "AIzaSyCAcL8sBxKVyDW-QW6z06lm56WaQ-9tTUY"
genai.configure(api_key=MOJ_KLJUC)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- 4. STRANI ---

# PRIJAVA IN REGISTRACIJA
if not st.session_state.logged_in:
    st.title("🔐 Dobrodošel v Qai")
    
    tab_login, tab_reg = st.tabs(["Prijava", "Registracija"])
    
    with tab_login:
        u_login = st.text_input("Uporabniško ime", key="u_log")
        p_login = st.text_input("Geslo", type="password", key="p_log")
        if st.button("Vstopi", key="btn_log"):
            if u_login in data["users"] and data["users"][u_login] == hash_password(p_login):
                st.session_state.logged_in, st.session_state.user, st.session_state.page = True, u_login, "home"
                st.rerun()
            else: st.error("Napačni podatki za prijavo.")
            
    with tab_reg:
        u_reg = st.text_input("Izberi uporabniško ime", key="u_reg")
        p_reg = st.text_input("Izberi geslo", type="password", key="p_reg")
        if st.button("Ustvari račun", key="btn_reg"):
            if u_reg and p_reg:
                if u_reg not in data["users"]:
                    data["users"][u_reg] = hash_password(p_reg)
                    data["folders"][u_reg] = {}
                    save_data(data)
                    st.success("Račun ustvarjen! Zdaj se prijavi v prvem zavihku.")
                else: st.error("To uporabniško ime je že zasedeno.")
            else: st.error("Prosim, izpolni vsa polja.")

# DOMOV
elif st.session_state.page == "home":
    st.title(f"📂 Moje mape")
    if st.sidebar.button("Odjava"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

    user_folders = data["folders"].get(st.session_state.user, {})

    with st.expander("✨ Ustvari novo AI mapo"):
        fn = st.text_input("Ime mape")
        vir_ai = st.text_area("Snov za AI")
        if st.button("Ustvari"):
            with st.spinner("Qai ustvarja..."):
                res = model.generate_content(f"Format: Vprašanje|Odgovor. Vir: {vir_ai}")
                cards = [{"q": l.split("|")[0].strip(), "a": l.split("|")[1].strip(), "known": False} 
                         for l in res.text.strip().split('\n') if "|" in l]
                if cards:
                    data["folders"][st.session_state.user][fn] = {"cards": cards, "color": "#4A90E2", "source": vir_ai}
                    save_data(data); st.rerun()

    st.divider()
    
    for f_name in list(user_folders.keys()):
        folder = user_folders[f_name]
        
        st.markdown(f"""
            <div class="folder-container">
                <div class="color-tab" style="background-color: {folder.get('color', '#4A90E2')};"></div>
                <div class="folder-info">
                    <p class="folder-title">{f_name}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Odpri mapo"):
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
    
    st.write("---")
    for i, card in enumerate(folder["cards"]):
        col_q, col_a, col_d = st.columns([1, 1, 0.2])
        folder["cards"][i]["q"] = col_q.text_input(f"Vpr {i+1}", card["q"], key=f"eq_{i}")
        folder["cards"][i]["a"] = col_a.text_input(f"Odg {i+1}", card["a"], key=f"ea_{i}")
        if col_d.button("🗑️", key=f"dc_{i}"):
            folder["cards"].pop(i)
            save_data(data)
            st.rerun()

    if st.button("➕ Dodaj novo kartico"):
        folder["cards"].append({"q": "Novo vprašanje", "a": "Nov odgovor", "known": False})
        save_data(data)
        st.rerun()

    st.write("---")
    col_save, col_back = st.columns(2)
    if col_save.button("💾 Shrani"):
        folder["color"] = new_c
        # Zamenjava ključa če se ime spremeni
        del data["folders"][st.session_state.user][f_old]
        data["folders"][st.session_state.user][new_n] = folder
        save_data(data)
        st.session_state.page = "home"
        st.rerun()
    
    if col_back.button("⬅️ Nazaj"):
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
        c_z, c_n = st.columns(2)
        if c_z.button("✅ ZNAM"):
            folder[st.session_state.card_index]['known'] = True
            save_data(data); st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
        if c_n.button("❌ NE ZNAM"):
            folder[st.session_state.card_index]['known'] = False
            save_data(data); st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
    else: st.success("Končano!"); st.button("Domov", on_click=lambda: setattr(st.session_state, 'page', 'home'))
