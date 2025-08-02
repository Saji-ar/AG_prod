import pandas as pd
from supabase import create_client, Client
import streamlit as st

# Charger les clés Supabase depuis les secrets Streamlit
def get_supabase_client() -> Client:
    """
    Initialise et retourne un client Supabase en utilisant st.secrets.
    """
    url = st.secrets['SUPABASE_URL']
    key = st.secrets['SUPABASE_KEY']
    return create_client(url, key)

# Initialiser le client Supabase
supabase: Client = get_supabase_client()

def get_ref_products() -> pd.DataFrame:
    """
    Récupère tous les produits référencés pour facturation (table ref_facture).
    Retourne un DataFrame pandas avec les colonnes id, name, price, tva.
    """
    response = supabase.table('ref_facture').select('id, nom, prix, tva').execute()
    data = response.data or []
    df = pd.DataFrame(data)
    return df

def get_clients() : 
    response = supabase.table('clients').select('*').execute()
    data = response.data or []
    df = pd.DataFrame(data)
    return df

def upload_file_to_bucket(file_content: bytes, filename: str) -> dict:
    """
    Upload un fichier vers le bucket 'factures' de Supabase Storage.
    
    Args:
        file_content: Contenu du fichier en bytes
        filename: Nom du fichier avec extension
    
    Returns:
        dict: {"success": bool, "public_url": str, "error": str}
    """
    try:
        # Upload vers Supabase Storage
        result = supabase.storage.from_("factures").upload(
            path=filename,
            file=file_content
        )
        
        if result:
            # Obtenir l'URL publique
            public_url = supabase.storage.from_("factures").get_public_url(filename)
            
            return {
                "success": True,
                "public_url": public_url,
                "error": None
            }
        else:
            return {
                "success": False,
                "public_url": None,
                "error": "Upload failed"
            }
            
    except Exception as e:
        return {
            "success": False,
            "public_url": None,
            "error": str(e)
        }
def get_next_facture_number():
    from datetime import datetime
    
    current_year = datetime.now().year
    
    # Récupérer tous les num_facture et filtrer par année
    response = supabase.table('factures').select('num_facture').execute()
    
    # if not response.data:
    #     return f"{current_year}001"
    
    # Filtrer les factures de l'année courante
    current_year_factures = []
    has_current_year_factures = False
    for f in response.data:
        facture_num_str = str(f['num_facture'])
        if facture_num_str.startswith(str(current_year)):
            has_current_year_factures = True
            # Extraire les 3 derniers chiffres
            try:
                number = int(facture_num_str[-3:])
                current_year_factures.append(number)
            except ValueError:
                continue
    
    # Si c'est la première facture de l'année
    if not has_current_year_factures:
        return f"{current_year}001"
    
    # Sinon, prendre le numéro suivant
    if not current_year_factures:
        return f"{current_year}001"
    
    next_number = max(current_year_factures) + 1
    return f"{current_year}{next_number:03d}"
def insert_facture(num_facture: str, date: str, client_id: int, tot_ttc: float, tot_ht: float, date_prestation: str = None, paye: bool = False) -> dict:
   """
   Insère une nouvelle facture dans la table factures.
   
   Args:
       num_facture: Numéro de facture (ex: "2025001")
       date: Date de la facture (format: "YYYY-MM-DD")
       client_id: ID du client
       tot_ttc: Total TTC
       tot_ht: Total HT
       date_prestation: Date de prestation (optionnel)
       paye: Statut de paiement (défaut: False)
   
   Returns:
       dict: {"success": bool, "data": dict, "error": str}
   """
   try:
       response = supabase.table('factures').insert({
           "num_facture": num_facture,
           "date": date,
           "client": client_id,
           "tot_ttc": tot_ttc,
           "tot_ht": tot_ht,
           "date_prestation": date_prestation,
           "paye": paye
       }).execute()
       
       return {
           "success": True,
           "data": response.data[0] if response.data else None,
           "error": None
       }
       
   except Exception as e:
       return {
           "success": False,
           "data": None,
           "error": str(e)
       }
   
def insert_ligne_facture(num_facture, produit, quantite, prix_unitaire, tva):
    """
    Insère une ligne de facture dans la base de données
    
    Args:
        num_facture: Numéro de la facture
        produit: Nom du produit
        quantite: Quantité du produit
        prix_unitaire: Prix unitaire du produit
        tva: Taux de TVA (en décimal, ex: 0.20 pour 20%)
    
    Returns:
        dict: {"success": bool, "data": dict, "error": str}
    """
    try:
        result = supabase.table('ligne_facture').insert({
            'num_facture': num_facture,
            'produit': produit,
            'quantite': float(quantite),
            'prix_unitaire': float(prix_unitaire),
            'tva': float(tva)
        }).execute()
        
        return {
            "success": True,
            "data": result.data[0] if result.data else None,
            "error": None
        }
        
    except Exception as e:
        print(f"Erreur lors de l'insertion de la ligne facture: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }


def delete_facture_and_lines(num_facture):
    """
    Supprime une facture et toutes ses lignes associées en cas d'erreur
    
    Args:
        num_facture: Numéro de la facture à supprimer
    
    Returns:
        dict: {"success": bool, "error": str}
    """
    try:
        # Supprimer d'abord les lignes de facture
        lignes_result = supabase.table('ligne_facture').delete().eq('num_facture', num_facture).execute()
        
        # Puis supprimer la facture
        facture_result = supabase.table('factures').delete().eq('num_facture', num_facture).execute()
        
        print(f"Facture {num_facture} et ses lignes supprimées avec succès")
        return {
            "success": True,
            "error": None
        }
        
    except Exception as e:
        error_msg = f"Erreur lors de la suppression de la facture {num_facture}: {e}"
        print(error_msg)
        return {
            "success": False,
            "error": error_msg
        }

def save_product_changes_from_session(product_session_state, current_product_df):
    """
    Sauvegarde les modifications des produits en utilisant les données de session Streamlit
    
    Args:
        product_session_state: État de session du data_editor des produits
        current_product_df: DataFrame actuel des produits
    
    Returns:
        dict: {"success": bool, "changes": dict, "error": str}
    """
    try:
        changes = {
            "inserted": 0,
            "updated": 0,
            "deleted": 0,
            "details": []
        }
        
        # Debug: afficher les informations de session
        print(f"DEBUG: edited_rows: {product_session_state.get('edited_rows', {})}")
        print(f"DEBUG: added_rows: {product_session_state.get('added_rows', [])}")
        print(f"DEBUG: deleted_rows: {product_session_state.get('deleted_rows', [])}")
        print(f"DEBUG: DataFrame shape: {current_product_df.shape}")
        
        # Traiter les lignes modifiées
        for index, updates in product_session_state.get("edited_rows", {}).items():
            product_id = current_product_df.iloc[index]['id']
            update_data = {}
            
            for key, value in updates.items():
                if key == 'nom':
                    update_data['nom'] = value
                elif key == 'prix':
                    update_data['prix'] = float(value) if value else 0.0
                elif key == 'tva':
                    update_data['tva'] = float(value) if value else 0.0
            
            if update_data:
                result = supabase.table('ref_facture').update(update_data).eq('id', product_id).execute()
                changes["updated"] += 1
                changes["details"].append(f"Modifié produit ID {product_id}: {list(update_data.keys())}")
        
        # Traiter les nouvelles lignes ajoutées
        for new_row in product_session_state.get("added_rows", []):
            if new_row.get('nom') and new_row['nom'].strip():
                result = supabase.table('ref_facture').insert({
                    'nom': new_row['nom'],
                    'prix': float(new_row.get('prix', 0)) if new_row.get('prix') else 0.0,
                    'tva': float(new_row.get('tva', 0)) if new_row.get('tva') else 0.0
                }).execute()
                changes["inserted"] += 1
                changes["details"].append(f"Ajouté: {new_row['nom']}")
        
        # Traiter les lignes supprimées
        for deleted_index in product_session_state.get("deleted_rows", []):
            try:
                # Vérifier que l'index existe et que l'ID est valide
                if deleted_index < len(current_product_df):
                    row = current_product_df.iloc[deleted_index]
                    product_id = row.get('id')
                    product_name = row.get('nom', 'Produit inconnu')
                    
                    # Vérifier que l'ID existe et n'est pas vide
                    if product_id and pd.notna(product_id) and str(product_id).strip():
                        result = supabase.table('ref_facture').delete().eq('id', product_id).execute()
                        changes["deleted"] += 1
                        changes["details"].append(f"Supprimé: {product_name} (ID: {product_id})")
                    else:
                        changes["details"].append(f"Ligne {deleted_index}: Pas d'ID valide pour la suppression")
                else:
                    changes["details"].append(f"Index {deleted_index}: Hors limites du DataFrame")
            except Exception as e:
                changes["details"].append(f"Erreur suppression ligne {deleted_index}: {str(e)}")
        
        return {
            "success": True,
            "changes": changes,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "changes": None,
            "error": str(e)
        }

def get_all_factures():
    """
    Récupère toutes les factures actives avec les informations des clients
    
    Returns:
        pd.DataFrame: DataFrame avec les factures et informations clients
    """
    try:
        # Récupérer les factures avec jointure sur la table clients
        response = supabase.table('factures').select(
            'num_facture, date, client, tot_ttc, tot_ht, paye, date_prestation, clients!inner(nom)'
        ).eq('inactif', False).order('num_facture', desc=True).execute()
        
        data = response.data or []
        
        # Transformer les données pour un affichage plus facile
        factures_list = []
        for facture in data:
            factures_list.append({
                'num_facture': facture['num_facture'],
                'date': facture['date'],
                'client_id': facture['client'],
                'client_nom': facture['clients']['nom'] if facture['clients'] else 'Client inconnu',
                'date_prestation': facture['date_prestation'],
                'tot_ht': facture['tot_ht'],
                'tot_ttc': facture['tot_ttc'],
                'paye': facture['paye']
            })
        
        return pd.DataFrame(factures_list)
        
    except Exception as e:
        print(f"Erreur lors de la récupération des factures: {e}")
        return pd.DataFrame()

def update_facture_paiement(num_facture, paye_status):
    """
    Met à jour le statut de paiement d'une facture
    
    Args:
        num_facture: Numéro de la facture
        paye_status: True si payée, False sinon
    
    Returns:
        dict: {"success": bool, "error": str}
    """
    try:
        result = supabase.table('factures').update({
            'paye': paye_status
        }).eq('num_facture', num_facture).execute()
        
        return {
            "success": True,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def soft_delete_facture(num_facture):
    """
    Marque une facture comme inactive (suppression logique)
    
    Args:
        num_facture: Numéro de la facture à désactiver
    
    Returns:
        dict: {"success": bool, "error": str}
    """
    try:
        result = supabase.table('factures').update({
            'inactif': True
        }).eq('num_facture', num_facture).execute()
        
        return {
            "success": True,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_factures_filtered(client_nom=None, date_debut=None, date_fin=None):
    """
    Récupère les factures avec filtres
    
    Args:
        client_nom: Nom du client (optionnel)
        date_debut: Date de début (optionnel)
        date_fin: Date de fin (optionnel)
    
    Returns:
        pd.DataFrame: DataFrame filtré des factures
    """
    try:
        # Requête de base avec jointure
        query = supabase.table('factures').select(
            'num_facture, date, client, tot_ttc, tot_ht, paye, date_prestation, clients!inner(nom)'
        ).eq('inactif', False)
        
        # Filtrer par date si spécifié
        if date_debut:
            query = query.gte('date', date_debut.strftime('%Y-%m-%d'))
        if date_fin:
            query = query.lte('date', date_fin.strftime('%Y-%m-%d'))
        
        response = query.order('num_facture', desc=True).execute()
        data = response.data or []
        
        # Transformer les données
        factures_list = []
        for facture in data:
            client_nom_facture = facture['clients']['nom'] if facture['clients'] else 'Client inconnu'
            
            # Filtrer par nom client si spécifié
            if client_nom and client_nom.lower() not in client_nom_facture.lower():
                continue
                
            factures_list.append({
                'num_facture': facture['num_facture'],
                'date': facture['date'],
                'client_id': facture['client'],
                'client_nom': client_nom_facture,
                'date_prestation': facture['date_prestation'],
                'tot_ht': facture['tot_ht'],
                'tot_ttc': facture['tot_ttc'],
                'paye': facture['paye']
            })
        
        return pd.DataFrame(factures_list)
        
    except Exception as e:
        print(f"Erreur lors de la récupération des factures filtrées: {e}")
        return pd.DataFrame()

def download_facture_from_storage(num_facture):
    """
    Télécharge une facture depuis le bucket Supabase Storage
    
    Args:
        num_facture: Numéro de la facture
    
    Returns:
        dict: {"success": bool, "data": bytes, "filename": str, "error": str}
    """
    try:
        # Nom du fichier dans le storage (format à adapter selon votre convention)
        filename = f"facture_{num_facture}.pdf"
        
        # Télécharger le fichier depuis le bucket 'factures'
        result = supabase.storage.from_("factures").download(filename)
        
        if result:
            return {
                "success": True,
                "data": result,
                "filename": filename,
                "error": None
            }
        else:
            return {
                "success": False,
                "data": None,
                "filename": None,
                "error": "Fichier non trouvé dans le storage"
            }
            
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "filename": None,
            "error": str(e)
        }

def list_factures_in_storage():
    """
    Liste tous les fichiers de factures disponibles dans le storage
    
    Returns:
        dict: {"success": bool, "files": list, "error": str}
    """
    try:
        # Lister les fichiers dans le bucket 'factures'
        result = supabase.storage.from_("factures").list()
        
        if result:
            # Filtrer pour ne garder que les fichiers PDF de factures
            facture_files = [
                file for file in result 
                if file['name'].startswith('facture_') and file['name'].endswith('.pdf')
            ]
            
            return {
                "success": True,
                "files": facture_files,
                "error": None
            }
        else:
            return {
                "success": True,
                "files": [],
                "error": None
            }
            
    except Exception as e:
        return {
            "success": False,
            "files": [],
            "error": str(e)
        }

def check_facture_exists_in_storage(num_facture):
    """
    Vérifie si une facture existe dans le storage
    
    Args:
        num_facture: Numéro de la facture
    
    Returns:
        bool: True si le fichier existe, False sinon
    """
    try:
        filename = f"facture_{num_facture}.pdf"
        
        # Lister les fichiers et vérifier la présence
        result = supabase.storage.from_("factures").list()
        
        if result:
            filenames = [file['name'] for file in result]
            return filename in filenames
        
        return False
        
    except Exception as e:
        print(f"Erreur lors de la vérification d'existence: {e}")
        return False

def add_client(nom, adresse_1=None, adresse_2=None, telephone=None):
    """
    Ajoute un nouveau client dans la base de données
    
    Args:
        nom: Nom du client (obligatoire)
        adresse_1: Première ligne d'adresse (optionnel)
        adresse_2: Deuxième ligne d'adresse (optionnel)
        telephone: Numéro de téléphone (optionnel)
    
    Returns:
        dict: {"success": bool, "data": dict, "error": str}
    """
    try:
        # Vérifier que le nom n'est pas vide
        if not nom or not nom.strip():
            return {
                "success": False,
                "data": None,
                "error": "Le nom du client est obligatoire"
            }
        
        # Préparer les données (sans ID car auto-généré)
        client_data = {
            'nom': nom.strip(),
            'adresse_1': adresse_1.strip() if adresse_1 else None,
            'adresse_2': adresse_2.strip() if adresse_2 else None,
            'telephone': telephone.strip() if telephone else None
        }
        
        # Nettoyer les valeurs None/vides
        client_data = {k: v for k, v in client_data.items() if v is not None and v != ""}
        
        # Insérer le nouveau client
        result = supabase.table('clients').insert(client_data).execute()
        
        return {
            "success": True,
            "data": result.data[0] if result.data else None,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }

def update_client(client_id, nom=None, adresse_1=None, adresse_2=None, telephone=None):
    """
    Met à jour les informations d'un client
    
    Args:
        client_id: ID du client à modifier
        nom: Nouveau nom du client (optionnel)
        adresse_1: Nouvelle première ligne d'adresse (optionnel)
        adresse_2: Nouvelle deuxième ligne d'adresse (optionnel)
        telephone: Nouveau numéro de téléphone (optionnel)
    
    Returns:
        dict: {"success": bool, "data": dict, "error": str}
    """
    try:
        # Préparer les données à mettre à jour
        update_data = {}
        
        if nom is not None:
            if not nom.strip():
                return {
                    "success": False,
                    "data": None,
                    "error": "Le nom du client ne peut pas être vide"
                }
            update_data['nom'] = nom.strip()
        
        if adresse_1 is not None:
            update_data['adresse_1'] = adresse_1.strip() if adresse_1.strip() else None
        
        if adresse_2 is not None:
            update_data['adresse_2'] = adresse_2.strip() if adresse_2.strip() else None
        
        if telephone is not None:
            update_data['telephone'] = telephone.strip() if telephone.strip() else None
        
        # Vérifier qu'il y a au moins une donnée à mettre à jour
        if not update_data:
            return {
                "success": False,
                "data": None,
                "error": "Aucune donnée à mettre à jour"
            }
        
        # Mettre à jour le client
        result = supabase.table('clients').update(update_data).eq('id', client_id).execute()
        
        return {
            "success": True,
            "data": result.data[0] if result.data else None,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }

def delete_client(client_id):
    """
    Supprime un client de la base de données
    ATTENTION: Vérifier avant qu'il n'a pas de factures associées
    
    Args:
        client_id: ID du client à supprimer
    
    Returns:
        dict: {"success": bool, "error": str}
    """
    try:
        # Vérifier s'il y a des factures associées
        factures_response = supabase.table('factures').select('num_facture').eq('client', client_id).execute()
        
        if factures_response.data:
            return {
                "success": False,
                "error": f"Impossible de supprimer: {len(factures_response.data)} facture(s) associée(s) à ce client"
            }
        
        # Supprimer le client
        result = supabase.table('clients').delete().eq('id', client_id).execute()
        
        return {
            "success": True,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_client_details(client_id):
    """
    Récupère les détails complets d'un client
    
    Args:
        client_id: ID du client
    
    Returns:
        dict: {"success": bool, "data": dict, "error": str}
    """
    try:
        result = supabase.table('clients').select('*').eq('id', client_id).execute()
        
        if result.data:
            return {
                "success": True,
                "data": result.data[0],
                "error": None
            }
        else:
            return {
                "success": False,
                "data": None,
                "error": "Client non trouvé"
            }
        
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }

def search_clients(search_term=None):
    """
    Recherche des clients par nom
    
    Args:
        search_term: Terme de recherche (optionnel)
    
    Returns:
        pd.DataFrame: DataFrame des clients trouvés
    """
    try:
        if search_term:
            # Recherche avec filtre sur le nom
            response = supabase.table('clients').select('*').ilike('nom', f'%{search_term}%').order('nom').execute()
        else:
            # Récupérer tous les clients
            response = supabase.table('clients').select('*').order('nom').execute()
        
        data = response.data or []
        return pd.DataFrame(data)
        
    except Exception as e:
        print(f"Erreur lors de la recherche de clients: {e}")
        return pd.DataFrame()