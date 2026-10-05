import streamlit as st
import sqlite3
import random
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- INITIALISATION DE LA BASE DE DONNÉES SÉCURISÉE ---
DB_NAME = "abimes_compta_v3.db"

def initialisation_abimes_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS config_tarifs (
                    id INTEGER PRIMARY KEY, ik_chauffeur REAL, subv_km_club REAL, 
                    forfait_matos_cadre REAL, assurance_2j REAL, assurance_5j REAL, 
                    coef_ptit_dej REAL, coef_midi REAL, coef_soir REAL)''')
    c.execute("SELECT COUNT(*) FROM config_tarifs")
    if c.fetchone() == 0:
        c.execute("INSERT INTO config_tarifs VALUES (1, 0.15, 0.02, 5.00, 7.20, 15.50, 0.25, 0.50, 1.00)")

    c.execute('''CREATE TABLE IF NOT EXISTS sorties (
                    id_sortie TEXT PRIMARY KEY, nom_sortie TEXT, date_debut TEXT, date_fin TEXT, 
                    lieu_gite TEXT, departements TEXT, cavites TEXT, type_activite TEXT, 
                    statut TEXT DEFAULT 'En cours', email_responsable TEXT, mot_de_passe_unique TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS participants (
                    id_participant INTEGER PRIMARY KEY AUTOINCREMENT, id_sortie TEXT, nom_format TEXT, 
                    email TEXT, statut_speleo TEXT, genre TEXT, tranche_age TEXT, 
                    option_assurance TEXT DEFAULT 'Aucune', option_matos INTEGER DEFAULT 0, 
                    propose_voiture INTEGER DEFAULT 0, statut_vote TEXT DEFAULT 'En attente', commentaire_vote TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS nuitees (
                    id_nuitee INTEGER PRIMARY KEY AUTOINCREMENT, id_sortie TEXT, id_participant INTEGER, nb_nuits INTEGER,
                    FOREIGN KEY(id_sortie) REFERENCES sorties(id_sortie) ON DELETE CASCADE,
                    FOREIGN KEY(id_participant) REFERENCES participants(id_participant) ON DELETE CASCADE)''')

    c.execute('''CREATE TABLE IF NOT EXISTS depenses (
                    id_depense INTEGER PRIMARY KEY AUTOINCREMENT, id_sortie TEXT, id_acheteur INTEGER, montant REAL,
                    code_compta TEXT, intitule TEXT, photo_ticket_path TEXT, imputation_type TEXT DEFAULT 'Collectif', liste_beneficiaires TEXT,
                    FOREIGN KEY(id_sortie) REFERENCES sorties(id_sortie) ON DELETE CASCADE)''')
    conn.commit()
    conn.close()

initialisation_abimes_db()

def generer_code_pin():
    return ''.join(random.choice('0123456789') for _ in range(6))

# 🌟 DOUBLE SÉCURITÉ SMTP : SSL (465) + TLS (587) AUTOMATIQUE
def envoyer_email_acces(email_destinataire, id_sortie, code_pin, nom_sortie):
    if "email" not in st.secrets:
        return False, "Configuration mail manquante dans les Secrets Streamlit."
    config = st.secrets["email"]
    
    msg = MIMEMultipart()
    msg['From'] = config["adresse_club"]
    msg['To'] = email_destinataire
    msg['Subject'] = f"🦇 ABIMES - Vos accès pour la sortie : {nom_sortie}"
    corps_texte = f"Bonjour,\n\nEspace créé pour la sortie : {nom_sortie}.\n\n➡️ Numéro de Sortie : {id_sortie}\n➡️ Code PIN d'accès : {code_pin}"
    msg.attach(MIMEText(corps_texte, 'plain', 'utf-8'))
    
    # Tentative 1 : SSL standard (Port 465)
    try:
        serveur = smtplib.SMTP_SSL(config["serveur_smtp"], int(config.get("port_smtp", 465)), timeout=10)
        serveur.login(config["adresse_club"], config["mot_de_passe_club"])
        serveur.sendmail(config["adresse_club"], email_destinataire, msg.as_string())
        serveur.quit()
        return True, "Email envoyé via SSL"
    except Exception:
        # Tentative 2 de secours : TLS standard (Port 587)
        try:
            serveur = smtplib.SMTP(config["serveur_smtp"], 587, timeout=10)
            serveur.starttls()
            serveur.login(config["adresse_club"], config["mot_de_passe_club"])
            serveur.sendmail(config["adresse_club"], email_destinataire, msg.as_string())
            serveur.quit()
            return True, "Email envoyé via TLS de secours"
        except Exception as e_tls:
            return False, f"Échec SSL et TLS. Détail : {str(e_tls)}"

# --- GESTION DES SESSIONS ---
if "statut_connexion" not in st.session_state: st.session_state["statut_connexion"] = "Deconnecte"
if "role_utilisateur" not in st.session_state: st.session_state["role_utilisateur"] = None
if "id_sortie_active" not in st.session_state: st.session_state["id_sortie_active"] = None

st.set_page_config(page_title="ABIMES - Compta", page_icon="🦇", layout="centered")

# --- BOUTON DE DÉCONNEXION ---
if st.session_state["statut_connexion"] == "Connecte":
    st.sidebar.title("🦇 ABIMES")
    st.sidebar.write(f"👤 **{st.session_state['role_utilisateur']}**")
    if st.session_state["id_sortie_active"]:
        st.sidebar.info(f"Sortie : `{st.session_state['id_sortie_active']}`")
    if st.sidebar.button("🚪 Se déconnecter"):
        st.session_state["statut_connexion"] = "Deconnecte"
        st.session_state["role_utilisateur"] = None
        st.session_state["id_sortie_active"] = None
        st.rerun()

# --- ÉCRAN ACCUEIL ---
if st.session_state["statut_connexion"] == "Deconnecte":
    st.title("🦇 Club ABIMES - Gestion des Sorties")
    onglet_creer, onglet_connexion = st.tabs(["🆕 Créer une sortie", "🔑 Connexion"])

    with onglet_creer:
        with st.form("formulaire_creation_sortie"):
            nom_sortie = st.text_input("Nom de la sortie (Obligatoire) :")
            email_responsable = st.text_input("Adresse email du responsable (Obligatoire) :")
            st.write("---")
            col1, col2 = st.columns(2)
            with col1: date_debut = st.date_input("Date de début :")
            with col2: date_fin = st.date_input("Date de fin :")
            type_activite = st.selectbox("Type d'activité :", ["classique", "explo", "formation/entrainement", "plongée", "secours", "scientifique", "canyon", "réunion"])
            lieu_gite = st.text_input("Lieu du gîte :")
            departements = st.text_input("N° Département(s) :")
            cavites = st.text_area("Liste des cavités :")
            submit_bouton = st.form_submit_button("🚀 Valider l'espace")

        if submit_bouton and nom_sortie and email_responsable:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            id_sortie = f"ABIMES-{date_debut.year}-S{random.randint(100, 999)}"
            code_pin = generer_code_pin()
            try:
                c.execute('''INSERT INTO sorties (id_sortie, nom_sortie, date_debut, date_fin, lieu_gite, departements, cavites, type_activite, email_responsable, mot_de_passe_unique) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (id_sortie, nom_sortie, str(date_debut), str(date_fin), lieu_gite, departements, cavites, type_activite, email_responsable, code_pin))
                conn.commit()
                st.success("🎉 Sortie créée !")
                envoyer_email_acces(email_responsable, id_sortie, code_pin, nom_sortie)
                st.info(f"➡️ **N° de Sortie :** `{id_sortie}`  |  ➡️ **Code PIN :** `{code_pin}`")
            except sqlite3.IntegrityError: st.error("Erreur de doublon.")
            finally: conn.close()

    with onglet_connexion:
        login_id = st.text_input("N° de Sortie ou 'ADMIN' :")
        login_mdp = st.text_input("Code PIN / Mot de passe :", type="password")
        if st.button("Se connecter 🔓"):
            if login_id.upper() == "ADMIN":
                admin_config = st.secrets.get("admin")
                if admin_config and login_mdp == admin_config["mot_de_passe"]:
                    st.session_state["statut_connexion"] = "Connecte"
                    st.session_state["role_utilisateur"] = "Administrateur"
                    st.rerun()
                else: st.error("❌ Mot de passe Admin incorrect.")
            else:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("SELECT nom_sortie FROM sorties WHERE id_sortie = ? AND mot_de_passe_unique = ?", (login_id.strip(), login_mdp.strip()))
                res = c.fetchone()
                conn.close()
                if res:
                    st.session_state["statut_connexion"] = "Connecte"
                    st.session_state["role_utilisateur"] = "Responsable Sortie"
                    st.session_state["id_sortie_active"] = login_id.strip()
                    st.rerun()
                else: st.error("❌ Identifiants incorrects.")

# --- ÉCRANS INTÉRIEURS ---
else:
    if st.session_state["role_utilisateur"] == "Administrateur":
        st.title("🛡️ Espace Administrateur")
        st.info("Espace trésorier en construction.")
        
    elif st.session_state["role_utilisateur"] == "Responsable Sortie":
        id_sortie = st.session_state["id_sortie_active"]
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT nom_sortie, date_debut, date_fin, lieu_gite, departements, cavites, type_activite FROM sorties WHERE id_sortie = ?", (id_sortie,))
        res_s = c.fetchone()
        conn.close()
        
        titre_affichage = res_s if res_s else id_sortie
        st.title(f"📝 Gestion des frais : {titre_affichage}")
        
        tab_membres, tab_modif, tab_frais = st.tabs(["👤 Les Participants", "⚙️ Modifier la sortie", "💰 Saisie des Dépenses"])
        
        with tab_membres:
            st.subheader("👥 Ajouter une personne présente sur la sortie")
            with st.form("formulaire_final_participants"):
                nom_part = st.text_input("Nom et Prénom :", placeholder="Format attendu : Prénom N", key="v_nom_part")
                email_part = st.text_input("Adresse Email (Optionnel) :", key="v_email_part")
                st.write("---")
