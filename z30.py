#!/usr/bin/env python3
import os
import sys
import time
import atexit
import psutil
import colorama
import logging
import threading

from config.settings import MINECRAFT_CLIENT_PATH, MINECRAFT_LOG_FILE, LOCK_FILE
from shared.logging_utils import setup_logger
from shared.file_utils import create_lock_file, remove_lock_file
from minecraft_bot.client import MinecraftClient
from minecraft_bot.relay import MinecraftDiscordRelay
from minecraft_bot.commands import CommandHandler
from minecraft_bot.utils import check_log_file, is_process_running, OnlinePlayersTracker

def main():
    # Initialize colorama for Windows ANSI color support
    colorama.init(autoreset=True)
    
    # Configure logging
    logger = setup_logger('minecraft_bot', log_file=MINECRAFT_LOG_FILE)
    logger.info("Starting Minecraft bot...")
    
    # Check if another instance is already running
    if is_process_running():
        logger.error("Another instance of the bot is already running")
        print("Another instance is already running. Exiting.")
        sys.exit(1)
    
    # Create lock file
    create_lock_file()
    
    # Ensure lock file is removed on exit
    atexit.register(remove_lock_file)
    
    try:
        # Initialize Minecraft client
        client = MinecraftClient()
        
        # Initialize command handler
        command_handler = CommandHandler(client)
        
        # IMPORTANT: Définir le callback pour les messages de chat AVANT de démarrer quoi que ce soit
        # C'est cette ligne qui était probablement manquante ou mal placée
        client.on_chat_message = command_handler.process_command
        
        # Initialize Discord relay
        relay = MinecraftDiscordRelay(client)
        
        # Initialize online players tracker
        tracker = OnlinePlayersTracker(client)
        
        # Start the client
        client.start()
        
        # Start command handler
        command_handler.start()
        
        # Start relay
        relay.start()
        
        # Start online players tracker
        tracker.start()
        
        # Start log file monitoring thread
        log_monitor_thread = threading.Thread(
            target=check_log_file,
            args=(MINECRAFT_LOG_FILE, client),
            daemon=True
        )
        log_monitor_thread.start()
        
        # Ajouter un thread pour la lecture directe des logs et le traitement des commandes
        direct_command_thread = threading.Thread(
            target=direct_command_processing,
            args=(MINECRAFT_LOG_FILE, client, command_handler),
            daemon=True
        )
        direct_command_thread.start()
        
        # Set join/leave event handler
        client.on_join_leave = relay.handle_join_leave
        
        # Main loop - keep running until interrupted
        try:
            logger.info("Minecraft bot started successfully, press Ctrl+C to exit")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        finally:
            # Clean shutdown
            logger.info("Shutting down...")
            tracker.stop()
            relay.stop()
            command_handler.stop()
            client.stop()
            
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1
    
    return 0

def direct_command_processing(log_file_path, client, command_handler):
    """Traite directement les commandes à partir du fichier log (comme dans l'ancienne version)"""
    logger = logging.getLogger('minecraft_bot.direct_commands')
    logger.info("Starting direct command processing from log file")
    
    # Regex pattern pour détecter les commandes 
    command_pattern = re.compile(
        r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} '
        r'(?P<channel>.*?)\s*>\s*'
        r'(?:\[(?P<rank>.*?)\]\s*)?'
        r'(?P<sender>.*?)\s*(?:\[(?P<gm>GM)\])?\s*:\s*'
        r'(?P<message>.*)',
        re.UNICODE
    )
    
    from config.settings import BOT_USERNAME
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as log_file:
            # Aller à la fin du fichier pour ne lire que les nouvelles entrées
            log_file.seek(0, os.SEEK_END)
            
            while True:
                line = log_file.readline().strip()
                if not line:
                    time.sleep(0.1)  # Éviter la consommation CPU excessive
                    continue
                    
                # Traiter la ligne pour détecter une commande
                match = command_pattern.search(line)
                if match:
                    channel = match.group('channel').strip()
                    sender = match.group('sender').strip()
                    message = match.group('message').strip()
                    
                    # Nettoyage de sender (enlever GM, etc.)
                    cleaned_sender = re.sub(r'\s*\[.*?\]\s*', '', sender).strip()
                    
                    # Vérifier que ce n'est pas un message du bot lui-même
                    if channel == "Guild" and cleaned_sender != BOT_USERNAME:
                        logger.info(f"Direct command processing: {cleaned_sender}: {message}")
                        
                        # Appeler directement process_command du command_handler
                        command_handler.process_command(channel, cleaned_sender, message)
    
    except Exception as e:
        logger.error(f"Error in direct command processing: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    sys.exit(main())