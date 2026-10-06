import streamlit as st
import sqlite3
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- CONFIGURATION DE LA BASE DE DONNÉES ---
DB_NAME = "abimes_compta_v2026.db"

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
    corps_texte = f"Bonjour,\n\n➡️ N° de Sortie : {id_sortie}\n➡️ Code PIN : {code_pin}"
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

if "statut_connexion" not in st.session_state: st.session_state["statut_connexion"] = "Deconnecte"
if "id_sortie_active" not in st.session_state: st.session_state["id_sortie_active"] = None
# Variable mémoire pour gérer l'interrupteur du mode édition du bandeau
if "mode_edition_bandeau" not in st.session_state: st.session_state["mode_edition_bandeau"] = False

st.set_page_config(page_title="ABIMES - Frais", page_icon="🦇", layout="centered")

# ==============================================================================
# --- ÉCRAN D'ACCUEIL (DÉCONNECTÉ)
# ==============================================================================
if st.session_state["statut_connexion"] == "Deconnecte":
    st.title("🦇 Club ABIMES - Gestion des Frais")
    onglet_creer, onglet_connexion = st.tabs(["🆕 Créer une sortie", "🔑 Connexion"])
    
    with onglet_creer:
        with st.form("form_creation_sortie_initiale"):
            nom_sortie = st.text_input("Nom de la sortie (Obligatoire) :")
            email_responsable = st.text_input("Adresse email du responsable (Obligatoire) :")
            st.write("---")
            col1, col2 = st.columns(2)
            with col1: date_debut = st.date_input("Date de début :", format="DD/MM/YYYY")
            with col2: date_fin = st.date_input("Date de fin :", format="DD/MM/YYYY")
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
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT nom_sortie FROM sorties WHERE id_sortie = ? AND mot_de_passe_unique = ?", (login_id.strip(), login_mdp.strip()))
            res = c.fetchone()
            conn.close()
            if res:
                st.session_state["statut_connexion"] = "Connecte"
                st.session_state["id_sortie_active"] = login_id.strip()
                st.rerun()
            else: st.error("❌ Identifiants incorrects.")

# ==============================================================================
# --- ÉCRANS INTÉRIEURS (CONNECTÉ)
# ==============================================================================
else:
    id_sortie = st.session_state["id_sortie_active"]
    
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

    try:
        date_deb_formatee = datetime.strptime(s_ddeb, "%Y-%m-%d").strftime("%d/%m/%Y")
        date_fin_formatee = datetime.strptime(s_dfin, "%Y-%m-%d").strftime("%d/%m/%Y")
    except:
        date_deb_formatee = s_ddeb
        date_fin_formatee = s_dfin

    # ==============================================================================
    # --- CONSTRUTION DU BANDEAU GAUCHE AVEC LE BOUTON INTERRUPTEUR MODIFIABLE
    # ==============================================================================
    st.sidebar.title("🦇 Club ABIMES")
    st.sidebar.write(f"📅 **N° Sortie :** `{id_sortie}`")
    st.sidebar.write("---")
    
    # ÉCRAN 1 : MODE LECTURE (S'affiche par défaut)
    if not st.session_state["mode_edition_bandeau"]:
        st.sidebar.subheader("📋 Caractéristiques validées :")
        st.sidebar.write(f"🏷️ **Nom :** {s_nom}")
        st.sidebar.write(f"⏱️ **Dates :** du {date_deb_formatee} au {date_fin_formatee}")
        st.sidebar.write(f"🏡 **Gîte :** {s_gite}")
        st.sidebar.write(f"🗺️ **Département(s) :** {s_deps}")
        st.sidebar.write(f"🧗 **Activité :** {s_type}")
        st.sidebar.write(f"🕳️ **Cavités :**\n{s_cavites}")
        st.sidebar.write("---")
        
        # Le bouton d'ouverture du mode modification
        if st.sidebar.button("⚙️ Modifier les infos", key="btn_ouvrir_edition"):
            st.session_state["mode_edition_bandeau"] = True
            st.rerun()
            
    # ÉCRAN 2 : MODE ÉDITION EN DIRECT (S'ouvre au clic)
    else:
        st.sidebar.subheader("⚙️ Modification des infos :")
        
        try:
            d_deb_obj = datetime.strptime(s_ddeb, "%Y-%m-%d").date()
            d_fin_obj = datetime.strptime(s_dfin, "%Y-%m-%d").date()
        except:
            d_deb_obj = datetime.today().date()
            d_fin_obj = datetime.today().date()
            
        edit_nom = st.sidebar.text_input("Nom de la sortie :", value=s_nom, key="ed_nom")
        edit_ddeb = st.sidebar.date_input("Date de début :", value=d_deb_obj, format="DD/MM/YYYY", key="ed_ddeb")
        edit_dfin = st.sidebar.date_input("Date de fin :", value=d_fin_obj, format="DD/MM/YYYY", key="ed_dfin")
        edit_gite = st.sidebar.text_input("Lieu du gîte :", value=s_gite if s_gite != "Non renseigné" else "", key="ed_gite")
        edit_deps = st.sidebar.text_input("N° Département(s) :", value=s_deps if s_deps != "Non renseigné" else "", key="ed_deps")
        
