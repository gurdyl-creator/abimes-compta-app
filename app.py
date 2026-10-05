import streamlit as st
import sqlite3
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- INITIALISATION DE LA BASE DE DONNÉES D'ORIGINE ---
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
    
    corps_texte = f"Bonjour,\n\nEspace créé pour la sortie : {nom_sortie}.\n\n➡️ Numéro de Sortie : {id_sortie}\n➡️ Code PIN d'accès : {code_pin}"
    msg.attach(MIMEText(corps_texte, 'plain', 'utf-8'))
    try:
        port = int(config.get("port_smtp", 587))
        serveur = smtplib.SMTP(config["serveur_smtp"], port, timeout=5)
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
if "mode_edition_barre" not in st.session_state: st.session_state["mode_edition_barre"] = False

st.set_page_config(page_title="ABIMES - Compta", page_icon="🦇", layout="centered")

# --- ÉCRAN ACCUEIL (DÉCONNECTÉ) ---
if st.session_state["statut_connexion"] == "Deconnecte":
    st.title("🦇 Club ABIMES - Gestion des Sorties")
    st.write("Outil open-source de gestion et répartition des frais de week-ends spéléo.")

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
                st.info(f"👉 **Notez précieusement vos accès de connexion :**\n\n"
                        f"➡️ **N° de Sortie :** `{id_sortie}`\n\n"
                        f"➡️ **Code PIN (6 chiffres) :** `{code_pin}`")
                
                ok_mail, erreur = envoyer_email_acces(email_responsable, id_sortie, code_pin, nom_sortie)
                if not ok_mail:
                    st.warning(f"⚠️ **Note : L'e-mail n'a pas pu partir automatiquement ({erreur}).** Pas d'inquiétude, utilisez les codes écrits ci-dessus pour vous connecter.")
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

# --- ÉCRANS INTÉRIEURS (SI CONNECTÉ) ---
else:
    id_sortie = st.session_state["id_sortie_active"]
    
    # Lecture dynamique des infos pour la barre latérale et le titre
    conn = sqlite3.connect("abimes_compta.db")
    c = conn.cursor()
    c.execute("SELECT nom_sortie, lieu_gite, type_activite, cavites, date_debut, date_fin, departements FROM sorties WHERE id_sortie = ?", (id_sortie,))
    infos = c.fetchone()
    conn.close()
    
    current_nom = infos[0] if infos else id_sortie
    current_gite = infos[1] if infos and infos[1] else "Non renseigné"
    current_type = infos[2] if infos and infos[2] else "classique"
    current_cavites = infos[3] if infos and infos[3] else "Aucune renseignée"
    current_ddeb = infos[4] if infos else ""
    current_dfin = infos[5] if infos else ""
    current_deps = infos[6] if infos and infos[6] else ""

    # 🌟 MODULE BARRE LATÉRALE GAUCHE : Affichage et modification en direct
    st.sidebar.title("🦇 Club ABIMES")
    st.sidebar.write(f"👤 Rôle : **{st.session_state['role_utilisateur']}**")
    st.sidebar.write("---")
    
    if not st.session_state["mode_edition_barre"]:
        st.sidebar.subheader("📋 Infos validées :")
        st.sidebar.write(f"📅 **ID Sortie :** `{id_sortie}`")
        st.sidebar.write(f"🏷️ **Nom :** {current_nom}")
        st.sidebar.write(f"🏡 **Gîte :** {current_gite}")
        st.sidebar.write(f"🧗 **Activité :** {current_type}")
        st.sidebar.write(f"🕳️ **Cavités :**\n{current_cavites}")
        
        if st.sidebar.button("⚙️ Modifier les infos"):
            st.session_state["mode_edition_barre"] = True
            st.rerun()
    else:
        st.sidebar.subheader("⚙️ Modification rapide :")
        edit_nom = st.sidebar.text_input("Nom de la sortie :", value=current_nom)
        edit_gite = st.sidebar.text_input("Lieu du gîte :", value=current_gite if current_gite != "Non renseigné" else "")
        edit_type = st.sidebar.selectbox("Activité :", ["classique", "explo", "formation/entrainement", "plongée", "secours", "scientifique", "canyon", "réunion"], index=["classique", "explo", "formation/entrainement", "plongée", "secours", "scientifique", "canyon", "réunion"].index(current_type))
        edit_cavites = st.sidebar.text_area("Cavités explorées :", value=current_cavites if current_cavites != "Aucune renseignée" else "")
        
        c_side1, c_side2 = st.sidebar.columns(2)
        with c_side1:
            if st.sidebar.button("💾 Sauver"):
                conn = sqlite3.connect("abimes_compta.db")
                c = conn.cursor()
                c.execute("UPDATE sorties SET nom_sortie=?, lieu_gite=?, type_activite=?, cavites=? WHERE id_sortie=?", (edit_nom, edit_gite, edit_type, edit_cavites, id_sortie))
