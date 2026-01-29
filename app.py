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
    /* Gumbi */
    div.stButton > button {
        display: block; margin: 0 auto; width: 100% !important;
        min-height: 50px !important; border-radius: 10px;
        font-size: 16px !important; font-weight: bold;
    }
    .flip-btn > button {
        height: 300px !important; white-space: normal !important;
        background-color: #ffffff !important; color: #1f1f1f !important;
        border: 2px solid #e6e9ef !important; font-size: 22px !important;
    }
    /* Kartica mape z barvnim zavihkom */
    .folder-container {
        display: flex; align-items: center; background: #f9f9f9;
        border-radius: 12px; margin-bottom: 10px; padding: 10px;
        border: 1px solid #eee; position: relative;
    }
    .color-tab {
        width: 12px; height: 50px; border-radius: 6px; margin-right: 15px;
    }
    .folder-info { flex-grow: 1; }
    .folder-title { font-weight: bold; font-size: 18px; margin: 0; }
    .folder-meta { font-size: 12px; color: #666; margin: 0; }
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

# PRIJAVA
if not st.session_state.logged_in:
    st.title("🔐 Qai Prijava")
    u = st.text_input("Uporabniško ime")
    p = st.text_input("Geslo", type="password")
    if st.button("Vstopi"):
        if u in data["users"] and data["users"][u] == hash_password(p):
            st.session_state.logged_in, st.session_state.user, st.session_state.page = True, u, "home"
            st.rerun()
        else: st.error("Napačni podatki.")

# DOMOV
elif st.session_state.page == "home":
    st.title(f"👋 Qai Shramba")
    if st.sidebar.button("Odjava"):
        st.session_state.logged_in = False
        st.rerun()

    user_folders = data["folders"].get(st.session_state.user, {})

    with st.expander("✨ Ustvari novo mapo"):
        fn = st.text_input("Ime mape")
        vir_ai = st.text_area("Snov / Gradivo")
        if st.button("Generiraj kartice"):
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
        znam = sum(1 for c in folder["cards"] if c["known"])
        
        # Vizualna vrstica mape
        st.markdown(f"""
            <div class="folder-container">
                <div class="color-tab" style="background-color: {folder['color']};"></div>
                <div class="folder-info">
                    <p class="folder-title">📁 {f_name}</p>
                    <p class="folder-meta">Napredek: {znam}/{len(folder['cards'])}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Gumbi pod mapo
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
    f_name = st.session_state.edit_folder
    folder = data["folders"][st.session_state.user][f_name]
    
    st.title(f"⚙️ Urejanje: {f_name}")
    
    new_name = st.text_input("Ime mape", f_name)
    new_color = st.color_picker("Barva zavihka", folder["color"])
    new_source = st.text_area("Snov / Gradivo", folder.get("source", ""))
    
    st.divider()
    st.subheader("Posamezne kartice")
    for i, card in enumerate(folder["cards"]):
        col_q, col_a = st.columns(2)
        folder["cards"][i]["q"] = col_q.text_input(f"Vprašanje {i+1}", card["q"], key=f"q_{i}")
        folder["cards"][i]["a"] = col_a.text_input(f"Odgovor {i+1}", card["a"], key=f"a_{i}")

    col_s, col_n, col_d = st.columns([1, 1, 1])
    if col_s.button("💾 Shrani in nazaj"):
        updated_folder = folder.copy()
        updated_folder["color"] = new_color
        updated_folder["source"] = new_source
        
        # Če se ime spremeni
        del data["folders"][st.session_state.user][f_name]
        data["folders"][st.session_state.user][new_name] = updated_folder
        save_data(data)
        st.session_state.page = "home"
        st.rerun()
        
    if col_n.button("❌ Prekliči"):
        st.session_state.page = "home"
        st.rerun()
        
    if col_d.button("🗑️ Izbriši mapo"):
        del data["folders"][st.session_state.user][f_name]
        save_data(data)
        st.session_state.page = "home"
        st.rerun()

# --- UČENJE IN TESTIRANJE (Logika ostaja ista) ---
elif st.session_state.page == "learning":
    folder_data = data["folders"][st.session_state.user][st.session_state.current_folder]
    cards = folder_data["cards"]
    st.button("🏠 Nazaj", on_click=lambda: setattr(st.session_state, 'page', 'home'))
    if st.session_state.card_index < len(cards):
        card = cards[st.session_state.card_index]
        st.progress(st.session_state.card_index / len(cards))
        st.markdown(f'<div class="flip-btn">', unsafe_allow_html=True)
        if st.button(card['a'] if st.session_state.flipped else card['q'], key="flip"):
            st.session_state.flipped = not st.session_state.flipped
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        if st.button("✅ ZNAM"):
            cards[st.session_state.card_index]['known'] = True
            save_data(data); st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
        if st.button("❌ NE ZNAM"):
            cards[st.session_state.card_index]['known'] = False
            save_data(data); st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
    else: st.session_state.page = "home"; st.rerun()
