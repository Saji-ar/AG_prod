import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Connexion Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("📦 Gestion des Produits")

@st.cache_data(ttl=30)
def charger_produits():
    data = supabase.table("produits").select("*").execute().data
    return pd.DataFrame(data)

df = charger_produits()

# Nettoyage des listes et fallback par défaut
df["sous_categories"] = df["sous_categories"].apply(lambda x: x if isinstance(x, list) else [])
df["dispo"] = [
    x if isinstance(x, list) else [True] * max(1, len(sous_cat if isinstance(sous_cat, list) else []))
    for x, sous_cat in zip(df["dispo"], df["sous_categories"])
]

# Colonnes supplémentaires à afficher si elles existent
colonnes_supp = ["prix", "description", "allergenes", "permanent"]
for col in colonnes_supp:
    if col not in df.columns:
        df[col] = ""
df = df.sort_values("nom")


# Préparation du DataFrame modifiable
editable_df = df[["nom", "sous_categories", "dispo", "prix", "description", "allergenes", "permanent"]].copy()
editable_df.rename(columns={
    "nom": "Nom",
    "sous_categories": "Sous-catégories",
    "dispo": "Disponibilité",
    "prix": "Prix",
    "description": "Description",
    "allergenes": "Allergènes",
    "permanent": "Permanent"
}, inplace=True)

st.subheader("📝 Modifier les produits existants ou en ajouter")

edited_df = st.data_editor(
    editable_df,
    use_container_width=True,
    num_rows="dynamic",
    key="produits_editor",
    column_config={
        "Sous-catégories": st.column_config.ListColumn("Sous-catégories"),
        "Disponibilité": st.column_config.ListColumn("Disponibilité", help="Liste de booléens"),
        "Permanent": st.column_config.CheckboxColumn("Permanent", default=False),
        "Prix": st.column_config.NumberColumn("Prix", step=0.01),
        "Description": st.column_config.TextColumn("Description"),
        "Allergènes": st.column_config.TextColumn("Allergènes")
    }
)

if st.button("💾 Enregistrer"):
    for _, row in edited_df.iterrows():
        nom = row.get("Nom")
        if not nom:
            continue

        # Nettoyage des listes
        sous_cat = row.get("Sous-catégories", [])
        dispo = row.get("Disponibilité", [])
        sous_cat = sous_cat if isinstance(sous_cat, list) else []
        dispo = dispo if isinstance(dispo, list) else [True] * max(1, len(sous_cat))
        if len(dispo) != len(sous_cat):
            dispo = [True] * len(sous_cat) if sous_cat else [True]

        produit = {
            "nom": nom,
            "sous_categories": sous_cat,
            "dispo": dispo,
            "prix": row.get("Prix"),
            "description": row.get("Description", ""),
            "allergenes": row.get("Allergènes", ""),
            "permanent": bool(row.get("Permanent"))
        }

        # Vérifier si le produit existe déjà
        ancien = df[df["nom"] == nom]
        if ancien.empty:
            supabase.table("produits").insert(produit).execute()
        else:
            ancien_row = ancien.iloc[0]
            if (
                ancien_row.get("sous_categories") != sous_cat or
                ancien_row.get("dispo") != dispo or
                ancien_row.get("prix") != row.get("Prix") or
                ancien_row.get("description", "") != row.get("Description", "") or
                ancien_row.get("allergenes", "") != row.get("Allergènes", "") or
                ancien_row.get("permanent", False) != bool(row.get("Permanent"))
            ):
                supabase.table("produits").update(produit).eq("nom", nom).execute()

    st.success("✅ Produits mis à jour avec succès.")
    st.cache_data.clear()
