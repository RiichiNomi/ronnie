import asyncio
import json
import yaml

from discord.ext import commands
from discord import Embed, app_commands, Interaction, Object
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

    @app_commands.command(name="help", description="Display the help message.")
    @app_commands.describe(command_name="(optional) Command to learn more about.")
    # TODO: make this come from the bot?
    @app_commands.choices(command_name=[
        app_commands.Choice(name="scores", value="scores"),
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="register", value="register"),
        app_commands.Choice(name="who", value="who"),
        app_commands.Choice(name="pause", value="pause"),
        app_commands.Choice(name="unpause", value="unpause")])
    async def help(self, interaction, command_name : Optional[app_commands.Choice[str]]):
        await interaction.response.defer()

        # general help message
        if command_name is None:
            await interaction.followup.send(embed=self.help_embed)
        else:
            command = self.bot.get_command(command_name.value)

            if command is None:
                return
                
            title = f'{command.name}'

            if command.name in command_emojis:
                title = command_emojis[command.name] + ' ' + title
            
            description = f'{command.help}'
            embed = Embed(title=title, description=description)
            embed.set_thumbnail(url=ICHIHIME_THUMBNAIL)
            await interaction.followup.send(embed=embed)
    

async def setup(bot):
    with open('servers.yaml', 'r') as file:
        config_raw = yaml.safe_load(file)

    servers = [Object(id=int(server['server_id'])) for server in config_raw['servers']]
    await bot.add_cog(HelpInterface(bot), guilds=servers)

