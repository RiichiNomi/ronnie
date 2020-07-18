# bot.py
import dotenv
import os
from os.path import join, dirname
import subprocess

from discord.ext import commands

from response import general

#LOAD BOT CONFIGURATION

env_path = join(dirname(__file__), 'config.env')
dotenv.load_dotenv('config.env')

PREFIXES = os.environ.get('command_prefixes').split()
TOKEN = os.environ.get('bot_token')
EXTENSIONS_ON_STARTUP_FILE = os.environ.get('extensions_on_startup_file')
EXTENSIONS_AFTER_STARTUP_FILE = os.environ.get('extensions_after_startup_file')

#INITIATE LIST OF EXTENSIONS TO LOAD BEFORE/AFTER STARTUP
try:
    with open(EXTENSIONS_ON_STARTUP_FILE, 'r') as f:
        EXTENSIONS_ON_STARTUP = f.readlines()
except FileNotFoundError:
    with open(EXTENSIONS_ON_STARTUP_FILE, 'w') as f:
        EXTENSIONS_ON_STARTUP = []

try:
    with open(EXTENSIONS_AFTER_STARTUP_FILE, 'r') as f:
        EXTENSIONS_AFTER_STARTUP = f.readlines()
except FileNotFoundError:
    with open(EXTENSIONS_AFTER_STARTUP_FILE, 'w') as f:
        EXTENSIONS_AFTER_STARTUP = []


#INSTANTIATE BOT
bot = commands.Bot(command_prefix=PREFIXES)

#EVENTS
@bot.event
async def on_ready():
    print("Connected")
    for extension in EXTENSIONS_AFTER_STARTUP:
        bot.load_extension(extension)

#COMMANDS
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send(general.PingMessage)

@bot.command(name='shutdown')
async def shutdown(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(f'{ctx.author.mention}' + general.UserNoAdminPermissions)
        return
    
    await ctx.send(general.ShutdownMessage)
    await bot.close()

@bot.command(name='restart')
async def restart(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(f'{ctx.author.mention}' + general.UserNoAdminPermissions)
        return 
    
    await ctx.send(general.RestartMessage)
    await bot.close()

    subprocess.run('start.sh')

@bot.command(name='load')
async def load_extension(ctx, extension_name): 
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(f'{ctx.author.mention}' + general.UserNoAdminPermissions)
        return 

    bot.load_extension(extension_name)

    await ctx.send(general.ExtensionLoadedMessage + f' "{extension_name}"')

@bot.command(name='unload')
async def unload_extension(ctx, extension_name):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(f'{ctx.author.mention}' + general.UserNoAdminPermissions)
        return 

    bot.unload_extension(extension_name)

    await ctx.send(general.ExtensionUnloadedMessage + f' "{extension_name}"')

@bot.command(name='reload')
async def reload_extension(ctx, extension_name=None):
    if (extension_name != None):
        bot.reload_extension(extension_name)

        await ctx.send(general.ExtensionReloadedMessage + f' "{extension_name}"')
    else:
        for extension in bot.extensions:
            bot.reload_extension(extension)
        
        await ctx.send(general.AllExtensionsReloadedMessage)

#START THE BOT
if __name__ == "__main__":
    for extension in EXTENSIONS_ON_STARTUP:
        bot.load_extension(extension)

    bot.run(TOKEN)