import logging
import sys
from datetime import datetime
import os
from config.settings import LOGS_DIR

def setup_logger(name, level=logging.INFO, log_to_file=True, log_file=None):
    """Configure un logger avec sortie console et optionnellement fichier"""
    logger = logging.getLogger(name)
    
    # Éviter les handlers dupliqués
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    
    # Format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                                 '%Y-%m-%d %H:%M:%S')
    
    # Handler console
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    # Handler fichier (optionnel)
    if log_to_file:
        if not log_file:
            date_str = datetime.now().strftime('%Y-%m-%d')
            log_file = os.path.join(LOGS_DIR, f"{date_str}_{name}.log")
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logger.info(f"Logger {name} configuré")
    return logger