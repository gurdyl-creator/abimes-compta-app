import streamlit as st
import sqlite3
import random
import string
import os

# --- INITIALISATION DE LA BASE DE DONNÉES ---
def initialisation_abimes_db():
    conn = sqlite3.connect("abimes_compta.db")
    c = conn.cursor()

    # Table des configurations/tarifs
    c.execute('''CREATE TABLE IF NOT EXISTS config_tarifs (
                    id INTEGER PRIMARY KEY, ik_chauffeur REAL, subv_km_club REAL, 
                    forfait_matos_cadre REAL, assurance_2j REAL, assurance_5j REAL, 
                    coef_ptit_dej REAL, coef_midi REAL, coef_soir REAL)''')
    c.execute("SELECT COUNT(*) FROM config_tarifs")
    if c.fetchone() == 0:
        c.execute("INSERT INTO config_tarifs VALUES (1, 0.15, 0.02, 5.00, 7.20, 15.50, 0.25, 0.50, 1.00)")

    # Table des sorties spéléo
    c.execute('''CREATE TABLE IF NOT EXISTS sorties (
                    id_sortie TEXT PRIMARY KEY, nom_sortie TEXT, date_debut TEXT, date_fin TEXT, 
                    lieu_gite TEXT, departements TEXT, cavites TEXT, type_activite TEXT, 
                    statut TEXT DEFAULT 'En cours', email_responsable TEXT, mot_de_passe_unique TEXT)''')

    # Table des participants
    c.execute('''CREATE TABLE IF NOT EXISTS participants (
                    id_participant INTEGER PRIMARY KEY AUTOINCREMENT, id_sortie TEXT, nom_format TEXT, 
                    email TEXT, statut_speleo TEXT, genre TEXT, tranche_age TEXT, 
                    option_assurance TEXT DEFAULT 'Aucune', option_matos INTEGER DEFAULT 0, 
                    propose_voiture INTEGER DEFAULT 0, statut_vote TEXT DEFAULT 'En attente', commentaire_vote TEXT)''')
    conn.commit()
    conn.close()

initialisation_abimes_db()

def generer_mot_de_passe():
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for _ in range(8))

# --- INTERFACE VISUELLE STREAMLIT ---
st.set_page_config(page_title="ABIMES - Compta", page_icon="🦇", layout="centered")

st.title("🦇 Club ABIMES - Gestion des Sorties")
st.write("Outil open-source de gestion et répartition des frais de week-ends spéléo.")

onglet_creer, onglet_connexion = st.tabs(["🆕 Créer une sortie", "🔑 Connexion Responsable / Admin"])

# --- ONGLET 1 : FORMULAIRE DE CRÉATION DE LA SORTIE ---
with onglet_creer:
    st.header("Déclarer un nouveau week-end ou camp")
    
    with st.form("formulaire_creation_sortie"):
        nom_sortie = st.text_input("Nom de la sortie (Obligatoire) :", placeholder="ex: Camp Vercors Octobre")
        email_responsable = st.text_input("Adresse email du responsable des comptes (Obligatoire) :", placeholder="prenom.nom@exemple.fr")
        
        st.write("---")
        st.write("👉 *Les informations ci-dessous sont optionnelles et modifiables par la suite.*")
        
        col1, col2 = st.columns(2)
        with col1:
            date_debut = st.date_input("Date de début :")
        with col2:
            date_fin = st.date_input("Date de fin :")
            
        type_activite = st.selectbox("Type d'activité spéléo :", [
            "classique", "explo", "formation/entrainement", "plongée", "secours", "scientifique", "canyon", "réunion"
        ])
        
        lieu_gite = st.text_input("Lieu du gîte / Hébergement :", placeholder="ex: Gîte des Cavottes")
        departements = st.text_input("N° Département(s) des explorations :", placeholder="ex: 25 ou 25, 39")
        cavites = st.text_area("Liste des cavités prévues ou visitées :", placeholder="ex: Cavottes, Verneau...")
        
        submit_bouton = st.form_submit_button("🚀 Valider et générer l'espace de la sortie")

    if submit_bouton:
        # Vérification des deux seuls champs obligatoires
        if nom_sortie and email_responsable:
            conn = sqlite3.connect("abimes_compta.db")
            c = conn.cursor()
            
            id_aleatoire = random.randint(100, 999)
            id_sortie = f"ABIMES-{date_debut.year}-S{id_aleatoire}"
            mot_de_passe = generer_mot_de_passe()
            
            try:
                c.execute('''INSERT INTO sorties (id_sortie, nom_sortie, date_debut, date_fin, lieu_gite, departements, cavites, type_activite, email_responsable, mot_de_passe_unique) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                          (id_sortie, nom_sortie, str(date_debut), str(date_fin), lieu_gite, departements, cavites, type_activite, email_responsable, mot_de_passe))
                conn.commit()
                
                st.success(f"🎉 La sortie '{nom_sortie}' a été créée avec succès dans la base de données ! ")
                st.info(f"**Voici vos accès exclusifs pour ce week-end :**\n\n"
                        f"➡️ **Identifiant / N° de Sortie :** `{id_sortie}`\n\n"
                        f"➡️ **Mot de passe unique de la sortie :** `{mot_de_passe}`\n\n"
                        f"⚠️ *Notez précieusement ce mot de passe. Il va vous être envoyé à l'adresse {email_responsable} et permettra de vous connecter dans l'onglet de connexion.*")
            except sqlite3.IntegrityError:
                st.error("Une erreur est survenue lors de la création de l'identifiant. Veuillez réessayer.")
            finally:
                conn.close()
        else:
            st.error("⚠️ Le nom de la sortie ET l'adresse email du responsable sont obligatoires pour générer l'espace.")

# --- ONGLET 2 : CONNEXION ---
with onglet_connexion:
    st.header("Accéder à un espace existant")
    st.text_input("N° de Sortie (ou 'ADMIN' pour le trésorier) :", key="login_id")
    st.text_input("Mot de passe :", type="password", key="login_mdp")
    st.button("Se connecter")
