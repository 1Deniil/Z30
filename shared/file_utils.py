import os
import json
import logging
from config.settings import LOCK_FILE

logger = logging.getLogger('shared.file_utils')

def create_lock_file():
    """Crée un fichier de verrouillage avec le PID actuel"""
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
            logger.info("Fichier de verrouillage existant supprimé")
        except OSError as e:
            logger.warning(f"Impossible de supprimer le fichier de verrouillage existant: {e}")
    
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except OSError as e:
        logger.error(f"Erreur lors de la création du fichier de verrouillage: {e}")
        return False

def remove_lock_file():
    """Supprime le fichier de verrouillage"""
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
            logger.info("Fichier de verrouillage supprimé")
        except OSError as e:
            logger.warning(f"Impossible de supprimer le fichier de verrouillage: {e}")

def load_json_file(file_path, default=None):
    """Charge un fichier JSON avec gestion d'erreur"""
    if default is None:
        default = {}
    
    if not os.path.exists(file_path):
        # Créer le fichier s'il n'existe pas
        save_json_file(file_path, default)
        return default
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Erreur lors du chargement du fichier {file_path}: {e}")
        return default

def save_json_file(file_path, data):
    """Sauvegarde des données dans un fichier JSON"""
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
        return True
    except OSError as e:
        logger.error(f"Erreur lors de la sauvegarde du fichier {file_path}: {e}")
        return False