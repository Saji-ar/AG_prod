

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("🗑️ Retrait des produits")

import os

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if "gcp_service_account" in st.secrets:
    # ✅ Streamlit Cloud : utiliser secrets
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
else:
    # ✅ Local : utiliser fichier json
    credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)

client = gspread.authorize(credentials)

# Chargement des feuilles
ag_prod = client.open("AG_prod")
prod_ws = ag_prod.worksheet("Prod")
stock_ws = ag_prod.worksheet("Stock")
retrait_ws = ag_prod.worksheet("Retrait")

# Récupération des données
prod_df = pd.DataFrame(prod_ws.get_all_records())
stock_df = pd.DataFrame(stock_ws.get_all_records())
retrait_df = pd.DataFrame(retrait_ws.get_all_records())

# Assurer cohérence des colonnes si vide
for df, cols in [(stock_df, ["Produit", "Quantité", "Date"]),
                 (prod_df, ["Produit", "Quantité", "Date"]),
                 (retrait_df, ["Produit", "Quantité", "Date de retrait", "Date de production", "Raison"])]:
    for col in cols:
        if col not in df.columns:
            df[col] = None

# Format des dates
stock_df["Date"] = pd.to_datetime(stock_df["Date"], errors="coerce")
prod_df["Date"] = pd.to_datetime(prod_df["Date"], errors="coerce")
today = datetime.today().date()
periode_recente = [today - timedelta(days=i) for i in range(1, 3)]
periode_7j = [today - timedelta(days=i) for i in range(1, 8)]

# === PARTIE 1 : RETRAITS AUTOMATIQUES ===
st.subheader("🔎 Retraits automatiques des produits anciens (> 3 jours)")

stock_today = stock_df[stock_df["Date"].dt.date == today]
stock_grouped = stock_today.groupby("Produit")["Quantité"].sum()

retrait_recents = retrait_df[
    retrait_df["Date de production"].notna() &
    retrait_df["Date de production"].isin(periode_recente)
].groupby("Produit")["Quantité"].sum().abs()

for produit, quantite_stock in stock_grouped.items():
    quantite_produite = prod_df[
        (prod_df["Produit"] == produit) &
        (prod_df["Date"].dt.date.isin(periode_recente))
    ]["Quantité"].sum()

    quantite_produite += retrait_recents.get(produit, 0)
    surplus = quantite_stock - quantite_produite

    if surplus <= 0:
        continue

    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"🔻 **{produit}** – À retirer : `{int(surplus)}` unités (anciens)")
        with col2:
            if st.button("✅ Valider retrait", key=f"{produit}_{surplus}"):
                retrait_ws.append_row([
                    produit, int(surplus), str(today), "", "Ancien > 4 jours"
                ])
                # stock_ws.append_row([
                #     produit, -int(surplus), str(today)
                # ])
                st.success(f"Retrait validé pour {int(surplus)} {produit}")

# === PARTIE 2 : RETRAIT MANUEL ===
st.subheader("✋ Retrait manuel d’un produit")

produits_7j = prod_df[prod_df["Date"].dt.date.isin(periode_7j)]["Produit"].dropna().unique().tolist()
produits_7j.append("Autre")
produit_sel = st.selectbox("Produit à retirer", produits_7j)

if produit_sel == "Autre":
    produit_sel = st.text_input("Nom du produit (personnalisé)")

quantite_retrait = st.number_input("Quantité à retirer", min_value=1, step=1)
date_prod = st.date_input("Date de production", max_value=today)
raison = st.text_input("Raison du retrait")
date_retrait = st.date_input("Date du retrait", value=today)

if st.button("📤 Enregistrer le retrait manuel"):
    retrait_ws.append_row([
        produit_sel, int(quantite_retrait), str(date_retrait), str(date_prod), raison
    ])
    # stock_ws.append_row([
    #     produit_sel, -int(quantite_retrait), str(date_retrait)
    # ])
    st.success(f"{quantite_retrait} {produit_sel} retiré manuellement ✔️")
