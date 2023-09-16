# bot.py
import dotenv
import os
from os.path import join, dirname
import subprocess

from discord import Intents
from discord.ext import commands

#LOAD BOT CONFIGURATION

env_path = join(dirname(__file__), 'config.env')
dotenv.load_dotenv('config.env')

PREFIXES = os.environ.get('command_prefixes').split()
DISCORD_TOKEN = os.environ.get('bot_token')
EXTENSIONS_FILE = os.environ.get('extensions_file')

if DISCORD_TOKEN is None:
    raise Exception("Missing bot_token in config.env")

#INITIATE LIST OF EXTENSIONS TO LOAD AFTER STARTUP

try:
    with open(EXTENSIONS_FILE, 'r') as f:
        EXTENSIONS = [l.strip('\n') for l in f.readlines()]
except FileNotFoundError:
    with open(EXTENSIONS_FILE, 'w') as f:
        EXTENSIONS = []

#INSTANTIATE BOT
# Ronnie needs message content, reactions, and guilds (for role monitoring)
intents = Intents(messages=True, reactions=True, message_content=True, guilds=True)
bot = commands.Bot(command_prefix=PREFIXES, intents=intents)

#EVENTS
@bot.event
async def on_ready():
    print("Connected")

# handle regular cmd errors
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.errors.NotOwner):
        await ctx.send(f"Missing privileges for this cmd")
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.send(f"Command not found")
    else:
        raise error


#COMMANDS
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send("Ping")

@bot.command(name='shutdown', hidden=True)
async def shutdown(ctx):
    await ctx.send("Shutting down...")
    await bot.close()

@bot.command(name='restart', hidden=True)
async def restart(ctx): 
    await ctx.send("Restarting...")
    await bot.close()

    subprocess.run('./start.sh')

@bot.command(name='load', hidden=True)
async def load_extension(ctx, extension_name): 
    bot.load_extension(extension_name)

    await ctx.send(f"Loaded extension: {extension_name}")

@bot.command(name='unload', hidden=True)
async def unload_extension(ctx, extension_name): 
    bot.unload_extension(extension_name)

    await ctx.send(f"Unloaded extension: {extension_name}")

@bot.command(name='reload', hidden=True)
async def reload_extension(ctx, extension_name=None):
    if (extension_name != None):
        bot.reload_extension(extension_name)

        await ctx.send(f"Reloaded extension: {extension_name}")
    else:
        for extension in bot.extensions:
            bot.reload_extension(extension)
        
        await ctx.send(f"Reloaded all extensions.")

@bot.command(name='sync', hidden=True)
async def sync(ctx: commands.Context):
    await bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"Updated slash commands for {ctx.guild.name}.")

async def setup():
    for extension in EXTENSIONS:
        print(f'Loading extension: {extension}')
        await bot.load_extension(extension)

#START THE BOT
if __name__ == "__main__":
    bot.remove_command('help')
    bot.setup_hook = setup
    bot.run(DISCORD_TOKEN)
