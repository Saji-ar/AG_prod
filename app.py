import streamlit as st

st.set_page_config(page_title="Gestion de Pâtisserie", layout="wide")

st.title("Bienvenue sur le tableau de bord de gestion")
st.markdown("Utilisez le menu à gauche pour naviguer entre les pages :")
st.markdown("- **🧾 Stock & Production** : suivre et ajuster la production quotidienne.")
st.markdown("- **🗑️ Retrait** : enregistrer les produits retirés de la vente.")
st.markdown("- **📦 Gestion des Produits** : mettre à jour les fiches produit.")
st.markdown("- **📆 Bilan par date** : consulter le récapitulatif d'une journée.")
st.markdown("- **📋 Relevé de température** : suivre les relevés des chambres froides.")
