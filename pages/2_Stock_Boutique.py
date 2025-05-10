
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("🏪 Stock actuel en boutique")

import os

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if "gcp_service_account" in st.secrets:
    # ✅ Streamlit Cloud : utiliser secrets
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
else:
    # ✅ Local : utiliser fichier json
    credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)

client = gspread.authorize(credentials)
# Accès à la feuille de production
ag_prod = client.open("AG_prod")
prod_ws = ag_prod.worksheet("Prod")
prod_data = prod_ws.get_all_records()
df_prod = pd.DataFrame(prod_data)

# Sélection des produits produits dans les 7 derniers jours
produits_recents = []
if not df_prod.empty:
    df_prod["Date"] = pd.to_datetime(df_prod["Date"], errors="coerce")
    date_limite = datetime.today() - timedelta(days=7)
    df_recent = df_prod[df_prod["Date"] >= date_limite]
    produits_recents = df_recent["Produit"].dropna().unique().tolist()

# Ajouter "Autre"
produits_recents.append("Autre")
produit = st.selectbox("Sélectionner un produit récent", produits_recents)

if produit == "Autre":
    produit = st.text_input("Nom du produit (spécial)")

quantite = st.number_input("Quantité présente", min_value=0, step=1)
date = st.date_input("Date du relevé", value=datetime.today())

if st.button("Ajouter au stock"):
    if not produit:
        st.error("Merci d’entrer un nom de produit.")
    else:
        stock_ws = ag_prod.worksheet("Stock")
        stock_ws.append_row([produit, int(quantite), str(date)])
        st.success("Stock enregistré dans Google Sheets ✅")
