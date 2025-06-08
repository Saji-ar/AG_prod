import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client

# Connexion Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("📆 Récapitulatif par date (Supabase)")

# Chargement
@st.cache_data(ttl=60)
def charger_donnees():
    produits = supabase.table("produits").select("*").execute().data
    stock = supabase.table("Stock").select("*").execute().data
    prod = supabase.table("Prod").select("*").execute().data
    retrait = supabase.table("Retrait").select("*").execute().data

    produits_df = pd.DataFrame(produits)
    stock_df = pd.DataFrame(stock)
    prod_df = pd.DataFrame(prod)
    retrait_df = pd.DataFrame(retrait)

    for df, col in [(stock_df, "date"), (prod_df, "date"), (retrait_df, "date_de_retrait")]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    return produits_df, stock_df, prod_df, retrait_df

produits_df, stock_df, prod_df, retrait_df = charger_donnees()

# Sélection de date
selected_date = st.date_input("📅 Choisir une date", value=datetime.today().date())
date_suivante = selected_date + timedelta(days=1)

# Calcul du récapitulatif
recap = []
produits_df["sous_categories"] = produits_df["sous_categories"].apply(lambda x: x if isinstance(x, list) else [""])

for _, prod in produits_df.iterrows():
    nom = prod["nom"]
    sous_cats = prod["sous_categories"]
    try:
        prix = float(str(prod.get("prix", 0)).replace(",", ".").replace("€", "").strip())
    except:
        prix = 0.0

    for sc in sous_cats:
        nom_complet = f"{nom} / {sc}" if sc else nom

        stock_j = stock_df[(stock_df["produit"] == nom) & (stock_df["sous_categorie"] == sc) & (stock_df["date"] == selected_date)]["quantite"].sum()
        stock_j1 = stock_df[(stock_df["produit"] == nom) & (stock_df["sous_categorie"] == sc) & (stock_df["date"] == date_suivante)]["quantite"].sum()
        prod_j = prod_df[(prod_df["produit"] == nom) & (prod_df["sous_categorie"] == sc) & (prod_df["date"] == selected_date)]["quantite"].sum()
        retrait_j = retrait_df[(retrait_df["produit"] == nom) & (retrait_df["sous_categorie"] == sc) & (retrait_df["date_de_retrait"] == selected_date)]["quantite"].sum()

        vendu = stock_j + prod_j - retrait_j - stock_j1
        montant = max(vendu, 0) * prix

        recap.append({
            "Produit": nom_complet,
            "Stock": stock_j,
            "Production": prod_j,
            "Retrait": retrait_j,
            "Stock J+1": stock_j1,
            "Vendu": vendu,
            "Prix (€)": prix,
            "Montant (€)": montant
        })

df_recap = pd.DataFrame(recap)
if not df_recap.empty:
    st.dataframe(df_recap)
else:
    st.info("Aucune donnée pour cette date.")
