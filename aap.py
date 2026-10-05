import streamlit as st
import sqlite3
import random
import string
import os

# --- INITIALISATION DE LA BASE DE DONNÉES (Exécutée une seule fois en ligne) ---
def initialisation_abimes_db():
    conn = sqlite3.connect("abimes_compta.db")
    c = conn.cursor()

    # Table des configurations/tarifs (Valeurs par défaut décidées en AG)
    c.execute('''CREATE TABLE IF NOT EXISTS config_tarifs (
                    id INTEGER PRIMARY KEY, ik_chauffeur REAL, subv_km_club REAL, 
                    forfait_matos_cadre REAL, assurance_2j REAL, assurance_5j REAL, 
                    coef_ptit_dej REAL, coef_midi REAL, coef_soir REAL)''')
    c.execute("SELECT COUNT(*) FROM config_tarifs")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO config_tarifs VALUES (1, 0.15, 0.02, 5.00, 7.20, 15.50, 0.25, 0.50, 1.00)")

    # Table des sorties spéléo
    c.execute('''CREATE TABLE IF NOT EXISTS sorties (
                    id_sortie TEXT PRIMARY KEY, nom_sortie TEXT, date_debut TEXT, date_fin TEXT, 
                    lieu_gite TEXT, departements TEXT, cavites TEXT, type_activite TEXT, 
                    statut TEXT DEFAULT 'En cours', email_responsable TEXT, mot_de_passe_unique TEXT)''')

    # Table des participants (avec email et suivi du vote)
    c.execute('''CREATE TABLE IF NOT EXISTS participants (
                    id_participant INTEGER PRIMARY KEY AUTOINCREMENT, id_sortie TEXT, nom_format TEXT, 
                    email TEXT, statut_speleo TEXT, genre TEXT, tranche_age TEXT, 
                    option_assurance TEXT DEFAULT 'Aucune', option_matos INTEGER DEFAULT 0, 
                    propose_voiture INTEGER DEFAULT 0, statut_vote TEXT DEFAULT 'En attente', commentaire_vote TEXT)''')
    conn.commit()
    conn.close()

# Lancement automatique de la création des tables
initialisation_abimes_db()

# --- FONCTION COMPLÉMENTAIRE : GÉNÉRATION DU MOT DE PASSE UNIQUE ---
def generer_mot_de_passe():
    # Génère une clé unique de 8 caractères (Lettres et Chiffres)
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for _ in range(8))

# --- INTERFACE VISUELLE STREAMLIT ---
st.set_page_config(page_title="ABIMES - Compta v2025", page_icon="🦇", layout="centered")

st.title("🦇 Club ABIMES - Gestion des Sorties")
st.write("Outil open-source de gestion et répartition des frais de week-ends spéléo.")

# Création des deux onglets principaux sur la page d'accueil
onglet_creer, onglet_connexion = st.tabs(["🆕 Créer une sortie", "🔑 Connexion Responsable / Admin"])

# --- ONGLET 1 : FORMULAIRE DE CRÉATION DE LA SORTIE ---
with onglet_creer:
    st.header("Déclarer un nouveau week-end ou camp")
    
    with st.form("formulaire_creation_sortie"):
        col1, col2 = st.columns(2)
        with col1:
            date_debut = st.date_input("Date de début du week-end :")
        with col2:
            date_fin = st.date_input("Date de fin du week-end :")
            
        type_activite = st.selectbox("Type d'activité spéléo :", [
            "classique", "explo", "formation/entrainement", "plongée", "secours", "scientifique", "canyon", "réunion"
        ])
        
        nom_sortie = st.text_input("Nom convivial de la sortie :", placeholder="ex: Stage Initiation Vercors")
        lieu_gite = st.text_input("Lieu du gîte / Hébergement :", placeholder="ex: Gîte des Cavottes")
        
        # Saisie libre pour un ou plusieurs départements (ex: 25, 39, 70)
        departements = st.text_input("N° Département(s) des explorations :", placeholder="ex: 25 ou 25, 39")
        
        # Liste des gouffres/grottes explorés
        cavites = st.text_area("Liste des cavités prévues ou visitées :", placeholder="ex: Gouffre Berger, Grotte de la Luire...")
        
        st.write("---")
        st.subheader("👤 Responsable de la saisie des comptes")
        email_responsable = st.text_input("Votre adresse email :", placeholder="prenom.nom@exemple.fr")
        
        submit_bouton = st.form_submit_button("🚀 Valider et générer l'espace de la sortie")

    # Logique lors du clic sur le bouton de validation
    if submit_bouton:
        if nom_sortie and lieu_gite and email_responsable:
            conn = sqlite3.connect("abimes_compta.db")
            c = conn.cursor()
            
            # Génération d'une référence unique pour la sortie (ex: S_2026_458)
            id_aleatoire = random.randint(100, 999)
            id_sortie = f"ABIMES-{date_debut.year}-S{id_aleatoire}"
            
            # Génération du mot de passe unique pour cette sortie précise
            mot_de_passe = generer_mot_de_passe()
            
            try:
                c.execute('''INSERT INTO sorties (id_sortie, nom_sortie, date_debut, date_fin, lieu_gite, departements, cavites, type_activite, email_responsable, mot_de_passe_unique) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                          (id_sortie, nom_sortie, str(date_debut), str(date_fin), lieu_gite, departements, cavites, type_activite, email_responsable, mot_de_passe))
                conn.commit()
                
                # Message de succès affichant les identifiants uniques
                st.success(f"🎉 La sortie a été créée avec succès dans la base de données de l'association !")
                st.info(f"**Voici vos accès exclusifs pour ce week-end :**\n\n"
                        f"➡️ **Identifiant / N° de Sortie :** `{id_sortie}`\n\n"
                        f"➡️ **Mot de passe unique de la sortie :** `{mot_de_passe}`\n\n"
                        f"⚠️ *Notez précieusement ce mot de passe. Il va également vous être envoyé à l'adresse {email_responsable} pour pouvoir vous connecter dans l'onglet ci-dessus.*")
            except sqlite3.IntegrityError:
                st.error("Une erreur est survenue lors de la création de l'identifiant. Veuillez réessayer.")
            finally:
                conn.close()
        else:
            st.warning("⚠️ Veuillez remplir au minimum le nom de la sortie, le lieu du gîte et votre adresse email.")

# --- ONGLET 2 : ZONE EN CONSTRUCTION (Connexion) ---
with onglet_connexion:
    st.header("Accéder à un espace existant")
    st.text_input("N° de Sortie (ou 'ADMIN' pour le trésorier) :", key="login_id")
    st.text_input("Mot de passe :", type="password", key="login_mdp")
    st.button("Se connecter")
