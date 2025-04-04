import discord
import logging
import asyncio
import os
import subprocess
import datetime
import psutil
from discord import Embed, Colour
from discord.ext import commands

from config.settings import Z30_SCRIPT_PATH, ADMIN_ROLE_IDS, LOG_CHANNEL_ID
from config.settings import LOCK_FILE

logger = logging.getLogger('discord_bot.commands')

def setup_commands(bot):
    """Sets up slash commands for the Discord bot"""
    
    @bot.tree.command(name="ping", description="Check if the bot is working")
    async def ping(interaction: discord.Interaction):
        await interaction.response.send_message('Pong!')
    
    @bot.tree.command(name="clear", description="Clear a specific number of messages in the channel")
    async def clear(interaction: discord.Interaction, amount: int):
        """Clear a specific number of messages in the current channel.
        
        Parameters:
        -----------
        amount: int
            The number of messages to delete (1-100)
        """
        # Check if user is authorized
        if not is_authorized(interaction):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return
        
        # Validate the amount
        if amount < 1:
            await interaction.response.send_message("⚠️ You must delete at least 1 message.", ephemeral=True)
            return
        
        if amount > 100:
            await interaction.response.send_message("⚠️ You can only delete up to 100 messages at once.", ephemeral=True)
            return
        
        # Defer the response because deletion might take some time
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Delete messages
            deleted = await interaction.channel.purge(limit=amount)

            # Confirm to the user
            await interaction.followup.send(f"✅ Successfully deleted {len(deleted)} messages.", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have the necessary permissions to delete messages.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ An error occurred while deleting messages: {str(e)}", ephemeral=True) 
    
    @bot.tree.command(name="status", description="Display Z30 bot status")
    async def status(interaction: discord.Interaction):
        """Display Z30 bot status."""
        if not is_authorized(interaction):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return
        
        z30_process = is_z30_running()
        if z30_process:
            status_text = "🟢 Online"
            bot_uptime = get_z30_uptime(bot)
        else:
            status_text = "🔴 Offline"
            bot_uptime = "N/A"
        
        # Get system uptime
        system_uptime = get_system_uptime()
        
        cpu_usage, ram_usage, ping = get_system_info()
        
        embed = Embed(title="Z30 Status", color=Colour.blue())
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/720085385694150740/1351740001364480012/7tLHlm5.png?ex=67db797a&is=67da27fa&hm=5e083ea2f8200d810cf47fa55d9d0a0324a7d8c35881669ed4055ba5ad6ab088&=&width=484&height=968")
        
        embed.add_field(name="🤖 System Uptime", value=f"{system_uptime}", inline=True)
        embed.add_field(name="🌐 Bot Uptime", value=f"{bot_uptime}", inline=True)
        embed.add_field(name="📊 Ping", value=f"{ping}ms", inline=True)
        
        embed.add_field(name="🖥️ CPU Usage", value=f"{cpu_usage}%", inline=True)
        embed.add_field(name="💾 RAM Usage", value=f"{ram_usage}%", inline=True)
        embed.add_field(name="💻 OS", value="Windows", inline=True)
        
        embed.set_footer(text="PROJECT DECENT")
        
        await interaction.response.send_message(embed=embed)
    
    @bot.tree.command(name="restart", description="Restart the Z30 bot")
    async def restart(interaction: discord.Interaction):
        """Restart the Z30 bot."""
        if not is_authorized(interaction):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return
        
        z30_process = is_z30_running()
        if z30_process:
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            
            # Only send a response visible to the user
            await interaction.response.defer(ephemeral=True)
            
            if log_channel:
                await log_channel.send("```md\n# Restarting Z30 bot...\n```")
            
            # Terminate existing process
            z30_process.terminate()
            try:
                z30_process.wait(5)  # Wait up to 5 seconds for process to terminate
            except psutil.TimeoutExpired:
                # If the process doesn't terminate cleanly, kill it
                z30_process.kill()
            
            # Wait a bit to ensure the process is terminated
            await asyncio.sleep(2)
            
            # Start a new process
            subprocess.Popen(['start', 'cmd', '/k', 'python', Z30_SCRIPT_PATH], shell=True)
            
            # Update start time
            bot.z30_start_time = datetime.datetime.now()
            
            if log_channel:
                await log_channel.send("```md\n# Z30 bot successfully restarted!\n```")
            
            await interaction.followup.send("Z30 bot has been restarted.", ephemeral=True)
        else:
            await interaction.response.send_message(
                "```md\n# Z30 bot is not running. Use the `/start` command to start it.\n```", 
                ephemeral=True
            )
    
    @bot.tree.command(name="start", description="Start the Z30 bot if it's not already running")
    async def start(interaction: discord.Interaction):
        """Start the Z30 bot if it's not already running."""
        if not is_authorized(interaction):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return
        
        # Check if the bot is already running
        if is_z30_running():
            await interaction.response.send_message("```md\n# Z30 bot is already running.\n```", ephemeral=True)
            return
        
        # Remove lock file if it still exists
        if os.path.exists(LOCK_FILE):
            try:
                os.remove(LOCK_FILE)
                logger.info("Removed existing lock file before starting.")
            except IOError:
                pass
        
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        
        # Defer the response and make it ephemeral
        await interaction.response.defer(ephemeral=True)
        
        if log_channel:
            await log_channel.send("```md\n# Starting Z30 bot...\n```")
        
        # Start the process
        try:
            if os.name == 'nt':  # Windows
                subprocess.Popen(['python', Z30_SCRIPT_PATH], shell=False, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:  # Linux/Mac
                subprocess.Popen(['python3', Z30_SCRIPT_PATH], shell=False, start_new_session=True)
            
            # Wait for the lock file to appear
            max_retries = 10
            retry_count = 0
            while retry_count < max_retries:
                await asyncio.sleep(1)
                if os.path.exists(LOCK_FILE):
                    # Update start time
                    bot.z30_start_time = datetime.datetime.now()
                    
                    if log_channel:
                        await log_channel.send("```md\n# Z30 bot successfully started!\n```")
                    
                    await interaction.followup.send("Z30 bot has been started.", ephemeral=True)
                    return
                retry_count += 1
            
            # If we get here, the lock file didn't appear
            if log_channel:
                await log_channel.send("```md\n# Z30 bot may have failed to start. Check the logs.\n```")
            
            await interaction.followup.send("Z30 bot may have failed to start. Check the logs.", ephemeral=True)
            
        except Exception as e:
            if log_channel:
                await log_channel.send(f"```md\n# Error starting Z30 bot: {str(e)}\n```")
            
            await interaction.followup.send(f"Error starting Z30 bot: {str(e)}", ephemeral=True)
    
    @bot.tree.command(name="stop", description="Stop the Z30 bot if it's running")
    async def stop(interaction: discord.Interaction):
        """Stop the Z30 bot if it's running."""
        if not is_authorized(interaction):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return
        
        z30_process = is_z30_running()
        if not z30_process:
            await interaction.response.send_message("```md\n# Z30 bot is not running.\n```", ephemeral=True)
            return
        
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        
        # Defer the response and make it ephemeral
        await interaction.response.defer(ephemeral=True)
        
        if log_channel:
            await log_channel.send("```md\n# Stopping Z30 bot...\n```")
        
        # Terminate the process
        try:
            z30_process.terminate()
            
            # Wait up to 5 seconds for the process to terminate
            try:
                z30_process.wait(timeout=5)
            except psutil.TimeoutExpired:
                # If the process doesn't terminate, kill it forcefully
                z30_process.kill()
            
            # Remove the lock file if it still exists
            if os.path.exists(LOCK_FILE):
                try:
                    os.remove(LOCK_FILE)
                    logger.info("Removed lock file after stopping process.")
                except IOError:
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        # Reset start time
        bot.z30_start_time = None
        
        if log_channel:
            await log_channel.send("```md\n# Z30 bot successfully stopped!\n```")
        
        await interaction.followup.send("Z30 bot has been stopped.", ephemeral=True)

def is_authorized(interaction):
    """Check if the user has an authorized role."""
    if interaction.user.guild_permissions.administrator:
        return True
    
    return any(role.id in ADMIN_ROLE_IDS for role in interaction.user.roles)

def is_z30_running():
    """Check if Z30 bot is running using lock file."""
    lock_file = LOCK_FILE
    if os.path.exists(lock_file):
        try:
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())
                try:
                    # Check if the process with this PID still exists
                    proc = psutil.Process(pid)
                    return proc
                except psutil.NoSuchProcess:
                    # The process no longer exists, remove the stale file
                    try:
                        os.remove(lock_file)
                        logger.info(f"Removed stale lock file (PID {pid} not found)")
                    except IOError:
                        pass
                    return None
        except (ValueError, IOError):
            # Problem reading the file, try to remove it
            try:
                os.remove(lock_file)
                logger.info("Removed invalid lock file")
            except IOError:
                pass
            return None
    return None

def get_z30_uptime(bot):
    """Get Z30 bot uptime."""
    if bot.z30_start_time is None:
        # If start time is not recorded, try to detect it
        proc = is_z30_running()
        if proc:
            bot.z30_start_time = datetime.datetime.fromtimestamp(proc.create_time())
    
    if bot.z30_start_time:
        now = datetime.datetime.now()
        delta = now - bot.z30_start_time
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"
    
    return "Unknown"

def get_system_info():
    """Get system information."""
    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent
    ping = 105  # Fixed value, adjust as needed
    return cpu_usage, ram_usage, ping

def get_system_uptime():
    """Get system uptime."""
    try:
        boot_time = psutil.boot_time()
        boot_datetime = datetime.datetime.fromtimestamp(boot_time)
        now = datetime.datetime.now()
        delta = now - boot_datetime
        
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"
    except Exception as e:
        logger.error(f"Error getting system uptime: {e}")
        return "Unknown"