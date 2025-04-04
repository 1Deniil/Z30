import subprocess
import threading
import time
import re
import logging
import random
from queue import Queue, Empty

from config.settings import MINECRAFT_CLIENT_PATH, BOT_USERNAME

logger = logging.getLogger('minecraft_bot.client')

class MinecraftClient:
    """Gère l'interaction avec le client Minecraft via subprocess"""
    
    def __init__(self):
        self.process = None
        self.server_joined = False
        self.last_sent_message = None
        self.last_sender = None
        self.retry_count = 0
        
        # Files d'attente et verrous
        self.command_queue = Queue()
        self.last_sent_lock = threading.Lock()
        
        # Callbacks pour les événements
        self.on_chat_message = None  # Pour les messages du chat
        self.on_join_leave = None    # Pour les événements de connexion/déconnexion
    
    def start(self):
        """Démarre le client Minecraft"""
        logger.info(f"Démarrage du client Minecraft...")
        
        try:
            self.process = subprocess.Popen(
                [MINECRAFT_CLIENT_PATH],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace',
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Démarrer les threads
            self._start_threads()
            
            # Attendre la connexion au serveur
            self._wait_for_server_join()
            
            # Initialiser limbo après connexion
            time.sleep(random.uniform(3, 7))
            self.send_command('/limbo')
            
            logger.info("Client Minecraft démarré et connecté au serveur")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du client Minecraft: {e}")
            return False
    
    def _start_threads(self):
        """Démarre les threads de lecture et d'écriture"""
        # Thread de lecture de la sortie du client
        output_thread = threading.Thread(
            target=self._read_output,
            daemon=True
        )
        output_thread.start()
        
        # Thread pour lire les entrées utilisateur
        input_thread = threading.Thread(
            target=self._read_input,
            daemon=True
        )
        input_thread.start()
        
        # Thread pour traiter la file de commandes
        command_thread = threading.Thread(
            target=self._process_command_queue,
            daemon=True
        )
        command_thread.start()
    
    def _wait_for_server_join(self):
        """Attend que le client soit connecté au serveur"""
        timeout = 60  # secondes
        start_time = time.time()
        
        while not self.server_joined:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.error(f"Timeout de connexion au serveur après {timeout} secondes")
                raise TimeoutError("Timeout lors de la connexion au serveur")
            time.sleep(0.5)
    
    def _read_output(self):
        """Thread pour lire la sortie du client Minecraft"""
        while self.process and self.process.poll() is None:
            try:
                output = self.process.stdout.readline()
                if not output:
                    if self.process.poll() is not None:
                        break
                    continue
                
                # Nettoyer et logger la sortie
                output = output.strip()
                logger.info(output)
                
                # Détecter la connexion au serveur
                if "[MCC] Server was successfully joined." in output:
                    self.server_joined = True
                
                # Détecter et extraire les messages du chat
                chat_match = re.match(
                    r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} '
                    r'(?P<channel>.*?)\s*>\s*'
                    r'(?:\[(?P<rank>.*?)\]\s*)?'
                    r'(?P<sender>.*?)\s*(?:\[(?P<gm>GM)\])?\s*:\s*'
                    r'(?P<message>.*)',
                    output
                )
                if chat_match:
                    # Traiter un message de chat
                    self._handle_chat_message(
                        chat_match.group('channel'),
                        chat_match.group('sender'),
                        chat_match.group('message')
                    )
                
                # Détecter les événements join/leave
                join_leave_match = re.match(
                    r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} '
                    r'§2§2Guild > §b§b(?P<name>.*?) §r§e§e(?P<action>left|joined)\.§r',
                    output
                )
                if join_leave_match:
                    if self.on_join_leave:
                        self.on_join_leave(
                            join_leave_match.group('name'),
                            join_leave_match.group('action')
                        )
                
                # Message double ?
                if "You cannot say the same message twice!" in output:
                    self._handle_duplicate_message()
            
            except Exception as e:
                logger.error(f"Erreur lors de la lecture de la sortie: {e}")
    
    def _handle_chat_message(self, channel, sender, message):
        """Message rent"""
        self.last_sender = sender
        
        # Log plus détaillé pour debugger
        logger.debug(f"RAW MESSAGE: channel='{channel}', sender='{sender}', message='{message}'")
        
        # Nettoyage plus agressif du sender (enlever [GM] ou autres tags)
        cleaned_sender = re.sub(r'\s*\[.*?\]\s*', '', sender).strip()
        logger.debug(f"CLEANED SENDER: '{cleaned_sender}'")
        
        # Vérifier si le message contient une commande
        if channel == "Guild" and cleaned_sender != BOT_USERNAME:
            logger.debug(f"VALID GUILD MESSAGE: from '{cleaned_sender}'")
            
            # Extraire la commande et les arguments
            parts = message.strip().split(' ', 1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""
            
            logger.debug(f"EXTRACTED COMMAND: '{command}' with args: '{args}'")
            
            # Appeler le callback si défini
            if self.on_chat_message:
                logger.debug(f"CALLING CALLBACK with channel='{channel}', sender='{cleaned_sender}', message='{message}'")
                # Appeler avec le sender nettoyé
                self.on_chat_message(channel, cleaned_sender, message)
            else:
                logger.warning(f"NO CALLBACK DEFINED for on_chat_message")
    
    def _handle_duplicate_message(self):
        """Gère le cas où un message est refusé car identique au précédent"""
        with self.last_sent_lock:
            if self.last_sent_message is not None:
                if self.retry_count < 3:
                    # Ajouter des espaces invisibles pour contourner la détection
                    suffix = " _ _ " * (self.retry_count + 1)
                    modified_message = f"{self.last_sent_message}{suffix}"
                    logger.info(f"Retrying with modified message: {modified_message}")
                    self.send_command(modified_message)
                    self.retry_count += 1
                    self.last_sent_message = modified_message
                else:
                    # Abandonner après 3 tentatives
                    alternate_message = "/gc Same message"
                    logger.info("Sending 'Same message' after multiple retries")
                    self.send_command(alternate_message)
                    self.last_sent_message = alternate_message
                    self.retry_count = 0
    
    def _read_input(self):
        """Thread pour lire les entrées de l'utilisateur"""
        while self.process and self.process.poll() is None:
            try:
                user_input = input()
                if user_input.strip():
                    self.send_command(user_input)
            except EOFError:
                break
            except Exception as e:
                logger.error(f"Erreur lors de la lecture de l'entrée: {e}")
    
    def _process_command_queue(self):
        """Thread pour traiter la file d'attente des commandes"""
        while self.process and self.process.poll() is None:
            try:
                command = self.command_queue.get(timeout=0.5)
                if command is None:
                    break
                
                self._send_raw_command(command)
                self.command_queue.task_done()
                
                # Petit délai pour éviter le spam
                time.sleep(0.1)
            except Empty:
                pass
            except Exception as e:
                logger.error(f"Erreur lors du traitement de la commande: {e}")
    
    def _send_raw_command(self, command):
        """Envoie une commande brute au client Minecraft"""
        if not self.process or self.process.poll() is not None:
            logger.error("Impossible d'envoyer la commande: client non démarré")
            return False
        
        try:
            self.process.stdin.write(f"{command}\n")
            self.process.stdin.flush()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la commande: {e}")
            return False
    
    def send_command(self, command):
        """Envoie une commande au client Minecraft"""
        # Préfixer avec /send si ce n'est pas déjà le cas
        if not command.startswith('/send'):
            command = f'/send {command}'
        
        # Ajouter à la file d'attente
        self.command_queue.put(command)
        return True
    
    def send_chat_message(self, message):
        """Envoie un message au chat de guilde"""
        with self.last_sent_lock:
            self.last_sent_message = message
            self.retry_count = 0
        
        # Garantir que le message commence par /gc
        if not message.startswith('/gc '):
            content = message
            message = f"/gc {message}"
        else:
            content = message[4:]  # Retirer '/gc '
        
        # Diviser les messages trop longs
        if len(content) > 92:  # Limite Minecraft
            chunks = [content[i:i+92] for i in range(0, len(content), 92)]
            for chunk in chunks:
                self.send_command(f"/gc {chunk}")
                time.sleep(0.1)
        else:
            self.send_command(message)
        
        return True
    
    def stop(self):
        """Arrête proprement le client Minecraft"""
        if not self.process:
            return
        
        try:
            # Envoyer la commande pour quitter
            self.send_command('/quit')
            
            # Attendre la fin du processus
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Forcer la fermeture si nécessaire
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            
            logger.info("Client Minecraft arrêté")
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du client: {e}")
        finally:
            self.process = None