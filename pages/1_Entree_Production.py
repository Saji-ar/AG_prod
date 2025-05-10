# import streamlit as st
# import pandas as pd
# import os
# from datetime import datetime

# st.title("📦 Produits sortis de production")

# try:
#     produits_df = pd.read_excel("produits.xlsx")
#     liste_produits = []

#     for _, row in produits_df.iterrows():
#         nom = row["Nom"]
#         sous_cats = str(row.get("Sous-catégories", "")).split(",")
#         sous_cats = [sc.strip() for sc in sous_cats if sc.strip()]
#         if sous_cats:
#             for sc in sous_cats:
#                 liste_produits.append(f"{nom} / {sc}")
#         else:
#             liste_produits.append(nom)
# except FileNotFoundError:
#     st.warning("Fichier produits.xlsx introuvable.")
#     liste_produits = []

# liste_produits.append("Autre")
# produit = st.selectbox("Sélectionner un produit", liste_produits)

# if produit == "Autre":
#     nom_libre = st.text_input("Nom du produit spécial")
#     produit = nom_libre.strip() + " (autre)" if nom_libre.strip() else ""

# quantite = st.number_input("Quantité produite", min_value=0, step=1)
# date = st.date_input("Date d’entrée en boutique", value=datetime.today())

# if st.button("Enregistrer"):
#     if not produit:
#         st.error("Merci de saisir un nom de produit.")
#     else:
#         nouvelle_entree = pd.DataFrame([[produit, quantite, date]], columns=["Produit", "Quantité", "Date"])
#         fichier = "production.xlsx"

#         if os.path.exists(fichier):
#             ancien = pd.read_excel(fichier)
#             df = pd.concat([ancien, nouvelle_entree], ignore_index=True)
#         else:
#             df = nouvelle_entree

#         df.to_excel(fichier, index=False)
#         st.success("Produit enregistré avec succès ✅")


import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("📦 Produits sortis de production")

# Authentification Google
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(credentials)

# Lire la feuille "Produits"
produits_ws = client.open("Produits").sheet1
produits_data = produits_ws.get_all_records()
produits_df = pd.DataFrame(produits_data)

# Construire la liste des produits / sous-catégories
liste_produits = []
for _, row in produits_df.iterrows():
    nom = row["Nom"]
    sous_cats = str(row.get("Sous-catégories", "")).split(",")
    sous_cats = [sc.strip() for sc in sous_cats if sc.strip()]
    if sous_cats:
        for sc in sous_cats:
            liste_produits.append(f"{nom} / {sc}")
    else:
        liste_produits.append(nom)

liste_produits.append("Autre")
produit = st.selectbox("Sélectionner un produit", liste_produits)

if produit == "Autre":
    nom_libre = st.text_input("Nom du produit spécial")
    produit = nom_libre.strip() + " (autre)" if nom_libre.strip() else ""

quantite = st.number_input("Quantité produite", min_value=0, step=1)
date = st.date_input("Date d’entrée en boutique", value=datetime.today())

# Ajout dans la feuille "Prod" du fichier AG_prod
if st.button("Enregistrer"):
    if not produit:
        st.error("Merci de saisir un nom de produit.")
    else:
        ag_prod = client.open("AG_prod")
        prod_ws = ag_prod.worksheet("Prod")
        prod_ws.append_row([produit, int(quantite), str(date)])
        st.success("Produit enregistré dans Google Sheets ✅")
