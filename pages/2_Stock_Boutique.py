import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("🏪 Stock actuel en boutique")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
) if "gcp_service_account" in st.secrets else ServiceAccountCredentials.from_json_keyfile_name(
    "service_account.json", scope
)
client = gspread.authorize(credentials)

# Accès aux feuilles
ag_prod = client.open("AG_prod")
prod_ws = ag_prod.worksheet("Prod")
stock_ws = ag_prod.worksheet("Stock")
produits_ws = client.open("Produits").sheet1

# Chargement des données
from utils.google_sheets import load_ws_df, load_sheet_df

prod_df = load_ws_df("AG_prod", "Prod")
stock_df = load_ws_df("AG_prod", "Stock")
produits_df = load_sheet_df("Produits")

# Nettoyage des dates
for df, col in [(prod_df, "Date"), (stock_df, "Date")]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

# Produits issus de la feuille Produits
produits_catalogue = set()
for _, row in produits_df.iterrows():
    nom = row["Nom"]
    sous_cats = [s.strip() for s in str(row.get("Sous-catégories", "")).split(",")] if row.get("Sous-catégories") else [""]
    for sc in sous_cats:
        produits_catalogue.add(f"{nom} / {sc}" if sc else nom)

# Produits "autres" vus dans les 7 derniers jours (prod ou stock)
date_limite = datetime.today() - timedelta(days=7)
autres = set()

for df in [prod_df, stock_df]:
    recent = df[df["Date"] >= date_limite]
    for nom in recent["Produit"].dropna().unique():
        if nom not in produits_catalogue:
            autres.add(nom)

# Liste finale
liste_produits = sorted(produits_catalogue.union(autres))
liste_produits.append("Autre")

# Interface
produit = st.selectbox("Sélectionner un produit", [""] + liste_produits)
if not produit:
    st.stop()

if produit == "Autre":
    produit = st.text_input("Nom du produit (spécial)")

quantite = st.number_input("Quantité présente", step=1)
if quantite < 0:
    st.warning("⚠️ Vous êtes en train de soustraire du stock.")

date = st.date_input("Date du relevé", value=datetime.today())

if st.button("Ajouter au stock"):
    if not produit:
        st.error("Merci d’entrer un nom de produit.")
    else:
        stock_ws.append_row([produit, int(quantite), str(date)])
        st.success("Stock enregistré dans Google Sheets ✅")

