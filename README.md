# Tableau de bord Pâtisserie

Cette application Streamlit permet de gérer la production, le stock et divers relevés pour une pâtisserie. Les données sont stockées dans une instance Supabase et peuvent être synchronisées avec des feuilles Google Sheets.

## Lancer l'application

1. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
2. Définissez les variables d'environnement ou le fichier `secrets.toml` pour Streamlit :
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `gcp_service_account` (clé du compte de service pour Google Sheets)
3. Exécutez Streamlit :
   ```bash
   streamlit run app.py
   ```

## Organisation du dépôt

- `app.py` : page d'accueil Streamlit.
- `pages/` : modules Streamlit pour chaque fonctionnalité.
- `utils/google_sheets.py` : utilitaires de lecture des feuilles Google.
- Fichiers `.xlsx` : exemples de données hors ligne.
- `service_account.json` : **clé Google** utilisée pour accéder aux Sheets (à ne pas partager publiquement).

## Structure de la base Supabase

Les principales tables utilisées sont :

| Table                | Champs clés                                                                                          |
|----------------------|------------------------------------------------------------------------------------------------------|
| `produits`           | `nom`, `sous_categories` (liste), `dispo` (liste), `prix`, `description`, `allergenes`, `permanent`    |
| `Stock`              | `date`, `produit`, `sous_categorie`, `quantite`                                                      |
| `Prod`               | `date`, `produit`, `sous_categorie`, `quantite`                                                      |
| `Retrait`            | `produit`, `sous_categorie`, `quantite`, `date_de_retrait`, `date_de_production`, `raison`            |
| `chambres`           | `id`, `nom`, `type`, `actif`, `emplacement`, ...                                                     |
| `releves_temperature`| `chambre_id`, `date`, `moment_journee`, `temperature`, `utilisateur`, `commentaire`, `created_at` ... |

Ces tables servent au suivi quotidien de la production, des retraits de produits invendus, et des relevés de température des chambres froides.

## Exemples de feuilles Excel

Les fichiers `production.xlsx`, `stock_boutique.xlsx` et `retrait.xlsx` contiennent un exemple minimal de ces données :

- **production.xlsx** : `Produit`, `Quantité`, `Date`.
- **stock_boutique.xlsx** : `Produit`, `Quantité`, `Date`.
- **retrait.xlsx** : `Produit`, `Quantité`, `Date de retrait`, `Date de production`, `Raison`.
- **produits.xlsx** : `Nom`, `Description`, `Allergène`, `Prix`, `Sous-catégories`.

