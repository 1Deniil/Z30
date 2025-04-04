#!/usr/bin/env python3
import sys
import asyncio
import logging

from config.credentials import BOT_TOKEN
from config.settings import DISCORD_LOG_FILE
from shared.logging_utils import setup_logger
from discord_bot.bot import DiscordBot
from discord_bot.commands import setup_commands
from discord_bot.events import setup_events

async def main():
    # Configure logging
    logger = setup_logger('discord_bot', log_file=DISCORD_LOG_FILE)
    logger.info("Starting Discord bot...")
    
    try:
        # Create Discord bot
        bot = DiscordBot()
        
        # Set up commands
        setup_commands(bot)
        
        # Set up event handlers
        setup_events(bot)
        
        # Start the bot
        logger.info("Starting bot...")
        await bot.start(BOT_TOKEN)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))