import streamlit as st
import pandas as pd
import json
import logging
from utils.get_data import get_ref_products
from utils.get_data import get_clients
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
product = get_ref_products()
logger.info(f"ÉTAPE: {len(product)} produits chargés")

st.header("Produits")
logger.info("ÉTAPE: Affichage de l'éditeur de produits")
product = st.data_editor(product, key="product", num_rows="dynamic", hide_index=True,column_order=["nom","prix","tva"])



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
    
    pdf_filename, insert = invoice_maker(r"template_facture_ASD11.xlsx","data/test.xlsx",st.session_state["df"],clients.loc[clients["nom"] == client].iloc[0],data_presta,
                                         total_ttc, total_ht)
    logger.info(f"ÉTAPE: Facture générée - Nom du fichier: {pdf_filename}")
    logger.info(f"ÉTAPE: Données insertées: {insert}")
    st.write(insert)
    st.success("Facture générée")
    
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

