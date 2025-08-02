# 🔐 Système d'Authentification

## Vue d'ensemble

Le système d'authentification protège l'accès aux pages sensibles de l'application :
- **💰 Facturation**
- **🧾 Gestion Factures** 
- **👥 Gestion Clients**

Les autres pages restent librement accessibles.

## Configuration

### 1. Fichier de secrets

Créez le fichier `.streamlit/secrets.toml` basé sur l'exemple :

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

### 2. Configuration du mot de passe

Éditez `.streamlit/secrets.toml` et remplacez le mot de passe par défaut :

```toml
ADMIN_PASSWORD = "votre_mot_de_passe_super_secret"
SESSION_TIMEOUT = 3600  # 1 heure en secondes
```

⚠️ **Important** : Utilisez un mot de passe fort et unique !

## Utilisation

### Pour les utilisateurs

1. **Accès libre** : Toutes les pages de gestion quotidienne sont accessibles sans connexion
2. **Connexion** : Cliquez sur une page protégée et saisissez le mot de passe
3. **Session** : Une fois connecté, l'accès reste actif pendant 1 heure
4. **Déconnexion** : Bouton "Se déconnecter" dans la barre latérale

### Pour les développeurs

```python
from utils.auth import require_auth, show_auth_status

# Protéger une page
if not require_auth():
    st.stop()

# Afficher le statut dans la sidebar
show_auth_status()
```

## Sécurité

### Fonctionnalités implémentées

- ✅ **Mot de passe sécurisé** stocké dans st.secrets
- ✅ **Session timeout** configurable (défaut: 1 heure)
- ✅ **Protection des pages sensibles** automatique
- ✅ **Interface utilisateur** claire avec statut visible
- ✅ **Logging** des tentatives de connexion
- ✅ **Code public** sans exposition des secrets

### Bonnes pratiques

1. **Mot de passe fort** : Minimum 12 caractères avec chiffres et symboles
2. **Rotation régulière** : Changez le mot de passe périodiquement
3. **Secrets protégés** : Le fichier secrets.toml est dans .gitignore
4. **Session limitée** : Timeout automatique après inactivité

## Architecture

### Fichiers du système d'authentification

- `utils/auth.py` - Logique d'authentification principale
- `.streamlit/secrets.toml` - Configuration des secrets (non versionné)
- `.streamlit/secrets.toml.example` - Exemple de configuration
- `app.py` - Page d'accueil avec statut d'authentification

### Pages protégées

Les pages suivantes incluent automatiquement la vérification :
- `pages/7_Facturation.py`
- `pages/8_Gestion_Factures.py`
- `pages/9_Gestion_Clients.py`

## Déploiement

### Streamlit Cloud

1. Ajoutez les secrets dans l'interface Streamlit Cloud
2. Configurez `ADMIN_PASSWORD` et `SESSION_TIMEOUT`
3. Les autres variables Supabase doivent déjà être configurées

### Déploiement local

1. Créez `.streamlit/secrets.toml` avec vos valeurs
2. Assurez-vous que le fichier n'est pas versionné
3. Lancez l'application normalement

## Dépannage

### Problèmes courants

**"Mot de passe incorrect"**
- Vérifiez le contenu de `.streamlit/secrets.toml`
- Assurez-vous qu'il n'y a pas d'espaces en trop

**"Session expirée"**
- Reconnectez-vous avec le mot de passe
- Augmentez `SESSION_TIMEOUT` si nécessaire

**"Secrets non trouvés"**
- Vérifiez que `.streamlit/secrets.toml` existe
- Redémarrez l'application Streamlit

### Logs

Les tentatives de connexion sont enregistrées dans les logs de l'application.

## Extension future

Le système est conçu pour être facilement extensible :
- Ajout d'utilisateurs multiples
- Intégration avec Supabase Auth
- Gestion des rôles et permissions
- Authentification par API key