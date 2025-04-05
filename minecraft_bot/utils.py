import re
import logging
import psutil
import os
import time
from queue import Queue
import threading

from config.settings import LOCK_FILE

logger = logging.getLogger('minecraft_bot.utils')

def is_process_running():
    """Checks if another instance of the bot is already running"""
    current_process = psutil.Process(os.getpid())
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == current_process.name() and proc.info['cmdline'] == current_process.cmdline():
                if proc.pid != current_process.pid:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def check_log_file(log_file_path, minecraft_client):
    """Monitors the log file for disconnection events"""
    pattern = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} (Connection has been lost\.|Login failed :)')
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as log_file:
            log_file.seek(0, os.SEEK_END)
            
            while True:
                line = log_file.readline().strip()
                if not line:
                    time.sleep(0.1)
                    continue
                
                match = pattern.match(line)
                if match:
                    logger.info(f"Detected message: {match.group(1)}. Initiating shutdown.")
                    
                    try:
                        minecraft_client.send_chat_message("/gc Connection lost. Quitting...")
                    except Exception as e:
                        logger.error(f"Error sending quit message: {e}")
                    
                    try:
                        minecraft_client.send_command('/quit')
                        time.sleep(1)
                    except Exception as e:
                        logger.error(f"Error sending /quit command: {e}")
                    
                    minecraft_client.stop()
                    
                    # Restart the script
                    script_path = os.path.abspath(__file__)
                    command = f'start cmd /c "{script_path}"'
                    os.system(command)
                    
                    os._exit(0)
    
    except FileNotFoundError:
        logger.error(f"The file {log_file_path} was not found.")
    except Exception as e:
        logger.error(f"An error occurred in check_log_file: {e}")

class OnlinePlayersTracker:
    """Tracks and manages online players information"""
    
    def __init__(self, minecraft_client):
        self.minecraft_client = minecraft_client
        self.last_online_members = []
        self.running = False
        self.thread = None
    
    def start(self):
        """Starts tracking online players"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._gonline_loop, daemon=True)
        self.thread.start()
        logger.info("Online players tracker started")
    
    def stop(self):
        """Stops tracking online players"""
        self.running = False
        logger.info("Online players tracker stopped")
    
    def _gonline_loop(self):
        """Main loop for periodically checking online players"""
        log_file_path = 'latest.log'
        
        while self.running:
            try:
                # Get current file size
                current_offset = os.path.getsize(log_file_path)
                
                # Execute command
                self.minecraft_client.send_command('/g online')
                
                # Wait for response
                time.sleep(3)
                
                # Check if file has been modified
                new_offset = os.path.getsize(log_file_path)
                if new_offset > current_offset:
                    # Read new lines
                    with open(log_file_path, 'rb') as f:
                        f.seek(current_offset)
                        new_data = f.read(new_offset - current_offset)
                    new_lines = new_data.decode('utf-8', errors='replace').splitlines()
                    
                    # Extract usernames
                    usernames = self._extract_usernames_from_lines(new_lines)
                    
                    if usernames:
                        # Check if there has been a change
                        current_members = sorted([member['username'] for member in usernames])
                        
                        # If the list has changed or it's the first execution
                        if current_members != self.last_online_members:
                            logger.info(f"Change detected in online members list: {len(usernames)} members")
                            
                            # Update the list of last online members
                            self.last_online_members = current_members
                            
                            # Send to Discord only if there's a change
                            self._send_online_users_to_discord(usernames)
                        else:
                            logger.info(f"No change in online members list: {len(usernames)} members")
                
                # Wait before next check
                time.sleep(60)  # Check every 60 seconds
                
            except Exception as e:
                logger.error(f"Error in gonline: {e}")
                time.sleep(30)  # Wait before retrying in case of error
    
    def _extract_usernames_from_lines(self, lines):
        """Extracts usernames and ranks from guild online messages"""
        usernames = []
        current_guild_rank = None
        guild_name = None
        
        # Patterns for different sections
        guild_name_pattern = re.compile(r'Guild Name: (.+)')
        section_pattern = re.compile(r'-- (.+) --')
        
        for line in lines:
            # Remove timestamp from beginning of line
            clean_line = re.sub(r'^[\d-]+ [\d:]+\s+', '', line)
            
            # Extract guild name
            name_match = guild_name_pattern.search(clean_line)
            if name_match:
                guild_name = name_match.group(1).strip()
                continue
            
            # Check for section headers
            section_match = section_pattern.search(clean_line)
            if section_match:
                current_guild_rank = section_match.group(1).strip()
                continue
            
            # Check if line contains usernames
            if "●" in clean_line:
                # Split the line by "●" and process each part
                parts = clean_line.split("●")
                
                for part in parts[:-1]:  # Le dernier split n'a pas de joueur
                    clean_part = part.strip()
                    
                    rank = None
                    username = None
                    
                    if "[" in clean_part:
                        rank_match = re.search(r'\[(.*?)\]', clean_part)
                        if rank_match:
                            rank = rank_match.group(1)
                            username_part = clean_part.split("]")[-1].strip()
                            username = re.sub(r'§.', '', username_part)
                    else:
                        username = re.sub(r'§.', '', clean_part.strip())
                    
                    if username:
                        username = username.strip()
                        if rank:
                            rank = re.sub(r'§.', '', rank)
                        
                        usernames.append({
                            'username': username,
                            'rank': rank if rank else "",
                            'guild_rank': current_guild_rank
                        })
        
        return usernames
    
    def _send_online_users_to_discord(self, usernames):
        """Sends online users information to Discord"""
        try:
            embed = self._format_online_members(usernames)
            
            # Send a new message
            payload = {
                "embeds": [embed]
            }
            
            from config.credentials import DISCORD_WEBHOOK_URL_ONLINE
            import requests
            
            response = requests.post(DISCORD_WEBHOOK_URL_ONLINE, json=payload)
            
            if response.status_code == 204:
                logger.info("Successfully sent new online members message")
            else:
                logger.error(f"Failed to send message, status code: {response.status_code}, response: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error sending online members message: {e}")
    
    def _format_online_members(self, usernames):
        """Format online members in a compact display by guild hierarchy"""
        
        # Emojis for each hierarchy level
        hierarchy_emojis = {
            "Guild Master": "👑",
            "Officer": "⚔️",
            "Member": "🛡️"
        }
        
        # Group by guild rank
        guild_ranks = {}
        for member in usernames:
            # Directly use the extracted guild rank
            guild_rank = member.get('guild_rank', 'Member')
            
            if guild_rank not in guild_ranks:
                guild_ranks[guild_rank] = []
            guild_ranks[guild_rank].append(member['username'])
        
        # Create the embed
        embed = {
            "title": "Guild Members Online",
            "description": f"Total: **{len(usernames)}** members online",
            "color": 0x51586e,  # Changed color to #51586e
            "fields": [],
            "footer": {
                "text": f"Updated • {time.strftime('%H:%M')}"  # Added time to footer
            }
        }
        
        # Add each hierarchy level as a field
        hierarchy_order = ["Guild Master", "Officer", "Member"]
        
        for rank in hierarchy_order:
            if rank in guild_ranks:
                members = sorted(guild_ranks[rank])
                emoji = hierarchy_emojis.get(rank, "")
                embed["fields"].append({
                    "name": f"{emoji} {rank} ({len(members)})",
                    "value": "- " + "\n- ".join(members) if members else "None online",
                    "inline": False
                })
        
        return embed

    def process_commands_from_log(log_file_path, client, command_handler):
    """Traite directement les commandes à partir du fichier log"""
    logger = logging.getLogger('minecraft_bot.log_parser')
    logger.info("Starting command processing from log file")
    
    from config.settings import BOT_USERNAME
    
    # Pattern pour détecter les commandes
    pattern = re.compile(
        r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} '
        r'(?P<channel>.*?)\s*>\s*'
        r'(?:\[.*?\]\s*)?'
        r'(?P<sender>.*?)\s*(?:\[.*?\])?\s*:\s*'
        r'(?P<command>\b\w+\b)\s*'
        r'(?P<args>.*)',
        re.UNICODE
    )
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as log_file:
            # Aller à la fin du fichier pour ne lire que les nouvelles entrées
            log_file.seek(0, os.SEEK_END)
            
            while True:
                line = log_file.readline().strip()
                if not line:
                    time.sleep(0.1)  # Éviter la consommation CPU excessive
                    continue
                
                # Nettoyer la ligne des codes couleur Minecraft
                cleaned_line = re.sub(r'§.', '', line)
                
                # Rechercher les commandes
                match = pattern.search(cleaned_line)
                if match:
                    channel = match.group('channel').strip()
                    sender = match.group('sender').strip()
                    command = match.group('command').strip()
                    args = match.group('args').strip()
                    
                    # Nettoyage du sender (enlever GM, etc.)
                    cleaned_sender = re.sub(r'\s*\[.*?\]\s*', '', sender).strip()
                    
                    # Vérifier que ce n'est pas un message du bot lui-même
                    if channel == "Guild" and cleaned_sender != BOT_USERNAME:
                        logger.info(f"COMMAND DETECTED: {cleaned_sender}: {command} {args}")
                        
                        # Traiter directement la commande
                        message = f"{command} {args}"
                        try:
                            result = command_handler.process_command(channel, cleaned_sender, message)
                            logger.info(f"Command result: {result}")
                        except Exception as e:
                            logger.error(f"Error processing command: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
    
    except Exception as e:
        logger.error(f"Error in log parser: {e}")
        import traceback
        logger.error(traceback.format_exc())