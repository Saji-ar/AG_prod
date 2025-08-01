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
    
    if not response.data:
        return f"{current_year}001"
    
    # Filtrer les factures de l'année courante
    current_year_factures = [
        int(str(f['num_facture'])[-3:]) 
        for f in response.data 
        if str(f['num_facture']).startswith(str(current_year))
    ]
    
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