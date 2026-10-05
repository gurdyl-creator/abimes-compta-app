import streamlit as st
import sqlite3
import os

st.set_page_config(page_title="ABIMES - Compta", page_icon="🦇")
st.title("🦇 Association ABIMES - Gestion des Sorties")

st.write("Félicitations ! L'application fonctionne en ligne sans aucune installation sur votre PC.")

# Un petit bouton de test pour vérifier la base de données SQLite
if st.button("Vérifier la structure de la base de données"):
    if os.path.exists("abimes_compta.db"):
        st.success("Le fichier coffre-fort 'abimes_compta.db' est bien présent et actif !")
    else:
        st.warning("Le fichier de base de données n'est pas encore créé, mais l'interface est prête.")
