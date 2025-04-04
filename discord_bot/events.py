import logging
import discord

logger = logging.getLogger('discord_bot.events')

def setup_events(bot):
    """Sets up event handlers for the Discord bot"""
    
    @bot.event
    async def on_guild_join(guild):
        """Called when the bot joins a guild"""
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
    
    @bot.event
    async def on_command_error(ctx, error):
        """Called when a command raises an error"""
        if isinstance(error, discord.ext.commands.CommandNotFound):
            return
        
        logger.error(f"Command error: {error}")
        
        # Inform the user
        await ctx.send(f"Error: {error}")