import streamlit as st
import sqlite3
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- CONFIGURATION DE LA BASE DE DONNÉES RECONSTRUITE DE ZÉRO ---
DB_NAME = "abimes_compta_v2026.db"

def initialisation_abimes_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 1. Table des tarifs officiels de l'AG
    c.execute('''CREATE TABLE IF NOT EXISTS config_tarifs (
                    id INTEGER PRIMARY KEY, ik_chauffeur REAL, subv_km_club REAL, 
                    forfait_matos_cadre REAL, assurance_2j REAL, assurance_5j REAL, 
                    coef_ptit_dej REAL, coef_midi REAL, coef_soir REAL)''')
    c.execute("SELECT COUNT(*) FROM config_tarifs")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO config_tarifs VALUES (1, 0.15, 0.02, 5.00, 7.20, 15.50, 0.25, 0.50, 1.00)")

    # 2. Table des sorties / week-ends
    c.execute('''CREATE TABLE IF NOT EXISTS sorties (
                    id_sortie TEXT PRIMARY KEY, nom_sortie TEXT, date_debut TEXT, date_fin TEXT, 
                    lieu_gite TEXT, departements TEXT, cavites TEXT, type_activite TEXT, 
                    statut TEXT DEFAULT 'En cours', email_responsable TEXT, mot_de_passe_unique TEXT)''')

    # 3. Table des participants (Champs configurés pour accepter le vide 'None')
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
    corps_texte = f"Bonjour,\n\nVous venez de créer l'espace de gestion des frais pour la sortie : {nom_sortie}.\n\n➡️ N° de Sortie : {id_sortie}\n➡️ Code PIN d'accès : {code_pin}"
    msg.attach(MIMEText(corps_texte, 'plain', 'utf-8'))
    try:
        port = int(config.get("port_smtp", 587))
        serveur = smtplib.SMTP(config["serveur_smtp"], port, timeout=3)
        serveur.starttls()
        serveur.login(config["adresse_club"], config["mot_de_passe_club"])
        serveur.sendmail(config["adresse_club"], email_destinataire, msg.as_string())
        serveur.quit()
        return True, "Email envoyé"
    except Exception as e:
        return False, str(e)

# --- SÉCURITÉ DE RACHRAÎCHISSEMENT DE L'INTERFACE ---
if "statut_connexion" not in st.session_state: st.session_state["statut_connexion"] = "Deconnecte"
if "id_sortie_active" not in st.session_state: st.session_state["id_sortie_active"] = None
if "edition_mode" not in st.session_state: st.session_state["edition_mode"] = False

st.set_page_config(page_title="ABIMES - Frais", page_icon="🦇", layout="centered")

# ==============================================================================
# --- ÉCRAN D'ACCUEIL (DÉCONNECTÉ)
# ==============================================================================
if st.session_state["statut_connexion"] == "Deconnecte":
    st.title("🦇 Club ABIMES - Gestion des Frais")
    st.write("Application de répartition comptable des week-ends et rassemblements.")
    
    onglet_creer, onglet_connexion = st.tabs(["🆕 Créer une sortie", "🔑 Connexion"])
    
    with onglet_creer:
        with st.form("form_creation_sortie_initiale"):
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
                c.execute('''INSERT INTO sorties VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'En cours', ?, ?)''', 
                          (id_sortie, nom_sortie, str(date_debut), str(date_fin), lieu_gite, departements, cavites, type_activite, email_responsable, code_pin))
                conn.commit()
                st.success("🎉 Votre espace de sortie a été créé avec succès !")
                
                # Format d'affichage d'origine aéré
                st.info(f"👉 **Notez précieusement vos accès de connexion :**\n\n"
                        f"➡️ **N° de Sortie :** `{id_sortie}`\n\n"
                        f"➡️ **Code PIN (6 chiffres) :** `{code_pin}`")
                
                ok_mail, erreur = envoyer_email_acces(email_responsable, id_sortie, code_pin, nom_sortie)
                if not ok_mail:
                    st.warning(f"⚠️ **Note : L'e-mail n'a pas pu partir automatiquement ({erreur}).** Pas d'inquiétude, utilisez les codes écrits ci-dessus pour vous connecter.")
            except sqlite3.IntegrityError:
                st.error("Erreur : Cet identifiant existe déjà, veuillez valider à nouveau.")
            finally:
                conn.close()

    with onglet_connexion:
        login_id = st.text_input("N° de Sortie :")
        login_mdp = st.text_input("Code PIN :", type="password")
        if st.button("Se connecter 🔓"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT nom_sortie FROM sorties WHERE id_sortie = ? AND mot_de_passe_unique = ?", (login_id.strip(), login_mdp.strip()))
            res = c.fetchone()
            conn.close()
            if res:
                st.session_state["statut_connexion"] = "Connecte"
                st.session_state["id_sortie_active"] = login_id.strip()
                st.rerun()
            else:
                st.error("❌ Identifiants incorrects.")

# ==============================================================================
# --- ÉCRANS INTÉRIEURS (CONNECTÉ)
# ==============================================================================
else:
    id_sortie = st.session_state["id_sortie_active"]
    
    # Lecture des données à chaque rechargement
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT nom_sortie, date_debut, date_fin, lieu_gite, departements, cavites, type_activite FROM sorties WHERE id_sortie = ?", (id_sortie,))
    res_s = c.fetchone()
    conn.close()
    
    s_nom = res_s[0] if res_s else id_sortie
    s_ddeb = res_s[1] if res_s else str(datetime.today().date())
    s_dfin = res_s[2] if res_s else str(datetime.today().date())
    s_gite = res_s[3] if res_s and res_s[3] else "Non renseigné"
    s_deps = res_s[4] if res_s and res_s[4] else "Non renseigné"
    s_cavites = res_s[5] if res_s and res_s[5] else "Aucune"
    s_type = res_s[6] if res_s and res_s[6] else "classique"

    # --- BANDEAU GAUCHE : VISUALISATION DES CARACTÉRISTIQUES ---
    st.sidebar.title("替代 ABIMES")
    st.sidebar.write(f"📅 **N° Sortie :** `{id_sortie}`")
    st.sidebar.write("---")
    st.sidebar.subheader("📋 Caractéristiques validées :")
    st.sidebar.write(f"🏷️ **Nom :** {s_nom}")
    st.sidebar.write(f"⏱️ **Dates :** du {s_ddeb} au {s_dfin}")
    st.sidebar.write(f"🏡 **Gîte :** {s_gite}")
    st.sidebar.write(f"🗺️ **Département(s) :** {s_deps}")
    st.sidebar.write(f"🧗 **Activité :** {s_type}")
    st.sidebar.write(f"🕳️ **Cavités :**\n{s_cavites}")
    st.sidebar.write("---")
    
    if st.sidebar.button("🚪 Se déconnecter"):
        st.session_state["statut_connexion"] = "Deconnecte"
        st.session_state["id_sortie_active"] = None
        st.session_state["edition_mode"] = False
        st.rerun()

    # --- ARCHITECTURE CENTRALE ---
    st.title(f"📝 Gestion terrain : {s_nom}")
    tab_membres, tab_modif, tab_frais = st.tabs(["👤 Les Participants", "⚙️ Modifier la sortie", "💰 Saisie des Dépenses"])
    
    # --------------------------------------------------------------------------
    # ONGLET 1 : LES PARTICIPANTS
    # --------------------------------------------------------------------------
    with tab_membres:
        st.subheader("👥 Ajouter une personne présente")
        
        with st.form("formulaire_participants_final"):
            nom_part = st.text_input("Nom et Prénom (Obligatoire) :", placeholder="Format attendu : Prénom N")
            email_part = st.text_input("Adresse Email (Optionnel) :")
            st.write("---")
            statut = st.selectbox("Statut Spéléo :", ["Spéléo Membre du club", "Débutant", "Spéléo Non membre du club", "Non membre du club"])
            genre = st.radio("Genre (Optionnel) :", ["Homme", "Femme"], horizontal=True, index=None)
            age = st.radio("Tranche d'âge (Optionnel) :", ["Sénior", "Jeune moins de 26 ans"], horizontal=True, index=None)
