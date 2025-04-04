import threading
import time
import re
import logging
import requests
from queue import Queue, Empty
from flask import Flask, request, jsonify

from config.settings import FLASK_HOST, FLASK_PORT
from config.credentials import DISCORD_WEBHOOK_URL, DISCORD_WEBHOOK_URL_ONLINE, WEBHOOK_SECRET
from config.settings import COLOR_MAPPING

logger = logging.getLogger('minecraft_bot.relay')

class MinecraftDiscordRelay:
    """Handles bidirectional communication between Minecraft and Discord"""
    
    def __init__(self, minecraft_client):
        self.minecraft_client = minecraft_client
        
        # Message queue for Discord -> Minecraft communication
        self.discord_queue = Queue()
        
        # Setup Flask app for webhook
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Set up callback for Minecraft -> Discord
        self.minecraft_client.on_chat_message = self.handle_chat_message
        
        # Thread management
        self.processing_thread = None
        self.flask_thread = None
        self.running = False
    
    def setup_routes(self):
        """Sets up Flask routes for the webhook"""
        
        @self.app.route('/discord-webhook', methods=['POST'])
        def discord_webhook():
            # Verify the secret
            if request.headers.get('X-Discord-Secret') != WEBHOOK_SECRET:
                return jsonify({"status": "error", "message": "Unauthorized"}), 401
            
            # Validate request format
            data = request.json
            if 'username' not in data or 'content' not in data:
                return jsonify({"status": "error", "message": "Invalid format"}), 400
            
            # Queue the message
            username = data['username']
            content = data['content']
            self.discord_queue.put((username, content))
            
            logger.info(f"Discord message received: {username}: {content}")
            return jsonify({"status": "success"}), 200
    
    def start(self):
        """Starts the relay"""
        if self.running:
            return
        
        self.running = True
        
        # Start message processing thread
        self.processing_thread = threading.Thread(
            target=self._process_discord_messages,
            daemon=True
        )
        self.processing_thread.start()
        
        # Start Flask server in a separate thread
        self.start_webhook_server()
        
        logger.info("Discord relay started")
    
    def start_webhook_server(self):
        """Starts the Flask webhook server"""
        self.flask_thread = threading.Thread(
            target=lambda: self.app.run(
                host=FLASK_HOST,
                port=FLASK_PORT,
                debug=False,
                use_reloader=False
            ),
            daemon=True
        )
        self.flask_thread.start()
        logger.info(f"Webhook server started on {FLASK_HOST}:{FLASK_PORT}")
    
    def stop(self):
        """Stops the relay"""
        self.running = False
        
        # Signal the processing thread to stop
        if self.processing_thread:
            self.discord_queue.put(None)
        
        logger.info("Discord relay stopped")
    
    def handle_chat_message(self, channel, sender, message):
        """Handles messages from Minecraft to relay to Discord"""
        if channel != "Guild":
            return
        
        # Check if it's a Discord message to avoid loops
        if "[DC]" in sender or "[DC]" in message:
            logger.info(f"Discord message ignored: {sender}: {message}")
            return
        
        # Format full message for Discord
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"{timestamp} {channel} > {sender}: {message}"
        
        # Convert to ANSI for Discord
        ansi_message = self.convert_minecraft_to_ansi(full_message)
        
        # Send to Discord
        self.send_to_discord(ansi_message)
    
    def handle_join_leave(self, player_name, action):
        """Handles player join/leave events"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"{timestamp} Guild > {player_name} {action}."
        
        # Apply color formatting
        colored_message = self.convert_minecraft_to_ansi(full_message)
        
        # Send to Discord
        self.send_to_discord(colored_message)
    
    def convert_minecraft_to_ansi(self, message):
        """Converts Minecraft color codes to ANSI codes for Discord"""
        for mc_code, ansi_code in COLOR_MAPPING.items():
            message = message.replace(mc_code, ansi_code)
        return message
    
    def send_to_discord(self, message):
        """Sends a message to Discord"""
        # Skip if it's already a Discord message
        if "[DC]" in message:
            logger.info(f"Discord message ignored to prevent loop: {message}")
            return
        
        # Remove timestamp from message start for cleaner display
        message_without_timestamp = re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ', '', message)
        
        # Format with ANSI for Discord
        ansi_message = f"```ansi\n{message_without_timestamp}\n```"
        
        payload = {
            "content": ansi_message
        }

        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
            if response.status_code != 204:
                logger.error(f"Failed to send message to Discord: {response.status_code} {response.text}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error sending message to Discord: {e}")
            return False
    
    def _process_discord_messages(self):
        """Processes messages from Discord to Minecraft"""
        while self.running:
            try:
                item = self.discord_queue.get(timeout=0.5)
                if item is None:  # Stop signal
                    break
                
                username, content = item
                
                # Format the message
                formatted_message = f'[DC] {username}: {content}'
                
                # Send to Minecraft
                if len(formatted_message) > 90:  # Minecraft limit
                    chunks = [formatted_message[i:i+90] for i in range(0, len(formatted_message), 90)]
                    for chunk in chunks:
                        self.minecraft_client.send_chat_message(chunk)
                        time.sleep(0.5)  # Prevent spam
                else:
                    self.minecraft_client.send_chat_message(formatted_message)
                
                self.discord_queue.task_done()
                
            except Empty:
                # Queue is empty, continue waiting
                pass
            except Exception as e:
                logger.error(f"Error processing Discord message: {e}")
                time.sleep(1)  # Wait before retrying