"""
Script pour télécharger toutes les factures (PDF et Excel) depuis Supabase Storage
vers un dossier local, en évitant les doublons.

Usage:
    python utils/download_all_factures.py [chemin_destination]
    
Exemple:
    python utils/download_all_factures.py ~/Documents/Factures_AG
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from supabase import create_client, Client
import streamlit as st
import pandas as pd


def get_supabase_client() -> Client:
    """
    Initialise et retourne un client Supabase en utilisant st.secrets.
    """
    try:
        url = st.secrets['SUPABASE_URL']
        key = st.secrets['SUPABASE_KEY']
        return create_client(url, key)
    except Exception as e:
        print(f"❌ Erreur lors de la connexion à Supabase: {e}")
        print("Assurez-vous que le fichier .streamlit/secrets.toml existe et contient SUPABASE_URL et SUPABASE_KEY")
        sys.exit(1)


def list_all_factures_in_storage(supabase: Client):
    """
    Liste tous les fichiers de factures (PDF et Excel) disponibles dans le storage.
    
    Returns:
        list: Liste des noms de fichiers de factures (PDF et Excel uniquement)
    """
    try:
        result = supabase.storage.from_("factures").list()
        
        if result:
            # Filtrer pour ne garder que les factures PDF et Excel
            facture_files = [
                file['name'] for file in result 
                if file['name'].startswith('facture_') and 
                (file['name'].endswith('.pdf') or file['name'].endswith('.xlsx'))
            ]
            return facture_files
        else:
            return []
            
    except Exception as e:
        print(f"❌ Erreur lors du listage des fichiers: {e}")
        return []


def download_facture(supabase: Client, filename: str, destination_folder: Path):
    """
    Télécharge un fichier de facture depuis le storage vers le dossier de destination.
    
    Args:
        supabase: Client Supabase
        filename: Nom du fichier à télécharger
        destination_folder: Chemin du dossier de destination
    
    Returns:
        bool: True si téléchargement réussi, False sinon
    """
    destination_path = destination_folder / filename
    
    # Vérifier si le fichier existe déjà localement
    if destination_path.exists():
        print(f"⏭️  Fichier déjà présent: {filename}")
        return True
    
    try:
        # Télécharger le fichier depuis Supabase
        result = supabase.storage.from_("factures").download(filename)
        
        if result:
            # Écrire le fichier localement
            with open(destination_path, 'wb') as f:
                f.write(result)
            print(f"✅ Téléchargé: {filename}")
            return True
        else:
            print(f"❌ Échec du téléchargement: {filename}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du téléchargement de {filename}: {e}")
def export_tables_to_csv(supabase: Client, destination_folder: Path):
    """
    Exporte les tables 'factures' et 'ligne_facture' depuis Supabase vers des fichiers CSV.
    
    Args:
        supabase: Client Supabase
        destination_folder: Chemin du dossier de destination
    
    Returns:
        dict: Résultats de l'export avec les noms de fichiers créés
    """
    try:
        # Générer le timestamp pour les noms de fichiers
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"\n{'='*60}")
        print(f"📊 Export des tables vers CSV...")
        print(f"{'='*60}")
        
        results = {
            "success": True,
            "files": [],
            "errors": []
        }
        
        # Export table 'factures'
        print(f"🔄 Export de la table 'factures'...")
        try:
            response = supabase.table('factures').select('*').execute()
            if response.data:
                df_factures = pd.DataFrame(response.data)
                filename_factures = f"factures_{timestamp}.csv"
                filepath_factures = destination_folder / filename_factures
                df_factures.to_csv(filepath_factures, index=False, encoding='utf-8')
                results["files"].append(filename_factures)
                print(f"✅ Exporté: {filename_factures} ({len(df_factures)} lignes)")
            else:
                print(f"⚠️  Table 'factures' vide")
        except Exception as e:
            error_msg = f"Erreur export 'factures': {e}"
            results["errors"].append(error_msg)
            print(f"❌ {error_msg}")
        
        # Export table 'ligne_facture'
        print(f"🔄 Export de la table 'ligne_facture'...")
        try:
            response = supabase.table('ligne_facture').select('*').execute()
            if response.data:
                df_lignes = pd.DataFrame(response.data)
                filename_lignes = f"ligne_facture_{timestamp}.csv"
                filepath_lignes = destination_folder / filename_lignes
                df_lignes.to_csv(filepath_lignes, index=False, encoding='utf-8')
                results["files"].append(filename_lignes)
                print(f"✅ Exporté: {filename_lignes} ({len(df_lignes)} lignes)")
            else:
                print(f"⚠️  Table 'ligne_facture' vide")
        except Exception as e:
            error_msg = f"Erreur export 'ligne_facture': {e}"
            results["errors"].append(error_msg)
            print(f"❌ {error_msg}")
        
        if results["errors"]:
            results["success"] = False
        
        return results
        
    except Exception as e:
        return {
            "success": False,
            "files": [],
            "errors": [f"Erreur générale export CSV: {e}"]
        }


def upload_pdf_to_storage(supabase: Client, pdf_path: Path):
    """
    Upload un fichier PDF vers Supabase Storage.
    
    Args:
        supabase: Client Supabase
        pdf_path: Chemin du fichier PDF à uploader
    
    Returns:
        bool: True si upload réussi, False sinon
    """
    try:
        # Lire le fichier PDF
        with open(pdf_path, 'rb') as f:
            file_content = f.read()
        
        # Upload vers Supabase Storage
        result = supabase.storage.from_("factures").upload(
            path=pdf_path.name,
            file=file_content
        )
        
        if result:
            print(f"✅ Uploadé vers Supabase: {pdf_path.name}")
            return True
        else:
            print(f"❌ Échec upload: {pdf_path.name}")
            return False
            
    except Exception as e:
        # Gérer le cas où le fichier existe déjà
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print(f"⏭️  Déjà dans Supabase: {pdf_path.name}")
            return True
        else:
            print(f"❌ Erreur upload {pdf_path.name}: {e}")
            return False


def convert_excel_to_pdf_mac(excel_path: Path, pdf_path: Path):
    """
    Convertit un fichier Excel en PDF sur macOS en utilisant LibreOffice.
    Conserve la mise en forme du fichier Excel.
    
    Args:
        excel_path: Chemin du fichier Excel source
        pdf_path: Chemin du fichier PDF de destination
    
    Returns:
        bool: True si conversion réussie, False sinon
    """
    try:
        # Vérifier que LibreOffice est installé
        libreoffice_paths = [
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            "/usr/local/bin/soffice",
            "/opt/homebrew/bin/soffice"
        ]
        
        soffice_path = None
        for path in libreoffice_paths:
            if os.path.exists(path):
                soffice_path = path
                break
        
        if not soffice_path:
            print(f"⚠️  LibreOffice non trouvé. Installation requise pour convertir en PDF.")
            print(f"   Installez avec: brew install --cask libreoffice")
            return False
        
        # Convertir en PDF avec LibreOffice
        # --headless : mode sans interface
        # --convert-to pdf : format de sortie
        # --outdir : dossier de destination
        result = subprocess.run(
            [
                soffice_path,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(pdf_path.parent),
                str(excel_path)
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and pdf_path.exists():
            return True
        else:
            print(f"⚠️  Erreur conversion: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⚠️  Timeout lors de la conversion de {excel_path.name}")
        return False
    except Exception as e:
        print(f"⚠️  Erreur lors de la conversion: {e}")
        return False


def download_all_factures(destination_folder: str):
    """
    Télécharge toutes les factures (PDF et Excel) depuis Supabase Storage
    vers le dossier de destination spécifié.
    Convertit les fichiers Excel en PDF si le PDF n'existe pas.
    
    Args:
        destination_folder: Chemin du dossier où enregistrer les factures
    
    Returns:
        dict: Statistiques du téléchargement
    """
    # Convertir en Path et créer le dossier si nécessaire
    dest_path = Path(destination_folder).expanduser().resolve()
    dest_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📁 Dossier de destination: {dest_path}")
    print(f"🔄 Connexion à Supabase...")
    
    # Initialiser le client Supabase
    supabase = get_supabase_client()
    
    print(f"📋 Récupération de la liste des factures...")
    
    # Lister tous les fichiers de factures
    facture_files = list_all_factures_in_storage(supabase)
    
    if not facture_files:
        print("ℹ️  Aucune facture trouvée dans le storage.")
        return {
            "total": 0,
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
            "converted": 0,
            "uploaded": 0
        }
    
    print(f"\n📊 {len(facture_files)} facture(s) trouvée(s) dans le storage")
    print(f"{'='*60}")
    
    # Statistiques
    stats = {
        "total": len(facture_files),
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "converted": 0,
        "uploaded": 0
    }
    
    # Télécharger chaque fichier
    for filename in sorted(facture_files):
        dest_file = dest_path / filename
        
        if dest_file.exists():
            stats["skipped"] += 1
            print(f"⏭️  Déjà présent: {filename}")
        else:
            success = download_facture(supabase, filename, dest_path)
            if success:
                stats["downloaded"] += 1
            else:
                stats["failed"] += 1
    
    # Convertir les fichiers Excel en PDF si le PDF n'existe pas
    print(f"\n{'='*60}")
    print(f"📄 Conversion des fichiers Excel en PDF...")
    print(f"{'='*60}")
    
    excel_files = list(dest_path.glob("facture_*.xlsx"))
    
    for excel_file in sorted(excel_files):
        # Construire le nom du fichier PDF correspondant
        pdf_filename = excel_file.stem + ".pdf"
        pdf_path = dest_path / pdf_filename
        
        # Vérifier si le PDF existe déjà
        if pdf_path.exists():
            print(f"⏭️  PDF déjà présent: {pdf_filename}")
            continue
        
        # Convertir Excel en PDF
        print(f"🔄 Conversion: {excel_file.name} → {pdf_filename}")
        success = convert_excel_to_pdf_mac(excel_file, pdf_path)
        
        if success:
            stats["converted"] += 1
            print(f"✅ Converti: {pdf_filename}")
        else:
            print(f"❌ Échec conversion: {excel_file.name}")
    
    # Upload des PDF locaux vers Supabase si absents du storage
    print(f"\n{'='*60}")
    print(f"☁️  Upload des PDF manquants vers Supabase...")
    print(f"{'='*60}")
    
    # Lister tous les PDF locaux
    local_pdf_files = list(dest_path.glob("facture_*.pdf"))
    
    # Créer un set des fichiers PDF dans Supabase pour recherche rapide
    storage_pdf_files = set(f for f in facture_files if f.endswith('.pdf'))
    
    for local_pdf in sorted(local_pdf_files):
        # Vérifier si le PDF existe dans Supabase
        if local_pdf.name not in storage_pdf_files:
            print(f"🔄 Upload vers Supabase: {local_pdf.name}")
            success = upload_pdf_to_storage(supabase, local_pdf)
            if success:
                stats["uploaded"] += 1
        else:
            print(f"⏭️  Déjà dans Supabase: {local_pdf.name}")
    
    # Afficher le résumé
    print(f"\n{'='*60}")
    print(f"📊 RÉSUMÉ - SYNCHRONISATION FACTURES")
    print(f"{'='*60}")
    print(f"  Total de factures:      {stats['total']}")
    print(f"  ✅ Téléchargées:        {stats['downloaded']}")
    print(f"  ⏭️  Déjà présentes:      {stats['skipped']}")
    print(f"  📄 Converties en PDF:   {stats['converted']}")
    print(f"  ☁️  Uploadées:           {stats['uploaded']}")
    print(f"  ❌ Échecs:              {stats['failed']}")
    print(f"{'='*60}\n")
    
    # Export des tables vers CSV
    csv_results = export_tables_to_csv(supabase, dest_path)
    
    if csv_results["success"]:
        print(f"✅ Export CSV réussi:")
        for file in csv_results["files"]:
            print(f"   📄 {file}")
    else:
        print(f"⚠️  Export CSV avec erreurs:")
        for error in csv_results["errors"]:
            print(f"   ❌ {error}")
    
    stats["csv_exported"] = csv_results["files"]
    stats["csv_errors"] = csv_results["errors"]
    
    return stats


def main():
    """
    Point d'entrée principal du script.
    """
    # Vérifier les arguments
    if len(sys.argv) > 1:
        destination = sys.argv[1]
    else:
        # Dossier par défaut
        destination = "/Users/sajidasarumugadas/Library/CloudStorage/OneDrive-Personnel/sarl ASD/Compta/2025/Factures_emises"
        print(f"ℹ️  Aucun dossier spécifié, utilisation du dossier par défaut: {destination}")
        print(f"💡 Usage: python utils/download_all_factures.py [chemin_destination]\n")
    
    try:
        stats = download_all_factures(destination)
        
        # Code de sortie selon les résultats
        if stats["failed"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Téléchargement interrompu par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
