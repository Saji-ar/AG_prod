# import streamlit as st
# import pandas as pd
# import os
# from datetime import datetime, timedelta

# st.title("🏪 Stock actuel en boutique")

# fichier_production = "production.xlsx"
# produits_recents = []

# # Charger les produits produits récemment
# if os.path.exists(fichier_production):
#     df_prod = pd.read_excel(fichier_production)
#     df_prod["Date"] = pd.to_datetime(df_prod["Date"])

#     # Produits des 7 derniers jours
#     date_limite = datetime.today() - timedelta(days=7)
#     df_recent = df_prod[df_prod["Date"] >= date_limite]
#     produits_recents = df_recent["Produit"].dropna().unique().tolist()

# else:
#     st.warning("Fichier production.xlsx introuvable.")
#     produits_recents = []

# # Ajouter l'option Autre
# produits_recents.append("Autre")

# produit = st.selectbox("Sélectionner un produit récent", produits_recents)

# if produit == "Autre":
#     produit = st.text_input("Nom du produit (spécial)")

# quantite = st.number_input("Quantité présente", min_value=0, step=1)
# date = st.date_input("Date du relevé", value=datetime.today())

# if st.button("Ajouter au stock"):
#     nouvelle_entree = pd.DataFrame([[produit, quantite, date]], columns=["Produit", "Quantité", "Date"])
#     fichier = "stock_boutique.xlsx"

#     if os.path.exists(fichier):
#         ancien = pd.read_excel(fichier)
#         df = pd.concat([ancien, nouvelle_entree], ignore_index=True)
#     else:
#         df = nouvelle_entree

#     df.to_excel(fichier, index=False)
#     st.success("Stock enregistré avec succès ✅")
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("🏪 Stock actuel en boutique")

# Authentification Google
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]
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
