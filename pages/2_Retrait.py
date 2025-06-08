import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client

st.title("🗑️ Retrait des produits")

# Connexion Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Paramètres
st.sidebar.header("Paramètres de retrait")
date_reference = st.sidebar.date_input("📅 Date de référence", value=datetime.today().date())
seuil_jours = st.sidebar.number_input("⏱️ Jours avant retrait", value=3, min_value=1, max_value=30)
today = date_reference
seuil_date = today - timedelta(days=seuil_jours)
date_7j = today - timedelta(days=7)

# Données Supabase
prod_df = pd.DataFrame(supabase.table("Prod").select("*").gte("date", str(date_7j)).execute().data)
stock_df = pd.DataFrame(supabase.table("Stock").select("*").eq("date", str(today)).execute().data)
retrait_df = pd.DataFrame(supabase.table("Retrait").select("*").gte("date_de_retrait", str(seuil_date)).execute().data)

# Format dates
for df, col in [(prod_df, "date"), (stock_df, "date"), (retrait_df, "date_de_retrait"), (retrait_df, "date_de_production")]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

# Périodes utiles
periode_recente = [today - timedelta(days=i) for i in range(1, seuil_jours)]
periode_7j = [today - timedelta(days=i) for i in range(1, 8)]

# === PARTIE 1 : RETRAITS AUTOMATIQUES ===
st.subheader(f"🔎 Retraits automatiques des produits anciens (> {seuil_jours} jours)")

stock_grouped = stock_df.groupby(["produit", "sous_categorie"])["quantite"].sum()
retrait_recents = retrait_df[
    retrait_df["date_de_production"].notna() &
    retrait_df["date_de_production"].dt.date.isin(periode_recente)
].groupby(["produit", "sous_categorie"])["quantite"].sum().abs()

retrait_today = retrait_df[
    retrait_df["date_de_retrait"].dt.date == today
].groupby(["produit", "sous_categorie"])["quantite"].sum().abs()

for (produit, sc), quantite_stock in stock_grouped.items():
    quantite_produite = prod_df[
        (prod_df["produit"] == produit) &
        (prod_df["sous_categorie"] == sc) &
        (prod_df["date"].dt.date.isin(periode_recente))
    ]["quantite"].sum()

    quantite_produite += retrait_recents.get((produit, sc), 0) + retrait_today.get((produit, sc), 0)
    surplus = quantite_stock - quantite_produite

    if surplus <= 0:
        continue

    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            label = f"🔻 **{produit} / {sc}** – À retirer : `{int(surplus)}` unités"
            st.markdown(label)
        with col2:
            if st.button("✅ Valider retrait", key=f"{produit}_{sc}_{surplus}"):
                supabase.table("Retrait").insert({
                    "produit": produit,
                    "sous_categorie": sc,
                    "quantite": int(surplus),
                    "date_de_retrait": str(today),
                    "date_de_production": None,
                    "raison": f"Ancien > {seuil_jours} jours"
                }).execute()
                st.success(f"Retrait validé pour {int(surplus)} {produit} / {sc}")

# === PARTIE 2 : RETRAIT MANUEL ===
st.subheader("✋ Retrait manuel d’un produit")

produits_7j = prod_df[prod_df["date"].dt.date.isin(periode_7j)]
disponibles = produits_7j[["produit", "sous_categorie"]].dropna().drop_duplicates()

options = [f"{row.produit} / {row.sous_categorie}" if row.sous_categorie else row.produit for row in disponibles.itertuples()]
options.append("Autre")

choix = st.selectbox("Produit à retirer", options)

if choix == "Autre":
    produit_sel = st.text_input("Nom du produit")
    sous_categorie = st.text_input("Sous-catégorie (optionnelle)")
else:
    parts = choix.split(" / ")
    produit_sel = parts[0]
    sous_categorie = parts[1] if len(parts) > 1 else ""

quantite_retrait = st.number_input("Quantité à retirer", min_value=1, step=1)
date_prod = st.date_input("Date de production", max_value=today)
raison = st.text_input("Raison du retrait")
date_retrait = st.date_input("Date du retrait", value=today)

if st.button("📤 Enregistrer le retrait manuel"):
    supabase.table("Retrait").insert({
        "produit": produit_sel,
        "sous_categorie": sous_categorie,
        "quantite": int(quantite_retrait),
        "date_de_retrait": str(date_retrait),
        "date_de_production": str(date_prod),
        "raison": raison
    }).execute()
    st.success(f"{quantite_retrait} {produit_sel} / {sous_categorie} retiré manuellement ✔️")
