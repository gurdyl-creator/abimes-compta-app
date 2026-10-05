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
                
                ok_mail, erreur = envoyer_email_acces(email_responsable, id_sortie, code_pin, nom_sortie)
                if not ok_mail:
                    st.warning(f"⚠️ **Note : L'e-mail n'a pas pu partir automatiquement ({erreur}).** Pas d'inquiétude, utilisez les codes écrits ci-dessus pour vous connecter.")
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
    s_gite = res_s[3] if res_s and res_s[3] else ""
    s_deps = res_s[4] if res_s and res_s[4] else ""
    s_cavites = res_s[5] if res_s and res_s[5] else ""
    s_type = res_s[6] if res_s and res_s[6] else "classique"

    try:
        d_deb_obj = datetime.strptime(s_ddeb, "%Y-%m-%d").date()
        d_fin_obj = datetime.strptime(s_dfin, "%Y-%m-%d").date()
    except:
        d_deb_obj = datetime.today().date()
        d_fin_obj = datetime.today().date()

    # --- CONFIGURATION DU BANDEAU GAUCHE ENREGISTRABLE ---
    st.sidebar.title("🦇 Club ABIMES")
    st.sidebar.write(f"📅 **N° Sortie :** `{id_sortie}`")
    st.sidebar.write("---")
    st.sidebar.subheader("⚙️ Modifier la sortie :")
    
    side_nom = st.sidebar.text_input("Nom du week-end :", value=s_nom, key="side_n")
    side_ddeb = st.sidebar.date_input("Date de début :", value=d_deb_obj, key="side_dd")
    side_dfin = st.sidebar.date_input("Date de fin :", value=d_fin_obj, key="side_df")
    side_gite = st.sidebar.text_input("Lieu du gîte :", value=s_gite, key="side_g")
    side_deps = st.sidebar.text_input("N° Département(s) :", value=s_deps, key="side_dep")
    
    liste_types = ["classique", "explo", "formation/entrainement", "plongée", "secours", "scientifique", "canyon", "réunion"]
    idx_defaut = liste_types.index(s_type) if s_type in liste_types else 0
    side_type = st.sidebar.selectbox("Activité :", liste_types, index=idx_defaut, key="side_t")
    
    side_cavites = st.sidebar.text_area("Cavités :", value=s_cavites, key="side_c")
    
    st.sidebar.write("---")
    bouton_sauver_barre = st.sidebar.button("💾 Enregistrer les modifications", key="btn_save_sidebar")
    
    if bouton_sauver_barre and side_nom:
        conn = sqlite3.connect("abimes_compta.db")
        c = conn.cursor()
        c.execute("UPDATE sorties SET nom_sortie=?, date_debut=?, date_fin=?, lieu_gite=?, departements=?, type_activite=?, cavites=? WHERE id_sortie=?", (side_nom, str(side_ddeb), str(side_dfin), side_gite, side_deps, side_type, side_cavites, id_sortie))
        conn.commit()
        conn.close()
        st.rerun()

    st.sidebar.write("---")
    if st.sidebar.button("🚪 Se déconnecter", key="btn_disco"):
        st.session_state["statut_connexion"] = "Deconnecte"
        st.session_state["role_utilisateur"] = None
        st.session_state["id_sortie_active"] = None
        st.rerun()

    # --- ZONE CENTRALE (LIGNE DROITE, AUCUN BLOC IMBRIQUÉ) ---
    st.title(f"📝 Gestion : {s_nom}")
    
    st.markdown("### 👤 Ajouter une personne présente sur la sortie")
    
    nom_part = st.text_input("Nom et Prénom (Obligatoire) :", placeholder="Format attendu : Prénom N", key="p_nom")
    email_part = st.text_input("Adresse Email (Optionnel) :", key="p_email")
    st.write("---")
    statut = st.selectbox("Statut Spéléo :", ["Spéléo Membre du club", "Débutant", "Spéléo Non membre du club", "Non membre du club"], key="p_statut")
