import asyncio
import json

from discord.ext import commands
from discord import Embed

from ext.HelpInterface.command_emojis import command_emojis

EMBED_JSON_FILE = 'ext/HelpInterface/help_embed.json'

ICHIHIME_THUMBNAIL = 'https://cdn.discordapp.com/attachments/740078597351538768/802301149427794020/ichihime-0.png'

class HelpInterface(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.help_embed = None

        self.create_help_embed()
    
    def create_help_embed(self):
        with open(EMBED_JSON_FILE, 'r') as f:
            embed_dict = json.load(f)

            self.help_embed = Embed.from_dict(embed_dict)

            for cog in self.bot.cogs.values():
                for command in cog.walk_commands():
                    if not command.hidden:
                        if command.name in command_emojis:
                            self.help_embed.add_field(name=f"{command_emojis[command.name]} {command.name}", value=command.short_doc, inline=True)
                        else:
                            self.help_embed.add_field(name=command.name, value=command.short_doc, inline=True)
    
    @commands.command(name='help')
    async def send_help_message(self, ctx, command_name:str=None):
        '''Displays this message.'''
        
        if command_name is None:
            await ctx.send(embed=self.help_embed)
        else:
            command = self.bot.get_command(command_name)

            if command is None:
                return
                
            title = f'{command.name}'

            if command.name in command_emojis:
                title = command_emojis[command.name] + ' ' + title
            
            description = f'{command.help}'
            embed = Embed(title=title, description=description)
            embed.set_thumbnail(url=ICHIHIME_THUMBNAIL)
            await ctx.send(embed=embed)
    

def setup(bot):
    bot.add_cog(HelpInterface(bot))

