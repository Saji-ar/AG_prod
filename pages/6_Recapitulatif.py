import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("📊 Récapitulatif journalier des produits")

# Authentification Google
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(credentials)

# Feuilles
produits_ws = client.open("Produits").sheet1
ag_prod = client.open("AG_prod")
prod_ws = ag_prod.worksheet("Prod")
stock_ws = ag_prod.worksheet("Stock")
retrait_ws = ag_prod.worksheet("Retrait")

# Données
produits_df = pd.DataFrame(produits_ws.get_all_records())
prod_df = pd.DataFrame(prod_ws.get_all_records())
stock_df = pd.DataFrame(stock_ws.get_all_records())
retrait_df = pd.DataFrame(retrait_ws.get_all_records())

today = datetime.today().date()
periode_7j = [today - timedelta(days=i) for i in range(7)]

# Format des dates
for df, col in [(prod_df, "Date"), (stock_df, "Date"), (retrait_df, "Date de retrait")]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

# Tous les produits référencés
produits_ref = set()
for _, row in produits_df.iterrows():
    nom = row["Nom"]
    sous_cats = [s.strip() for s in str(row.get("Sous-catégories", "")).split(",")] if row.get("Sous-catégories") else [""]
    for sc in sous_cats:
        produits_ref.add(f"{nom} / {sc}" if sc else nom)

# Produits vus dans les 7 derniers jours
produits_vus = set()
for df, date_col in [(prod_df, "Date"), (stock_df, "Date"), (retrait_df, "Date de retrait")]:
    if "Produit" in df.columns and date_col in df.columns:
        sous_df = df[df[date_col].isin(periode_7j)]
        produits_vus.update(sous_df["Produit"].dropna().unique())

# Séparation référencés / autres
produits_autres = produits_vus - produits_ref
produits_valides = produits_vus & produits_ref

# Construction des lignes référencées
recap_rows = []
checkbox_states = {}

for _, row in produits_df.iterrows():
    nom = row["Nom"]
    sous_cats = [s.strip() for s in str(row.get("Sous-catégories", "")).split(",")] if row.get("Sous-catégories") else [""]
    print(str(row.get("Dispo", "")))
    dispo_raw = str(row.get("Dispo", "")).strip().lower().split(",")
    dispo_vals = (dispo_raw + ["n"] * len(sous_cats))[:len(sous_cats)]


    print(dispo_vals)
    for i, sous_cat in enumerate(sous_cats):
        nom_complet = f"{nom} / {sous_cat}" if sous_cat else nom
        if nom_complet not in produits_valides:
            continue

        stock = stock_df[(stock_df["Produit"] == nom_complet) & (stock_df["Date"] == today)]["Quantité"].sum()
        prod = prod_df[(prod_df["Produit"] == nom_complet) & (prod_df["Date"] == today)]["Quantité"].sum()
        retrait = retrait_df[(retrait_df["Produit"] == nom_complet) & (retrait_df["Date de retrait"] == today)]["Quantité"].sum()
        total = stock + prod - retrait

        key = f"{nom}__{i}"
        checkbox_states[key] = st.checkbox(f"{nom_complet} (Total: {total})", value=(dispo_vals[i] == "y"), key=key)

        recap_rows.append({
            "Nom complet": nom_complet,
            "Nom": nom,
            "Index": i,
            "Sous-catégorie": sous_cat,
            "Stock": stock,
            "Production": prod,
            "Retrait": retrait,
            "Total théorique": total
        })

# ✅ Tableau des produits référencés
if recap_rows:
    recap_df = pd.DataFrame(recap_rows)
    st.subheader("🧾 Produits référencés (avec case à cocher)")
    st.dataframe(recap_df[["Nom complet", "Stock", "Production", "Retrait", "Total théorique"]])
else:
    st.info("Aucun produit référencé actif sur les 7 derniers jours.")

# ✅ Tableau des produits autres
autres_rows = []

for nom in produits_autres:
    stock = stock_df[(stock_df["Produit"] == nom) & (stock_df["Date"] == today)]["Quantité"].sum()
    prod = prod_df[(prod_df["Produit"] == nom) & (prod_df["Date"] == today)]["Quantité"].sum()
    retrait = retrait_df[(retrait_df["Produit"] == nom) & (retrait_df["Date de retrait"] == today)]["Quantité"].sum()
    total = stock + prod - retrait

    autres_rows.append({
        "Produit": nom,
        "Stock": stock,
        "Production": prod,
        "Retrait": retrait,
        "Total théorique": total
    })

if autres_rows:
    autres_df = pd.DataFrame(autres_rows)
    st.subheader("📦 Produits non référencés (autres)")
    st.dataframe(autres_df)
else:
    st.info("Aucun produit hors catalogue produit ces 7 derniers jours.")

# ✅ Sauvegarde des cases à cocher
if st.button("💾 Sauvegarder la disponibilité"):
    for nom in produits_df["Nom"].unique():
        ligne = produits_df[produits_df["Nom"] == nom].iloc[0]
        sous_cats = [s.strip() for s in str(ligne.get("Sous-catégories", "")).split(",")] if ligne.get("Sous-catégories") else [""]
        dispo_final = []
        for i in range(len(sous_cats)):
            dispo_final.append("y" if checkbox_states.get(f"{nom}__{i}", False) else "n")
        dispo_str = ",".join(dispo_final)
        row_index = produits_df[produits_df["Nom"] == nom].index[0]
        produits_ws.update_cell(row_index + 2, produits_df.columns.get_loc("Dispo") + 1, dispo_str)

    st.success("Disponibilités mises à jour ✅")
