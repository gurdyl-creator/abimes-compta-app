import streamlit as st
import sqlite3
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- INITIALISATION DE LA BASE DE DONNÉES ---
def initialisation_abimes_db():
    conn = sqlite3.connect("abimes_compta.db")
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
    conn.commit()
    conn.close()

initialisation_abimes_db()

def generer_code_pin():
    return ''.join(random.choice('0123456789') for _ in range(6))

def envoyer_email_acces(email_destinataire, id_sortie, code_pin, nom_sortie):
    if "email" not in st.secrets:
        return False, "Configuration mail manquante dans les Secrets Streamlit."
    config = st.secrets["email"]
    
    msg = MIMEMultipart()
    msg['From'] = config["adresse_club"]
    msg['To'] = email_destinataire
    msg['Subject'] = f"🦇 ABIMES - Vos accès pour la sortie : {nom_sortie}"

    corps_texte = f"""Bonjour,\n\nVous venez de créer l'espace de gestion des frais pour la sortie spéléo : {nom_sortie}.\n\nVoici vos identifiants uniques pour vous connecter :\n\n➡️ Numéro de Sortie : {id_sortie}\n➡️ Code PIN d'accès : {code_pin}\n\nBonne sortie,\nLe Bureau - Club ABIMES"""
    msg.attach(MIMEText(corps_texte, 'plain', 'utf-8'))

    try:
        serveur = smtplib.SMTP_SSL(config["serveur_smtp"], config["port_smtp"])
        serveur.login(config["adresse_club"], config["mot_de_passe_club"])
        serveur.sendmail(config["adresse_club"], email_destinataire, msg.as_string())
        serveur.quit()
        return True, "Email envoyé"
    except Exception as e:
        return False, str(e)

# --- GESTION DES SESSIONS DE CONNEXION (Mémoire de l'état de l'application) ---
if "statut_connexion" not in st.session_state:
    st.session_state["statut_connexion"] = "Deconnecte"
if "role_utilisateur" not in st.session_state:
    st.session_state["role_utilisateur"] = None
if "id_sortie_active" not in st.session_state:
    st.session_state["id_sortie_active"] = None

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="ABIMES - Compta", page_icon="🦇", layout="centered")

# --- BOUTON DE DÉCONNEXION (Toujours visible si connecté) ---
if st.session_state["statut_connexion"] == "Connecte":
    st.sidebar.write(f"👤 Connecté en tant que : **{st.session_state['role_utilisateur']}**")
    if st.session_state["id_sortie_active"]:
        st.sidebar.write(f"📅 Sortie active : `{st.session_state['id_sortie_active']}`")
    
    if st.sidebar.button("🚪 Se déconnecter"):
        st.session_state["statut_connexion"] = "Deconnecte"
        st.session_state["role_utilisateur"] = None
        st.session_state["id_sortie_active"] = None
        st.rerun()

# --- ÉCRAN 1 : FORMULAIRES D'ACCUEIL (SI DÉCONNECTÉ) ---
if st.session_state["statut_connexion"] == "Deconnecte":
    st.title("🦇 Club ABIMES - Gestion des Sorties")
    st.write("Outil open-source de gestion et répartition des frais de week-ends spéléo.")

    onglet_creer, onglet_connexion = st.tabs(["🆕 Créer une sortie", "🔑 Connexion Responsable / Admin"])

    with onglet_creer:
        st.header("Déclarer un nouveau week-end ou camp")
        with st.form("formulaire_creation_sortie"):
            nom_sortie = st.text_input("Nom de la sortie (Obligatoire) :", placeholder="ex: Camp Vercors Octobre")
            email_responsable = st.text_input("Adresse email du responsable (Obligatoire) :", placeholder="prenom.nom@exemple.fr")
            st.write("---")
            col1, col2 = st.columns(2)
            with col1: date_debut = st.date_input("Date de début :")
            with col2: date_fin = st.date_input("Date de fin :")
            type_activite = st.selectbox("Type d'activité spéléo :", ["classique", "explo", "formation/entrainement", "plongée", "secours", "scientifique", "canyon", "réunion"])
            lieu_gite = st.text_input("Lieu du gîte / Hébergement :")
            departements = st.text_input("N° Département(s) des explorations :")
            cavites = st.text_area("Liste des cavités prévues ou visitées :")
            submit_bouton = st.form_submit_button("🚀 Valider et générer l'espace")

        if submit_bouton:
            if nom_sortie and email_responsable:
                conn = sqlite3.connect("abimes_compta.db")
                c = conn.cursor()
                id_aleatoire = random.randint(100, 999)
                id_sortie = f"ABIMES-{date_debut.year}-S{id_aleatoire}"
                code_pin = generer_code_pin()
                try:
                    c.execute('''INSERT INTO sorties (id_sortie, nom_sortie, date_debut, date_fin, lieu_gite, departements, cavites, type_activite, email_responsable, mot_de_passe_unique) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (id_sortie, nom_sortie, str(date_debut), str(date_fin), lieu_gite, departements, cavites, type_activite, email_responsable, code_pin))
                    conn.commit()
                    st.success(f"🎉 La sortie '{nom_sortie}' a été créée !")
                    succes_mail, msg_erreur = envoyer_email_acces(email_responsable, id_sortie, code_pin, nom_sortie)
                    if succes_mail: st.toast("📧 E-mail envoyé !", icon="📩")
                    st.info(f"➡️ **N° de Sortie :** `{id_sortie}`\n\n➡️ **Code PIN unique :** `{code_pin}`")
                except sqlite3.IntegrityError: st.error("Erreur de doublon. Réessayez.")
                finally: conn.close()
            else: st.error("⚠️ Le nom de la sortie ET l'email sont obligatoires.")

    with onglet_connexion:
        st.header("Accéder à un espace existant")
        login_id = st.text_input("N° de Sortie (ou 'ADMIN' pour le trésorier) :", placeholder="ABIMES-2026-Sxxx ou ADMIN")
        login_mdp = st.text_input("Code PIN / Mot de passe :", type="password")
        bouton_connexion = st.button("Se connecter 🔓")

        if bouton_connexion:
            # CAS 1 : TENTATIVE DE CONNEXION ADMINISTRATEUR
            if login_id.upper() == "ADMIN":
                admin_config = st.secrets.get("admin")
                if admin_config and login_mdp == admin_config["mot_de_passe"]:
                    st.session_state["statut_connexion"] = "Connecte"
                    st.session_state["role_utilisateur"] = "Administrateur"
                    st.session_state["id_sortie_active"] = None
                    st.success("Connexion Admin réussie !")
                    st.rerun()
                else:
                    st.error("❌ Mot de passe Administrateur incorrect.")
            
            # CAS 2 : TENTATIVE DE CONNEXION D'UN RESPONSABLE DE SORTIE
            else:
                conn = sqlite3.connect("abimes_compta.db")
                c = conn.cursor()
                c.execute("SELECT nom_sortie FROM sorties WHERE id_sortie = ? AND mot_de_passe_unique = ?", (login_id.strip(), login_mdp.strip()))
                resultat = c.fetchone()
                conn.close()

                if resultat:
                    st.session_state["statut_connexion"] = "Connecte"
                    st.session_state["role_utilisateur"] = "Responsable Sortie"
                    st.session_state["id_sortie_active"] = login_id.strip()
                    st.success(f"Connexion réussie à la sortie : {resultat[0]}")
                    st.rerun()
                else:
                    st.error("❌ Numéro de sortie ou Code PIN incorrect.")

# --- ÉCRAN 2 : LES ESPACES INTÉRIEURS (SI CONNECTÉ) ---
else:
    if st.session_state["role_utilisateur"] == "Administrateur":
        st.title("🛡️ Espace Administrateur - Trésorerie Générale")
        st.write("Bienvenue dans votre outil de contrôle des comptes annuels d'ABIMES.")
        # [Le futur tableau de bord Admin s'affichera ici]
        st.info("Espace de surveillance en cours de construction.")
        
    elif st.session_state["role_utilisateur"] == "Responsable Sortie":
        st.title("📝 Espace Responsable - Saisie des Comptes")
        st.write(f"Gestion en cours pour la sortie : `{st.session_state['id_sortie_active']}`")
        # [Le futur tableau de bord du responsable avec formulaires s'affichera ici]
        st.info("Espace de saisie terrain en cours de construction.")
