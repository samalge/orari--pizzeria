import streamlit as st
import json
import os
import pandas as pd

st.set_page_config(page_title="Gestione Tavoli Pizzeria", layout="wide")
st.title("📋 Gestione Turni e Orari del Personale")

STAFF_FILE = "orari_dipendenti.json"

# --- FUNZIONI DATABASE DIPENDENTI ---
def carica_orari():
    if os.path.exists(STAFF_FILE):
        try:
            with open(STAFF_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def salva_orari(dati):
    with open(STAFF_FILE, "w") as f:
        json.dump(dati, f, indent=4)

db_orari = carica_orari()

# Elenco dei giorni della settimana
giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# --- BARRA LATERALE: GESTIONE ANAGRAFICA STAFF ---
st.sidebar.header("👤 Gestione Personale")

# 1. Inserimento nuovo dipendente
nuovo_nome = st.sidebar.text_input("Nome Nuovo Dipendente:", placeholder="es. Marco").strip()
if st.sidebar.button("➕ Aggiungi Dipendente"):
    if nuovo_nome == "":
        st.sidebar.error("⚠️ Inserisci un nome valido.")
    elif nuovo_nome in db_orari:
        st.sidebar.error("⚠️ Questo dipendente esiste già.")
    else:
        db_orari[nuovo_nome] = {g: "Riposo" for g in giorni}
        salva_orari(db_orari)
        st.sidebar.success(f"✅ {nuovo_nome} aggiunto!")
        st.rerun()

st.sidebar.markdown("<hr style='margin: 10px 0; border: 0.5px solid #555;'>", unsafe_allow_html=True)

# 2. MODIFICA NOME (Rinomina rapida)
if db_orari:
    st.sidebar.subheader("✏️ Rinomina Dipendente")
    dipendente_da_rinominare = st.sidebar.selectbox("Seleziona chi cambiare:", list(db_orari.keys()), key="select_rinomina")
    nome_aggiornato = st.sidebar.text_input("Nuovo nome per questo dipendente:", value=dipendente_da_rinominare, key="input_rinomina").strip()
    
    if st.sidebar.button("💾 Aggiorna Nome"):
        if nome_aggiornato == "":
            st.sidebar.error("⚠️ Il nome non può essere vuoto.")
        elif nome_aggiornato in db_orari and nome_aggiornato != dipendente_da_rinominare:
            st.sidebar.error("⚠️ Questo nome è già utilizzato da un altro dipendente.")
        else:
            # Sostituiamo la chiave mantenendo intatti i vecchi orari inseriti
            db_orari[nome_aggiornato] = db_orari.pop(dipendente_da_rinominare)
            salva_orari(db_orari)
            st.sidebar.success(f"✅ Nome aggiornato in {nome_aggiornato}!")
            st.rerun()

    st.sidebar.markdown("<hr style='margin: 10px 0; border: 0.5px solid #555;'>", unsafe_allow_html=True)

    # 3. Rimozione dipendente esistente
    dipendente_da_eliminare = st.sidebar.selectbox("Elimina Dipendente:", list(db_orari.keys()), key="select_elimina")
    if st.sidebar.button("🗑️ Rimuovi Definitivamente"):
        del db_orari[dipendente_da_eliminare]
        salva_orari(db_orari)
        st.sidebar.success(f"✅ Rimossa la scheda di {dipendente_da_eliminare}")
        st.rerun()
else:
    st.sidebar.info("Nessun dipendente registrato.")

st.sidebar.markdown("<hr style='margin: 15px 0; border: 0.5px solid #555;'>", unsafe_allow_html=True)

# --- TABELLONE PRINCIPALE DEGLI ORARI ---
if not db_orari:
    st.info("💡 Inizia aggiungendo i nomi dei tuoi dipendenti nella barra laterale di sinistra.")
else:
    st.header("🕒 Modifica Turni Settimanali")
    st.write("Seleziona un dipendente per modificare i suoi orari di entrata e uscita nei vari giorni.")
    
    dipendente_selezionato = st.selectbox("Scegli il dipendente da modificare:", list(db_orari.keys()), key="main_select_dip")
    
    st.markdown(f"### Scheda Oraria di: **{dipendente_selezionato}**")
    
    orari_attuali = db_orari[dipendente_selezionato]
    nuovi_orari_inseriti = {}
    
    # Organizziamo il layout grafico a colonne per i giorni
    col1, col2, col3, col4 = st.columns(4)
    col5, col6, col7, _ = st.columns(4)
    colonne_giorni = [col1, col2, col3, col4, col5, col6, col7]
    
    for i, giorno in enumerate(giorni):
        with colonne_giorni[i]:
            valore_attuale = orari_attuali.get(giorno, "Riposo")
            opzione_tipo = st.radio(f"Stato {giorno}:", ["Turno", "Riposo"], index=0 if valore_attuale != "Riposo" else 1, key=f"tipo_{giorno}")
            
            if opzione_tipo == "Turno":
                testo_orario_default = valore_attuale if valore_attuale != "Riposo" else "10:00 - 15:00 / 18:00 - 23:00"
                orario_testo = st.text_input(f"Orario {giorno}:", value=testo_orario_default, key=f"input_{giorno}")
                nuovi_orari_inseriti[giorno] = orario_testo if orario_testo.strip() != "" else "Riposo"
            else:
                nuovi_orari_inseriti[giorno] = "Riposo"
                st.caption("🛌 Giorno di Riposo")
                
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 SALVA ORARI SETTIMANALI", type="primary"):
        db_orari[dipendente_selezionato] = nuovi_orari_inseriti
        st.write(db_orari)
        salva_database = carica_orari()
        salva_database[dipendente_selezionato] = nuovi_orari_inseriti
        salva_orari(salva_database)
        st.success(f"✅ Orari di {dipendente_selezionato} aggiornati con successo nel database!")
        st.rerun()

    # --- TABELLA RIASSUNTIVA FINALE ---
    st.markdown("<hr style='margin: 30px 0; border: 0.5px solid #444;'>", unsafe_allow_html=True)
    st.header("📅 Quadro Orario Generale della Settimana")
    
    dati_tabella = []
    for nome, turni in db_orari.items():
        riga = {"Dipendente": nome}
        for giorno in giorni:
            riga[giorno] = turni.get(giorno, "Riposo")
        dati_tabella.append(riga)
        
    df = pd.DataFrame(dati_tabella)
    st.dataframe(df.set_index("Dipendente"), use_container_width=True)
