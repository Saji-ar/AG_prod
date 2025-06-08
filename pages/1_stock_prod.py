import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import numpy as np

# Connexion Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("🧾 Suivi journalier : Stock & Production modifiables")

@st.cache_data(show_spinner="Chargement des données...", ttl=10)
def charger_donnees_initiales():
    produits = supabase.table("produits").select("*").execute().data
    prod = supabase.table("Prod").select("*").execute().data
    stock = supabase.table("Stock").select("*").execute().data

    produits_df = pd.DataFrame(produits)
    prod_df = pd.DataFrame(prod)
    stock_df = pd.DataFrame(stock)

    for df, col in [(prod_df, "date"), (stock_df, "date")]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    return produits_df, prod_df, stock_df

produits_df, prod_df, stock_df = charger_donnees_initiales()

date_cible = st.date_input("📅 Choisir une date", value=datetime.today().date())
date_limite = datetime.today().date() - timedelta(days=7)

# Générer les lignes produit/sous-catégorie
rows = []
for _, row in produits_df.iterrows():
    nom_produit = row["nom"]
    sous_cats = row.get("sous_categories") or [""]
    if isinstance(sous_cats, str):
        sous_cats = [sous_cats]  # fallback si erreur
    for sc in sous_cats:
        nom = f"{nom_produit} / {sc}" if sc else nom_produit
        stock_val = stock_df[
            (stock_df["produit"] == nom_produit) &
            (stock_df["sous_categorie"] == sc) &
            (stock_df["date"] == date_cible)
        ]["quantite"].sum()
        prod_val = prod_df[
            (prod_df["produit"] == nom_produit) &
            (prod_df["sous_categorie"] == sc) &
            (prod_df["date"] == date_cible)
        ]["quantite"].sum()

        rows.append({
            "Produit": nom_produit,
            "sous_categorie": sc,
            "Nom": nom,
            "Stock": int(stock_val),
            "Production": int(prod_val)
        })

df_final = pd.DataFrame(rows)
df_final = df_final.sort_values("Nom")


st.subheader("📝 Modifier les valeurs pour la journée")

if "df_modif" not in st.session_state or st.session_state.get("last_date") != date_cible:
    st.session_state.df_modif = df_final[["Nom", "Stock", "Production"]].copy()
    st.session_state.last_date = date_cible


# Éditeur de données
df_modif = st.data_editor(
    st.session_state.df_modif.reset_index(drop=True),
    use_container_width=True,
    num_rows="dyamic",
    key="editable",
    hide_index=True
)


if st.button("💾 Enregistrer les modifications"):
    lignes_stock = []
    lignes_prod = []

    for i, row in df_modif.iterrows():
        ligne_orig = df_final[df_final["Nom"] == row["Nom"]].iloc[0]
        produit = ligne_orig["Produit"]
        sous_categorie = ligne_orig["sous_categorie"]
        stock_new = int(row["Stock"]) if pd.notna(row["Stock"]) else 0
        prod_new = int(row["Production"]) if pd.notna(row["Production"]) else 0

        if stock_new == 0 and prod_new == 0:
            continue

        old_stock = ligne_orig["Stock"]
        old_prod = ligne_orig["Production"]
        diff_stock = stock_new - old_stock
        diff_prod = prod_new - old_prod

        if diff_stock != 0:
            lignes_stock.append({
                "produit": produit,
                "sous_categorie": sous_categorie,
                "quantite": diff_stock,
                "date": str(date_cible)
            })
        if diff_prod != 0:
            lignes_prod.append({
                "produit": produit,
                "sous_categorie": sous_categorie,
                "quantite": diff_prod,
                "date": str(date_cible)
            })

    for ligne in lignes_stock:
        ligne = {
            k: int(v) if isinstance(v, np.integer) else v
            for k, v in ligne.items()
        }        
        supabase.table("Stock").insert(ligne).execute()

    for ligne in lignes_prod:
        ligne = {
            k: int(v) if isinstance(v, np.integer) else v
            for k, v in ligne.items()
        }       
        supabase.table("Prod").insert(ligne).execute()

    st.success("✅ Modifications enregistrées dans Supabase.")
    st.cache_data.clear()
    st.session_state.df_modif = df_final[["Nom", "Stock", "Production"]].copy()
