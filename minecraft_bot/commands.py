import re
import logging
import threading
from queue import Queue, Empty

from shared.timing_utils import log_execution_time
from shared.shortcuts import ShortcutManager
from minecraft_bot.stats import HypixelScraper
from config.settings import BOT_USERNAME


logger = logging.getLogger('minecraft_bot.commands')

class CommandHandler:
    """Handles commands received from Minecraft chat"""
    
    def __init__(self, minecraft_client):
        self.minecraft_client = minecraft_client
        self.shortcut_manager = ShortcutManager()
        self.scraper = HypixelScraper()
        self.stats_queue = Queue()
        self.processing_thread = None
    
    def start(self):
        """Starts command processing"""
        self.processing_thread = threading.Thread(
            target=self._process_stats_queue,
            daemon=True
        )
        self.processing_thread.start()
    
    def stop(self):
        """Stops command processing"""
        if self.processing_thread:
            self.stats_queue.put(None)  # Signal to stop the thread
    
    @log_execution_time("detect_command")
    def detect_command_type(self, command, args, sender, recursion_depth=0):
        """Determines the command type and extracts arguments"""
        args = str(args).strip().replace("/", "")
        MAX_RECURSION_DEPTH = 2
        
        if recursion_depth > MAX_RECURSION_DEPTH:
            return ('error', 'Maximum shortcut nesting depth (2) exceeded')
        
        # Check for shortcuts at first level
        if recursion_depth == 0:
            shortcut_command = self.shortcut_manager.load_shortcut(sender, command)
            if shortcut_command:
                if shortcut_command.strip() == command:
                    return ('error', f'Direct recursion in shortcut "{command}"')
                
                full_command = f"{shortcut_command} {args}".strip()
                new_command, _, new_args = full_command.partition(' ')
                return self.detect_command_type(new_command, new_args, sender, recursion_depth + 1)
        
        # User commands
        if command == 'usr':
            args = args.strip()
            if args.startswith('shortcut'):
                parts = args.split()
                if len(parts) < 2:
                    return ('error', 'Invalid format: usr shortcut <actual_username> [alias1] [alias2...]')
                actual_username = parts[1]
                aliases = parts[2:]
                if not re.match(r'^[a-zA-Z0-9_]{3,16}$', actual_username):
                    return ('error', 'Invalid actual username format')
                if aliases:
                    return ('user_shortcut_create', (actual_username, aliases))
                else:
                    return ('user_shortcut_delete_all', actual_username)
            elif args.startswith('delete'):
                parts = args.split()
                if len(parts) < 2:
                    return ('error', 'Invalid format: usr delete <alias>')
                alias = parts[1]
                return ('user_shortcut_delete', alias)
            elif args == 'list shortcut':
                return ('list_user_shortcuts', None)
        
        # Shortcut commands
        if command == 'shortcut':
            args = args.strip()
            if not args:
                return ('error', 'Missing shortcut arguments')
            
            if ' ' in args:
                shortcut_name, shortcut_command = args.split(' ', 1)
                shortcut_name = shortcut_name.strip()
                shortcut_command = shortcut_command.strip()
                if not shortcut_name or not shortcut_command:
                    return ('error', 'Invalid format: shortcut <name> <command>')
                return ('shortcut_create', (shortcut_name, shortcut_command))
            else:
                return ('shortcut_delete', args.strip())
        
        # List command
        elif command == 'list':
            if args.strip() == 'shortcut':
                return ('list_shortcuts', sender)
            return ('unknown', args)
        
        # Other command types
        if command == 'g':
            return ('guild', args)
        elif command in ['1s', '2s', '3s', '4s', '4v4', 'core', 'bw']:
            return ('gamemode_stat', args)
        else:
            return ('unknown', args)
    
    def process_command(self, channel, sender, message):
        """Processes a command received from chat"""
        if channel != "Guild" or sender == BOT_USERNAME:
            return False
        
        # Extract the command
        parts = message.strip().split(' ', 1)
        if not parts:
            return False
        
        command = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        
        # Log for debugging
        logger.info(f"Processing command from {sender}: {message}")
        logger.info(f"Extracted command: {command}, args: {args}")
        
        # Detect command type
        command_type, command_args = self.detect_command_type(command, args, sender)
        logger.info(f"Command detected: {command_type}, command: {command}, args: {command_args}")
        
        # Handle error
        if command_type == 'error':
            self.minecraft_client.send_chat_message(f"Error: {command_args}")
            return True
        
        # Handle commands
        if command_type == 'shortcut_create':
            shortcut_name, shortcut_command = command_args
            if not re.match(r'^\w+$', shortcut_name):
                self.minecraft_client.send_chat_message(f"Invalid shortcut name. Use letters/numbers only.")
            else:
                self.shortcut_manager.save_shortcut(sender, shortcut_name, shortcut_command)
                self.minecraft_client.send_chat_message(f"Shortcut '{shortcut_name}' created: {shortcut_command}")
        
        elif command_type == 'shortcut_delete':
            shortcut_name = command_args
            if self.shortcut_manager.delete_shortcut(sender, shortcut_name):
                self.minecraft_client.send_chat_message(f"Shortcut '{shortcut_name}' deleted for {sender}")
            else:
                self.minecraft_client.send_chat_message(f"Shortcut '{shortcut_name}' not found for {sender}")
        
        elif command_type == 'list_shortcuts':
            shortcuts = self.shortcut_manager.list_shortcuts(sender)
            if shortcuts:
                for shortcut_name, shortcut_command in shortcuts.items():
                    self.minecraft_client.send_chat_message(f"{shortcut_name}: {shortcut_command}")
            else:
                self.minecraft_client.send_chat_message(f"No shortcuts found for {sender}")
        
        elif command_type == 'user_shortcut_create':
            actual_username, aliases = command_args
            invalid_aliases = [a for a in aliases if not re.match(r'^[a-zA-Z0-9_]{1,16}$', a)]
            if invalid_aliases:
                self.minecraft_client.send_chat_message(f"Invalid alias format: {', '.join(invalid_aliases)}")
            else:
                self.shortcut_manager.save_user_shortcut(sender, actual_username, aliases)
                self.minecraft_client.send_chat_message(f"Created username shortcuts: {', '.join(aliases)} → {actual_username}")
        
        elif command_type == 'user_shortcut_delete':
            alias = command_args
            if self.shortcut_manager.delete_user_shortcut(sender, alias):
                self.minecraft_client.send_chat_message(f"Deleted username shortcut: {alias}")
            else:
                self.minecraft_client.send_chat_message(f"Shortcut '{alias}' not found")
        
        elif command_type == 'user_shortcut_delete_all':
            actual_username = command_args
            if self.shortcut_manager.delete_all_user_shortcuts(sender, actual_username):
                self.minecraft_client.send_chat_message(f"Deleted all shortcuts for username: {actual_username}")
            else:
                self.minecraft_client.send_chat_message(f"No shortcuts found for username: {actual_username}")
        
        elif command_type == 'list_user_shortcuts':
            shortcuts = self.shortcut_manager.load_user_shortcuts(sender)
            if shortcuts:
                for alias, actual in shortcuts.items():
                    self.minecraft_client.send_chat_message(f"{alias} → {actual}")
            else:
                self.minecraft_client.send_chat_message(f"No username shortcuts found")
        
        elif command_type == 'guild':
            # Process guild info requests
            usernames = self._extract_usernames(command_args, sender)
            for username in usernames:
                # Resolve any alias
                resolved_username = self.shortcut_manager.resolve_username(sender, username)
                # Queue guild info request
                self._process_guild_info(resolved_username)
        
        elif command_type == 'gamemode_stat':
            # Process BedWars stats requests
            self._process_bedwars_stats(command, command_args, sender)
        
        return True
    
    def _extract_usernames(self, args, default_sender):
        """Extracts valid usernames from command arguments"""
        components = args.split()
        usernames = [arg for arg in components if re.match(r'^[a-zA-Z0-9_]{3,16}$', arg)]
        
        # If no valid usernames, use sender
        if not usernames:
            usernames = [default_sender]
            
        return usernames
    
    def _process_guild_info(self, username):
        """Gets and sends guild info for a player"""
        result = self.scraper.get_guild_info(username)
        if result:
            self.minecraft_client.send_chat_message(f"{result}")
    
    def _process_bedwars_stats(self, command, args, sender):
        """Queues BedWars stats requests for processing in separate thread"""
        components = args.split()
        top_flag = False
        subcategory = None
        
        # Check for 'top' flag
        if "top" in components:
            top_flag = True
            components.remove("top")
        
        # Extract subcategory if present
        if components and components[0] not in ['all', 'lvl'] and not re.match(r'^[a-zA-Z0-9_]{3,16}$', components[0]):
            subcategory = components[0]
            components = components[1:]
        else:
            subcategory = 'all'  # Default
        
        # Get usernames
        usernames = [comp for comp in components if re.match(r'^[a-zA-Z0-9_]{3,16}$', comp)]
        if not usernames:
            usernames = [sender]
        
        # Resolve any aliases in usernames
        resolved_usernames = []
        for username in usernames:
            resolved_username = self.shortcut_manager.resolve_username(sender, username)
            resolved_usernames.append(resolved_username)
        
        # Queue for processing
        self.stats_queue.put((command, resolved_usernames, top_flag, subcategory))
    
    def _process_stats_queue(self):
        """Thread that processes queued stats requests"""
        while True:
            try:
                item = self.stats_queue.get(timeout=1.0)
                if item is None:  # Stop signal
                    break
                
                command, usernames, top_flag, subcategory = item
                
                if top_flag:
                    self._process_top_stats(command, usernames, subcategory)
                else:
                    for username in usernames:
                        result = self.scraper.get_bedwars_stats(username, command, subcategory)
                        if result:
                            self.minecraft_client.send_chat_message(result)
                
                self.stats_queue.task_done()
                
            except Empty:
                # Queue is empty, continue waiting
                pass
            except Exception as e:
                logger.error(f"Error processing stats queue: {e}")
    
    def _process_top_stats(self, command, usernames, subcategory):
        """Processes a 'top' request to find the player with the highest stat"""
        results = []
        
        for username in usernames:
            result = self.scraper.get_bedwars_stats(username, command, subcategory)
            if result:
                logger.info(f"Result for {username}: {result}")
                
                # Extract value based on subcategory
                if subcategory == 'lvl':
                    # Extract level from string like "[123✫] Username"
                    level_pattern = r'\s(\d+(?:\.\d+)?)'
                    level_match = re.search(level_pattern, result)
                    if level_match:
                        level_value = float(level_match.group(1))
                        results.append((username, level_value))
                else:
                    # Find the stat value
                    value_pattern = f"{subcategory}\\s+(\\d+(?:,\\d+)*(?:\\.\\d+)?)"
                    value_match = re.search(value_pattern, result, re.IGNORECASE)
                    if value_match:
                        value_str = value_match.group(1).replace(',', '')
                        try:
                            value = float(value_str)
                            results.append((username, value))
                        except ValueError:
                            logger.error(f"Could not convert '{value_str}' to float")
        
        # Find the highest value
        if results:
            top_user = max(results, key=lambda x: x[1])
            if top_user[1].is_integer():
                value_str = f"{int(top_user[1])}"
            else:
                value_str = f"{top_user[1]:.2f}"
            
            self.minecraft_client.send_chat_message(
                f"{top_user[0]} - {subcategory.capitalize()}: {value_str}"
            )
        else:
            self.minecraft_client.send_chat_message(
                "No results found to determine the top user."
            )