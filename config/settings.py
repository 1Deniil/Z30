import os
from pathlib import Path

# Chemins relatifs du projet
ROOT_DIR = Path(__file__).parent.parent
Z30_SCRIPT_PATH = str(ROOT_DIR / "z30.py")
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"

# Créer les répertoires nécessaires
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Fichiers de données
SHORTCUTS_FILE = str(DATA_DIR / "shortcuts.json")
USER_SHORTCUTS_FILE = str(DATA_DIR / "user_shortcuts.json")
LOCK_FILE = str(DATA_DIR / "z30_running.lock")

# Fichiers de logs
MINECRAFT_LOG_FILE = str(LOGS_DIR / "latest.log")
DISCORD_LOG_FILE = str(LOGS_DIR / "bot.log")

# Client Minecraft
MINECRAFT_CLIENT_PATH = "MinecraftClient.exe"
BOT_USERNAME = "ourbot"

# Paramètres de message
MESSAGE_COOLDOWN = 1.0  # secondes entre chaque message

# Serveur Webhook (pour la communication Discord)
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000

# Discord Bot
GUILD_ID = 1328865920910626916  # DECENT
CHANNEL_ID = 1328955672955453461
LOG_CHANNEL_ID = 1328955672955453461
ONLINE_USERS_CHANNEL_ID = 1328958286392856576
ADMIN_ROLE_IDS = [
    1328870797955301416,  # ADMIN
    1351734093049761873   # OFFI
]

# Préfixes et constantes
TIMING_PREFIX = "[TIMING] "

# Mapping couleurs Minecraft vers ANSI
COLOR_MAPPING = {
    '§0': '\033[0;30m',  # Black
    '§1': '\033[0;34m',  # Dark Blue
    '§2': '\033[0;32m',  # Dark Green
    '§3': '\033[0;35m',  # Dark Aqua
    '§4': '\033[0;31m',  # Dark Red
    '§5': '\033[0;35m',  # Dark Purple
    '§6': '\033[0;33m',  # Gold
    '§7': '\033[0;37m',  # Gray
    '§8': '\033[0;90m',  # Dark Gray
    '§9': '\033[0;94m',  # Blue
    '§a': '\033[0;32m',  # Green
    '§b': '\033[0;34m',  # Aqua
    '§c': '\033[0;91m',  # Red
    '§d': '\033[0;95m',  # Light Purple
    '§e': '\033[0;93m',  # Yellow
    '§f': '\033[0;97m',  # White
    '§r': '\033[0m',     # Reset
}