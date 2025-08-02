import streamlit as st

# Configuration de la page - DOIT être en premier
st.set_page_config(layout="wide", page_title="Gestion des Clients")

import pandas as pd
import logging
from utils.auth import require_auth, show_auth_status
from utils.get_data import get_clients, add_client, update_client, delete_client, get_client_details, search_clients

# Vérification de l'authentification
if not require_auth():
    st.stop()

# Afficher le statut d'authentification dans la sidebar
show_auth_status()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [GESTION_CLIENTS] - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('gestion_clients.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

st.title("👥 Gestion des Clients")

logger.info("ÉTAPE: Démarrage de la page Gestion des Clients")

# Section de recherche
st.header("🔍 Recherche et Filtres")

col1, col2 = st.columns([2, 1])

with col1:
    search_term = st.text_input("Rechercher un client par nom", placeholder="Tapez le nom du client...")

with col2:
    st.write("")  # Espace pour aligner
    search_button = st.button("🔍 Rechercher", type="primary")

# Récupération des données
logger.info("ÉTAPE: Récupération des clients")

if search_button or search_term:
    if search_term.strip():
        logger.info(f"ÉTAPE: Recherche clients avec terme: '{search_term}'")
        clients_df = search_clients(search_term.strip())
    else:
        clients_df = get_clients()
else:
    clients_df = get_clients()

st.session_state["clients_df"] = clients_df
logger.info(f"ÉTAPE: {len(clients_df)} clients récupérés")

# Affichage des clients
st.header(f"👥 Clients ({len(clients_df)} résultats)")

if len(clients_df) == 0:
    st.info("Aucun client trouvé.")
else:
    # Configuration des colonnes pour l'affichage
    column_config = {
        "id": st.column_config.NumberColumn(
            "ID",
            format="%d"
        ),
        "nom": st.column_config.TextColumn(
            "Nom"
        ),
        "adresse_1": st.column_config.TextColumn(
            "Adresse 1"
        ),
        "adresse_2": st.column_config.TextColumn(
            "Adresse 2"
        ),
        "telephone": st.column_config.TextColumn(
            "Téléphone"
        ),
        "created_at": st.column_config.DatetimeColumn(
            "Créé le",
            format="DD/MM/YYYY HH:mm"
        )
    }
    
    # Affichage du tableau (lecture seule pour l'instant)
    st.dataframe(
        clients_df,
        column_config=column_config,
        hide_index=True,
        use_container_width=True
    )

# Section des actions
st.header("⚡ Actions")

# Onglets pour différentes actions
tab1, tab2, tab3 = st.tabs(["➕ Ajouter un client", "✏️ Modifier un client", "🗑️ Supprimer un client"])

with tab1:
    st.subheader("Ajouter un nouveau client")
    
    with st.form("add_client_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_nom = st.text_input("Nom *", help="Champ obligatoire")
            new_adresse_1 = st.text_input("Adresse ligne 1")
        
        with col2:
            new_telephone = st.text_input("Téléphone")
            new_adresse_2 = st.text_input("Adresse ligne 2")
        
        submitted = st.form_submit_button("Ajouter le client", type="primary")
        
        if submitted:
            if not new_nom or not new_nom.strip():
                st.error("❌ Le nom du client est obligatoire")
            else:
                logger.info(f"ÉTAPE: Tentative d'ajout client: {new_nom}")
                
                result = add_client(
                    nom=new_nom,
                    adresse_1=new_adresse_1 if new_adresse_1 else None,
                    adresse_2=new_adresse_2 if new_adresse_2 else None,
                    telephone=new_telephone if new_telephone else None
                )
                
                if result["success"]:
                    st.success(f"✅ Client '{new_nom}' ajouté avec succès!")
                    logger.info(f"ÉTAPE: Client {new_nom} ajouté avec ID {result['data']['id']}")
                    
                    # Rafraîchir les données
                    st.session_state["clients_df"] = get_clients()
                    st.rerun()
                else:
                    st.error(f"❌ Erreur lors de l'ajout: {result['error']}")
                    logger.error(f"ÉTAPE: Erreur ajout client {new_nom}: {result['error']}")

with tab2:
    st.subheader("Modifier un client existant")
    
    if len(clients_df) > 0:
        # Sélection du client à modifier
        client_options = [f"{row['nom']} (ID: {row['id']})" for _, row in clients_df.iterrows()]
        selected_client = st.selectbox("Sélectionner un client à modifier", client_options)
        
        if selected_client:
            # Récupérer l'ID du client sélectionné
            selected_id = int(selected_client.split("ID: ")[1].split(")")[0])
            
            # Récupérer les détails du client
            client_details = get_client_details(selected_id)
            
            if client_details["success"]:
                client_data = client_details["data"]
                
                with st.form("edit_client_form"):
                    st.info(f"Modification du client: **{client_data['nom']}**")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_nom = st.text_input("Nom *", value=client_data['nom'])
                        edit_adresse_1 = st.text_input("Adresse ligne 1", value=client_data['adresse_1'] or "")
                    
                    with col2:
                        edit_telephone = st.text_input("Téléphone", value=client_data['telephone'] or "")
                        edit_adresse_2 = st.text_input("Adresse ligne 2", value=client_data['adresse_2'] or "")
                    
                    edit_submitted = st.form_submit_button("Modifier le client", type="primary")
                    
                    if edit_submitted:
                        logger.info(f"ÉTAPE: Tentative de modification client ID {selected_id}")
                        
                        result = update_client(
                            client_id=selected_id,
                            nom=edit_nom,
                            adresse_1=edit_adresse_1,
                            adresse_2=edit_adresse_2,
                            telephone=edit_telephone
                        )
                        
                        if result["success"]:
                            st.success(f"✅ Client modifié avec succès!")
                            logger.info(f"ÉTAPE: Client ID {selected_id} modifié avec succès")
                            
                            # Rafraîchir les données
                            st.session_state["clients_df"] = get_clients()
                            st.rerun()
                        else:
                            st.error(f"❌ Erreur lors de la modification: {result['error']}")
                            logger.error(f"ÉTAPE: Erreur modification client ID {selected_id}: {result['error']}")
            else:
                st.error(f"❌ Erreur lors de la récupération des détails: {client_details['error']}")
    else:
        st.info("Aucun client disponible pour modification.")

with tab3:
    st.subheader("Supprimer un client")
    
    if len(clients_df) > 0:
        # Sélection du client à supprimer
        client_options_delete = [f"{row['nom']} (ID: {row['id']})" for _, row in clients_df.iterrows()]
        selected_client_delete = st.selectbox("Sélectionner un client à supprimer", client_options_delete, key="delete_select")
        
        if selected_client_delete:
            # Récupérer l'ID du client sélectionné
            selected_id_delete = int(selected_client_delete.split("ID: ")[1].split(")")[0])
            
            st.warning("⚠️ **Attention**: Cette action est irréversible!")
            st.info("💡 **Note**: Un client ne peut être supprimé que s'il n'a aucune facture associée.")
            
            # Confirmation de suppression
            confirm_delete = st.checkbox("Je confirme vouloir supprimer ce client définitivement", key="confirm_client_delete")
            
            if st.button("Supprimer", type="secondary", disabled=not confirm_delete, key="delete_client_btn"):
                logger.info(f"ÉTAPE: Tentative de suppression client ID {selected_id_delete}")
                
                result = delete_client(selected_id_delete)
                
                if result["success"]:
                    st.success(f"✅ Client supprimé avec succès!")
                    logger.info(f"ÉTAPE: Client ID {selected_id_delete} supprimé avec succès")
                    
                    # Rafraîchir les données
                    st.session_state["clients_df"] = get_clients()
                    st.rerun()
                else:
                    st.error(f"❌ {result['error']}")
                    logger.error(f"ÉTAPE: Erreur suppression client ID {selected_id_delete}: {result['error']}")
    else:
        st.info("Aucun client disponible pour suppression.")

# Statistiques
if len(clients_df) > 0:
    st.header("📊 Statistiques")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_clients = len(clients_df)
        st.metric("Total Clients", total_clients)
    
    with col2:
        clients_avec_telephone = len(clients_df[clients_df["telephone"].notna() & (clients_df["telephone"] != "")])
        st.metric("Avec Téléphone", clients_avec_telephone)
    
    with col3:
        clients_avec_adresse = len(clients_df[clients_df["adresse_1"].notna() & (clients_df["adresse_1"] != "")])
        st.metric("Avec Adresse", clients_avec_adresse)
    
    with col4:
        if total_clients > 0:
            pourcentage_complet = ((clients_avec_telephone + clients_avec_adresse) / (total_clients * 2)) * 100
            st.metric("Profils Complets", f"{pourcentage_complet:.1f}%")

logger.info("ÉTAPE: Page Gestion des Clients affichée")