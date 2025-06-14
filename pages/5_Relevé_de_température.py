import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from supabase import create_client, Client
import json
import os

COOKIE_FILE = ".user_cookie.json"

# Fonctions de gestion du nom utilisateur en cookie

def save_user_name(name):
    with open(COOKIE_FILE, "w") as f:
        json.dump({"name": name}, f)


def load_user_name():
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r") as f:
            return json.load(f).get("name")
    return None

# Titre de l'app
st.title("📋 Relevé de température")

# Authentification / Nom utilisateur
user_name = load_user_name()
if not user_name:
    user_name = st.text_input("Entrez votre nom", key="username")
    if st.button("Valider"):
        if user_name:
            save_user_name(user_name)
            st.success(f"Bienvenue {user_name} !")
            #st.experimental_rerun()
else:
    st.markdown(f"👤 Connecté en tant que **{user_name}**")

# Connexion à Supabase via secrets
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Sélection de la date du relevé (par défaut aujourd'hui)
selected_date = st.date_input("📅 Date du relevé", value=date.today())

# Récupération des chambres actives en emplacement 'boutique'
response = supabase.table("chambres").select("*") \
    .eq("actif", True).eq("emplacement", "boutique").execute()
chambres = response.data
chambres_df = pd.DataFrame(chambres)

# IDs des chambres
chambre_ids = chambres_df["id"].tolist()

# Récupération des relevés pour la date sélectionnée
response2 = supabase.table("releves_temperature") \
    .select("*") \
    .eq("date", str(selected_date)) \
    .in_("chambre_id", chambre_ids) \
    .execute()
releves = response2.data
releves_df = pd.DataFrame(releves)

# Construction de releves_recents sans erreur si pas de created_at
if not releves_df.empty and "created_at" in releves_df.columns:
    releves_recents = (
        releves_df.sort_values("created_at", ascending=False)
        .drop_duplicates(subset=["chambre_id", "moment_journee"], keep="first")
    )
else:
    releves_recents = pd.DataFrame(columns=["chambre_id", "moment_journee", "temperature"])

# Interface de saisie des relevés
st.subheader("🌡️ Tableau des relevés")
inputs = {}
for _, chambre in chambres_df.iterrows():
    chambre_id = chambre["id"]
    nom = chambre["nom"]
    type_chambre = chambre.get("type", "")

    # Extraction des températures existantes s'il y en a
    temp_matin = releves_recents.query(
        "chambre_id == @chambre_id and moment_journee == 'matin'"
    )[
        "temperature"
    ]
    temp_soir = releves_recents.query(
        "chambre_id == @chambre_id and moment_journee == 'soir'"
    )[
        "temperature"
    ]

    # Définir valeur par défaut si aucun relevé
    default_matin = float(temp_matin.iloc[0]) if not temp_matin.empty else 0.0
    default_soir = float(temp_soir.iloc[0]) if not temp_soir.empty else 0.0

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"{nom}")
    with col2:
        key_m = f"{chambre_id}_matin"
        inputs[key_m] = st.number_input(
            label="",
            value=default_matin,
            format="%.1f",
            key=key_m,
            step=0.1,
            label_visibility="collapsed",
        )
    with col3:
        key_s = f"{chambre_id}_soir"
        inputs[key_s] = st.number_input(
            label="",
            value=default_soir,
            format="%.1f",
            key=key_s,
            step=0.1,
            label_visibility="collapsed",
        )

# Bouton d'enregistrement des relevés
if st.button("💾 Enregistrer"):
    nb_insert = 0
    for _, chambre in chambres_df.iterrows():
        chambre_id = chambre["id"]
        nom = chambre["nom"]
        type_chambre = chambre.get("type", "")
        for moment in ["matin", "soir"]:
            key = f"{chambre_id}_{moment}"
            val = inputs.get(key)
            if val is None:
                continue
            if float(val) == 0.0:
                continue
            # Vérification seuils selon type
            if type_chambre == "positif" and (val > 6 or val < 0):
                st.warning(
                    f"⚠️ Mesure anormale pour {nom} ({moment}): {val}°C. "
                    "Merci de refaire une mesure dans 30 minutes."
                )
            elif type_chambre == "negatif" and (val > -16 or val < -22):
                st.warning(
                    f"⚠️ Mesure anormale pour {nom} ({moment}): {val}°C. "
                    "Merci de refaire une mesure dans 30 minutes."
                )
            existing = releves_recents.query(
                "chambre_id == @chambre_id and moment_journee == @moment"
            )

            if existing.empty or float(existing.iloc[0]["temperature"]) != float(val):
                item = {
                    "date": str(selected_date),
                    "moment_journee": moment,
                    "temperature": float(val),
                    "utilisateur": user_name,
                    "commentaire": "",
                }
                supabase.table("releves_temperature").insert(item).execute()
                nb_insert += 1
    if nb_insert > 0:
        st.success(f"✅ {nb_insert} relevés enregistrés.")
    else:
        st.info("Aucun relevé nouveau ou modifié à enregistrer.")

# Tableau historique 7 derniers jours
st.subheader("📊 Historique des 7 derniers jours")
# Préparer les dates et colonnes
jours = [selected_date - timedelta(days=i) for i in range(7)]
cols = ["Chambre"] + [f"{j.strftime('%d/%m')} {moment}" for j in jours for moment in ("soir", "matin")]

# Récupérer tous les relevés des 7 jours
dates_str = [str(j) for j in jours]
resp_hist = supabase.table("releves_temperature") \
    .select("*") \
    .in_("chambre_id", chambre_ids) \
    .in_("date", dates_str) \
    .execute()
hist_df = pd.DataFrame(resp_hist.data)

# Si created_at existe, prendre le plus récent par chambre/date/moment
if not hist_df.empty and "created_at" in hist_df.columns:
    hist_df = (
        hist_df.sort_values("created_at", ascending=False)
        .drop_duplicates(subset=["chambre_id", "date", "moment_journee"], keep="first")
    )

# Construire les lignes
data = []
for _, chambre in chambres_df.iterrows():
    row = {"Chambre": chambre["nom"]}
    for j in jours:
        for moment in ("soir", "matin"):
            filtre = hist_df.query(
                "chambre_id == @chambre_id and date == @d_str and moment_journee == @moment",
                local_dict={
                    "chambre_id": chambre["id"],
                    "d_str": str(j),
                    "moment": moment,
                },
            )
            if not filtre.empty:
                row[f"{j.strftime('%d/%m')} {moment}"] = filtre.iloc[0]["temperature"]
            else:
                row[f"{j.strftime('%d/%m')} {moment}"] = ""
    data.append(row)

hist_table = pd.DataFrame(data, columns=cols)
st.dataframe(hist_table)
