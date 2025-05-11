import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("📆 Récapitulatif par date (sans cases)")

# Authentification
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
) if "gcp_service_account" in st.secrets else ServiceAccountCredentials.from_json_keyfile_name(
    "service_account.json", scope
)
client = gspread.authorize(credentials)

# Feuilles
produits_ws = client.open("Produits").sheet1
ag_prod = client.open("AG_prod")
prod_ws = ag_prod.worksheet("Prod")
stock_ws = ag_prod.worksheet("Stock")
retrait_ws = ag_prod.worksheet("Retrait")

# Lecture
produits_df = pd.DataFrame(produits_ws.get_all_records())
prod_df = pd.DataFrame(prod_ws.get_all_records())
stock_df = pd.DataFrame(stock_ws.get_all_records())
retrait_df = pd.DataFrame(retrait_ws.get_all_records())

# Format dates
for df, col in [(prod_df, "Date"), (stock_df, "Date"), (retrait_df, "Date de retrait")]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

# Sélection date
selected_date = st.date_input("Choisir une date", value=datetime.today().date())
date_suivante = selected_date + timedelta(days=1)

# Tous les produits référencés
produits_ref = set()
for _, row in produits_df.iterrows():
    nom = row["Nom"]
    sous_cats = [s.strip() for s in str(row.get("Sous-catégories", "")).split(",")] if row.get("Sous-catégories") else [""]
    for sc in sous_cats:
        produits_ref.add(f"{nom} / {sc}" if sc else nom)

# Données
recap_rows = []

for _, row in produits_df.iterrows():
    nom = row["Nom"]
    try:
        prix = float(str(row.get("Prix", 0)).replace(",", ".").replace("€", "").strip())
    except:
        prix = 0.0
        print(prix)
    sous_cats = [s.strip() for s in str(row.get("Sous-catégories", "")).split(",")] if row.get("Sous-catégories") else [""]

    for sc in sous_cats:
        nom_complet = f"{nom} / {sc}" if sc else nom

        stock = stock_df[(stock_df["Produit"] == nom_complet) & (stock_df["Date"] == selected_date)]["Quantité"].sum()
        stock_lendemain = stock_df[(stock_df["Produit"] == nom_complet) & (stock_df["Date"] == date_suivante)]["Quantité"].sum()
        prod = prod_df[(prod_df["Produit"] == nom_complet) & (prod_df["Date"] == selected_date)]["Quantité"].sum()
        retrait = retrait_df[(retrait_df["Produit"] == nom_complet) & (retrait_df["Date de retrait"] == selected_date)]["Quantité"].sum()

        vendu = stock + prod - retrait - stock_lendemain
        montant = max(vendu - retrait, 0) * prix  # sécurité retrait > vendu

        recap_rows.append({
            "Produit": nom_complet,
            "Stock": stock,
            "Production": prod,
            "Retrait": retrait,
            "Stock J+1": stock_lendemain,
            "Vendu": vendu,
            "Prix (€)": prix,
            "Montant (€)": montant
        })

# Affichage
df_final = pd.DataFrame(recap_rows)
if not df_final.empty:
    st.dataframe(df_final)
else:
    st.info("Aucune donnée pour cette date.")
