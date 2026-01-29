import streamlit as st
import google.generativeai as genai
import json
import os
import hashlib

# --- 1. TRAJNO SHRANJEVANJE IN VARNOST ---
DB_FILE = "qai_users_data.json"

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"users": {}, "folders": {}}
    return {"users": {}, "folders": {}}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. NASTAVITVE IN STIL ---
st.set_page_config(page_title="Qai - Študijski Tinder", layout="centered")

st.markdown("""
<style>
    div.stButton > button {
        display: block; margin: 0 auto; width: 100% !important;
        min-height: 70px !important; border-radius: 15px;
        font-size: 20px !important; font-weight: bold;
        white-space: nowrap !important;
    }
    .flip-btn > button {
        height: 300px !important; white-space: normal !important;
        background-color: #ffffff !important; color: #1f1f1f !important;
        border: 2px solid #e6e9ef !important;
    }
    .status-box {
        padding: 10px; border-radius: 10px; background-color: #f0f2f6;
        margin-bottom: 20px; text-align: center; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. INICIALIZACIJA STANJA ---
data = load_data()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = "login"
if 'card_index' not in st.session_state: st.session_state.card_index = 0
if 'flipped' not in st.session_state: st.session_state.flipped = False

# POVEZAVA Z AI
MOJ_KLJUC = "AIzaSyCAcL8sBxKVyDW-QW6z06lm56WaQ-9tTUY"
genai.configure(api_key=MOJ_KLJUC)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- 4. STRANI ---

# --- PRIJAVA / REGISTRACIJA ---
if not st.session_state.logged_in:
    st.title("🔐 Qai Prijava")
    tab1, tab2 = st.tabs(["Prijava", "Registracija"])
    
    with tab1:
        u_name = st.text_input("Uporabniško ime", key="login_u")
        u_pass = st.text_input("Geslo", type="password", key="login_p")
        if st.button("Vstopi"):
            hashed_p = hash_password(u_pass)
            if u_name in data["users"] and data["users"][u_name] == hashed_p:
                st.session_state.logged_in = True
                st.session_state.user = u_name
                st.session_state.page = "home"
                st.rerun()
            else:
                st.error("Napačno ime ali geslo.")
                
    with tab2:
        new_u = st.text_input("Izberi uporabniško ime", key="reg_u")
        new_p = st.text_input("Izberi geslo", type="password", key="reg_p")
        if st.button("Ustvari račun"):
            if new_u in data["users"]:
                st.warning("Uporabnik že obstaja.")
            elif new_u and new_p:
                data["users"][new_u] = hash_password(new_p)
                data["folders"][new_u] = {} # Pripravimo prostor za njegove mape
                save_data(data)
                st.success("Račun ustvarjen! Zdaj se lahko prijaviš.")
            else:
                st.error("Izpolni vsa polja.")

# --- DOMOV (Ko je uporabnik prijavljen) ---
elif st.session_state.page == "home":
    st.title(f"👋 Zdravo, {st.session_state.user}!")
    if st.sidebar.button("Odjava"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

    user_folders = data["folders"].get(st.session_state.user, {})

    with st.expander("✨ Ustvari novo mapo z AI"):
        fname = st.text_input("Ime mape")
        vpr = st.text_area("Vprašanja")
        vir = st.text_area("Vir besedila")
        if st.button("Ustvari"):
            if fname and vpr and vir:
                with st.spinner("Qai ustvarja..."):
                    res = model.generate_content(f"Format: Vprašanje|Odgovor. Vir: {vir}. Teme: {vpr}")
                    cards = [{"q": l.split("|")[0].strip(), "a": l.split("|")[1].strip(), "known": False} 
                             for l in res.text.strip().split('\n') if "|" in l]
                    if cards:
                        data["folders"][st.session_state.user][fname] = cards
                        save_data(data)
                        st.rerun()

    st.divider()
    for f_name, cards in user_folders.items():
        znam_st = sum(1 for c in cards if c.get('known', False))
        col1, col2, col3, col4 = st.columns([2, 0.8, 0.8, 0.4])
        col1.markdown(f"📁 **{f_name}** (`{znam_st}/{len(cards)}`)")
        if col2.button("📖 Uči", key=f"l_{f_name}"): 
            st.session_state.current_folder = f_name
            st.session_state.page = "learning"
            st.session_state.card_index = 0
            st.rerun()
        if col3.button("📝 Test", key=f"t_{f_name}"): 
            st.session_state.current_folder = f_name
            st.session_state.page = "testing"
            st.session_state.card_index = 0
            st.rerun()
        if col4.button("🗑️", key=f"del_{f_name}"):
            del data["folders"][st.session_state.user][f_name]
            save_data(data)
            st.rerun()

# --- UČENJE ---
elif st.session_state.page == "learning":
    user_folders = data["folders"][st.session_state.user]
    folder = user_folders[st.session_state.current_folder]
    
    if st.button("🏠 Domov"): st.session_state.page = "home"; st.rerun()
    
    if st.session_state.card_index < len(folder):
        card = folder[st.session_state.card_index]
        st.progress(st.session_state.card_index / len(folder))
        
        status_txt = "POZNAM" if card.get('known') else "ŠE NE POZNAM"
        st.markdown(f"<div class='status-box'>{status_txt}</div>", unsafe_allow_html=True)
        
        vsebina = card['a'] if st.session_state.flipped else card['q']
        st.markdown('<div class="flip-btn">', unsafe_allow_html=True)
        if st.button(vsebina, key="flip"):
            st.session_state.flipped = not st.session_state.flipped
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ ZNAM"):
            data["folders"][st.session_state.user][st.session_state.current_folder][st.session_state.card_index]['known'] = True
            save_data(data)
            st.session_state.card_index += 1
            st.session_state.flipped = False
            st.rerun()
        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
        if st.button("❌ NE ZNAM"):
            data["folders"][st.session_state.user][st.session_state.current_folder][st.session_state.card_index]['known'] = False
            save_data(data)
            st.session_state.card_index += 1
            st.session_state.flipped = False
            st.rerun()
    else:
        st.success("Mapa končana!")
        if st.button("Nazaj na domov"): st.session_state.page = "home"; st.rerun()

# --- TESTIRANJE ---
elif st.session_state.page == "testing":
    user_folders = data["folders"][st.session_state.user]
    folder = user_folders[st.session_state.current_folder]
    if st.button("🏠 Domov"): st.session_state.page = "home"; st.rerun()

    if st.session_state.card_index < len(folder):
        card = folder[st.session_state.card_index]
        st.info(f"**Vprašanje:** {card['q']}")
        user_ans = st.text_input("Tvoj odgovor:", key=f"test_{st.session_state.card_index}")
        
        if st.button("PREVERI"): st.session_state.flipped = True
            
        if st.session_state.flipped:
            st.write(f"**Pravilen:** {card['a']}")
            if st.button("✅ OZNAČI KOT PRAVILNO"):
                data["folders"][st.session_state.user][st.session_state.current_folder][st.session_state.card_index]['known'] = True
                save_data(data)
                st.session_state.card_index += 1
                st.session_state.flipped = False
                st.rerun()
            if st.button("❌ OZNAČI KOT NAPAČNO"):
                data["folders"][st.session_state.user][st.session_state.current_folder][st.session_state.card_index]['known'] = False
                save_data(data)
                st.session_state.card_index += 1
                st.session_state.flipped = False
                st.rerun()
    else:
        st.success("Test končan!")
        if st.button("Domov"): st.session_state.page = "home"; st.rerun()
