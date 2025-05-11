

import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("📦 Produits sortis de production")

# Authentification Google

import os

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if "gcp_service_account" in st.secrets:
    # ✅ Streamlit Cloud : utiliser secrets
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
else:
    # ✅ Local : utiliser fichier json
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
produit = st.selectbox("Sélectionner un produit", [""] + liste_produits)
if not produit:
    st.stop()
if produit == "Autre":
    nom_libre = st.text_input("Nom du produit spécial")
    produit = nom_libre.strip() + " (autre)" if nom_libre.strip() else ""

quantite = st.number_input("Quantité produite", step=1)
if quantite < 0:
    st.warning("⚠️ Vous êtes en train de soustraire du stock.")

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
