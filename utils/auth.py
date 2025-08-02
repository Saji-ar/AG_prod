import streamlit as st
import hashlib
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_auth_config():
    """
    Récupère la configuration d'authentification depuis st.secrets
    
    Returns:
        dict: Configuration d'authentification
    """
    try:
        return {
            "admin_password": st.secrets.get("ADMIN_PASSWORD", "admin123"),
            "session_timeout": st.secrets.get("SESSION_TIMEOUT", 3600),  # 1 heure par défaut
            "protected_pages": [
                "7_Facturation.py",
                "8_Gestion_Factures.py", 
                "9_Gestion_Clients.py"
            ]
        }
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération des secrets: {e}")
        # Configuration par défaut si secrets non disponibles
        return {
            "admin_password": "admin123",  # À CHANGER en production !
            "session_timeout": 3600,
            "protected_pages": [
                "7_Facturation.py",
                "8_Gestion_Factures.py", 
                "9_Gestion_Clients.py"
            ]
        }

def hash_password(password):
    """
    Hash un mot de passe avec SHA-256
    
    Args:
        password: Mot de passe en clair
    
    Returns:
        str: Mot de passe hashé
    """
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, expected_password):
    """
    Vérifie un mot de passe
    
    Args:
        password: Mot de passe saisi
        expected_password: Mot de passe attendu
    
    Returns:
        bool: True si correct, False sinon
    """
    return password == expected_password

def is_authenticated():
    """
    Vérifie si l'utilisateur est authentifié
    
    Returns:
        bool: True si authentifié, False sinon
    """
    return st.session_state.get("authenticated", False)

def set_authenticated(status=True):
    """
    Définit le statut d'authentification
    
    Args:
        status: True pour connecté, False pour déconnecté
    """
    st.session_state["authenticated"] = status
    if status:
        st.session_state["auth_timestamp"] = st.session_state.get("auth_timestamp", None)
        logger.info("Utilisateur authentifié avec succès")
    else:
        st.session_state.pop("auth_timestamp", None)
        logger.info("Utilisateur déconnecté")

def logout():
    """
    Déconnecte l'utilisateur
    """
    set_authenticated(False)
    st.session_state.clear()
    st.success("✅ Déconnexion réussie")
    st.rerun()

def check_session_timeout():
    """
    Vérifie si la session a expiré
    
    Returns:
        bool: True si session valide, False si expirée
    """
    if not is_authenticated():
        return False
    
    auth_timestamp = st.session_state.get("auth_timestamp")
    if not auth_timestamp:
        return False
    
    import time
    config = get_auth_config()
    session_timeout = config["session_timeout"]
    
    if time.time() - auth_timestamp > session_timeout:
        logger.info("Session expirée")
        logout()
        return False
    
    return True

def login_form():
    """
    Affiche le formulaire de connexion
    
    Returns:
        bool: True si connexion réussie, False sinon
    """
    st.title("🔐 Authentification")
    st.info("Veuillez vous connecter pour accéder aux pages de gestion.")
    
    with st.form("login_form"):
        st.subheader("Connexion Administrateur")
        
        password = st.text_input("Mot de passe", type="password", help="Saisissez le mot de passe administrateur")
        
        login_button = st.form_submit_button("Se connecter", type="primary")
        
        if login_button:
            if password:
                config = get_auth_config()
                expected_password = config["admin_password"]
                
                if verify_password(password, expected_password):
                    import time
                    st.session_state["auth_timestamp"] = time.time()
                    set_authenticated(True)
                    st.success("✅ Connexion réussie!")
                    st.rerun()
                    return True
                else:
                    st.error("❌ Mot de passe incorrect")
                    logger.warning("Tentative de connexion avec mot de passe incorrect")
                    return False
            else:
                st.error("❌ Veuillez saisir un mot de passe")
                return False
    
    return False

def require_auth():
    """
    Décorateur pour protéger une page
    Utilisation: Appeler cette fonction au début d'une page protégée
    
    Returns:
        bool: True si accès autorisé, False sinon
    """
    # Vérifier si la session est encore valide
    if not check_session_timeout():
        if is_authenticated():
            st.warning("⏰ Votre session a expiré. Veuillez vous reconnecter.")
            logout()
        
        # Afficher le formulaire de connexion
        login_form()
        return False
    
    return True

def is_protected_page(page_name):
    """
    Vérifie si une page est protégée
    
    Args:
        page_name: Nom de la page
    
    Returns:
        bool: True si protégée, False sinon
    """
    config = get_auth_config()
    protected_pages = config["protected_pages"]
    
    # Vérifier si le nom de la page correspond à une page protégée
    for protected_page in protected_pages:
        if protected_page in page_name or page_name in protected_page:
            return True
    
    return False

def show_auth_status():
    """
    Affiche le statut d'authentification dans la sidebar
    """
    if is_authenticated():
        with st.sidebar:
            st.success("🔓 Connecté")
            if st.button("🚪 Se déconnecter", key="logout_btn"):
                logout()
    else:
        with st.sidebar:
            st.warning("🔒 Non connecté")
            st.info("Connexion requise pour:\n- Facturation\n- Gestion Factures\n- Gestion Clients")

def get_current_page():
    """
    Récupère le nom de la page actuelle
    
    Returns:
        str: Nom de la page
    """
    try:
        # Méthode pour récupérer la page actuelle dans Streamlit
        import inspect
        frame = inspect.currentframe()
        while frame:
            filename = frame.f_code.co_filename
            if 'pages/' in filename:
                return filename.split('pages/')[-1]
            frame = frame.f_back
        return "unknown"
    except:
        return "unknown"