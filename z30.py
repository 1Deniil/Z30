#!/usr/bin/env python3
import os
import sys
import time
import atexit
import psutil
import colorama
import logging
import threading

from config.settings import MINECRAFT_LOG_FILE, LOCK_FILE
from shared.logging_utils import setup_logger
from shared.file_utils import create_lock_file, remove_lock_file
from minecraft_bot.client import MinecraftClient
from minecraft_bot.relay import MinecraftDiscordRelay
from minecraft_bot.commands import CommandHandler
from minecraft_bot.utils import check_log_file, is_process_running, OnlinePlayersTracker, process_commands_from_log

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
        logger.info("Minecraft client initialized")
        
        # Initialize command handler
        command_handler = CommandHandler(client)
        logger.info("Command handler initialized")
        
        # Initialize Discord relay
        relay = MinecraftDiscordRelay(client)
        logger.info("Discord relay initialized")
        
        # Initialize online players tracker
        tracker = OnlinePlayersTracker(client)
        logger.info("Online players tracker initialized")
        
        # Start the client
        client.start()
        logger.info("Minecraft client started")
        
        # Démarrer le gestionnaire de commandes
        command_handler.start()
        logger.info("Command handler started")
        
        # Démarrer le relay
        relay.start()
        logger.info("Discord relay started")
        
        # Start online players tracker
        tracker.start()
        logger.info("Online players tracker started")
        
        # Start log file monitoring thread for disconnection detection
        log_monitor_thread = threading.Thread(
            target=check_log_file,
            args=(MINECRAFT_LOG_FILE, client),
            daemon=True
        )
        log_monitor_thread.start()
        logger.info("Log file monitoring started")
        
        # Démarrer le thread de traitement des commandes à partir des logs
        command_thread = threading.Thread(
            target=process_commands_from_log,
            args=(MINECRAFT_LOG_FILE, client, command_handler),
            daemon=True
        )
        command_thread.start()
        logger.info("Command processing from logs started")
        
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

if __name__ == "__main__":
    sys.exit(main())