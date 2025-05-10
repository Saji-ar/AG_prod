
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("📝 Ajouter ou modifier un produit")

import os

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if "gcp_service_account" in st.secrets:
    # ✅ Streamlit Cloud : utiliser secrets
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
else:
    # ✅ Local : utiliser fichier json
    credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)

client = gspread.authorize(credentials)

# Feuille Produits
produits_ws = client.open("Produits").sheet1
data = produits_ws.get_all_records()
produits_df = pd.DataFrame(data)

# Liste des noms existants
noms_existants = produits_df["Nom"].dropna().tolist()
noms_existants.append("Nouveau produit")

selection = st.selectbox("Choisir un produit à modifier ou 'Nouveau produit'", noms_existants)

# Formulaire
if selection == "Nouveau produit":
    nom = st.text_input("Nom du produit")
    if nom in produits_df["Nom"].values:
        st.error("Un produit avec ce nom existe déjà.")
    description = st.text_area("Description")
    allergene = st.text_input("Allergène")
    prix = st.number_input("Prix (€)", min_value=0.0, step=0.01)
    sous_cat = st.text_input("Sous-catégories (ex: Chocolat, Fraise)")
else:
    row = produits_df[produits_df["Nom"] == selection].iloc[0]
    nom = st.text_input("Nom du produit", value=row["Nom"], disabled=True)
    description = st.text_area("Description", value=row["Description"])
    allergene = st.text_input("Allergène", value=row["Allergène"])
    prix = st.number_input("Prix (€)", min_value=0.0, step=0.01, value=float(row["Prix"]))
    sous_cat = st.text_input("Sous-catégories (ex: Chocolat, Fraise)", value=row.get("Sous-catégories", ""))

# Sauvegarde
if st.button("Sauvegarder"):
    if selection == "Nouveau produit" and nom in produits_df["Nom"].values:
        st.error("Ce produit existe déjà.")
    else:
        nouvelle_ligne = [nom, description, allergene, prix, sous_cat]

        # Supprimer l'ancienne ligne (si modification)
        if nom in produits_df["Nom"].values:
            index = produits_df[produits_df["Nom"] == nom].index[0]
            produits_ws.delete_rows(index + 2)  # +2 car gspread est 1-indexé et on saute l'entête

        # Ajouter la nouvelle ligne
        produits_ws.append_row(nouvelle_ligne)
        st.success("Produit ajouté/modifié avec succès ✅")
