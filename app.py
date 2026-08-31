import streamlit as st
import json
import os
import pandas as pd
import re
from datetime import datetime, timedelta

st.set_page_config(page_title="Gestione Turni Pizzeria", layout="wide")
st.title("📋 Gestione Turni e Orari con Calcolo Ore")

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

# --- FUNZIONE INTELLIGENTE DI CALCOLO ORE DA TESTO ---
def calcola_ore_da_stringa(testo_orario):
    if not testo_orario or "riposo" in testo_orario.lower():
        return 0.0
    
    # Trova tutte le coppie di orari nel formato HH:MM - HH:MM o simili
    orari = re.findall(r'(\d{1,2})[:.](\d{2})\s*-\s*(\d{1,2})[:.](\d{2})', testo_orario)
    totale_ore = 0.0
    
    for h1, m1, h2, m2 in orari:
        try:
            inizio = float(h1) + float(m1) / 60.0
            fine = float(h2) + float(m2) / 60.0
            
            # Gestione del turno che scavalca la mezzanotte (es. 18:00 - 01:00)
            if fine < inizio:
                fine += 24.0
                
            totale_ore += (fine - inizio)
        except ValueError:
            continue
            
    return round(totale_ore, 2)

# --- CALCOLO DATE DELLA SETTIMANA CORRENTE ---
oggi = datetime.now()
# Trova il lunedì della settimana corrente
lunedi_corrente = oggi - timedelta(days=oggi.weekday())
date_settimana = {}
for i, g in enumerate(giorni):
    data_giorno = lunedi_corrente + timedelta(days=i)
    date_settimana[g] = data_giorno.strftime("%d/%m")

# --- 🔐 SECURE SESSION LOGIN / LOGOUT SYSTEM ---
st.sidebar.header("🔐 Accesso Amministratore")

if "staff_admin_logged_in" not in st.session_state:
    st.session_state["staff_admin_logged_in"] = False

if not st.session_state["staff_admin_logged_in"]:
    psw_input = st.sidebar.text_input("Inserisci Password di Sicurezza:", type="password", key="staff_psw_field")
    if st.sidebar.button("🔓 Sblocca Sistema"):
        if psw_input == "Samuelmark123#":
            st.session_state["staff_admin_logged_in"] = True
            st.rerun()
        else:
            st.sidebar.error("❌ Password errata!")
else:
    st.sidebar.success("🔒 Modalità Modifica Attiva")
    if st.sidebar.button("🔒 Blocca e Esci"):
        st.session_state["staff_admin_logged_in"] = False
        st.rerun()

st.sidebar.markdown("<hr style='margin: 10px 0; border: 0.5px solid #555;'>", unsafe_allow_html=True)


# --- BARRA LATERALE: GESTIONE ANAGRAFICA STAFF (SOLO SE LOGGATO) ---
if st.session_state["staff_admin_logged_in"]:
    st.sidebar.subheader("👤 Amministrazione Personale")

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
        nome_aggiornato = st.sidebar.text_input("Nuovo nome:", value=dipendente_da_rinominare, key="input_rinomina").strip()
        
        if st.sidebar.button("💾 Aggiorna Nome"):
            if nome_aggiornato == "":
                st.sidebar.error("⚠️ Il nome non può essere vuoto.")
            elif nome_aggiornato in db_orari and nome_aggiornato != dipendente_da_rinominare:
                st.sidebar.error("⚠️ Questo nome è già utilizzato.")
            else:
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


# --- TABELLONE PRINCIPALE DEGLI ORARI ---
if not db_orari:
    st.info("💡 Nessun dipendente registrato nel sistema.")
else:
    # SE LOGGATO: Mostra i pannelli interattivi di modifica turni
    if st.session_state["staff_admin_logged_in"]:
        st.header("🕒 Modifica Turni Settimanali")
        st.write("Modifica gli orari di entrata e uscita nei vari giorni per il dipendente selezionato.")
        
        dipendente_selezionato = st.selectbox("Scegli il dipendente da modificare:", list(db_orari.keys()), key="main_select_dip")
        st.markdown(f"### Scheda Oraria di: **{dipendente_selezionato}**")
        
        orari_attuali = db_orari[dipendente_selezionato]
        nuovi_orari_inseriti = {}
        
        col1, col2, col3, col4 = st.columns(4)
        col5, col6, col7, _ = st.columns(4)
        colonne_giorni = [col1, col2, col3, col4, col5, col6, col7]
        
        for i, giorno in enumerate(giorni):
            with colonne_giorni[i]:
                valore_attuale = orari_attuali.get(giorno, "Riposo")
                opzione_tipo = st.radio(f"Stato {giorno} ({date_settimana[giorno]}):", ["Turno", "Riposo"], index=0 if valore_attuale != "Riposo" else 1, key=f"tipo_{giorno}")
                
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
            salva_database = carica_orari()
            salva_database[dipendente_selezionato] = nuovi_orari_inseriti
            salva_orari(salva_database)
            st.success(f"✅ Orari di {dipendente_selezionato} aggiornati con successo!")
            st.rerun()

    # --- TABELLA RIASSUNTIVA FINALE (SEMPRE VISIBILE A TUTTI) ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.header(f"📅 Quadro Orario Generale (Settimana dal {date_settimana['Lunedì']} al {date_settimana['Domenica']})")
    
    dati_tabella = []
    for nome, turni in db_orari.items():
        riga = {"Dipendente": nome}
        ore_settimanali = 0.0
        
        for giorno in giorni:
            testo_turno = turni.get(giorno, "Riposo")
            # Mostra nel titolo della colonna sia il giorno che la data
            riga[f"{giorno} ({date_settimana[giorno]})"] = testo_turno
            ore_settimanali += calcola_ore_da_stringa(testo_turno)
            
        riga["Ore Settimanali"] = f"{round(ore_settimanali, 1)} h"
        # Calcolo mensile stimato basato sulle 4 settimane canoniche del mese lavorativo
        riga["Ore Mensili (Stima)"] = f"{round(ore_settimanali * 4.33, 1)} h"
        dati_tabella.append(riga)
        
    df = pd.DataFrame(dati_tabella)
    st.dataframe(df.set_index("Dipendente"), use_container_width=True)
