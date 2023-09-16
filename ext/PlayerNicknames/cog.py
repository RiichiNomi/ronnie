import asyncio
import json
import random
import yaml

from discord.ext import commands
from discord import Embed, app_commands, Interaction, Object

NICKNAME_FILE = 'ext/PlayerNicknames/NAMES.json'

class PlayerNicknames(commands.Cog):
    """Player IDs"""
    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.load()

    def load(self):
        try:
            with open(NICKNAME_FILE, 'r') as f:
                self.players = json.load(f)
        except FileNotFoundError:
            pass
    
    def save(self):
        with open(NICKNAME_FILE, 'w') as f:
            json.dump(self.players, f)
    
    def ensure(self, user):
        player = self.players.get(str(user.id), {
            'majsoul_name': None,
            'tenhou_name': None,
        })

        player['discord_name'] = user.display_name
        self.players[str(user.id)] = player
    
    def exists(self, user):
        return user.id in self.players['discord_id'].values
    
    @app_commands.command(name='who')
    async def display_player_names(self, interaction : Interaction):
        '''Displays your registered names.
        
        Usage: `/who`

        Displays the Majsoul and Tenhou names that have been registered for the Discord user.
        '''
        await interaction.response.defer()

        self.ensure(interaction.user)
        self.save()

        embed = Embed(description="Registered account names:")

        embed.set_author(name=f"{interaction.user.display_name}", icon_url=interaction.user.avatar)
        embed.set_thumbnail(url=interaction.user.avatar)

        embed.add_field(name="Majsoul", value=self.players[str(interaction.user.id)]['majsoul_name'])
        embed.add_field(name="Tenhou", value=self.players[str(interaction.user.id)]['tenhou_name'])

        await interaction.followup.send(embed=embed)

    @app_commands.command(name='majsoul-name')
    @app_commands.describe(name='majsoul name to register')
    async def register_mahjsoul_name(self, interaction: Interaction, name:str):
        '''Registers your majsoul name.
        
        Usage: `/majsoul-name <name>`

        Links your majsoul name to your Discord account. This is a prerequisite
        for being able to use `ms/pause` or `ms/unpause` without specifying
        that name.
        '''
        await interaction.response.defer()

        self.ensure(interaction.user)
        self.players[str(interaction.user.id)]['majsoul_name'] = name
        self.save()

        await interaction.followup.send(f'Majsoul nickname registered for {interaction.user.mention}.')
    
    @app_commands.command(name='tenhou-name')
    @app_commands.describe(name='tenhou name to register')
    async def register_tenhou_name(self, interaction : Interaction, name:str):
        '''Registers your tenhou name.
        
        Usage: `/tenhou-name <name>`
        
        Linkes your tenhou name to your Discord account. Currently this has no use.
        '''
        await interaction.response.defer()

        self.ensure(interaction.user)
        self.players[str(interaction.user.id)]['tenhou_name'] = name
        self.save()

        await interaction.followup.send(f'Tenhou nickname registered for {interaction.user.mention}.')
    
    @commands.command(name='display-names', hidden=True)
    async def display_names(self, ctx):
        '''Displays all names.'''
        print(self.players)

async def setup(bot):
    with open('servers.yaml', 'r') as file:
        config_raw = yaml.safe_load(file)

    servers = [Object(id=int(server['server_id'])) for server in config_raw['servers']]
    await bot.add_cog(PlayerNicknames(bot), guilds=servers)
