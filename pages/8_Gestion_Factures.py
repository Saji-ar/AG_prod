import streamlit as st

# Configuration de la page - DOIT être en premier
st.set_page_config(layout="wide", page_title="Gestion des Factures")

import pandas as pd
import logging
from datetime import datetime, timedelta
from utils.auth import require_auth, show_auth_status
from utils.get_data import (
    get_all_factures,
    get_factures_filtered,
    update_facture_paiement,
    soft_delete_facture,
    get_clients,
    download_facture_from_storage,
    check_facture_exists_in_storage
)

# Vérification de l'authentification
if not require_auth():
    st.stop()

# Afficher le statut d'authentification dans la sidebar
show_auth_status()

# Vider le cache au démarrage si nécessaire
if hasattr(st, 'cache_data'):
    st.cache_data.clear()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [GESTION_FACTURES] - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('gestion_factures.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

st.title("🧾 Gestion des Factures")

logger.info("ÉTAPE: Démarrage de la page Gestion des Factures")

# Section des filtres
st.header("🔍 Filtres")

col1, col2, col3, col4 = st.columns(4)

with col1:
    clients = get_clients()
    client_names = ["Tous"] + clients["nom"].tolist()
    selected_client = st.selectbox("Client", client_names)

with col2:
    date_debut = st.date_input("Date début", value=None, help="Laisser vide pour ignorer")

with col3:
    date_fin = st.date_input("Date fin", value=None, help="Laisser vide pour ignorer")

with col4:
    st.write("")
    apply_filters = st.button("Appliquer les filtres", type="primary")

# Récupération des données
logger.info("ÉTAPE: Récupération des factures")

if apply_filters or "factures_df" not in st.session_state:
    client_filter = None if selected_client == "Tous" else selected_client
    
    if client_filter or date_debut or date_fin:
        logger.info(f"Application filtres - Client: {client_filter}, Période: {date_debut} à {date_fin}")
        factures_df = get_factures_filtered(
            client_nom=client_filter,
            date_debut=date_debut,
            date_fin=date_fin
        )
    else:
        logger.info("Récupération de toutes les factures")
        factures_df = get_all_factures()
    
    st.session_state["factures_df"] = factures_df
else:
    factures_df = st.session_state["factures_df"]

# Affichage des résultats
st.header(f"📋 Factures ({len(factures_df)} résultats)")

if len(factures_df) == 0:
    st.info("Aucune facture trouvée avec ces critères.")
else:
    logger.info("ÉTAPE: Vérification de la disponibilité des fichiers PDF/Excel dans le storage")

    display_df = factures_df.copy()
    file_status = []

    for _, row in factures_df.iterrows():
        num_facture = row["num_facture"]

        # Vérifie la présence du PDF ou Excel
        pdf_exists = check_facture_exists_in_storage(f"facture_{num_facture}.pdf")
        excel_exists = check_facture_exists_in_storage(f"facture_{num_facture}.xlsx")

        if pdf_exists:
            file_status.append("📄 PDF disponible")
        elif excel_exists:
            file_status.append("📊 Excel disponible")
        else:
            file_status.append("❌ Aucun fichier")

    display_df["fichier_disponible"] = file_status

    # Configuration des colonnes pour l'affichage
    column_config = {
        "num_facture": st.column_config.NumberColumn("N° Facture", format="%d"),
        "date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
        "client_nom": st.column_config.TextColumn("Client"),
        "date_prestation": st.column_config.DateColumn("Date Prestation", format="DD/MM/YYYY"),
        "tot_ht": st.column_config.NumberColumn("Total HT", format="%.2f €"),
        "tot_ttc": st.column_config.NumberColumn("Total TTC", format="%.2f €"),
        "paye": st.column_config.CheckboxColumn("Payé"),
        "fichier_disponible": st.column_config.TextColumn("📎 Fichier disponible")
    }

    edited_df = st.data_editor(
        display_df,
        column_config=column_config,
        disabled=["num_facture", "date", "client_nom", "date_prestation", "tot_ht", "tot_ttc", "fichier_disponible"],
        hide_index=True,
        use_container_width=True,  # ✅ garde ton paramètre d'origine
        key="factures_editor"
    )

    # Gestion du statut payé
    if "factures_editor" in st.session_state:
        editor_state = st.session_state["factures_editor"]
        for index, updates in editor_state.get("edited_rows", {}).items():
            if "paye" in updates:
                num_facture = display_df.iloc[index]["num_facture"]
                new_status = updates["paye"]
                logger.info(f"Mise à jour paiement facture {num_facture}: {new_status}")
                result = update_facture_paiement(num_facture, new_status)
                if result["success"]:
                    st.success(f"✅ Facture {num_facture} mise à jour.")
                else:
                    st.error(f"❌ Erreur : {result['error']}")

# Section des actions
st.header("⚡ Actions")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📥 Télécharger une facture")

    if len(factures_df) > 0:
        facture_options = [f"Facture {row['num_facture']} - {row['client_nom']}" for _, row in factures_df.iterrows()]
        selected_facture_download = st.selectbox("Sélectionner une facture", facture_options, key="download_select")

        selected_index = facture_options.index(selected_facture_download)
        selected_row = factures_df.iloc[selected_index]
        num_facture = selected_row["num_facture"]

        pdf_file = f"facture_{num_facture}.pdf"
        excel_file = f"facture_{num_facture}.xlsx"

        pdf_exists = check_facture_exists_in_storage(pdf_file)
        excel_exists = check_facture_exists_in_storage(excel_file)

        if pdf_exists:
            st.success(f"✅ PDF disponible pour la facture {num_facture}")
            if st.button("Télécharger PDF", key="download_pdf_btn"):
                logger.info(f"Téléchargement PDF {pdf_file}")
                download_result = download_facture_from_storage(pdf_file)
                if download_result["success"]:
                    st.download_button(
                        label=f"📄 Télécharger Facture {num_facture}",
                        data=download_result["data"],
                        file_name=download_result["filename"],
                        mime="application/pdf",
                        key="dl_pdf_btn"
                    )
                else:
                    st.error(f"❌ Erreur : {download_result['error']}")

        elif excel_exists:
            st.warning(f"⚠️ PDF non trouvé, mais Excel disponible.")
            if st.button("Télécharger Excel", key="download_excel_btn"):
                logger.info(f"Téléchargement Excel {excel_file}")
                download_result = download_facture_from_storage(excel_file)
                if download_result["success"]:
                    st.download_button(
                        label=f"📊 Télécharger Excel Facture {num_facture}",
                        data=download_result["data"],
                        file_name=download_result["filename"],
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_excel_btn"
                    )
                else:
                    st.error(f"❌ Erreur : {download_result['error']}")
        else:
            st.error(f"❌ Aucun fichier trouvé pour la facture {num_facture}")

with col2:
    st.subheader("🗑️ Supprimer une facture")
    if len(factures_df) > 0:
        facture_options_delete = [f"Facture {row['num_facture']} - {row['client_nom']}" for _, row in factures_df.iterrows()]
        selected_facture_delete = st.selectbox("Sélectionner une facture", facture_options_delete, key="delete_select")
        confirm_delete = st.checkbox("Je confirme vouloir supprimer cette facture", key="confirm_delete")

        if st.button("Supprimer", type="secondary", disabled=not confirm_delete, key="delete_btn"):
            selected_index = facture_options_delete.index(selected_facture_delete)
            selected_row = factures_df.iloc[selected_index]
            num_facture = selected_row["num_facture"]

            result = soft_delete_facture(num_facture)
            if result["success"]:
                st.success(f"✅ Facture {num_facture} supprimée avec succès")
                st.session_state["factures_df"] = get_all_factures()
                st.rerun()
            else:
                st.error(f"❌ Erreur : {result['error']}")

# Statistiques
if len(factures_df) > 0:
    st.header("📊 Statistiques")
    total_factures = len(factures_df)
    factures_payees = len(factures_df[factures_df["paye"] == True])
    factures_impayees = len(factures_df[factures_df["paye"] == False])
    total_ttc = factures_df["tot_ttc"].sum()
    total_paye = factures_df[factures_df["paye"] == True]["tot_ttc"].sum()
    reste_a_payer = factures_df[factures_df["paye"] == False]["tot_ttc"].sum()

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric("Total Factures", total_factures)
    with col2: st.metric("Factures Payées", factures_payees)
    with col3: st.metric("Factures Impayées", factures_impayees)
    with col4: st.metric("Total TTC", f"{total_ttc:.2f} €")
    with col5: st.metric("Reste à Payer", f"{reste_a_payer:.2f} €")

    if total_ttc > 0:
        pourcentage_paye = (total_paye / total_ttc) * 100
        pourcentage_impaye = (reste_a_payer / total_ttc) * 100
        st.subheader("📈 Répartition des paiements")
        col_left, col_right = st.columns(2)
        with col_left:
            st.success(f"💰 Montant payé : {total_paye:.2f} € ({pourcentage_paye:.1f}%)")
            st.error(f"⏳ Reste à payer : {reste_a_payer:.2f} € ({pourcentage_impaye:.1f}%)")
        with col_right:
            st.write("**Progression des paiements**")
            st.progress(total_paye / total_ttc)
            st.caption(f"{pourcentage_paye:.1f}% des factures sont payées")

logger.info("ÉTAPE: Page Gestion des Factures affichée")
