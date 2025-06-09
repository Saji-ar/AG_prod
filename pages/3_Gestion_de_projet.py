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
# Chaque liste de sous-catégories est convertie en chaîne pour faciliter l'édition
# Listes par défaut
df["sous_categories"] = df["sous_categories"].apply(lambda x: x if isinstance(x, list) else [])
if "dispo" not in df.columns:
    df["dispo"] = [[] for _ in range(len(df))]
df["dispo"] = [
    x if isinstance(x, list) else [True] * max(1, len(sous_cat if isinstance(sous_cat, list) else []))
    for x, sous_cat in zip(df["dispo"], df["sous_categories"])
]

# Conversion des sous-catégories en texte pour une édition plus simple
df["sous_cats_str"] = df["sous_categories"].apply(lambda lst: ", ".join(lst))

# Colonnes supplémentaires à afficher si elles existent
colonnes_supp = ["prix", "description", "Allergène", "permanent"]
for col in colonnes_supp:
    if col not in df.columns:
        df[col] = ""
df = df.sort_values("nom")


# Préparation du DataFrame modifiable
editable_df = df[["nom", "sous_cats_str", "dispo", "prix", "description", "Allergène", "permanent"]].copy()
editable_df.rename(columns={
    "nom": "Nom",
    "sous_cats_str": "Sous-catégories",
    "dispo": "Disponibilité",
    "prix": "Prix",
    "description": "Description",
    "Allergène": "Allergène",
    "permanent": "Permanent"
}, inplace=True)

st.subheader("📝 Modifier les produits existants ou en ajouter")

edited_df = st.data_editor(
    editable_df,
    use_container_width=True,
    num_rows="dynamic",
    key="produits_editor",
    column_config={
        "Sous-catégories": st.column_config.TextColumn("Sous-catégories (séparées par des virgules)"),
        "Disponibilité": st.column_config.ListColumn("Disponibilité", help="Liste de booléens"),
        "Permanent": st.column_config.CheckboxColumn("Permanent", default=False),
        "Prix": st.column_config.NumberColumn("Prix", step=0.01),
        "Description": st.column_config.TextColumn("Description"),
        "Allergène": st.column_config.TextColumn("Allergène")
    }
)

if st.button("💾 Enregistrer"):
    for _, row in edited_df.iterrows():
        nom = row.get("Nom")
        if not nom:
            continue

        # Nettoyage des listes
        sous_cat_str = str(row.get("Sous-catégories", ""))
        sous_cat = [sc.strip() for sc in sous_cat_str.split(",") if sc.strip()]
        dispo = row.get("Disponibilité", [])
        dispo = dispo if isinstance(dispo, list) else [True] * max(1, len(sous_cat))
        if len(dispo) != len(sous_cat):
            dispo = [True] * len(sous_cat) if sous_cat else [True]

        produit = {
            "nom": nom,
            "sous_categories": sous_cat,
            "dispo": dispo,
            "prix": row.get("Prix"),
            "description": row.get("Description", ""),
            "Allergène": row.get("Allergène", ""),
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
                ancien_row.get("Allergène", "") != row.get("Allergène", "") or
                ancien_row.get("permanent", False) != bool(row.get("Permanent"))
            ):
                supabase.table("produits").update(produit).eq("nom", nom).execute()

    st.success("✅ Produits mis à jour avec succès.")
    st.cache_data.clear()
