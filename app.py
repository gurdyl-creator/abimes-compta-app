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
        return False, "Configuration mail manquante."
    config = st.secrets["email"]
    msg = MIMEMultipart()
    msg['From'] = config["adresse_club"]
    msg['To'] = email_destinataire
    msg['Subject'] = f"🦇 ABIMES - Accès : {nom_sortie}"
    corps_texte = f"Bonjour,\n\nIdentifiants unique pour la sortie {nom_sortie} :\n\n➡️ N° Sortie : {id_sortie}\n➡️ Code PIN : {code_pin}"
    msg.attach(MIMEText(corps_texte, 'plain', 'utf-8'))
    try:
        serveur = smtplib.SMTP_SSL(config["serveur_smtp"], config["port_smtp"])
        serveur.login(config["adresse_club"], config["mot_de_passe_club"])
        serveur.sendmail(config["adresse_club"], email_destinataire, msg.as_string())
        serveur.quit()
        return True, "Email envoyé"
    except Exception as e:
        return False, str(e)

# --- GESTION DES SESSIONS ---
if "statut_connexion" not in st.session_state: st.session_state["statut_connexion"] = "Deconnecte"
if "role_utilisateur" not in st.session_state: st.session_state["role_utilisateur"] = None
if "id_sortie_active" not in st.session_state: st.session_state["id_sortie_active"] = None

st.set_page_config(page_title="ABIMES - Compta", page_icon="🦇", layout="wide")

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

# --- ÉCRAN ACCUEIL (DÉCONNECTÉ) ---
if st.session_state["statut_connexion"] == "Deconnecte":
    st.title("🦇 Club ABIMES - Gestion des Sorties")
    onglet_creer, onglet_connexion = st.tabs(["🆕 Créer une sortie", "🔑 Connexion Responsable / Admin"])

    with onglet_creer:
        st.header("Déclarer un nouveau week-end ou camp")
        with st.form("formulaire_creation_sortie"):
            nom_sortie = st.text_input("Nom de la sortie (Obligatoire) :")
            email_responsable = st.text_input("Adresse email du responsable (Obligatoire) :")
            col1, col2 = st.columns(2)
            with col1: date_debut = st.date_input("Date de début :")
            with col2: date_fin = st.date_input("Date de fin :")
            type_activite = st.selectbox("Type d'activité :", ["classique", "explo", "formation/entrainement", "plongée", "secours", "scientifique", "canyon", "réunion"])
            lieu_gite = st.text_input("Lieu du gîte :")
            departements = st.text_input("N° Département(s) :")
            cavites = st.text_area("Liste des cavités :")
            submit_bouton = st.form_submit_button("🚀 Valider l'espace")

        if submit_bouton:
            if nom_sortie and email_responsable:
                conn = sqlite3.connect("abimes_compta.db")
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
            else: st.error("⚠️ Nom et email obligatoires.")

    with onglet_connexion:
        st.header("Accéder à un espace existant")
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
                conn = sqlite3.connect("abimes_compta.db")
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

# --- ÉCRANS INTÉRIEURS (CONNECTÉ) ---
else:
    if st.session_state["role_utilisateur"] == "Administrateur":
        st.title("🛡️ Espace Administrateur")
        st.info("Espace trésorier en construction.")
        
    elif st.session_state["role_utilisateur"] == "Responsable Sortie":
        id_sortie = st.session_state["id_sortie_active"]
        
        # Récupération des infos de la sortie pour le titre
        conn = sqlite3.connect("abimes_compta.db")
        c = conn.cursor()
        c.execute("SELECT nom_sortie FROM sorties WHERE id_sortie = ?", (id_sortie,))
        nom_de_la_sortie = c.fetchone()[0]
        conn.close()
        
        st.title(f"📝 Gestion des frais : {nom_de_la_sortie}")
        
        # Sous-onglets de l'espace terrain
        tab_membres, tab_modif, tab_frais = st.tabs(["👤 Les Participants", "⚙️ Modifier la sortie", "💰 Saisie des Dépenses"])
        
        # --- BLOC DE SAISIE DES PARTICIPANTS ---
        with tab_membres:
            st.subheader("👥 Ajouter une personne présente sur la sortie")
            
            with st.form("form_ajouter_participant"):
                col_n, col_m = st.columns(2)
                with col_n:
                    nom_part = st.text_input("Nom et Prénom :", placeholder="Format attendu : Prénom N")
                with col_m:
                    email_part = st.text_input("Adresse Email (Optionnel, utile pour le vote) :")
                
                st.write("---")
                col_s, col_g, col_a = st.columns(3)
                with col_s:
                    statut = st.selectbox("Statut Spéléo :", ["Spéléo Membre du club", "Débutant", "Spéléo Non membre du club", "Non membre du club"])
                with col_g:
                    genre = st.radio("Genre :", ["Homme", "Femme"], horizontal=True)
                with col_a:
                    age = st.radio("Tranche d'âge :", ["Sénior", "Jeune moins de 26 ans"], horizontal=True)
                
                st.write("---")
                st.write("⚙️ *Options spécifiques (Véhicules et Initiation)*")
                c1, c2, c3 = st.columns(3)
                with c1:
                    voiture = st.checkbox("🚗 Propose sa voiture pour la sortie")
                with c2:
                    assurance = st.selectbox("🛡️ Assurance Débutant :", ["Aucune", "Assurance 2 jours", "Assurance 5 jours"])
                with c3:
                    matos = st.checkbox("🎒 Prêt de matériel débutant club")
                
                bouton_participant = st.form_submit_button("💾 Enregistrer le participant")
            
            if bouton_participant and nom_part:
                conn = sqlite3.connect("abimes_compta.db")
