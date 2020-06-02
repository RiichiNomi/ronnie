# bot.py
import os
import time

from discord.ext import commands
from dotenv import load_dotenv

#LOAD ENVIRONMENT VARIABLES
load_dotenv('variables.env')

EXTENSIONS_FILE = 'startup_extensions.txt'
PREFIX = '!'
TOKEN = os.environ.get('BOT_TOKEN')

#INSTANTIATE BOT
bot = commands.Bot(command_prefix=PREFIX)

#EVENTS

@bot.event
async def on_ready():
    print("Connected")

#COMMANDS

@bot.command()
async def ping(ctx):
    await ctx.send('ping')

@bot.command(name='shutdown')
@commands.has_permissions(administrator=True)
async def shutdown(ctx):
    '''
    Shuts the bot down. Right now anyone can shut it down, will have to add permission checks later
    '''

    await ctx.send("Turning myself off now...")
    await bot.close()

@bot.command(name='load')
@commands.has_permissions(administrator=True)
async def load_extension(ctx, extension_name):
    '''
    Loads a given extension
    '''
    
    bot.load_extension(extension_name)

    response = f'Loaded extension "{extension_name}"'
    await ctx.send(response)

@bot.command(name='unload')
@commands.has_permissions(administrator=True)
async def unload_extension(ctx, extension_name):
    '''
    Unloads a given extension
    '''

    bot.unload_extension(extension_name)

    response = f'Unloaded extension "{extension_name}"'
    await ctx.send(response)

@bot.command(name='reload')
@commands.has_permissions(administrator=True)
async def reload_extension(ctx, extension_name):
    '''
    Reloads a given extension
    '''
    bot.reload_extension(extension_name)

    response = f'Reloaded extension "{extension_name}"'
    await ctx.send(response)

#START THE BOT
if __name__ == "__main__":
    with open(EXTENSIONS_FILE, 'r') as f:
        startup_extensions = f.read().split('\n')
    
    for extension in startup_extensions:
        bot.load_extension(extension)

    bot.remove_command('help')

    bot.run(TOKEN)