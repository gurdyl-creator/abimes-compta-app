import streamlit as st
import sqlite3
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- BASE DE DONNÉES ---
def init_db():
    conn = sqlite3.connect("abimes_compta.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS config_tarifs (id INTEGER PRIMARY KEY, ik_chauffeur REAL, subv_km_club REAL)''')
    c.execute("SELECT COUNT(*) FROM config_tarifs")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO config_tarifs VALUES (1, 0.15, 0.02)")
    c.execute('''CREATE TABLE IF NOT EXISTS sorties (id_sortie TEXT PRIMARY KEY, nom_sortie TEXT, email_responsable TEXT, mot_de_passe_unique TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS participants (id_participant INTEGER PRIMARY KEY AUTOINCREMENT, id_sortie TEXT, nom_format TEXT, email TEXT, statut_speleo TEXT, genre TEXT, tranche_age TEXT, propose_voiture INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- SESSIONS ---
if "connecte" not in st.session_state: st.session_state["connecte"] = False
if "sortie_id" not in st.session_state: st.session_state["sortie_id"] = None

st.set_page_config(page_title="ABIMES", page_icon="🦇", layout="centered")

# --- SI DECONNECTE ---
if not st.session_state["connecte"]:
    st.title("🦇 Club ABIMES")
    t_creer, t_conn = st.tabs(["🆕 Créer", "🔑 Connexion"])
    
    with t_creer:
        with st.form("fc"):
            nom = st.text_input("Nom de la sortie (Obligatoire) :")
            mail = st.text_input("Votre Email (Obligatoire) :")
            btn_c = st.form_submit_button("🚀 Créer l'espace")
        if btn_c and nom and mail:
            pin = ''.join(random.choice('0123456789') for _ in range(6))
            sid = f"ABIMES-2026-S{random.randint(100,999)}"
            conn = sqlite3.connect("abimes_compta.db")
            c = conn.cursor()
            c.execute("INSERT INTO sorties VALUES (?, ?, ?, ?)", (sid, nom, mail, pin))
            conn.commit()
            conn.close()
            st.success("🎉 Sortie créée !")
            st.info(f"➡️ N° Sortie : `{sid}`  |  ➡️ Code PIN : `{pin}`")
            
    with t_conn:
        l_id = st.text_input("N° de Sortie :")
        l_pin = st.text_input("Code PIN :", type="password")
        if st.button("Se connecter 🔓"):
            conn = sqlite3.connect("abimes_compta.db")
            c = conn.cursor()
            c.execute("SELECT nom_sortie FROM sorties WHERE id_sortie=? AND mot_de_passe_unique=?", (l_id.strip(), l_pin.strip()))
            ok = c.fetchone()
            conn.close()
            if ok:
                st.session_state["connecte"] = True
                st.session_state["sortie_id"] = l_id.strip()
                st.rerun()
            else: st.error("Identifiants incorrects.")

# --- SI CONNECTE ---
else:
    st.sidebar.title("🦇 ABIMES")
    st.sidebar.write(f"Sortie : `{st.session_state['sortie_id']}`")
    if st.sidebar.button("🚪 Déconnexion"):
        st.session_state["connecte"] = False
        st.session_state["sortie_id"] = None
        st.rerun()

    st.title("👤 Gestion des Participants")
    
    # 🌟 FORMULAIRE TRÈS SIMPLE ET FIABLE
    with st.form("f_add_p"):
        p_nom = st.text_input("Nom et Prénom (Format : Prénom N) :")
        p_mail = st.text_input("Adresse Email (Optionnel) :")
        p_statut = st.selectbox("Statut Spéléo :", ["Spéléo Membre du club", "Débutant", "Spéléo Non membre du club", "Non membre du club"])
        p_genre = st.radio("Genre :", ["Homme", "Femme"], horizontal=True)
        p_age = st.radio("Tranche d'âge :", ["Sénior", "Jeune moins de 26 ans"], horizontal=True)
        p_voiture = st.checkbox("🚗 Propose sa voiture pour la sortie")
        
        btn_save = st.form_submit_button("💾 Enregistrer le participant")

    if btn_save and p_nom:
        conn = sqlite3.connect("abimes_compta.db")
        c = conn.cursor()
        c.execute("INSERT INTO participants (id_sortie, nom_format, email, statut_speleo, genre, tranche_age, propose_voiture) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (st.session_state["sortie_id"], p_nom, p_mail, p_statut, p_genre, p_age, 1 if p_voiture else 0))
        conn.commit()
        conn.close()
        st.success(f"👤 {p_nom} ajouté !")
        st.rerun()

    # Liste
    st.write("---")
    st.subheader("📋 Équipe enregistrée")
    conn = sqlite3.connect("abimes_compta.db")
    c = conn.cursor()
    c.execute("SELECT nom_format, statut_speleo, genre, tranche_age FROM participants WHERE id_sortie=?", (st.session_state["sortie_id"],))
    equipe = c.fetchall()
    conn.close()
    
    if equipe:
        for p in equipe:
            st.text(f"🥾 {p[0]} - {p[1]} ({p[2]} / {p[3]})")
    else:
        st.info("Aucun participant pour le moment.")
