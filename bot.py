# bot.py
import os
import time
import json
import subprocess

from discord.ext import commands

from response import general

import nacl

#LOAD BOT CONFIGURATION
with open('config.json', 'r') as f:
    config = json.load(f)

PREFIXES = config['command_prefixes']
TOKEN = config['bot_token']

#INSTANTIATE BOT
bot = commands.Bot(command_prefix=PREFIXES)

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
    bot.remove_command('help')
    bot.run(TOKEN)