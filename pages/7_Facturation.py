import streamlit as st
import pandas as pd
import logging
from utils.get_data import get_ref_products
from utils.get_data import get_clients
from utils.get_data import save_product_changes_from_session
from utils.invoice_maker import invoice_maker

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [FACTURATION] - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('facturation.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Function to validate and clean invoice data
def validate_and_clean_invoice_data(df):
    """
    Valide et nettoie les données de la facture avant génération
    Retourne le DataFrame nettoyé et une liste d'erreurs
    """
    logger.info("ÉTAPE: Début de validation des données de facture")
    errors = []
    cleaned_df = df.copy()
    
    # 1. Supprimer les lignes vides (où Produit est vide ou None)
    initial_rows = len(cleaned_df)
    cleaned_df = cleaned_df[
        (cleaned_df['Produit'].notna()) & 
        (cleaned_df['Produit'].str.strip() != '')
    ].copy()
    removed_empty_rows = initial_rows - len(cleaned_df)
    if removed_empty_rows > 0:
        logger.info(f"ÉTAPE: {removed_empty_rows} ligne(s) vide(s) supprimée(s)")
    
    # 2. Vérifier que si prix unitaire est rempli, TVA l'est aussi
    for index, row in cleaned_df.iterrows():
        if pd.notna(row['Prix unitaire']) and row['Prix unitaire'] != '':
            if pd.isna(row['TVA']) or row['TVA'] == '':
                error_msg = f"Ligne {index + 1}: TVA manquante pour le produit '{row['Produit']}' (prix unitaire: {row['Prix unitaire']})"
                errors.append(error_msg)
                logger.error(f"VALIDATION ERROR: {error_msg}")
    
    # 3. Vérifier qu'il reste au moins une ligne valide
    if len(cleaned_df) == 0:
        error_msg = "Aucune ligne valide dans la facture"
        errors.append(error_msg)
        logger.error(f"VALIDATION ERROR: {error_msg}")
    
    # 4. Vérifier que toutes les lignes ont un produit, quantité et prix
    for index, row in cleaned_df.iterrows():
        # Validation quantité
        try:
            quantite = float(row['Quantité']) if pd.notna(row['Quantité']) else 0
            if quantite <= 0:
                error_msg = f"Ligne {index + 1}: Quantité invalide pour le produit '{row['Produit']}'"
                errors.append(error_msg)
                logger.error(f"VALIDATION ERROR: {error_msg}")
        except (ValueError, TypeError):
            error_msg = f"Ligne {index + 1}: Quantité non numérique pour le produit '{row['Produit']}'"
            errors.append(error_msg)
            logger.error(f"VALIDATION ERROR: {error_msg}")
        
        # Validation prix unitaire
        try:
            prix = float(row['Prix unitaire']) if pd.notna(row['Prix unitaire']) else 0
            if prix <= 0:
                error_msg = f"Ligne {index + 1}: Prix unitaire invalide pour le produit '{row['Produit']}'"
                errors.append(error_msg)
                logger.error(f"VALIDATION ERROR: {error_msg}")
        except (ValueError, TypeError):
            error_msg = f"Ligne {index + 1}: Prix unitaire non numérique pour le produit '{row['Produit']}'"
            errors.append(error_msg)
            logger.error(f"VALIDATION ERROR: {error_msg}")
    
    if len(errors) == 0:
        logger.info(f"ÉTAPE: Validation réussie - {len(cleaned_df)} ligne(s) valide(s)")
    else:
        logger.error(f"ÉTAPE: Validation échouée - {len(errors)} erreur(s) trouvée(s)")
    
    return cleaned_df, errors

# Function to handle changes in the DataFrame
def df_on_change():
    logger.info("ÉTAPE: Début de df_on_change - Gestion des modifications du DataFrame")
    # Get modified dataframe
    state = st.session_state["df_editor"]
    logger.info(f"ÉTAPE: État récupéré - {len(state['edited_rows'])} lignes modifiées, {len(state['added_rows'])} lignes ajoutées, {len(state['deleted_rows'])} lignes supprimées")
    for index, updates in state["edited_rows"].items():
        logger.info(f"ÉTAPE: Traitement ligne {index} - Modifications: {updates}")
        # modify each changed value by the user in the session_state df
        for key, value in updates.items():
            logger.info(f"ÉTAPE: Mise à jour {key} = {value} pour ligne {index}")
            st.session_state["df"].loc[st.session_state["df"].index == index, key] = (
                value
            )
        # Get the pr for changed lines
        for key, value in updates.items():
            if (
                key == "Produit"
                and value in product["nom"].tolist()
                and product.loc[product["nom"] == value, "prix"] is not None
            ):
                prix = product.loc[product["nom"] == value, "prix"].iat[0]
                logger.info(f"ÉTAPE: Mise à jour prix unitaire pour produit '{value}': {prix}")
                st.session_state["df"].loc[
                    st.session_state["df"].index == index, "Prix unitaire"
                ] = prix
            if (
                key == "Produit"
                and value in product["nom"].tolist()
                and product.loc[product["nom"] == value, "tva"] is not None
            ):
                tva = product.loc[product["nom"] == value, "tva"].iat[0]
                logger.info(f"ÉTAPE: Mise à jour TVA pour produit '{value}': {tva}%")
                st.session_state["df"].loc[
                    st.session_state["df"].index == index, "TVA"
                ] = tva

        # # Update the result column based on the input column
        if not (pd.isna(st.session_state["df"].loc[index, "Prix unitaire"])):
            quantite = int(st.session_state["df"].loc[index, "Quantité"])
            prix_unitaire = float(st.session_state["df"].loc[index, "Prix unitaire"])
            prix_total = quantite * prix_unitaire
            logger.info(f"ÉTAPE: Calcul prix total HT ligne {index}: {quantite} × {prix_unitaire} = {prix_total}")
            st.session_state["df"].loc[index, "Prix total HT"] = prix_total

        # st.session_state["df"].loc[st.session_state["df"].index == index, "result"] = 2
        #     float(
        #         st.session_state["df"].loc[
        #             st.session_state["df"].index == index, "Prix Unit"
        #         ][0]
        #     )
        #     * st.session_state["df"].loc[st.session_state["df"].index == index, "q"][0]
        # )

    for ins in state["added_rows"]:
        logger.info(f"ÉTAPE: Ajout nouvelle ligne: {ins}")
        st.session_state["df"].loc[len(st.session_state["df"])] = {
            "Produit": "",
            "Quantité": 1,
            "Prix unitaire": None,
            "Prix total HT": None,
        }
    for index in state["deleted_rows"]:
        logger.info(f"ÉTAPE: Suppression ligne {index}")
        st.session_state["df"] = st.session_state["df"].drop(index=index)

    st.session_state["df"] = st.session_state["df"].reset_index(drop=True)
    logger.info("ÉTAPE: Fin de df_on_change - DataFrame mis à jour et réinitialisé")



st.set_page_config(layout="wide", page_title="Facturation AG-Grid")

logger.info("ÉTAPE: Démarrage de l'application Facturation")
logger.info("ÉTAPE: Récupération des produits de référence")
original_products = get_ref_products()
logger.info(f"ÉTAPE: {len(original_products)} produits chargés")

# Stocker les produits originaux pour comparaison
if "original_products" not in st.session_state:
    st.session_state["original_products"] = original_products.copy()

st.header("Produits")
logger.info("ÉTAPE: Affichage de l'éditeur de produits")
product = st.data_editor(original_products, key="product", num_rows="dynamic", hide_index=True,column_order=["nom","prix","tva"])



# Initial DataFrame
logger.info("ÉTAPE: Initialisation du DataFrame de facturation")
df = pd.DataFrame(
    columns=[
        "Produit",
        "Quantité",
        "Prix unitaire",
        "TVA",
        "Prix total HT",
    ]
)

logger.info("ÉTAPE: Récupération de la liste des clients")
clients = get_clients()
logger.info(f"ÉTAPE: {len(clients)} clients disponibles")
client = st.selectbox("Client",options=clients["nom"])

data_presta = st.date_input(
    "Date de la prestation",
    value=None,                      # pas de valeur par défaut
    min_value=None,
    max_value=None,
    key="data_presta"
)


st.header("Facture")

logger.info("ÉTAPE: Initialisation de la session pour le DataFrame de facturation")
if "df" not in st.session_state:
    st.session_state["df"] = df
    logger.info("ÉTAPE: Nouveau DataFrame créé dans la session")
st.data_editor(
    st.session_state["df"],
    key="df_editor",
    on_change=df_on_change,
    num_rows="dynamic",
    hide_index=True,
    column_config={
        "Produit": st.column_config.SelectboxColumn(options=product["nom"])
    },
    column_order=["Produit","Quantité", "Prix unitaire", "TVA", "Prix total HT"]
)
logger.info("ÉTAPE: Calcul des totaux de la facture")
st.write(st.session_state["df"])
total_ht = pd.to_numeric(st.session_state["df"]["Prix total HT"], errors='coerce').sum()
logger.info(f"ÉTAPE: Total HT calculé: {total_ht:.2f} €")

mont_ttc= st.session_state["df"]["Prix total HT"]  * (st.session_state["df"]["TVA"] / 100 +1)
total_ttc = mont_ttc.sum()
logger.info(f"ÉTAPE: Total TTC calculé: {total_ttc:.2f} €")
st.write(f"Total HT : {total_ht:.2f} €")
st.write(f"Total TTC : {total_ttc:.2f} €")


if st.button("Générer la facture") : 
    logger.info("ÉTAPE: Début de génération de facture")
    logger.info(f"ÉTAPE: Client sélectionné: {client}")
    logger.info(f"ÉTAPE: Date prestation: {data_presta}")
    logger.info(f"ÉTAPE: Nombre de lignes dans la facture: {len(st.session_state['df'])}")
    
    # Validation et nettoyage des données
    cleaned_df, validation_errors = validate_and_clean_invoice_data(st.session_state["df"])
    
    if validation_errors:
        # Afficher les erreurs de validation
        st.error("⚠️ Erreurs de validation détectées :")
        for error in validation_errors:
            st.error(f"• {error}")
        logger.error("ÉTAPE: Génération de facture annulée à cause d'erreurs de validation")
    else:
        # Validation réussie, procéder à la génération
        logger.info("ÉTAPE: Validation réussie, génération de la facture en cours")
        
        # Sauvegarder les modifications des produits avant la génération
        logger.info("ÉTAPE: Sauvegarde des modifications de produits")
        if "product" in st.session_state:
            product_save_result = save_product_changes_from_session(
                st.session_state["product"], 
                st.session_state["original_products"]
            )
            
            if product_save_result["success"]:
                changes = product_save_result["changes"]
                logger.info(f"ÉTAPE: Produits sauvegardés - {changes['inserted']} ajoutés, {changes['updated']} modifiés, {changes['deleted']} supprimés")
                
                if any([changes['inserted'], changes['updated'], changes['deleted']]):
                    st.info(f"📦 Produits mis à jour: {changes['inserted']} ajoutés, {changes['updated']} modifiés, {changes['deleted']} supprimés")
                    for detail in changes['details']:
                        logger.info(f"DÉTAIL: {detail}")
                    
                    # Recharger les produits depuis la base après sauvegarde
                    st.session_state["original_products"] = get_ref_products()
                    logger.info("ÉTAPE: Produits originaux mis à jour depuis la base")
            else:
                logger.error(f"ÉTAPE: Erreur lors de la sauvegarde des produits: {product_save_result['error']}")
                st.warning(f"⚠️ Erreur lors de la sauvegarde des produits: {product_save_result['error']}")
        
        # Recalculer les totaux avec les données nettoyées
        cleaned_total_ht = pd.to_numeric(cleaned_df["Prix total HT"], errors='coerce').sum()
        cleaned_mont_ttc = cleaned_df["Prix total HT"] * (cleaned_df["TVA"] / 100 + 1)
        cleaned_total_ttc = cleaned_mont_ttc.sum()
        
        logger.info(f"ÉTAPE: Totaux recalculés - HT: {cleaned_total_ht:.2f} €, TTC: {cleaned_total_ttc:.2f} €")
        
        # Mettre à jour la session avec les données nettoyées
        st.session_state["df"] = cleaned_df
        
        pdf_filename, insert = invoice_maker(r"template_facture_ASD11.xlsx","data/test.xlsx",cleaned_df,clients.loc[clients["nom"] == client].iloc[0],data_presta,
                                             cleaned_total_ttc, cleaned_total_ht)
        logger.info(f"ÉTAPE: Facture générée - Nom du fichier: {pdf_filename}")
        logger.info(f"ÉTAPE: Données insertées: {insert}")
        st.write(insert)
        st.success("✅ Facture générée avec succès")
        
        logger.info("ÉTAPE: Lecture du fichier PDF généré")
        with open('data/temp.pdf', 'rb') as pdf_file:
            pdf_data = pdf_file.read()
        logger.info(f"ÉTAPE: PDF lu, taille: {len(pdf_data)} bytes")
        
        st.write(pdf_filename)
        st.download_button(
            label="Télécharger PDF",
            data=pdf_data,
            file_name=pdf_filename,
            mime="application/pdf"
            )
        logger.info("ÉTAPE: Bouton de téléchargement affiché")
        
        # Afficher un résumé de ce qui a été nettoyé
        if len(cleaned_df) < len(st.session_state["df"]):
            removed_count = len(st.session_state["df"]) - len(cleaned_df)
            st.info(f"ℹ️ {removed_count} ligne(s) vide(s) ont été automatiquement supprimée(s)")

