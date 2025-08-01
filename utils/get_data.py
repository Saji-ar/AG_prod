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