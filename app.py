import streamlit as st
import google.generativeai as genai
import json
import os

# --- 1. TRAJNO SHRANJEVANJE (JSON) ---
DB_FILE = "qai_data.json"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.folders, f, ensure_ascii=False, indent=4)

# --- 2. NASTAVITVE IN STIL (Fix za cele besede) ---
st.set_page_config(page_title="Qai - Študijski Tinder", layout="centered")

st.markdown("""
<style>
    /* Glavni stil za vse gumbe - preprečevanje polovičnih besed */
    div.stButton > button {
        display: block;
        margin: 0 auto;
        width: 100% !important;
        min-height: 70px !important;
        border-radius: 15px;
        font-size: 20px !important;
        font-weight: bold;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        white-space: nowrap !important; /* Beseda se ne bo nikoli prelomila */
        overflow: hidden;
        text-overflow: ellipsis;
        padding: 0 20px !important;
    }
    
    /* Poseben stil za kartico (Flip gumb) - tukaj prelom dovolimo */
    .flip-btn > button {
        height: 300px !important;
        background-color: #ffffff !important;
        color: #1f1f1f !important;
        border: 2px solid #e6e9ef !important;
        font-size: 22px !important;
        white-space: normal !important; 
    }

    .status-box {
        padding: 10px; border-radius: 10px; background-color: #f0f2f6;
        margin-bottom: 20px; text-align: center; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. INICIALIZACIJA ---
if 'folders' not in st.session_state:
    st.session_state.folders = load_data()

if 'page' not in st.session_state: st.session_state.page = "home"
if 'current_folder' not in st.session_state: st.session_state.current_folder = None
if 'card_index' not in st.session_state: st.session_state.card_index = 0
if 'flipped' not in st.session_state: st.session_state.flipped = False

# POVEZAVA Z GEMINI 2.5 (Vpiši svoj ključ)
MOJ_KLJUC = "AIzaSyCAcL8sBxKVyDW-QW6z06lm56WaQ-9tTUY"
genai.configure(api_key=MOJ_KLJUC)
model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- 4. FUNKCIJE ---
def start_session(folder_name, mode):
    st.session_state.current_folder = folder_name
    st.session_state.page = mode
    st.session_state.card_index = 0
    st.session_state.flipped = False

def update_card_status(knew_it):
    folder_name = st.session_state.current_folder
    idx = st.session_state.card_index
    st.session_state.folders[folder_name][idx]['known'] = knew_it
    save_data()
    st.session_state.card_index += 1
    st.session_state.flipped = False
    st.rerun()

# --- 5. STRANI ---

# --- DOMOV ---
if st.session_state.page == "home":
    st.title("📂 Qai Shramba")
    
    with st.expander("✨ Ustvari novo mapo z AI"):
        fname = st.text_input("Ime mape")
        vpr = st.text_area("Vprašanja (opiši teme)")
        vir = st.text_area("Vir besedila")
        if st.button("Ustvari"):
            if fname and vpr and vir:
                with st.spinner("Qai ustvarja kartice..."):
                    try:
                        res = model.generate_content(f"Format: Vprašanje|Odgovor. Vir: {vir}. Teme: {vpr}")
                        cards = [{"q": l.split("|")[0].strip(), "a": l.split("|")[1].strip(), "known": False} 
                                 for l in res.text.strip().split('\n') if "|" in l]
                        if cards:
                            st.session_state.folders[fname] = cards
                            save_data()
                            st.rerun()
                    except Exception as e: st.error(f"Napaka AI: {e}")

    st.divider()
    if not st.session_state.folders:
        st.info("Ni še map. Ustvari prvo zgoraj!")

    for f_name in list(st.session_state.folders.keys()):
        cards = st.session_state.folders[f_name]
        znam_st = sum(1 for c in cards if c.get('known', False))
        skupaj = len(cards)
        
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 0.8, 0.8, 0.4])
            col1.markdown(f"📁 **{f_name}** \n`✅ {znam_st} / {skupaj}`")
            if col2.button("📖 Uči", key=f"l_{f_name}"): start_session(f_name, "learning"); st.rerun()
            if col3.button("📝 Test", key=f"t_{f_name}"): start_session(f_name, "testing"); st.rerun()
            if col4.button("🗑️", key=f"del_{f_name}"):
                del st.session_state.folders[f_name]
                save_data()
                st.rerun()
            
            with st.expander("Pregled kartic"):
                for c in cards:
                    status = "✅" if c.get('known') else "❌"
                    st.write(f"{status} {c['q']}")

# --- UČENJE ---
elif st.session_state.page == "learning":
    folder = st.session_state.folders[st.session_state.current_folder]
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

        if st.button("✅ ZNAM"): update_card_status(True)
        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
        if st.button("❌ NE ZNAM"): update_card_status(False)
    else:
        st.balloons()
        st.success("Mapa končana!")
        if st.button("Nazaj na domov"): st.session_state.page = "home"; st.rerun()

# --- TESTIRANJE ---
elif st.session_state.page == "testing":
    folder = st.session_state.folders[st.session_state.current_folder]
    if st.button("🏠 Domov"): st.session_state.page = "home"; st.rerun()

    if st.session_state.card_index < len(folder):
        card = folder[st.session_state.card_index]
        st.progress(st.session_state.card_index / len(folder))
        st.info(f"**Vprašanje:** {card['q']}")
        user_ans = st.text_input("Tvoj odgovor:", key=f"test_{st.session_state.card_index}")
        
        if st.button("PREVERI"): st.session_state.flipped = True
            
        if st.session_state.flipped:
            st.write(f"**Pravilen odgovor:** {card['a']}")
            with st.spinner("Qai ocenjuje..."):
                try:
                    eval = model.generate_content(f"Ali je '{user_ans}' pomensko isto kot '{card['a']}'? Odgovori samo z DA ali NE.")
                    st.write("Pravilno!" if "DA" in eval.text.upper() else "Napačno.")
                except: st.write("AI ocena ni uspela.")
            
            if st.button("✅ OZNAČI KOT PRAVILNO"): update_card_status(True)
            if st.button("❌ OZNAČI KOT NAPAČNO"): update_card_status(False)
    else:
        st.success("Test končan!")
        if st.button("Domov"): st.session_state.page = "home"; st.rerun()
