import discord
import logging
import datetime
import asyncio
from discord.ext import commands, tasks
from discord import Embed, Colour

from config.settings import GUILD_ID, LOG_CHANNEL_ID, ONLINE_USERS_CHANNEL_ID, ADMIN_ROLE_IDS
from config.credentials import BOT_TOKEN

logger = logging.getLogger('discord_bot.bot')

class DiscordBot(commands.Bot):
    """Main Discord bot class that handles commands and events"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        
        # Bot start time
        self.start_time = datetime.datetime.now()
        
        # Z30 start time
        self.z30_start_time = None
    
    async def setup_hook(self):
        """Setup hook for bot initialization"""
        logger.info("Running setup_hook")
        
        # Register commands with the guild
        try:
            logger.info("Synchronizing commands...")
            guild = discord.Object(id=GUILD_ID)
            
            # Register commands to the guild
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            
            logger.info(f"Commands synchronized to guild {GUILD_ID}")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
        
        # Start tasks
        self.gonline_manager.start()
    
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'Bot logged in as {self.user.name}')
        logger.info(f'Bot ID: {self.user.id}')
        logger.info('------')
    
    async def on_message(self, message):
        """Called for every message the bot can see"""
        # Ignore messages from the bot itself
        if message.author.bot:
            return
        
        # Check if the message is from the configured channel
        if message.channel.id == LOG_CHANNEL_ID:
            try:
                # Get the user's display name on the server
                display_name = message.author.display_name
                
                # Send the message to the webhook
                import requests
                from config.settings import FLASK_HOST, FLASK_PORT
                from config.credentials import WEBHOOK_SECRET
                
                response = requests.post(
                    f"http://{FLASK_HOST}:{FLASK_PORT}/discord-webhook",
                    json={
                        'username': display_name,
                        'content': message.content
                    },
                    headers={
                        'Content-Type': 'application/json',
                        'X-Discord-Secret': WEBHOOK_SECRET
                    }
                )
                
                # Check if the request was successful
                if response.status_code == 200:
                    logger.info(f'Message sent: {display_name}: {message.content}')
                else:
                    logger.error(f'Error sending message: {response.status_code} - {response.text}')
            except Exception as e:
                logger.error(f'Error sending message: {e}')
        
        # Process commands
        await self.process_commands(message)
    
    @tasks.loop(seconds=5)
    async def gonline_manager(self):
        """Manages online users channel messages to keep them clean"""
        try:
            online_channel = self.get_channel(ONLINE_USERS_CHANNEL_ID)
            
            if online_channel:
                messages = []
                async for message in online_channel.history(limit=2):
                    messages.append(message)
                
                if len(messages) > 1:
                    for message in messages[1:]:
                        await message.delete()
        
        except Exception as e:
            logger.error(f"Error in gonline_manager: {e}")
    
    @gonline_manager.before_loop
    async def before_gonline_manager(self):
        """Wait until the bot is ready before starting the task"""
        await self.wait_until_ready()