import streamlit as st
import google.generativeai as genai
import json
import os

# --- 1. TRAJNO SHRANJEVANJE (JSON) ---
DB_FILE = "qai_data.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.folders, f, ensure_ascii=False, indent=4)

# --- 2. NASTAVITVE IN STIL ---
st.set_page_config(page_title="Qai - Študijski Tinder", layout="centered")

st.markdown("""
<style>
    div.stButton > button {
        display: block; margin: 0 auto; width: 85% !important;
        height: 70px !important; border-radius: 15px;
        font-size: 20px !important; font-weight: bold;
    }
    .flip-btn > button {
        height: 280px !important; background-color: #ffffff !important;
        color: #1f1f1f !important; border: 2px solid #e6e9ef !important;
    }
    .status-box {
        padding: 10px; border-radius: 10px; background-color: #f0f2f6;
        margin-bottom: 20px; text-align: center;
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

# POVEZAVA Z GEMINI 2.5
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
    
    save_data() # Takoj shranimo v datoteko
    st.session_state.card_index += 1
    st.session_state.flipped = False
    st.rerun()

# --- 5. STRANI ---

if st.session_state.page == "home":
    st.title("📂 Qai Shramba")
    
    with st.expander("✨ Ustvari novo mapo z AI"):
        fname = st.text_input("Ime mape")
        vpr = st.text_area("Vprašanja")
        vir = st.text_area("Vir besedila")
        if st.button("Ustvari"):
            if fname and vpr and vir:
                with st.spinner("Qai ustvarja..."):
                    try:
                        res = model.generate_content(f"Format: Vprašanje|Odgovor. Vir: {vir}. Teme: {vpr}")
                        cards = [{"q": l.split("|")[0].strip(), "a": l.split("|")[1].strip(), "known": False} 
                                 for l in res.text.strip().split('\n') if "|" in l]
                        if cards:
                            st.session_state.folders[fname] = cards
                            save_data()
                            st.rerun()
                    except Exception as e:
                        st.error(f"Napaka: {e}")

    st.divider()
    st.subheader("Tvoje mape")
    
    # Če ni map, pokaži navodila
    if not st.session_state.folders:
        st.info("Tukaj bodo tvoje mape. Ustvari prvo zgoraj!")

    for f_name in list(st.session_state.folders.keys()):
        cards = st.session_state.folders[f_name]
        znam_st = sum(1 for c in cards if c.get('known', False))
        skupaj = len(cards)
        procent = int((znam_st / skupaj) * 100) if skupaj > 0 else 0
        
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 1, 1, 0.5])
            col1.markdown(f"📁 **{f_name}** \n`✅ {znam_st} / {skupaj} ({procent}%)`")
            if col2.button("📖 Uči", key=f"l_{f_name}"): start_session(f_name, "learning"); st.rerun()
            if col3.button("📝 Test", key=f"t_{f_name}"): start_session(f_name, "testing"); st.rerun()
            
            # Gumb za brisanje mape
            if col4.button("🗑️", key=f"del_{f_name}"):
                del st.session_state.folders[f_name]
                save_data()
                st.rerun()
            
            with st.expander("Pregled kartic"):
                for c in cards:
                    status = "✅" if c.get('known') else "❌"
                    st.write(f"{status} {c['q']}")

elif st.session_state.page == "learning":
    folder = st.session_state.folders[st.session_state.current_folder]
    st.button("🏠 Domov", on_click=lambda: setattr(st.session_state, 'page', 'home'))
    
    if st.session_state.card_index < len(folder):
        card = folder[st.session_state.card_index]
        st.progress(st.session_state.card_index / len(folder))
        
        trenutni_status = "Poznam" if card.get('known') else "Še ne poznam"
        st.markdown(f"<div class='status-box'>Status: <b>{trenutni_status}</b></div>", unsafe_allow_html=True)
        
        vsebina = card['a'] if st.session_state.flipped else card['q']
        st.markdown('<div class="flip-btn">', unsafe_allow_html=True)
        if st.button(vsebina, key="flip"):
            st.session_state.flipped = not st.session_state.flipped
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("✅ ZNAM", key="z_btn"): update_card_status(True)
        st.write("")
        if st.button("❌ NE ZNAM", key="n_btn"): update_card_status(False)
    else:
        st.balloons()
        st.success("Konec mape!")
        if st.button("Nazaj na domov"): st.session_state.page = "home"; st.rerun()