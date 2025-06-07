import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client

# Connexion Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("🧾 Suivi journalier : Stock & Production modifiables")


# Chargement des données une seule fois
@st.cache_data(show_spinner="Chargement des données...", ttl=10)
def charger_donnees_initiales():
    produits = supabase.table("produits").select("*").execute().data
    prod = supabase.table("Prod").select("*").execute().data
    stock = supabase.table("Stock").select("*").execute().data

    produits_df = pd.DataFrame(produits)
    prod_df = pd.DataFrame(prod)
    stock_df = pd.DataFrame(stock)

    print(produits_df)
    print(prod_df)
    print(stock_df)

    for df, col in [(prod_df, "date"), (stock_df, "date")]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    return produits_df, prod_df, stock_df

produits_df, prod_df, stock_df = charger_donnees_initiales()

# Date sélectionnée
date_cible = st.date_input("📅 Choisir une date", value=datetime.today().date())
date_limite = datetime.today().date() - timedelta(days=7)

# Liste des produits : catalogue + autres récents
produits_ref = []
for _, row in produits_df.iterrows():
    nom = row["nom"]
    sous_cats = [s.strip() for s in str(row.get("sous_categories", "")).split(",")] if row.get("sous_categories") else [""]
    for sc in sous_cats:
        produits_ref.append(f"{nom} / {sc}" if sc else nom)

produits_7j = set()
for df in [prod_df, stock_df]:
    recent = df[df["date"] >= date_limite]
    produits_7j.update(recent["produit"].dropna().unique().tolist())
autres = list(produits_7j - set(produits_ref))

liste_produits = sorted(set(produits_ref + autres))
st.write(stock_df.columns)

# Données pour la date choisie
donnees_initiales = []
for nom in liste_produits:
    stock_val = stock_df[(stock_df["produit"] == nom) & (stock_df["date"] == date_cible)]["quantite"].sum()
    prod_val = prod_df[(prod_df["produit"] == nom) & (prod_df["date"] == date_cible)]["quantite"].sum()
    donnees_initiales.append({
        "Produit": nom,
        "Stock": int(stock_val),
        "Production": int(prod_val)
    })

st.subheader("📝 Modifier les valeurs pour la journée")

# Initialiser les données en session si absentes
if "df_modif" not in st.session_state or st.session_state.get("last_date") != date_cible:
    st.session_state.df_modif = pd.DataFrame(donnees_initiales)
    st.session_state.last_date = date_cible

# Éditeur de données avec cache temporaire
df_modif = st.data_editor(
    st.session_state.df_modif,
    use_container_width=True,
    num_rows="dynamic",
    key="editable"
)

# Enregistrement des modifications
if st.button("💾 Enregistrer les modifications"):
    lignes_stock = []
    lignes_prod = []

    for i, row in df_modif.iterrows():
        nom = str(row["Produit"]).strip()
        stock_new = int(row["Stock"])
        prod_new = int(row["Production"])


        old = next((r for r in donnees_initiales if r["Produit"] == row["Produit"]), {"Stock": 0, "Production": 0})
        diff_stock = stock_new - int(old["Stock"])
        diff_prod = prod_new - int(old["Production"])

        if diff_stock != 0:
            lignes_stock.append({"produit": nom, "quantite": diff_stock, "date": str(date_cible)})
        if diff_prod != 0:
            lignes_prod.append({"produit": nom, "quantite": diff_prod, "date": str(date_cible)})

    # Envoi dans Supabase
    for ligne in lignes_stock:
        supabase.table("Stock").insert(ligne).execute()
    for ligne in lignes_prod:
        supabase.table("Prod").insert(ligne).execute()

    st.success("✅ Modifications enregistrées dans Supabase.")
    st.cache_data.clear()
    st.session_state.df_modif = df_modif.copy()