# bot.py
import os
import time

from discord.ext import commands
from dotenv import load_dotenv

from extensions_startup import startup_extensions
from extensions_after import after_startup_extensions

#LOAD ENVIRONMENT VARIABLES
load_dotenv('variables.env')

PREFIX = os.environ.get('COMMAND_PREFIX')
TOKEN = os.environ.get('BOT_TOKEN')

#INSTANTIATE BOT
bot = commands.Bot(command_prefix=PREFIX)

#LIST TRACKING LOADED EXTENSIONS

loaded = []

#EVENTS

@bot.event
async def on_ready():
    print("Connected")
    for extension in after_startup_extensions:
        bot.load_extension(extension)

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
    loaded.append(extension_name)

    response = f'Loaded extension "{extension_name}"'
    await ctx.send(response)

@bot.command(name='unload')
@commands.has_permissions(administrator=True)
async def unload_extension(ctx, extension_name):
    '''
    Unloads a given extension
    '''

    bot.unload_extension(extension_name)
    loaded.remove(extension_name)

    response = f'Unloaded extension "{extension_name}"'
    await ctx.send(response)

@bot.command(name='reload')
@commands.has_permissions(administrator=True)
async def reload_extension(ctx, extension_name=None):
    '''
    Reloads a given extension
    '''
    if (extension_name != None):
        bot.reload_extension(extension_name)

        response = f'Reloaded extension "{extension_name}"'
        await ctx.send(response)
    else:
        for extension in loaded:
            bot.reload_extension(extension)
        
        await ctx.send("Reloaded all extensions.")

#START THE BOT
if __name__ == "__main__":
    bot.remove_command('help')
    for extension in startup_extensions:
        bot.load_extension(extension)
        loaded.append(extension)

    bot.run(TOKEN)