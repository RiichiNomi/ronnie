import asyncio
import json
import yaml

from discord.ext import commands
from discord import Embed, app_commands, Interaction, Object, Permissions
from typing import Optional

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

                for command in cog.walk_app_commands():
                    if not command.default_permissions or not command.default_permissions.administrator:
                        if command.name in command_emojis:
                                self.help_embed.add_field(name=f"{command_emojis[command.name]} {command.name}", value=command.description, inline=True)
                        else:
                            self.help_embed.add_field(name=command.name, value=command.description, inline=True)

    @app_commands.command(name="help", description="Display the help message.")
    @app_commands.describe(command_name="(optional) Command to learn more about.")
    async def help(self, interaction, command_name : Optional[str]):
        await interaction.response.defer()

        # general help message
        if command_name is None:
            await interaction.followup.send(embed=self.help_embed)
        else:
            command = self.bot.get_command(command_name)

            for cog in self.bot.cogs.values():
                for c in cog.walk_app_commands():
                    if c.name == command_name and (not c.default_permissions or interaction.permissions >= c.default_permissions):
                        command = c
                        break

            if command is None:
                await interaction.followup.send('Could not find command {}'.format(command_name))
                return
                
            title = f'{command.name}'

            if command.name in command_emojis:
                title = command_emojis[command.name] + ' ' + title
            
            try:
                description = f'{command.help}'
            except AttributeError:
                description = f'{command.description}'
            embed = Embed(title=title, description=description)
            embed.set_thumbnail(url=ICHIHIME_THUMBNAIL)
            await interaction.followup.send(embed=embed)
    

async def setup(bot):
    with open('servers.yaml', 'r') as file:
        config_raw = yaml.safe_load(file)

    servers = [Object(id=int(server['server_id'])) for server in config_raw['servers']]
    await bot.add_cog(HelpInterface(bot), guilds=servers)

