import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("🧾 Suivi journalier : Stock & Production modifiables")

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

# Chargement des données une seule fois
@st.cache_data(show_spinner="Chargement des données...", ttl=300)
def charger_donnees_initiales():
    produits_df = pd.DataFrame(produits_ws.get_all_records())
    prod_df = pd.DataFrame(prod_ws.get_all_records())
    stock_df = pd.DataFrame(stock_ws.get_all_records())
    for df, col in [(prod_df, "Date"), (stock_df, "Date")]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return produits_df, prod_df, stock_df

produits_df, prod_df, stock_df = charger_donnees_initiales()

# Date sélectionnée
date_cible = st.date_input("📅 Choisir une date", value=datetime.today().date())
date_limite = datetime.today().date() - timedelta(days=7)

# Liste des produits : catalogue + autres récents
produits_ref = []
for _, row in produits_df.iterrows():
    nom = row["Nom"]
    sous_cats = [s.strip() for s in str(row.get("Sous-catégories", "")).split(",")] if row.get("Sous-catégories") else [""]
    for sc in sous_cats:
        produits_ref.append(f"{nom} / {sc}" if sc else nom)

produits_7j = set()
for df in [prod_df, stock_df]:
    recent = df[df["Date"] >= date_limite]
    produits_7j.update(recent["Produit"].dropna().unique().tolist())
autres = list(produits_7j - set(produits_ref))

liste_produits = sorted(set(produits_ref + autres))

# Données pour la date choisie
donnees_initiales = []
for nom in liste_produits:
    stock_val = stock_df[(stock_df["Produit"] == nom) & (stock_df["Date"] == date_cible)]["Quantité"].sum()
    prod_val = prod_df[(prod_df["Produit"] == nom) & (prod_df["Date"] == date_cible)]["Quantité"].sum()
    donnees_initiales.append({
        "Produit": nom,
        "Stock": int(stock_val),
        "Production": int(prod_val)
    })

st.subheader("📝 Modifier les valeurs pour la journée")

df_edit = pd.DataFrame(donnees_initiales)
if "editable" not in st.session_state:
    st.session_state["editable"] = df_edit.copy()

with st.form("form_stock_prod"):
    df_modif = st.data_editor(
        st.session_state["editable"],
        use_container_width=True,
        num_rows="dynamic",
        key="editable"
    )
    submitted = st.form_submit_button("💾 Enregistrer les modifications")

# Enregistrement des modifications
if submitted:
    lignes_stock = []
    lignes_prod = []

    for i, row in df_modif.iterrows():
        nom = str(row["Produit"]).strip()
        stock_new = int(row["Stock"])
        prod_new = int(row["Production"])

        # Ajout de (Autre) si non référencé
        if nom not in produits_ref and not nom.endswith("(Autre)"):
            nom += " (Autre)"

        old = next((r for r in donnees_initiales if r["Produit"] == row["Produit"]), {"Stock": 0, "Production": 0})
        diff_stock = stock_new - int(old["Stock"])
        diff_prod = prod_new - int(old["Production"])

        if diff_stock != 0:
            lignes_stock.append([nom, diff_stock, str(date_cible)])
        if diff_prod != 0:
            lignes_prod.append([nom, diff_prod, str(date_cible)])

    # Envoi dans Google Sheets
    for ligne in lignes_stock:
        stock_ws.append_row([str(ligne[0]), int(ligne[1]), str(ligne[2])])
    for ligne in lignes_prod:
        prod_ws.append_row([str(ligne[0]), int(ligne[1]), str(ligne[2])])

    st.success("✅ Modifications enregistrées dans les feuilles.")
    st.cache_data.clear()  # Invalider le cache pour les prochaines utilisations
