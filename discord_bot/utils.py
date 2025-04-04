import logging
import discord
import os

logger = logging.getLogger('discord_bot.utils')

def get_channel(bot, channel_id):
    """Safely get a channel by ID"""
    try:
        channel = bot.get_channel(channel_id)
        if channel is None:
            logger.warning(f"Channel with ID {channel_id} not found")
        return channel
    except Exception as e:
        logger.error(f"Error getting channel {channel_id}: {e}")
        return None

def get_guild(bot, guild_id):
    """Safely get a guild by ID"""
    try:
        guild = bot.get_guild(guild_id)
        if guild is None:
            logger.warning(f"Guild with ID {guild_id} not found")
        return guild
    except Exception as e:
        logger.error(f"Error getting guild {guild_id}: {e}")
        return None

def is_admin(member, admin_role_ids):
    """Check if a member has an admin role"""
    return any(role.id in admin_role_ids for role in member.roles)