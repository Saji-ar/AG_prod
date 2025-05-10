# import streamlit as st
# import pandas as pd
# import os

# st.title("📝 Ajouter ou modifier un produit")

# fichier_produits = "produits.xlsx"

# # Chargement
# if os.path.exists(fichier_produits):
#     produits_df = pd.read_excel(fichier_produits)
# else:
#     produits_df = pd.DataFrame(columns=["Nom", "Description", "Allergène", "Prix", "Sous-catégories"])

# noms_existants = produits_df["Nom"].dropna().tolist()
# noms_existants.append("Nouveau produit")

# selection = st.selectbox("Choisir un produit à modifier ou 'Nouveau produit'", noms_existants)

# if selection == "Nouveau produit":
#     nom = st.text_input("Nom du produit")
#     if nom in produits_df["Nom"].values:
#         st.error("Un produit avec ce nom existe déjà.")
#     description = st.text_area("Description")
#     allergene = st.text_input("Allergène")
#     prix = st.number_input("Prix (€)", min_value=0.0, step=0.01)
#     sous_cat = st.text_input("Sous-catégories (ex: Chocolat, Fraise)")
# else:
#     row = produits_df[produits_df["Nom"] == selection].iloc[0]
#     nom = st.text_input("Nom du produit", value=row["Nom"], disabled=True)
#     description = st.text_area("Description", value=row["Description"])
#     allergene = st.text_input("Allergène", value=row["Allergène"])
#     prix = st.number_input("Prix (€)", min_value=0.0, step=0.01, value=float(row["Prix"]))
#     sous_cat = st.text_input("Sous-catégories (ex: Chocolat, Fraise)", value=row.get("Sous-catégories", ""))

# if st.button("Sauvegarder"):
#     nouvelle_ligne = pd.DataFrame([[nom, description, allergene, prix, sous_cat]], 
#                                   columns=["Nom", "Description", "Allergène", "Prix", "Sous-catégories"])
#     produits_df = produits_df[produits_df["Nom"] != nom]
#     produits_df = pd.concat([produits_df, nouvelle_ligne], ignore_index=True)
#     produits_df.to_excel(fichier_produits, index=False)
#     st.success("Produit ajouté/modifié avec succès ✅")


import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("📝 Ajouter ou modifier un produit")

# Authentification Google
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]
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
