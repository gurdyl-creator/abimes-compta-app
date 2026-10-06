import streamlit as st
import sqlite3
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

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
    msg['Subject'] = f"🦇 ABIMES - Vos accès pour la sortie : {nom_sortie}"
    corps_texte = f"Bonjour,\n\n➡️ Numéro de Sortie : {id_sortie}\n➡️ Code PIN : {code_pin}"
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

# --- GESTION DES SESSIONS ---
if "statut_connexion" not in st.session_state: st.session_state["statut_connexion"] = "Deconnecte"
if "role_utilisateur" not in st.session_state: st.session_state["role_utilisateur"] = None
if "id_sortie_active" not in st.session_state: st.session_state["id_sortie_active"] = None

st.set_page_config(page_title="ABIMES - Compta", page_icon="🦇", layout="centered")

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
            conn = sqlite3.connect("abimes_compta.db")
            c = conn.cursor()
            id_sortie = f"ABIMES-{date_debut.year}-S{random.randint(100, 999)}"
            code_pin = generer_code_pin()
            try:
                c.execute('''INSERT INTO sorties (id_sortie, nom_sortie, date_debut, date_fin, lieu_gite, departements, cavites, type_activite, email_responsable, mot_de_passe_unique) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (id_sortie, nom_sortie, str(date_debut), str(date_fin), lieu_gite, departements, cavites, type_activite, email_responsable, code_pin))
                conn.commit()
                st.success("🎉 Votre espace de sortie a été créé avec succès !")
                st.info(f"👉 **Notez précieusement vos accès de connexion :**\n\n➡️ **N° de Sortie :** `{id_sortie}`\n\n➡️ **Code PIN (6 chiffres) :** `{code_pin}`")
                envoyer_email_acces(email_responsable, id_sortie, code_pin, nom_sortie)
            except sqlite3.IntegrityError: st.error("Erreur de doublon.")
            finally: conn.close()

    with onglet_connexion:
        login_id = st.text_input("N° de Sortie :")
        login_mdp = st.text_input("Code PIN :", type="password")
        if st.button("Se connecter 🔓"):
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
    id_sortie = st.session_state["id_sortie_active"]
    
    conn = sqlite3.connect("abimes_compta.db")
    c = conn.cursor()
    c.execute("SELECT nom_sortie, date_debut, date_fin, lieu_gite, departements, cavites, type_activite FROM sorties WHERE id_sortie = ?", (id_sortie,))
    res_s = c.fetchone()
    conn.close()
    
    s_nom = res_s[0] if res_s and res_s[0] else id_sortie
    s_ddeb = res_s[1] if res_s and res_s[1] else str(datetime.today().date())
    s_dfin = res_s[2] if res_s and res_s[2] else str(datetime.today().date())
    s_gite = res_s[3] if res_s and res_s[3] else "Non renseigné"
    s_deps = res_s[4] if res_s and res_s[4] else "Non renseigné"
    s_cavites = res_s[5] if res_s and res_s[5] else "Aucune"
    s_type = res_s[6] if res_s and res_s[6] else "classique"

    # Bandeau gauche fixe de rappel
    st.sidebar.title("🦇 Club ABIMES")
    st.sidebar.write(f"👤 Rôle : **{st.session_state['role_utilisateur']}**")
    st.sidebar.write("---")
    st.sidebar.subheader("📋 Infos de la sortie :")
    st.sidebar.write(f"📅 **N° Sortie :** `{id_sortie}`")
    st.sidebar.write(f"🏷️ **Nom :** {s_nom}")
    st.sidebar.write(f"⏱️ **Dates :** du {s_ddeb} au {s_dfin}")
    st.sidebar.write(f"🏡 **Gîte :** {s_gite}")
    st.sidebar.write(f"🗺️ **Département(s) :** {s_deps}")
    st.sidebar.write(f"🧗 **Activité :** {s_type}")
    st.sidebar.write(f"🕳️ **Cavités :**\n{s_cavites}")
    st.sidebar.write("---")
    if st.sidebar.button("🚪 Se déconnecter"):
        st.session_state["statut_connexion"] = "Deconnecte"
        st.session_state["role_utilisateur"] = None
        st.session_state["id_sortie_active"] = None
        st.rerun()

    # Zone centrale principale
    st.title(f"📝 Gestion : {s_nom}")
    tab_membres, tab_modif, tab_frais = st.tabs(["👤 Les Participants", "⚙️ Modifier la sortie", "💰 Saisie des Dépenses"])
    
    # --- TAB 1 : LES PARTICIPANTS ---
    with tab_membres:
        st.subheader("👥 Ajouter une personne présente sur la sortie")
        
        with st.form("formulaire_final_participants"):
            nom_part = st.text_input("Nom et Prénom (Obligatoire) :", placeholder="Format attendu : Prénom N")
            email_part = st.text_input("Adresse Email (Optionnel) :")
            st.write("---")
            statut = st.selectbox("Statut Spéléo :", ["Spéléo Membre du club", "Débutant", "Spéléo Non membre du club", "Non membre du club"])
            genre = st.radio("Genre (Optionnel) :", ["Homme", "Femme"], horizontal=True, index=None)
            age = st.radio("Tranche d'âge (Optionnel) :", ["Sénior", "Jeune moins de 26 ans"], horizontal=True, index=None)
            st.write("---")
            voiture = st.checkbox("🚗 Propose sa voiture pour la sortie")
            
            st.write("🔧 *Options Débutant (À remplir uniquement si le statut ci-dessus est 'Débutant')*")
            assurance = st.selectbox("🛡️ Assurance Débutant :", ["Aucune", "Assurance 2 jours", "Assurance 5 jours"])
            matos = st.checkbox("🎒 Prêt de matériel débutant club")
            
            st.write("---")
            bouton_participant = st.form_submit_button("💾 Enregistrer le participant")
        
        if bouton_participant:
            if not nom_part:
                st.error("⚠️ Le Nom et Prénom sont obligatoires.")
            else:
                genre_texte = str(genre) if genre is not None else "Non spécifié"
                age_texte = str(age) if age is not None else "Non spécifié"
                assurance_finale = assurance if statut == "Débutant" else "Aucune"
                matos_final = 1 if (statut == "Débutant" and matos) else 0
                
                conn = sqlite3.connect("abimes_compta.db")
                c = conn.cursor()
