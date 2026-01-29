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
    div.stButton > button {
        display: block; margin: 0 auto; width: 100% !important;
        min-height: 60px !important; border-radius: 12px;
        font-size: 18px !important; font-weight: bold;
        white-space: nowrap !important;
    }
    .flip-btn > button {
        height: 300px !important; white-space: normal !important;
        background-color: #ffffff !important; color: #1f1f1f !important;
        border: 2px solid #e6e9ef !important;
    }
    .folder-card {
        padding: 15px; border-radius: 15px; border-left: 10px solid #ccc;
        margin-bottom: 10px; background-color: #f9f9f9;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. INICIALIZACIJA ---
data = load_data()
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = "login"
if 'card_index' not in st.session_state: st.session_state.card_index = 0
if 'flipped' not in st.session_state: st.session_state.flipped = False

MOJ_KLJUC = "AIzaSyCAcL8sBxKVyDW-QW6z06lm56WaQ-9tTUY"
genai.configure(api_key=MOJ_KLJUC)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- 4. STRANI ---

if not st.session_state.logged_in:
    st.title("🔐 Qai Prijava")
    t1, t2 = st.tabs(["Prijava", "Registracija"])
    with t1:
        u = st.text_input("Uporabniško ime")
        p = st.text_input("Geslo", type="password")
        if st.button("Vstopi"):
            if u in data["users"] and data["users"][u] == hash_password(p):
                st.session_state.logged_in, st.session_state.user, st.session_state.page = True, u, "home"
                st.rerun()
            else: st.error("Napačni podatki.")
    with t2:
        nu = st.text_input("Novo ime")
        np = st.text_input("Novo geslo", type="password")
        if st.button("Ustvari račun"):
            if nu and np and nu not in data["users"]:
                data["users"][nu], data["folders"][nu] = hash_password(np), {}
                save_data(data); st.success("Račun ustvarjen!")
            else: st.error("Napaka pri registraciji.")

elif st.session_state.page == "home":
    st.title(f"👋 Zdravo, {st.session_state.user}!")
    if st.sidebar.button("Odjava"):
        st.session_state.logged_in = False
        st.rerun()

    user_folders = data["folders"].get(st.session_state.user, {})

    with st.expander("✨ Ustvari novo mapo z AI"):
        fn = st.text_input("Ime mape")
        vpr_ai = st.text_area("Vprašanja za AI")
        vir_ai = st.text_area("Snov / Gradivo")
        if st.button("Generiraj"):
            with st.spinner("Qai ustvarja..."):
                res = model.generate_content(f"Format: Vprašanje|Odgovor. Vir: {vir_ai}. Teme: {vpr_ai}")
                cards = [{"q": l.split("|")[0].strip(), "a": l.split("|")[1].strip(), "known": False} 
                         for l in res.text.strip().split('\n') if "|" in l]
                if cards:
                    data["folders"][st.session_state.user][fn] = {"cards": cards, "color": "#4A90E2", "source": vir_ai, "prompts": vpr_ai}
                    save_data(data); st.rerun()

    st.divider()
    
    for f_name in list(user_folders.keys()):
        folder = user_folders[f_name]
        # Če je stara verzija podatkov, popravi strukturo
        if "cards" not in folder: folder = {"cards": folder, "color": "#4A90E2", "source": "", "prompts": ""}
        
        znam = sum(1 for c in folder["cards"] if c["known"])
        
        # Vizualna kartica mape
        st.markdown(f"""<div class='folder-card' style='border-left-color: {folder['color']};'>
            <h3 style='margin:0;'>📁 {f_name}</h3>
            <p style='margin:0;'>Napredek: {znam}/{len(folder['cards'])}</p>
        </div>""", unsafe_allow_html=True)
        
        # Gumbi za hitre akcije (Minimizirano s pomočjo expanderja)
        with st.expander(f"Upravljanje mape: {f_name}"):
            c1, c2 = st.columns(2)
            if c1.button("📖 Uči", key=f"l_{f_name}"):
                st.session_state.current_folder, st.session_state.page, st.session_state.card_index = f_name, "learning", 0
                st.rerun()
            if c2.button("📝 Test", key=f"t_{f_name}"):
                st.session_state.current_folder, st.session_state.page, st.session_state.card_index = f_name, "testing", 0
                st.rerun()
            
            st.divider()
            st.subheader("Urejanje")
            
            # 1. Barva in Ime
            new_name = st.text_input("Preimenuj mapo", f_name, key=f"rn_{f_name}")
            new_color = st.color_picker("Barva mape", folder["color"], key=f"cp_{f_name}")
            
            # 2. Urejanje snovi in vprašanj
            edit_vpr = st.text_area("Vprašanja (za AI)", folder.get("prompts", ""), key=f"ev_{f_name}")
            edit_snov = st.text_area("Snov / Gradivo", folder.get("source", ""), key=f"es_{f_name}")
            
            col_save, col_del = st.columns(2)
            if col_save.button("Shrani spremembe", key=f"sv_{f_name}"):
                # Posodobi podatke
                updated_folder = folder.copy()
                updated_folder["color"] = new_color
                updated_folder["prompts"] = edit_vpr
                updated_folder["source"] = edit_snov
                
                # Če se ime spremeni, zamenjaj ključ v diktu
                del data["folders"][st.session_state.user][f_name]
                data["folders"][st.session_state.user][new_name] = updated_folder
                save_data(data); st.rerun()
                
            if col_del.button("🗑️ Izbriši mapo", key=f"dl_{f_name}"):
                del data["folders"][st.session_state.user][f_name]
                save_data(data); st.rerun()

elif st.session_state.page == "learning":
    # (Logika učenja ostaja ista, le pot do kartic je zdaj folder["cards"])
    folder_data = data["folders"][st.session_state.user][st.session_state.current_folder]
    folder = folder_data["cards"]
    if st.button("🏠 Domov"): st.session_state.page = "home"; st.rerun()
    
    if st.session_state.card_index < len(folder):
        card = folder[st.session_state.card_index]
        st.progress(st.session_state.card_index / len(folder))
        st.markdown(f"<div class='status-box' style='color:{folder_data['color']}'>KARTICA {st.session_state.card_index + 1}</div>", unsafe_allow_html=True)
        
        vsebina = card['a'] if st.session_state.flipped else card['q']
        st.markdown('<div class="flip-btn">', unsafe_allow_html=True)
        if st.button(vsebina, key="flip"):
            st.session_state.flipped = not st.session_state.flipped
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ ZNAM"):
            data["folders"][st.session_state.user][st.session_state.current_folder]["cards"][st.session_state.card_index]['known'] = True
            save_data(data); st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
        st.write("")
        if st.button("❌ NE ZNAM"):
            data["folders"][st.session_state.user][st.session_state.current_folder]["cards"][st.session_state.card_index]['known'] = False
            save_data(data); st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
    else:
        st.success("Končano!")
        if st.button("Domov"): st.session_state.page = "home"; st.rerun()

# --- TESTING (Logika podobna learning) ---
elif st.session_state.page == "testing":
    folder_data = data["folders"][st.session_state.user][st.session_state.current_folder]
    folder = folder_data["cards"]
    if st.button("🏠 Domov"): st.session_state.page = "home"; st.rerun()
    if st.session_state.card_index < len(folder):
        card = folder[st.session_state.card_index]
        st.info(f"Vprašanje: {card['q']}")
        user_ans = st.text_input("Odgovor:", key=f"t_{st.session_state.card_index}")
        if st.button("Preveri"): st.session_state.flipped = True
        if st.session_state.flipped:
            st.write(f"Pravilen: {card['a']}")
            if st.button("✅ PRAVILNO"):
                data["folders"][st.session_state.user][st.session_state.current_folder]["cards"][st.session_state.card_index]['known'] = True
                save_data(data); st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
            if st.button("❌ NAPAČNO"):
                data["folders"][st.session_state.user][st.session_state.current_folder]["cards"][st.session_state.card_index]['known'] = False
                save_data(data); st.session_state.card_index += 1; st.session_state.flipped = False; st.rerun()
    else: st.session_state.page = "home"; st.rerun()
