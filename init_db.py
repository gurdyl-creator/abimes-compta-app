import sqlite3

def initialisation_abimes_db():
    # Connexion au fichier local de la base de données
    conn = sqlite3.connect("abimes_compta.db")
    c = conn.cursor()

    # 1. TABLE CONFIGURATION DES TARIFS (Modifiable par l'Admin)
    c.execute('''CREATE TABLE IF NOT EXISTS config_tarifs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ik_chauffeur REAL DEFAULT 0.15,
                    subv_km_club REAL DEFAULT 0.02,
                    forfait_matos_cadre REAL DEFAULT 5.00,
                    assurance_2j REAL DEFAULT 7.20,
                    assurance_5j REAL DEFAULT 15.50,
                    coef_ptit_dej REAL DEFAULT 0.25,
                    coef_midi REAL DEFAULT 0.50,
                    coef_soir REAL DEFAULT 1.00)''')

    # Insertion des tarifs d'origine si la table est vide
    c.execute("SELECT COUNT(*) FROM config_tarifs")
    if c.fetchone()[0] == 0:
        c.execute('''INSERT INTO config_tarifs (ik_chauffeur, subv_km_club, forfait_matos_cadre, assurance_2j, assurance_5j, coef_ptit_dej, coef_midi, coef_soir)
                     VALUES (0.15, 0.02, 5.00, 7.20, 15.50, 0.25, 0.50, 1.00)''')

    # 2. TABLE DES SORTIES SPÉLÉO
    c.execute('''CREATE TABLE IF NOT EXISTS sorties (
                    id_sortie TEXT PRIMARY KEY,
                    nom_sortie TEXT,
                    date_debut TEXT,
                    date_fin TEXT,
                    lieu_gite TEXT,
                    departements TEXT,
                    cavites TEXT,
                    type_activite TEXT,
                    statut TEXT DEFAULT 'En cours',
                    email_responsable TEXT,
                    mot_de_passe_unique TEXT)''')

    # 3. TABLE DES PARTICIPANTS
    c.execute('''CREATE TABLE IF NOT EXISTS participants (
                    id_participant INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_sortie TEXT,
                    nom_format TEXT,
                    email TEXT,
                    statut_speleo TEXT,
                    genre TEXT,
                    tranche_age TEXT,
                    option_assurance TEXT DEFAULT 'Aucune',
                    option_matos INTEGER DEFAULT 0,
                    propose_voiture INTEGER DEFAULT 0,
                    statut_vote TEXT DEFAULT 'En attente',
                    commentaire_vote TEXT,
                    FOREIGN KEY(id_sortie) REFERENCES sorties(id_sortie) ON DELETE CASCADE)''')

    # 4. TABLE DES REPAS (Grille dynamique à coefficients décimaux)
    c.execute('''CREATE TABLE IF NOT EXISTS repas_coefs (
                    id_coef INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_participant INTEGER,
                    nom_repas TEXT,
                    valeur_coef REAL DEFAULT 1.00,
                    FOREIGN KEY(id_participant) REFERENCES participants(id_participant) ON DELETE CASCADE)''')

    # 5. TABLE DES VÉHICULES (Trajets collectifs / individuels / Blablacar)
    c.execute('''CREATE TABLE IF NOT EXISTS vehicules (
                    id_vehicule INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_sortie TEXT,
                    id_chauffeur INTEGER,
                    type_transport TEXT DEFAULT 'Collectif',
                    km_depart INTEGER DEFAULT 0,
                    km_arrivee INTEGER DEFAULT 0,
                    recette_blablacar REAL DEFAULT 0.00,
                    FOREIGN KEY(id_sortie) REFERENCES sorties(id_sortie) ON DELETE CASCADE,
                    FOREIGN KEY(id_chauffeur) REFERENCES participants(id_participant) ON DELETE CASCADE)''')

    # 6. TABLE DES DÉPENSES (Gîte, Nourriture, Matériel, Remboursements Club)
    c.execute('''CREATE TABLE IF NOT EXISTS depenses (
                    id_depense INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_sortie TEXT,
                    id_acheteur INTEGER,
                    montant REAL,
                    code_compta TEXT,
                    intitule TEXT,
                    photo_ticket_path TEXT,
                    imputation_type TEXT DEFAULT 'Collectif',
                    liste_beneficiaires TEXT,
                    FOREIGN KEY(id_sortie) REFERENCES sorties(id_sortie) ON DELETE CASCADE,
                    FOREIGN KEY(id_acheteur) REFERENCES participants(id_participant) ON DELETE CASCADE)''')

    conn.commit()
    conn.close()
    print("Structure de la base de données ABIMES créée avec succès !")

if __name__ == "__main__":
    initialisation_abimes_db()
