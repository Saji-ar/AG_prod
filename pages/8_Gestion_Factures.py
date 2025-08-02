import streamlit as st
import pandas as pd
import logging
from datetime import datetime, timedelta

# Vider le cache au démarrage si nécessaire
if hasattr(st, 'cache_data'):
    st.cache_data.clear()

from utils.get_data import get_all_factures, get_factures_filtered, update_facture_paiement, soft_delete_facture, get_clients, download_facture_from_storage, check_facture_exists_in_storage

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

st.set_page_config(layout="wide", page_title="Gestion des Factures")

st.title("🧾 Gestion des Factures")

logger.info("ÉTAPE: Démarrage de la page Gestion des Factures")

# Section des filtres
st.header("🔍 Filtres")

col1, col2, col3, col4 = st.columns(4)

with col1:
    # Filtre par client
    clients = get_clients()
    client_names = ["Tous"] + clients["nom"].tolist()
    selected_client = st.selectbox("Client", client_names)

with col2:
    # Filtre par période - Date début
    date_debut = st.date_input(
        "Date début",
        value=None,
        help="Laisser vide pour ignorer"
    )

with col3:
    # Filtre par période - Date fin
    date_fin = st.date_input(
        "Date fin",
        value=None,
        help="Laisser vide pour ignorer"
    )

with col4:
    # Bouton pour appliquer les filtres
    st.write("")  # Espace pour aligner avec les autres champs
    apply_filters = st.button("Appliquer les filtres", type="primary")

# Récupération des données
logger.info("ÉTAPE: Récupération des factures")

if apply_filters or "factures_df" not in st.session_state:
    # Appliquer les filtres
    client_filter = None if selected_client == "Tous" else selected_client
    
    if client_filter or date_debut or date_fin:
        logger.info(f"ÉTAPE: Application des filtres - Client: {client_filter}, Période: {date_debut} à {date_fin}")
        factures_df = get_factures_filtered(
            client_nom=client_filter,
            date_debut=date_debut,
            date_fin=date_fin
        )
    else:
        logger.info("ÉTAPE: Récupération de toutes les factures")
        factures_df = get_all_factures()
    
    st.session_state["factures_df"] = factures_df
    logger.info(f"ÉTAPE: {len(factures_df)} factures récupérées")
else:
    factures_df = st.session_state["factures_df"]

# Affichage des résultats
st.header(f"📋 Factures ({len(factures_df)} résultats)")

if len(factures_df) == 0:
    st.info("Aucune facture trouvée avec ces critères.")
else:
    # Ajouter une colonne pour indiquer la disponibilité du PDF
    logger.info("ÉTAPE: Vérification de la disponibilité des PDFs dans le storage")
    
    # Créer une copie du DataFrame pour ajouter la colonne PDF
    display_df = factures_df.copy()
    pdf_status = []
    
    for _, row in factures_df.iterrows():
        pdf_exists = check_facture_exists_in_storage(row["num_facture"])
        pdf_status.append("📄 Disponible" if pdf_exists else "❌ Indisponible")
    
    display_df["pdf_disponible"] = pdf_status
    
    # Configuration des colonnes pour l'affichage
    column_config = {
        "num_facture": st.column_config.NumberColumn(
            "N° Facture",
            format="%d"
        ),
        "date": st.column_config.DateColumn(
            "Date",
            format="DD/MM/YYYY"
        ),
        "client_nom": st.column_config.TextColumn(
            "Client"
        ),
        "date_prestation": st.column_config.DateColumn(
            "Date Prestation",
            format="DD/MM/YYYY"
        ),
        "tot_ht": st.column_config.NumberColumn(
            "Total HT",
            format="%.2f €"
        ),
        "tot_ttc": st.column_config.NumberColumn(
            "Total TTC",
            format="%.2f €"
        ),
        "paye": st.column_config.CheckboxColumn(
            "Payé"
        ),
        "pdf_disponible": st.column_config.TextColumn(
            "PDF"
        )
    }
    
    # Affichage du tableau avec édition possible pour le statut payé
    edited_df = st.data_editor(
        display_df,
        column_config=column_config,
        disabled=["num_facture", "date", "client_nom", "date_prestation", "tot_ht", "tot_ttc", "pdf_disponible"],
        hide_index=True,
        use_container_width=True,
        key="factures_editor"
    )
    
    # Gestion des modifications du statut de paiement
    if "factures_editor" in st.session_state:
        editor_state = st.session_state["factures_editor"]
        
        for index, updates in editor_state.get("edited_rows", {}).items():
            if "paye" in updates:
                num_facture = display_df.iloc[index]["num_facture"]
                new_status = updates["paye"]
                
                logger.info(f"ÉTAPE: Mise à jour statut paiement facture {num_facture}: {new_status}")
                
                result = update_facture_paiement(num_facture, new_status)
                
                if result["success"]:
                    st.success(f"✅ Statut de paiement mis à jour pour la facture {num_facture}")
                    logger.info(f"ÉTAPE: Statut paiement facture {num_facture} mis à jour avec succès")
                else:
                    st.error(f"❌ Erreur lors de la mise à jour: {result['error']}")
                    logger.error(f"ÉTAPE: Erreur mise à jour facture {num_facture}: {result['error']}")

# Section des actions
st.header("⚡ Actions")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📥 Télécharger une facture")
    
    if len(factures_df) > 0:
        # Sélection de la facture à télécharger
        facture_options = [f"Facture {row['num_facture']} - {row['client_nom']}" for _, row in factures_df.iterrows()]
        selected_facture_download = st.selectbox("Sélectionner une facture", facture_options, key="download_select")
        
        # Vérifier la disponibilité du PDF
        selected_index = facture_options.index(selected_facture_download)
        selected_row = factures_df.iloc[selected_index]
        num_facture = selected_row["num_facture"]
        
        # Vérifier si le fichier existe dans le storage
        pdf_exists = check_facture_exists_in_storage(num_facture)
        
        if pdf_exists:
            st.success(f"✅ PDF disponible pour la facture {num_facture}")
            
            if st.button("Télécharger PDF", key="download_btn"):
                logger.info(f"ÉTAPE: Tentative de téléchargement facture {num_facture} depuis Supabase Storage")
                
                # Télécharger depuis Supabase Storage
                download_result = download_facture_from_storage(num_facture)
                
                if download_result["success"]:
                    st.download_button(
                        label=f"📄 Télécharger Facture {num_facture}",
                        data=download_result["data"],
                        file_name=download_result["filename"],
                        mime="application/pdf",
                        key="download_pdf_btn"
                    )
                    logger.info(f"ÉTAPE: Téléchargement facture {num_facture} proposé depuis Storage")
                else:
                    st.error(f"❌ Erreur lors du téléchargement: {download_result['error']}")
                    logger.error(f"ÉTAPE: Erreur téléchargement facture {num_facture}: {download_result['error']}")
        else:
            st.warning(f"⚠️ Le fichier PDF pour la facture {num_facture} n'est pas disponible dans le storage.")
            logger.warning(f"ÉTAPE: PDF facture {num_facture} non trouvé dans Supabase Storage")

with col2:
    st.subheader("🗑️ Supprimer une facture")
    
    if len(factures_df) > 0:
        # Sélection de la facture à supprimer
        facture_options_delete = [f"Facture {row['num_facture']} - {row['client_nom']}" for _, row in factures_df.iterrows()]
        selected_facture_delete = st.selectbox("Sélectionner une facture", facture_options_delete, key="delete_select")
        
        # Confirmation de suppression
        confirm_delete = st.checkbox("Je confirme vouloir supprimer cette facture", key="confirm_delete")
        
        if st.button("Supprimer", type="secondary", disabled=not confirm_delete, key="delete_btn"):
            # Index de la facture sélectionnée
            selected_index = facture_options_delete.index(selected_facture_delete)
            selected_row = factures_df.iloc[selected_index]
            num_facture = selected_row["num_facture"]
            
            logger.info(f"ÉTAPE: Tentative de suppression facture {num_facture}")
            
            result = soft_delete_facture(num_facture)
            
            if result["success"]:
                st.success(f"✅ Facture {num_facture} supprimée avec succès")
                logger.info(f"ÉTAPE: Facture {num_facture} marquée comme inactive")
                
                # Rafraîchir les données
                st.session_state["factures_df"] = get_all_factures()
                st.rerun()
            else:
                st.error(f"❌ Erreur lors de la suppression: {result['error']}")
                logger.error(f"ÉTAPE: Erreur suppression facture {num_facture}: {result['error']}")

# Statistiques
if len(factures_df) > 0:
    st.header("📊 Statistiques")
    
    # Calculs des statistiques
    total_factures = len(factures_df)
    factures_payees = len(factures_df[factures_df["paye"] == True])
    factures_impayees = len(factures_df[factures_df["paye"] == False])
    
    # Calculs financiers
    total_ttc = factures_df["tot_ttc"].sum()
    total_paye = factures_df[factures_df["paye"] == True]["tot_ttc"].sum()
    reste_a_payer = factures_df[factures_df["paye"] == False]["tot_ttc"].sum()
    
    logger.info(f"ÉTAPE: Statistiques calculées - {total_factures} factures, Total: {total_ttc:.2f}€, Reste à payer: {reste_a_payer:.2f}€")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Factures", total_factures)
    
    with col2:
        st.metric("Factures Payées", factures_payees)
    
    with col3:
        st.metric("Factures Impayées", factures_impayees)
    
    with col4:
        st.metric("Total TTC", f"{total_ttc:.2f} €")
    
    with col5:
        st.metric(
            "Reste à Payer", 
            f"{reste_a_payer:.2f} €",
            delta=f"-{total_paye:.2f} €" if total_paye > 0 else None
        )
    
    # Affichage supplémentaire avec pourcentages
    st.subheader("📈 Répartition des paiements")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        if total_ttc > 0:
            pourcentage_paye = (total_paye / total_ttc) * 100
            pourcentage_impaye = (reste_a_payer / total_ttc) * 100
            
            st.success(f"💰 **Montant payé :** {total_paye:.2f} € ({pourcentage_paye:.1f}%)")
            st.error(f"⏳ **Reste à payer :** {reste_a_payer:.2f} € ({pourcentage_impaye:.1f}%)")
    
    with col_right:
        # Graphique simple avec des barres de progression
        if total_ttc > 0:
            progress_paye = total_paye / total_ttc
            st.write("**Progression des paiements**")
            st.progress(progress_paye)
            st.caption(f"{pourcentage_paye:.1f}% des factures sont payées")

logger.info("ÉTAPE: Page Gestion des Factures affichée")