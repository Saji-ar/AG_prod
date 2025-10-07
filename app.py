import streamlit as st
from utils.auth import show_auth_status, is_authenticated
import os

# Crée le dossier "data" si nécessaire
os.makedirs("data", exist_ok=True)

st.set_page_config(page_title="Gestion de Pâtisserie", layout="wide")

# Afficher le statut d'authentification dans la sidebar
show_auth_status()

st.title("🏪 Bienvenue sur le tableau de bord de gestion")

st.markdown("## 📋 Navigation")
st.markdown("Utilisez le menu à gauche pour naviguer entre les pages :")


# Pages publiques
st.markdown("### 📂 Pages libres d'accès")
st.markdown("- **🧾 Stock & Production** : suivre et ajuster la production quotidienne")
st.markdown("- **🗑️ Retrait** : enregistrer les produits retirés de la vente")
st.markdown("- **📦 Gestion des Produits** : mettre à jour les fiches produit")
st.markdown("- **📆 Bilan par date** : consulter le récapitulatif d'une journée")
st.markdown("- **📋 Relevé de température** : suivre les relevés des chambres froides")

# Pages protégées
st.markdown("### 🔒 Pages protégées (authentification requise)")
if is_authenticated():
    st.markdown("- **💰 Facturation** : créer et gérer les factures clients")
    st.markdown("- **🧾 Gestion Factures** : consulter, modifier et télécharger les factures")
    st.markdown("- **👥 Gestion Clients** : ajouter et modifier les informations clients")
    st.success("✅ Vous êtes connecté - Accès complet disponible")
else:
    st.markdown("- **💰 Facturation** : 🔒 *Connexion requise*")
    st.markdown("- **🧾 Gestion Factures** : 🔒 *Connexion requise*")
    st.markdown("- **👥 Gestion Clients** : 🔒 *Connexion requise*")
    st.warning("⚠️ Connectez-vous pour accéder aux pages de gestion financière")

# Section d'information
st.markdown("## ℹ️ Informations")
st.info("""
**Gestion de Pâtisserie** - Version avec authentification

- 🔓 **Pages publiques** : Accès libre pour la gestion quotidienne
- 🔒 **Pages protégées** : Authentification requise pour les données financières et clients
- 🔐 **Sécurité** : Session automatique avec timeout configurable
""")

# Instructions de connexion si non connecté
if not is_authenticated():
    st.markdown("## 🔑 Comment se connecter ?")
    st.markdown("""
    1. Cliquez sur une page protégée (Facturation, Gestion Factures, ou Gestion Clients)
    2. Saisissez le mot de passe administrateur
    3. Profitez de l'accès complet à toutes les fonctionnalités
    
    *La session reste active pendant 1 heure d'inactivité.*
    """)