import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client

st.title("🗑️ Retrait des produits")

# Connexion Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Choix du jour de référence et du seuil
st.sidebar.header("Paramètres de retrait")
date_reference = st.sidebar.date_input("🗕️ Date de référence", value=datetime.today().date())
seuil_jours = st.sidebar.number_input("⏱️ Jours avant retrait", value=3, min_value=1, max_value=30)
today = date_reference  # déjà défini avec st.date_input
seuil_date = today - timedelta(days=seuil_jours)
date_7j = today - timedelta(days=7)

# Chargement des données Supabase
prod_resp = supabase.table("Prod")\
    .select("*")\
    .gte("date", str(date_7j))\
    .execute()
prod_df = pd.DataFrame(prod_resp.data)

# Requête optimisée pour Stock : uniquement la date du jour sélectionné
stock_resp = supabase.table("Stock")\
    .select("*")\
    .eq("date", str(today))\
    .execute()
stock_df = pd.DataFrame(stock_resp.data)

# Requête optimisée pour Retrait : uniquement les lignes où "date_de_production" est dans les jours récents
retrait_resp = supabase.table("Retrait")\
    .select("*")\
    .gte("date_de_retrait", str(seuil_date))\
    .execute()
retrait_df = pd.DataFrame(retrait_resp.data)

# Format des dates
stock_df["date"] = pd.to_datetime(stock_df["date"], errors="coerce")
prod_df["date"] = pd.to_datetime(prod_df["date"], errors="coerce")
retrait_df["date_de_production"] = pd.to_datetime(retrait_df.get("date_de_production", pd.NaT), errors="coerce")
retrait_df["date_de_retrait"] = pd.to_datetime(retrait_df.get("date_de_retrait", pd.NaT), errors="coerce")

# Périodes utiles
periode_recente = [today - timedelta(days=i) for i in range(1, seuil_jours)]
periode_7j = [today - timedelta(days=i) for i in range(1, 8)]

# === PARTIE 1 : RETRAITS AUTOMATIQUES ===
st.subheader(f"🔎 Retraits automatiques des produits anciens (> {seuil_jours} jours)")

stock_today = stock_df[stock_df["date"].dt.date == today]

stock_grouped = stock_today.groupby("produit")["quantite"].sum()



retrait_recents = retrait_df[
    retrait_df["date_de_production"].notna() & 
    retrait_df["date_de_production"].apply(lambda x: isinstance(x, datetime)) & 
    retrait_df["date_de_production"].dt.date.isin(periode_recente)
].groupby("produit")["quantite"].sum().abs()

retrait_today = retrait_df[
    retrait_df["date_de_retrait"].dt.date == today
].groupby("produit")["quantite"].sum().abs()




for produit, quantite_stock in stock_grouped.items():
    quantite_produite = prod_df[
        (prod_df["produit"] == produit) &
        (prod_df["date"].dt.date.isin(periode_recente))
    ]["quantite"].sum()

    quantite_produite += retrait_recents.get(produit, 0)  + retrait_today.get(produit, 0)
    surplus = quantite_stock - quantite_produite

    if surplus <= 0:
        continue

    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"🔻 **{produit}** – À retirer : `{int(surplus)}` unités (anciens)")
        with col2:
            if st.button("✅ Valider retrait", key=f"{produit}_{surplus}"):
                supabase.table("Retrait").insert({
                    "produit": produit,
                    "quantite": int(surplus),
                    "date_de_retrait": str(today),
                    "date_de_production": None,
                    "raison": f"Ancien > {seuil_jours} jours"
                }).execute()
                st.success(f"Retrait validé pour {int(surplus)} {produit}")

# === PARTIE 2 : RETRAIT MANUEL ===
st.subheader("✋ Retrait manuel d’un produit")

produits_7j = prod_df[prod_df["date"].dt.date.isin(periode_7j)]["produit"].dropna().unique().tolist()
produits_7j.append("Autre")
produit_sel = st.selectbox("Produit à retirer", produits_7j)

if produit_sel == "Autre":
    produit_sel = st.text_input("Nom du produit (personnalisé)")

quantite_retrait = st.number_input("Quantité à retirer", min_value=1, step=1)
date_prod = st.date_input("Date de production", max_value=today)
raison = st.text_input("Raison du retrait")
date_retrait = st.date_input("Date du retrait", value=today)

if st.button("📤 Enregistrer le retrait manuel"):
    supabase.table("Retrait").insert({
        "produit": produit_sel,
        "quantite": int(quantite_retrait),
        "date_de_retrait": str(date_retrait),
        "date_de_production": str(date_prod),
        "raison": raison
    }).execute()
    st.success(f"{quantite_retrait} {produit_sel} retiré manuellement ✔️")
