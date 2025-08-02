import requests
import logging
from msal import ConfidentialClientApplication
import os
import streamlit as st

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration (à adapter selon vos secrets)
CLIENT_ID = st.secrets["APPLICATION_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRETS"]
TENANT_ID = st.secrets["TENANT"]


app = ConfidentialClientApplication(
    CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    client_credential=CLIENT_SECRET,
)

def get_access_token():
    """Obtient un token d'accès pour Microsoft Graph"""
    logger.info("Demande de token d'accès...")
    scopes = ["https://graph.microsoft.com/.default"]
    
    try:
        result = app.acquire_token_for_client(scopes=scopes)
        if "access_token" in result:
            logger.info("Token d'accès obtenu avec succès")
            return result["access_token"]
        else:
            logger.error(f"Erreur d'authentification: {result.get('error_description')}")
            return None
    except Exception as e:
        logger.error(f"Erreur lors de l'obtention du token: {str(e)}")
        return None


app = ConfidentialClientApplication(
    CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    client_credential=CLIENT_SECRET,
)

def quick_onedrive_test(user_id):
    """
    Test rapide d'accès OneDrive sans vérifier l'utilisateur
    """
    logger.info(f"Test rapide OneDrive pour: {user_id}")
    
    token = get_access_token()
    if not token:
        return False
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Test direct du drive OneDrive
        drive_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive"
        logger.info("Test direct du drive OneDrive...")
        
        drive_response = requests.get(drive_url, headers=headers)
        logger.info(f"Code réponse drive: {drive_response.status_code}")
        
        if drive_response.status_code == 200:
            logger.info("✅ OneDrive accessible directement!")
            return True
        else:
            logger.error(f"❌ Erreur drive: {drive_response.status_code} - {drive_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Erreur test rapide: {str(e)}")
        return False
    """
    Vérifie si l'utilisateur a accès à OneDrive
    
    Args:
        user_id: ID ou UPN de l'utilisateur
    
    Returns:
        bool: True si OneDrive accessible, False sinon
    """
    logger.info(f"Vérification de l'accès OneDrive pour: {user_id}")
    
    # Obtenir le token d'accès
    token = get_access_token()
    if not token:
        logger.error("Impossible d'obtenir le token d'accès")
        return False
    
    # Headers pour l'API Graph
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Test 1: Vérifier si l'utilisateur existe
        user_url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
        logger.info("Test 1: Vérification de l'existence de l'utilisateur...")
        
        user_response = requests.get(user_url, headers=headers)
        logger.info(f"Code réponse utilisateur: {user_response.status_code}")
        
        if user_response.status_code != 200:
            logger.error(f"Utilisateur non trouvé: {user_response.text}")
            return False
        
        user_data = user_response.json()
        logger.info(f"Utilisateur trouvé: {user_data.get('displayName', 'N/A')}")
        
        # Test 2: Vérifier l'accès au drive OneDrive
        drive_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive"
        logger.info("Test 2: Vérification de l'accès au drive...")
        
        drive_response = requests.get(drive_url, headers=headers)
        logger.info(f"Code réponse drive: {drive_response.status_code}")
        
        if drive_response.status_code == 200:
            drive_data = drive_response.json()
            logger.info(f"✅ OneDrive accessible - ID: {drive_data.get('id', 'N/A')}")
            logger.info(f"✅ Propriétaire: {drive_data.get('owner', {}).get('user', {}).get('displayName', 'N/A')}")
            return True
        elif drive_response.status_code == 404:
            logger.error("❌ OneDrive non trouvé - Probablement pas activé pour cet utilisateur")
            return False
        else:
            logger.error(f"❌ Erreur d'accès OneDrive: {drive_response.status_code} - {drive_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Erreur lors de la vérification: {str(e)}")
        return False

def check_documents_folder_access(user_id):
    """
    Vérifie spécifiquement l'accès au dossier Documents
    
    Args:
        user_id: ID ou UPN de l'utilisateur
    
    Returns:
        bool: True si dossier Documents accessible, False sinon
    """
    logger.info(f"Vérification de l'accès au dossier Documents pour: {user_id}")
    
    # Obtenir le token d'accès
    token = get_access_token()
    if not token:
        return False
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Vérifier l'accès au dossier Documents
        documents_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/root:/Documents"
        
        response = requests.get(documents_url, headers=headers)
        logger.info(f"Code réponse dossier Documents: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ Dossier Documents accessible")
            return True
        elif response.status_code == 404:
            logger.warning("⚠️ Dossier Documents n'existe pas - Sera créé lors du premier upload")
            return True  # OneDrive crée automatiquement le dossier Documents
        else:
            logger.error(f"❌ Erreur d'accès Documents: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Erreur lors de la vérification Documents: {str(e)}")
        return False
    """Obtient un token d'accès pour Microsoft Graph"""
    logger.info("Demande de token d'accès...")
    scopes = ["https://graph.microsoft.com/.default"]
    
    try:
        result = app.acquire_token_for_client(scopes=scopes)
        if "access_token" in result:
            logger.info("Token d'accès obtenu avec succès")
            return result["access_token"]
        else:
            logger.error(f"Erreur d'authentification: {result.get('error_description')}")
            return None
    except Exception as e:
        logger.error(f"Erreur lors de l'obtention du token: {str(e)}")
        return None

def upload_file_to_onedrive(file_path):
    """
    Upload un fichier local vers le dossier Documents de OneDrive
    
    Args:
        file_path: Chemin vers le fichier local (ex: "facture.pdf")
    
    Returns:
        bool: True si succès, False sinon
    """
    logger.info(f"Début upload du fichier: {file_path}")
    
    # Vérifier que le fichier existe
    if not os.path.exists(file_path):
        logger.error(f"Fichier non trouvé: {file_path}")
        return False
    
    file_size = os.path.getsize(file_path)
    logger.info(f"Taille du fichier: {file_size} bytes")
    
    # Obtenir le token d'accès
    token = get_access_token()
    if not token:
        logger.error("Impossible d'obtenir le token d'accès")
        return False
    
    # Extraire le nom du fichier
    filename = os.path.basename(file_path)
    logger.info(f"Nom du fichier: {filename}")
    
    # Headers pour l'API Graph
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/octet-stream'
    }
    
    # URL pour uploader dans Documents - AVEC USER ID au lieu de /me
    USER_ID = "sarl.dks.jp_gmail.com#EXT#@sarldksjpgmail.onmicrosoft.com"
    url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/drive/root:/Documents/{filename}:/content"
    logger.info(f"URL d'upload: {url}")
    
    try:
        # Lire et uploader le fichier
        logger.info("Lecture du fichier...")
        with open(file_path, 'rb') as file:
            file_content = file.read()
            
        logger.info("Envoi vers OneDrive...")
        response = requests.put(url, headers=headers, data=file_content)
        
        logger.info(f"Code de réponse: {response.status_code}")
        
        if response.status_code in [200, 201]:
            logger.info(f"SUCCESS: Fichier '{filename}' uploadé avec succès dans Documents!")
            return True
        else:
            logger.error(f"ERREUR upload: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"ERREUR lors de l'upload: {str(e)}")
        return False

# Exemple d'utilisation avec vérifications
if __name__ == "__main__":
    USER_ID = "sarl.dks.jp_gmail.com#EXT#@sarldksjpgmail.onmicrosoft.com"
    
    logger.info("=== TEST RAPIDE ===")
    
    # Test rapide sans permissions User.Read.All
    drive_ok = quick_onedrive_test(USER_ID)
    if drive_ok:
        logger.info("✅ OneDrive accessible - Tentative d'upload...")
        
        # Test de l'upload direct
        file_to_upload = "test_file.pdf"  # Remplacez par votre fichier
        success = upload_file_to_onedrive(file_to_upload)
        
        if success:
            logger.info("=== UPLOAD TERMINÉ AVEC SUCCÈS ===")
        else:
            logger.error("=== ÉCHEC DE L'UPLOAD ===")
    else:
        logger.error("❌ OneDrive non accessible")
        
    logger.info("=== FIN DU PROCESSUS ===")