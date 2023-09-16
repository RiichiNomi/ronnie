import asyncio
import json
import yaml

from discord.ext import commands
from discord import Embed, app_commands, Interaction, Object
from typing import Optional
import pandas as pd

class NLeague(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    nleague = app_commands.Group(name="nleague", description="n-league commands")
    
    @nleague.command(name="standings", description="Display n-league standings")
    @app_commands.describe(season="(optional) N-league season.")
    @app_commands.choices(season=[
        app_commands.Choice(name="2", value=2),
        app_commands.Choice(name="1", value=1)])
    async def nleague_scores(self, interaction, season : Optional[app_commands.Choice[int]]):
        await interaction.response.defer()

        format_str = '{:<5}\t{:<22}\t{:<12}\t{:<12}\t{:<5}\n'

        s = '```'
        s += format_str.format('Rank', 'Team Name', 'Total Score', '# Games', 'Margin')
        s += format_str.format(1, 'Queens Mahjong Triad', 446.2, 19, '-')
        s += format_str.format(2, 'The Destroyers', 224.0, 19, 222.2)
        s += format_str.format(3, 'Brooklyn Sours', 62.0, 19, 162.0)
        s += format_str.format(4, 'Team Yakumen', -38.7, 16, 100.7)
        s += format_str.format(5, 'The Emperor Penguins', -47.4, 16, 8.7)
        s += format_str.format(6, 'The Peregrine FalKANs', -75.0, 19, 27.6)
        s += format_str.format(7, 'Opie Dopes', -133.0, 16, 58.0)
        s += format_str.format(8, 'Rinshan Kaibros', -466.1, 16, 333.1)
        s += '```'


        # default to the most recent season
        if season is None or season.value == 2:
            await interaction.followup.send('```Coming soon!```')
        else:
            await interaction.followup.send(s)

    @nleague.command(name="teams", description="Display n-league teams")
    @app_commands.describe(season="(optional) N-league season.")
    @app_commands.choices(season=[
        app_commands.Choice(name="2", value=2),
        app_commands.Choice(name="1", value=1)])
    async def nleague_teams(self, interaction, season : Optional[app_commands.Choice[int]]):
        await interaction.response.defer()
        
        nleague_teams = ['The Peregrine FalKANs', 'Brooklyn Sours', 
                            'Opie Dopes', 'The Emperor Penguins',
                            'Queens Mahjong Triad', 'Team Yakumen',
                            'The Destroyers']
        
        nleague_season1 = [team for team in nleague_teams]
        nleague_season1.append('Rinshan Kaibros')
        nleague_teams.append('Dora Neko')

        # default to the most recent season
        if season is None or season.value == 2:
            season_num = 2
            s = f"N League Season {season_num} Teams:\n"
            for team in nleague_teams:
                s += team + '\n'
            await interaction.followup.send(s)

        else:
            s = f"N League Season {season.value} Teams:\n"
            for team in nleague_season1:
                s += team + '\n'
            await interaction.followup.send(s)



async def setup(bot):
    i = NLeague(bot)
    with open('servers.yaml', 'r') as file:
        config_raw = yaml.safe_load(file)

    servers = [Object(id=int(server['server_id'])) for server in config_raw['servers']]

    await bot.add_cog(NLeague(bot), guilds=servers)