import streamlit as st
import json
import os
import re
import shutil
from datetime import datetime, timedelta, time
import pandas as pd


# ============================================================
# CONFIGURAZIONE
# ============================================================

st.set_page_config(
    page_title="Gestione Turni Pizzeria",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

STAFF_FILE = "orari_dipendenti.json"
BACKUP_DIR = "backup_turni"

GIORNI = [
    "Lunedì",
    "Martedì",
    "Mercoledì",
    "Giovedì",
    "Venerdì",
    "Sabato",
    "Domenica"
]

ORE_STANDARD = 40.0
SOGLIA_ATTENZIONE_GIORNALIERA = 10.0


# ============================================================
# STILE
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        color: #777;
        margin-bottom: 1.5rem;
    }

    .metric-box {
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ddd;
        background-color: #fafafa;
        text-align: center;
    }

    .warning-box {
        padding: 12px 15px;
        border-radius: 8px;
        background-color: #fff3cd;
        border-left: 5px solid #f0ad4e;
        margin-bottom: 10px;
    }

    .danger-box {
        padding: 12px 15px;
        border-radius: 8px;
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        margin-bottom: 10px;
    }

    .success-box {
        padding: 12px 15px;
        border-radius: 8px;
        background-color: #d1e7dd;
        border-left: 5px solid #198754;
        margin-bottom: 10px;
    }

    .rest-box {
        padding: 10px;
        border-radius: 8px;
        background-color: #f1f1f1;
        text-align: center;
    }

    @media (max-width: 768px) {
        .main-title {
            font-size: 1.6rem;
        }
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# DATABASE
# ============================================================

def carica_orari():
    """Carica il database JSON."""
    if not os.path.exists(STAFF_FILE):
        return {}

    try:
        with open(STAFF_FILE, "r", encoding="utf-8") as f:
            dati = json.load(f)

        if isinstance(dati, dict):
            return dati

        return {}

    except Exception:
        return {}


def crea_backup():
    """Crea un backup del database prima di modificare i dati."""
    if not os.path.exists(STAFF_FILE):
        return None

    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_file = os.path.join(
            BACKUP_DIR,
            f"orari_dipendenti_{timestamp}.json"
        )

        shutil.copy2(STAFF_FILE, backup_file)

        return backup_file

    except Exception:
        return None


def salva_orari(dati, crea_backup_file=True):
    """Salva il database JSON."""
    if crea_backup_file and os.path.exists(STAFF_FILE):
        crea_backup()

    try:
        with open(STAFF_FILE, "w", encoding="utf-8") as f:
            json.dump(
                dati,
                f,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as e:
        st.error(f"Errore durante il salvataggio: {e}")
        return False


db_orari = carica_orari()


# ============================================================
# PASSWORD
# ============================================================

def get_password_amministratore():
    """
    Cerca la password in st.secrets.
    Se non viene trovata, utilizza la vecchia password
    come fallback per non bloccare l'app.
    """

    try:
        if "ADMIN_PASSWORD" in st.secrets:
            return st.secrets["ADMIN_PASSWORD"]
    except Exception:
        pass

    return "Samuelmark123#"


# ============================================================
# FUNZIONI DATE
# ============================================================

def ottieni_lunedi(data):
    """Restituisce il lunedì della settimana."""
    return data - timedelta(days=data.weekday())


def chiave_settimana(data):
    """Restituisce una chiave stabile per la settimana."""
    lunedi = ottieni_lunedi(data)

    # Usiamo ISO week per evitare problemi a cavallo dell'anno.
    return lunedi.strftime("%Y_W%V")


def informazioni_settimana(data):
    """Restituisce lunedì, domenica e date dei giorni."""
    lunedi = ottieni_lunedi(data)
    domenica = lunedi + timedelta(days=6)

    date = {}

    for i, giorno in enumerate(GIORNI):
        giorno_data = lunedi + timedelta(days=i)
        date[giorno] = giorno_data

    return lunedi, domenica, date


# ============================================================
# FUNZIONI ORARI
# ============================================================

def normalizza_orario(testo):
    """Normalizza alcune varianti comuni degli orari."""

    if not testo:
        return ""

    testo = str(testo).strip()

    testo = testo.replace(".", ":")
    testo = testo.replace("–", "-")
    testo = testo.replace("—", "-")

    return testo


def calcola_ore_da_stringa(testo_orario):
    """
    Calcola le ore da una stringa del tipo:

    10:00 - 15:00
    10:00 - 15:00 / 18:00 - 23:00

    Gestisce anche turni notturni.
    """

    if not testo_orario:
        return 0.0

    testo = normalizza_orario(testo_orario)

    if "riposo" in testo.lower():
        return 0.0

    pattern = r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})'

    intervalli = re.findall(pattern, testo)

    totale_ore = 0.0

    for h1, m1, h2, m2 in intervalli:

        try:
            inizio = int(h1) * 60 + int(m1)
            fine = int(h2) * 60 + int(m2)

            if fine < inizio:
                fine += 24 * 60

            durata = fine - inizio

            totale_ore += durata / 60

        except Exception:
            continue

    return round(totale_ore, 2)


def estrai_intervalli(testo_orario):
    """Restituisce gli intervalli presenti in un turno."""

    if not testo_orario:
        return []

    testo = normalizza_orario(testo_orario)

    pattern = r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})'

    return re.findall(pattern, testo)


def turno_valido(testo_orario):
    """
    Controlla se la stringa contiene almeno un intervallo
    orario valido.
    """

    if not testo_orario:
        return False

    if "riposo" in testo_orario.lower():
        return True

    intervalli = estrai_intervalli(testo_orario)

    if not intervalli:
        return False

    for h1, m1, h2, m2 in intervalli:

        if not (0 <= int(h1) <= 23):
            return False

        if not (0 <= int(h2) <= 23):
            return False

        if not (0 <= int(m1) <= 59):
            return False

        if not (0 <= int(m2) <= 59):
            return False

    return True


def crea_turno_da_orari(
    entrata1,
    uscita1,
    entrata2=None,
    uscita2=None
):
    """Costruisce automaticamente la stringa del turno."""

    turno = ""

    if entrata1 and uscita1:
        turno = (
            f"{entrata1.strftime('%H:%M')} - "
            f"{uscita1.strftime('%H:%M')}"
        )

    if entrata2 and uscita2:
        if turno:
            turno += " / "

        turno += (
            f"{entrata2.strftime('%H:%M')} - "
            f"{uscita2.strftime('%H:%M')}"
        )

    return turno


def minuti_da_stringa_orario(valore):
    """Converte HH:MM in minuti."""

    if not valore:
        return None

    try:
        h, m = valore.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None


# ============================================================
# FUNZIONI DATI SETTIMANALI
# ============================================================

def ottieni_turno(dipendente, settimana, giorno):
    """Restituisce il turno del dipendente per un giorno."""

    dati = db_orari.get(dipendente, {})

    settimana_dati = dati.get(settimana, {})

    return settimana_dati.get(giorno, "Riposo")


def calcola_ore_settimana(dipendente, settimana):
    """Calcola le ore totali settimanali."""

    totale = 0.0

    for giorno in GIORNI:
        totale += calcola_ore_da_stringa(
            ottieni_turno(dipendente, settimana, giorno)
        )

    return round(totale, 2)


def conta_giorni_lavorati(dipendente, settimana):
    """Conta i giorni lavorati."""

    conta = 0

    for giorno in GIORNI:
        turno = ottieni_turno(
            dipendente,
            settimana,
            giorno
        )

        if (
            turno
            and "riposo" not in turno.lower()
            and calcola_ore_da_stringa(turno) > 0
        ):
            conta += 1

    return conta


def conta_riposi(dipendente, settimana):
    return 7 - conta_giorni_lavorati(
        dipendente,
        settimana
    )


# ============================================================
# SESSION STATE
# ============================================================

if "data_riferimento" not in st.session_state:
    st.session_state["data_riferimento"] = datetime.now().date()

if "staff_admin_logged_in" not in st.session_state:
    st.session_state["staff_admin_logged_in"] = False

if "conferma_eliminazione" not in st.session_state:
    st.session_state["conferma_eliminazione"] = False


# ============================================================
# CALCOLO SETTIMANA ATTUALE
# ============================================================

data_riferimento = st.session_state["data_riferimento"]

lunedi_scelto, domenica_scelta, date_settimana = informazioni_settimana(
    data_riferimento
)

settimana_chiave = chiave_settimana(data_riferimento)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">📋 Gestione Turni e Orari</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Gestione settimanale del personale della pizzeria</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR LOGIN
# ============================================================

st.sidebar.header("🔐 Amministratore")

if not st.session_state["staff_admin_logged_in"]:

    psw_input = st.sidebar.text_input(
        "Password:",
        type="password",
        key="staff_psw_field"
    )

    if st.sidebar.button(
        "🔓 Sblocca Sistema",
        use_container_width=True
    ):

        if psw_input == get_password_amministratore():

            st.session_state["staff_admin_logged_in"] = True
            st.rerun()

        else:
            st.sidebar.error("❌ Password errata.")

else:

    st.sidebar.success("🔒 Modalità amministratore attiva")

    if st.sidebar.button(
        "🔒 Blocca e Esci",
        use_container_width=True
    ):

        st.session_state["staff_admin_logged_in"] = False
        st.rerun()


st.sidebar.markdown("---")


# ============================================================
# GESTIONE STAFF
# ============================================================

if st.session_state["staff_admin_logged_in"]:

    st.sidebar.header("👥 Gestione Personale")

    # -------------------------
    # AGGIUNGI
    # -------------------------

    nuovo_nome = st.sidebar.text_input(
        "Nuovo dipendente:",
        placeholder="Es. Marco"
    ).strip()

    if st.sidebar.button(
        "➕ Aggiungi Dipendente",
        use_container_width=True
    ):

        if not nuovo_nome:

            st.sidebar.error(
                "⚠️ Inserisci un nome."
            )

        elif nuovo_nome in db_orari:

            st.sidebar.error(
                "⚠️ Questo dipendente esiste già."
            )

        else:

            db_orari[nuovo_nome] = {}

            if salva_orari(db_orari):

                st.sidebar.success(
                    f"✅ {nuovo_nome} aggiunto."
                )

                st.rerun()

    st.sidebar.markdown("---")

    # -------------------------
    # RINOMINA
    # -------------------------

    if db_orari:

        st.sidebar.subheader("✏️ Rinomina")

        dipendente_rinomina = st.sidebar.selectbox(
            "Dipendente:",
            list(db_orari.keys()),
            key="select_rinomina"
        )

        nuovo_nome_rinomina = st.sidebar.text_input(
            "Nuovo nome:",
            value=dipendente_rinomina,
            key="input_rinomina"
        ).strip()

        if st.sidebar.button(
            "💾 Cambia Nome",
            use_container_width=True
        ):

            if not nuovo_nome_rinomina:

                st.sidebar.error(
                    "⚠️ Il nome non può essere vuoto."
                )

            elif (
                nuovo_nome_rinomina in db_orari
                and nuovo_nome_rinomina != dipendente_rinomina
            ):

                st.sidebar.error(
                    "⚠️ Nome già utilizzato."
                )

            elif nuovo_nome_rinomina != dipendente_rinomina:

                db_orari[nuovo_nome_rinomina] = db_orari.pop(
                    dipendente_rinomina
                )

                salva_orari(db_orari)

                st.sidebar.success(
                    "✅ Nome aggiornato."
                )

                st.rerun()

        st.sidebar.markdown("---")

        # -------------------------
        # ELIMINA
        # -------------------------

        st.sidebar.subheader("🗑️ Elimina")

        dipendente_elimina = st.sidebar.selectbox(
            "Dipendente da eliminare:",
            list(db_orari.keys()),
            key="select_elimina"
        )

        if not st.session_state["conferma_eliminazione"]:

            if st.sidebar.button(
                "🗑️ Elimina Dipendente",
                use_container_width=True
            ):

                st.session_state["conferma_eliminazione"] = True
                st.rerun()

        else:

            st.sidebar.warning(
                f"Sei sicuro di eliminare definitivamente "
                f"{dipendente_elimina}?"
            )

            col_a, col_b = st.sidebar.columns(2)

            with col_a:

                if st.button(
                    "❌ No",
                    key="annulla_elimina",
                    use_container_width=True
                ):

                    st.session_state["conferma_eliminazione"] = False
                    st.rerun()

            with col_b:

                if st.button(
                    "✅ Sì",
                    key="conferma_elimina",
                    use_container_width=True
                ):

                    if dipendente_elimina in db_orari:

                        del db_orari[dipendente_elimina]

                        salva_orari(db_orari)

                    st.session_state["conferma_eliminazione"] = False

                    st.rerun()


# ============================================================
# NAVIGAZIONE SETTIMANA
# ============================================================

st.header("🗓️ Settimana")

col_prev, col_center, col_next = st.columns([1, 2, 1])

with col_prev:

    if st.button(
        "◀️ Settimana precedente",
        use_container_width=True
    ):

        st.session_state["data_riferimento"] -= timedelta(days=7)
        st.rerun()


with col_center:

    data_scelta = st.date_input(
        "Scegli una data:",
        value=data_riferimento,
        key="calendario_navigazione"
    )

    if data_scelta != data_riferimento:

        st.session_state["data_riferimento"] = data_scelta
        st.rerun()


with col_next:

    if st.button(
        "Settimana successiva ▶️",
        use_container_width=True
    ):

        st.session_state["data_riferimento"] += timedelta(days=7)
        st.rerun()


st.markdown(
    f"""
    ### 📅
    **{lunedi_scelto.strftime('%d/%m/%Y')}**
    →
    **{domenica_scelta.strftime('%d/%m/%Y')}**
    """
)


# ============================================================
# AZIONI SETTIMANA
# ============================================================

if db_orari and st.session_state["staff_admin_logged_in"]:

    col_copy, col_reset, col_today = st.columns(3)

    settimana_precedente_data = lunedi_scelto - timedelta(days=7)
    settimana_precedente = chiave_settimana(
        settimana_precedente_data
    )

    with col_copy:

        if st.button(
            "📋 Copia settimana precedente",
            use_container_width=True
        ):

            crea_backup()

            modificati = 0

            for nome in db_orari:

                turni_precedenti = db_orari[
                    nome
                ].get(
                    settimana_precedente,
                    {}
                )

                if turni_precedenti:

                    db_orari[nome][settimana_chiave] = (
                        turni_precedenti.copy()
                    )

                    modificati += 1

            salva_orari(
                db_orari,
                crea_backup_file=False
            )

            st.success(
                f"✅ Settimana copiata per {modificati} dipendenti."
            )

            st.rerun()

    with col_today:

        if st.button(
            "📍 Torna alla settimana attuale",
            use_container_width=True
        ):

            st.session_state["data_riferimento"] = datetime.now().date()
            st.rerun()

    with col_reset:

        if st.button(
            "🧹 Svuota settimana selezionata",
            use_container_width=True
        ):

            crea_backup()

            for nome in db_orari:

                if settimana_chiave in db_orari[nome]:
                    del db_orari[nome][settimana_chiave]

            salva_orari(
                db_orari,
                crea_backup_file=False
            )

            st.success(
                "✅ Settimana svuotata."
            )

            st.rerun()


# ============================================================
# DASHBOARD
# ============================================================

st.markdown("---")

totale_ore_settimana = 0.0
dipendenti_oltre_40 = 0
dipendenti_attivi = len(db_orari)

for nome in db_orari:

    ore = calcola_ore_settimana(
        nome,
        settimana_chiave
    )

    totale_ore_settimana += ore

    if ore > ORE_STANDARD:
        dipendenti_oltre_40 += 1


c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "👥 Dipendenti",
        dipendenti_attivi
    )

with c2:
    st.metric(
        "⏱️ Ore settimana",
        f"{round(totale_ore_settimana, 1)} h"
    )

with c3:
    st.metric(
        "📊 Media per dipendente",
        (
            f"{round(totale_ore_settimana / dipendenti_attivi, 1)} h"
            if dipendenti_attivi
            else "0 h"
        )
    )

with c4:
    st.metric(
        "⚠️ Oltre 40 ore",
        dipendenti_oltre_40
    )


# ============================================================
# AVVISI
# ============================================================

for nome in db_orari:

    ore = calcola_ore_settimana(
        nome,
        settimana_chiave
    )

    if ore > ORE_STANDARD:

        st.markdown(
            f"""
            <div class="danger-box">
            🔴 <strong>ATTENZIONE:</strong>
            {nome} ha {ore:.1f} ore questa settimana,
            cioè oltre le {ORE_STANDARD:.0f} ore standard.
            </div>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# MODIFICA TURNI
# ============================================================

if db_orari and st.session_state["staff_admin_logged_in"]:

    st.markdown("---")

    st.header("🕒 Modifica Turni")

    dipendente_selezionato = st.selectbox(
        "Seleziona dipendente:",
        list(db_orari.keys()),
        key="main_select_dip"
    )

    st.markdown(
        f"### 👤 {dipendente_selezionato}"
    )

    st.caption(
        f"Settimana: "
        f"{lunedi_scelto.strftime('%d/%m/%Y')} - "
        f"{domenica_scelta.strftime('%d/%m/%Y')}"
    )

    orari_settimana_corrente = db_orari.get(
        dipendente_selezionato,
        {}
    ).get(
        settimana_chiave,
        {}
    )

    nuovi_orari = {}

    # --------------------------------------------------------
    # GIORNI
    # --------------------------------------------------------

    for indice, giorno in enumerate(GIORNI):

        data_giorno = date_settimana[giorno]

        valore_attuale = orari_settimana_corrente.get(
            giorno,
            "Riposo"
        )

        st.markdown("---")

        col_title, col_hours = st.columns([2, 1])

        with col_title:

            st.subheader(
                f"{giorno} — {data_giorno.strftime('%d/%m')}"
            )

        with col_hours:

            ore_attuali = calcola_ore_da_stringa(
                valore_attuale
            )

            if ore_attuali > 0:

                if ore_attuali > SOGLIA_ATTENZIONE_GIORNALIERA:

                    st.error(
                        f"🔴 {ore_attuali:.1f} ore"
                    )

                else:

                    st.info(
                        f"⏱️ {ore_attuali:.1f} ore"
                    )

            else:

                st.caption("🛌 Riposo")

        opzioni = ["Turno", "Riposo"]

        tipo_attuale = (
            "Riposo"
            if "riposo" in str(valore_attuale).lower()
            else "Turno"
        )

        indice_tipo = (
            0 if tipo_attuale == "Turno" else 1
        )

        tipo = st.radio(
            f"Stato {giorno}:",
            opzioni,
            index=indice_tipo,
            horizontal=True,
            key=f"tipo_{giorno}"
        )

        if tipo == "Riposo":

            nuovi_orari[giorno] = "Riposo"

            st.markdown(
                '<div class="rest-box">🛌 Giorno di riposo</div>',
                unsafe_allow_html=True
            )

        else:

            # ------------------------------------------------
            # ESTRAZIONE ORARI ATTUALI
            # ------------------------------------------------

            intervalli = estrai_intervalli(
                valore_attuale
            )

            if intervalli:

                h1, m1, h2, m2 = intervalli[0]

                default_entrata1 = time(
                    int(h1),
                    int(m1)
                )

                default_uscita1 = time(
                    int(h2),
                    int(m2)
                )

            else:

                default_entrata1 = time(10, 0)
                default_uscita1 = time(15, 0)

            if len(intervalli) >= 2:

                h1b, m1b, h2b, m2b = intervalli[1]

                default_entrata2 = time(
                    int(h1b),
                    int(m1b)
                )

                default_uscita2 = time(
                    int(h2b),
                    int(m2b)
                )

                secondo_turno = True

            else:

                default_entrata2 = time(18, 0)
                default_uscita2 = time(23, 0)

                secondo_turno = False

            col_a, col_b = st.columns(2)

            with col_a:

                entrata1 = st.time_input(
                    "Entrata 1",
                    value=default_entrata1,
                    key=f"entrata1_{giorno}"
                )

            with col_b:

                uscita1 = st.time_input(
                    "Uscita 1",
                    value=default_uscita1,
                    key=f"uscita1_{giorno}"
                )

            usa_secondo_turno = st.checkbox(
                "➕ Aggiungi secondo turno",
                value=secondo_turno,
                key=f"secondo_{giorno}"
            )

            entrata2 = None
            uscita2 = None

            if usa_secondo_turno:

                col_c, col_d = st.columns(2)

                with col_c:

                    entrata2 = st.time_input(
                        "Entrata 2",
                        value=default_entrata2,
                        key=f"entrata2_{giorno}"
                    )

                with col_d:

                    uscita2 = st.time_input(
                        "Uscita 2",
                        value=default_uscita2,
                        key=f"uscita2_{giorno}"
                    )

            turno_generato = crea_turno_da_orari(
                entrata1,
                uscita1,
                entrata2,
                uscita2
            )

            ore_turno = calcola_ore_da_stringa(
                turno_generato
            )

            # -----------------------------------------------
            # CONTROLLO ENTRATA / USCITA
            # -----------------------------------------------

            if (
                minuti_da_stringa_orario(
                    entrata1.strftime("%H:%M")
                )
                ==
                minuti_da_stringa_orario(
                    uscita1.strftime("%H:%M")
                )
            ):

                st.warning(
                    "⚠️ Entrata e uscita del primo turno coincidono."
                )

            if (
                usa_secondo_turno
                and entrata2
                and uscita2
                and (
                    entrata2.strftime("%H:%M")
                    ==
                    uscita2.strftime("%H:%M")
                )
            ):

                st.warning(
                    "⚠️ Entrata e uscita del secondo turno coincidono."
                )

            if ore_turno > SOGLIA_ATTENZIONE_GIORNALIERA:

                st.error(
                    f"🔴 Attenzione: {ore_turno:.1f} ore "
                    f"nella giornata."
                )

            else:

                st.success(
                    f"⏱️ Totale giornata: {ore_turno:.1f} ore"
                )

            # ------------------------------------------------
            # MODIFICA MANUALE
            # ------------------------------------------------

            modifica_manuale = st.checkbox(
                "✏️ Modifica manualmente il testo del turno",
                key=f"manuale_{giorno}"
            )

            if modifica_manuale:

                turno_finale = st.text_input(
                    "Testo turno:",
                    value=turno_generato,
                    key=f"manuale_input_{giorno}"
                ).strip()

            else:

                turno_finale = turno_generato

            nuovi_orari[giorno] = (
                turno_finale
                if turno_finale
                else "Riposo"
            )


    # ========================================================
    # SALVATAGGIO
    # ========================================================

    st.markdown("---")

    if st.button(
        "💾 SALVA ORARI SETTIMANALI",
        type="primary",
        use_container_width=True
    ):

        errori = []

        for giorno, turno in nuovi_orari.items():

            if turno == "Riposo":
                continue

            if not turno_valido(turno):

                errori.append(
                    f"{giorno}: formato orario non riconosciuto."
                )

        if errori:

            for errore in errori:
                st.error(f"❌ {errore}")

        else:

            crea_backup()

            if settimana_chiave not in db_orari[
                dipendente_selezionato
            ]:

                db_orari[
                    dipendente_selezionato
                ][settimana_chiave] = {}

            db_orari[
                dipendente_selezionato
            ][settimana_chiave] = nuovi_orari

            if salva_orari(
                db_orari,
                crea_backup_file=False
            ):

                st.success(
                    f"✅ Orari di {dipendente_selezionato} "
                    f"salvati correttamente."
                )

                st.rerun()


# ============================================================
# QUADRO GENERALE
# ============================================================

st.markdown("---")

st.header(
    f"📅 Quadro Generale"
)

st.caption(
    f"Settimana dal "
    f"{lunedi_scelto.strftime('%d/%m/%Y')} "
    f"al "
    f"{domenica_scelta.strftime('%d/%m/%Y')}"
)

if not db_orari:

    st.info(
        "💡 Nessun dipendente registrato."
    )

else:

    dati_tabella = []

    for nome, dati_annuali in db_orari.items():

        riga = {
            "Dipendente": nome
        }

        turni = dati_annuali.get(
            settimana_chiave,
            {}
        )

        ore_totali = 0.0

        for giorno in GIORNI:

            turno = turni.get(
                giorno,
                "Riposo"
            )

            ore = calcola_ore_da_stringa(
                turno
            )

            ore_totali += ore

            riga[
                f"{giorno}\n{date_settimana[giorno].strftime('%d/%m')}"
            ] = turno

        riga["Ore Settimanali"] = round(
            ore_totali,
            1
        )

        riga["Giorni Lavorati"] = conta_giorni_lavorati(
            nome,
            settimana_chiave
        )

        riga["Riposi"] = conta_riposi(
            nome,
            settimana_chiave
        )

        dati_tabella.append(riga)

    df = pd.DataFrame(
        dati_tabella
    )

    st.dataframe(
        df.set_index("Dipendente"),
        use_container_width=True,
        height=400
    )


# ============================================================
# VISTA INDIVIDUALE
# ============================================================

if db_orari:

    st.markdown("---")

    st.header("👤 Vista individuale")

    dipendente_vista = st.selectbox(
        "Visualizza turni di:",
        list(db_orari.keys()),
        key="vista_individuale"
    )

    ore_vista = calcola_ore_settimana(
        dipendente_vista,
        settimana_chiave
    )

    giorni_lavorati_vista = conta_giorni_lavorati(
        dipendente_vista,
        settimana_chiave
    )

    a, b, c = st.columns(3)

    with a:
        st.metric(
            "⏱️ Ore",
            f"{ore_vista:.1f} h"
        )

    with b:
        st.metric(
            "📅 Giorni lavorati",
            giorni_lavorati_vista
        )

    with c:
        st.metric(
            "🛌 Riposi",
            7 - giorni_lavorati_vista
        )

    for giorno in GIORNI:

        turno = ottieni_turno(
            dipendente_vista,
            settimana_chiave,
            giorno
        )

        ore = calcola_ore_da_stringa(
            turno
        )

        if "riposo" in turno.lower():

            st.markdown(
                f"**{giorno}** — 🛌 Riposo"
            )

        else:

            st.markdown(
                f"**{giorno}** — 🕒 {turno} "
                f"**({ore:.1f} h)**"
            )


# ============================================================
# RIEPILOGO MENSILE
# ============================================================

st.markdown("---")

st.header("📊 Riepilogo Mensile")

mese_selezionato = st.date_input(
    "Seleziona un mese:",
    value=data_riferimento,
    key="mese_riepilogo"
)

anno = mese_selezionato.year
mese = mese_selezionato.month

primo_giorno_mese = mese_selezionato.replace(day=1)

if mese == 12:

    primo_giorno_mese_successivo = primo_giorno_mese.replace(
        year=anno + 1,
        month=1
    )

else:

    primo_giorno_mese_successivo = primo_giorno_mese.replace(
        month=mese + 1
    )

ultimo_giorno_mese = (
    primo_giorno_mese_successivo
    - timedelta(days=1)
)

settimane_mese = set()

giorno_corrente = primo_giorno_mese

while giorno_corrente <= ultimo_giorno_mese:

    settimane_mese.add(
        chiave_settimana(
            giorno_corrente
        )
    )

    giorno_corrente += timedelta(days=1)


dati_mensili = []

for nome in db_orari:

    ore_mese = 0.0
    giorni_lavorati = 0

    for settimana in settimane_mese:

        ore_mese += calcola_ore_settimana(
            nome,
            settimana
        )

        giorni_lavorati += conta_giorni_lavorati(
            nome,
            settimana
        )

    dati_mensili.append(
        {
            "Dipendente": nome,
            "Ore mese": round(ore_mese, 1),
            "Giorni lavorati": giorni_lavorati,
            "Media ore/settimana": round(
                ore_mese / len(settimane_mese),
                1
            ) if settimane_mese else 0
        }
    )


if dati_mensili:

    df_mese = pd.DataFrame(
        dati_mensili
    )

    st.dataframe(
        df_mese.set_index("Dipendente"),
        use_container_width=True
    )


# ============================================================
# ESPORTAZIONE CSV
# ============================================================

st.markdown("---")

st.header("📤 Esportazione")

if db_orari:

    dati_export = []

    for nome in db_orari:

        turni = db_orari[nome].get(
            settimana_chiave,
            {}
        )

        for giorno in GIORNI:

            turno = turni.get(
                giorno,
                "Riposo"
            )

            dati_export.append(
                {
                    "Dipendente": nome,
                    "Giorno": giorno,
                    "Data": date_settimana[
                        giorno
                    ].strftime("%d/%m/%Y"),
                    "Turno": turno,
                    "Ore": calcola_ore_da_stringa(
                        turno
                    )
                }
            )

    df_export = pd.DataFrame(
        dati_export
    )

    csv = df_export.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "📥 Scarica turni in Excel/CSV",
        data=csv,
        file_name=(
            f"turni_"
            f"{lunedi_scelto.strftime('%Y-%m-%d')}.csv"
        ),
        mime="text/csv",
        use_container_width=True
    )


# ============================================================
# BACKUP
# ============================================================

if st.session_state["staff_admin_logged_in"]:

    st.markdown("---")

    st.header("💾 Backup")

    col_backup1, col_backup2 = st.columns(2)

    with col_backup1:

        if os.path.exists(STAFF_FILE):

            with open(
                STAFF_FILE,
                "rb"
            ) as f:

                st.download_button(
                    "📥 Scarica database JSON",
                    data=f,
                    file_name="orari_dipendenti_backup.json",
                    mime="application/json",
                    use_container_width=True
                )

    with col_backup2:

        if os.path.exists(BACKUP_DIR):

            numero_backup = len(
                [
                    x
                    for x in os.listdir(BACKUP_DIR)
                    if x.endswith(".json")
                ]
            )

            st.info(
                f"💾 Backup automatici presenti: "
                f"{numero_backup}"
            )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "📋 Gestione Turni Pizzeria • "
    f"Ultimo aggiornamento: "
    f"{datetime.now().strftime('%d/%m/%Y %H:%M')}"
)
