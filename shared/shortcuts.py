import logging
import re
from shared.file_utils import load_json_file, save_json_file
from config.settings import SHORTCUTS_FILE, USER_SHORTCUTS_FILE

logger = logging.getLogger('shared.shortcuts')

class ShortcutManager:
    """Gestionnaire des raccourcis de commandes et alias utilisateurs"""
    
    def __init__(self):
        self.shortcuts = load_json_file(SHORTCUTS_FILE, {})
        self.user_shortcuts = load_json_file(USER_SHORTCUTS_FILE, {})
    
    # --- Raccourcis de commandes ---
    
    def save_shortcut(self, sender, shortcut_name, shortcut_command):
        """Sauvegarde un raccourci de commande"""
        if sender not in self.shortcuts:
            self.shortcuts[sender] = {}
            
        self.shortcuts[sender][shortcut_name] = shortcut_command
        return save_json_file(SHORTCUTS_FILE, self.shortcuts)
    
    def load_shortcut(self, sender, shortcut_name):
        """Charge un raccourci de commande"""
        return self.shortcuts.get(sender, {}).get(shortcut_name)
    
    def delete_shortcut(self, sender, shortcut_name):
        """Supprime un raccourci de commande"""
        if sender in self.shortcuts and shortcut_name in self.shortcuts[sender]:
            del self.shortcuts[sender][shortcut_name]
            
            # Supprimer le sender s'il n'a plus de raccourcis
            if not self.shortcuts[sender]:
                del self.shortcuts[sender]
                
            return save_json_file(SHORTCUTS_FILE, self.shortcuts)
        return False
    
    def list_shortcuts(self, sender):
        """Liste tous les raccourcis d'un utilisateur"""
        return self.shortcuts.get(sender, {})
    
    # --- Alias utilisateurs ---
    
    def save_user_shortcut(self, sender, actual_username, aliases):
        """Sauvegarde des alias pour un utilisateur"""
        if sender not in self.user_shortcuts:
            self.user_shortcuts[sender] = {}
        
        # Supprimer les alias existants pour cet utilisateur
        self.user_shortcuts[sender] = {
            k: v for k, v in self.user_shortcuts[sender].items()
            if v.lower() != actual_username.lower()
        }
        
        # Ajouter les nouveaux alias
        for alias in aliases:
            self.user_shortcuts[sender][alias.lower()] = actual_username.lower()
        
        return save_json_file(USER_SHORTCUTS_FILE, self.user_shortcuts)
    
    def load_user_shortcuts(self, sender):
        """Charge tous les alias d'un utilisateur"""
        return self.user_shortcuts.get(sender, {})
    
    def delete_user_shortcut(self, sender, alias):
        """Supprime un alias utilisateur"""
        if sender in self.user_shortcuts and alias.lower() in self.user_shortcuts[sender]:
            del self.user_shortcuts[sender][alias.lower()]
            return save_json_file(USER_SHORTCUTS_FILE, self.user_shortcuts)
        return False
    
    def delete_all_user_shortcuts(self, sender, actual_username):
        """Supprime tous les alias pour un utilisateur donné"""
        if sender in self.user_shortcuts:
            original_length = len(self.user_shortcuts[sender])
            self.user_shortcuts[sender] = {
                k: v for k, v in self.user_shortcuts[sender].items()
                if v.lower() != actual_username.lower()
            }
            new_length = len(self.user_shortcuts[sender])
            
            if original_length != new_length:
                return save_json_file(USER_SHORTCUTS_FILE, self.user_shortcuts)
        
        return False
    
    def resolve_username(self, sender, username):
        """Résout un alias en nom d'utilisateur réel"""
        shortcuts = self.load_user_shortcuts(sender)
        return shortcuts.get(username.lower(), username)