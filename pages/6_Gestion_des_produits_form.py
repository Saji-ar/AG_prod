import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Connexion Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("📦 Gestion des Produits (Formulaire)")

@st.cache_data(ttl=30)
def charger_produits():
    data = supabase.table("produits").select("*").execute().data
    return pd.DataFrame(data)

def parse_bool_list(s, n):
    if not s:
        return [True] * n if n > 0 else [True]
    vals = []
    for part in s.split(','):
        val = part.strip().lower()
        vals.append(val in ["true", "1", "vrai", "oui"])
    if len(vals) != n:
        vals = [True] * n if n > 0 else [True]
    return vals

def main():
    df = charger_produits()
    options = ["Nouveau produit"] + sorted(df["nom"].tolist())
    choix = st.selectbox("Choisir un produit", options)

    if choix != "Nouveau produit":
        produit_data = df[df["nom"] == choix].iloc[0].to_dict()
    else:
        produit_data = {}

    with st.form("produit_form"):
        nom = st.text_input("Nom", value=produit_data.get("nom", ""))
        sous_cat_str = ", ".join(produit_data.get("sous_categories", []))
        sous_cat = st.text_input("Sous-catégories (séparées par des virgules)", value=sous_cat_str)
        dispo_str = ", ".join(str(x) for x in produit_data.get("dispo", []))
        dispo = st.text_input("Disponibilité (True/False séparés par des virgules)", value=dispo_str)
        prix = st.number_input("Prix", value=float(produit_data.get("Prix") or 0), step=0.01)
        description = st.text_area("Description", value=produit_data.get("Description", ""))
        allergenes = st.text_input("Allergènes", value=produit_data.get("Allergène", ""))
        permanent = st.checkbox("Permanent", value=bool(produit_data.get("permanent", False)))
        submitted = st.form_submit_button("Enregistrer")

    if submitted:
        sous_list = [x.strip() for x in sous_cat.split(',') if x.strip()]
        dispo_list = parse_bool_list(dispo, len(sous_list))
        prod = {
            "nom": nom,
            "sous_categories": sous_list,
            "dispo": dispo_list,
            "Prix": prix,
            "Description": description,
            "Allergène": allergenes,
            "permanent": permanent,
        }
        if choix == "Nouveau produit":
            supabase.table("produits").insert(prod).execute()
            st.success("✅ Produit ajouté")
        else:
            supabase.table("produits").update(prod).eq("nom", choix).execute()
            st.success("✅ Produit mis à jour")
        st.cache_data.clear()

if __name__ == "__main__":
    main()
