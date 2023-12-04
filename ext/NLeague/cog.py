import asyncio
import json
import yaml
import os

from discord.ext import commands
from discord import Embed, app_commands, Interaction, Object
from typing import Optional
import pandas as pd
import requests

QUERY_URL = 'https://www.wixapis.com/wix-data/v2/items/query'
NLEAGUE_LOGO_URL = 'https://static.wixstatic.com/media/3f033d_b6eb0d9e4c0b484a96bcf8be59f76138~mv2.jpg/v1/fill/w_1080,h_686,al_c,q_85,enc_auto/n_league_edited.jpg'

class NLeague(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.wix_token = os.environ.get('wix_token')
        self.wix_site_id = os.environ.get('wix_site_id')

    nleague = app_commands.Group(name="nleague", description="n-league commands")
    
    @nleague.command(name="standings", description="Display n-league standings")
    @app_commands.describe(season="(optional) N-league season.")
    @app_commands.choices(season=[
        app_commands.Choice(name="2", value=2),
        app_commands.Choice(name="1", value=1)])
    async def nleague_scores(self, interaction, season : Optional[app_commands.Choice[int]]):
        await interaction.response.defer()

        if season == None:
            season_num = 2
        else:
            season_num = season.value

        headers = {'wix-site-id': self.wix_site_id, 'Authorization': self.wix_token,
                    'Content-Type': 'application/json'}
        body = {"dataCollectionId": "NomiLeagueScores", "query": {"filter": {"season": 'S{}'.format(season_num)}, "fields": ["team", "score"], "paging": {"limit": 500}},
                "includeReferencedItems": ["team"]}
        r = requests.post(QUERY_URL, json=body, headers=headers)
        if r.status_code == 200:
            body = r.json()
            d = {}
            for item in body['dataItems']:
                if d.get(item['data']['team']['name']) == None:
                    d[item['data']['team']['name']] = item['data']['score']
                else:
                    d[item['data']['team']['name']] += item['data']['score']
            l = list(d.items())
            sorted_l = sorted(l, key=lambda team:-team[1])
            s = '```\n'


            embed = Embed(description="N League S{} Standings".format(season_num))
            embed.set_author(name=f"{self.bot.user.display_name}", icon_url=self.bot.user.avatar)


            s = '```'
            for i in range(len(sorted_l)):
                team = sorted_l[i]
                s += '{}. {:<25} {:<.1f}\n'.format(i + 1, team[0], team[1])
            s += '```'
            embed.add_field(name='Standings', value=s, inline=False)
            embed.set_thumbnail(url=NLEAGUE_LOGO_URL)
            await interaction.followup.send(s)
        else:
            await interaction.followup.send('Error pulling scores')

    @nleague.command(name="teams", description="Display n-league teams")
    @app_commands.describe(season="(optional) N-league season.")
    @app_commands.choices(season=[
        app_commands.Choice(name="2", value=2),
        app_commands.Choice(name="1", value=1)])
    async def nleague_teams(self, interaction, season : Optional[app_commands.Choice[int]]):
        await interaction.response.defer()

        if season == None:
            season_num = 2
        else:
            season_num = season.value
        
        headers = {'wix-site-id': self.wix_site_id, 'Authorization': self.wix_token,
                    'Content-Type': 'application/json'}
        body = {"dataCollectionId": "NomiLeagueTeams", "query": {"filter": {"season": 'S{}'.format(season_num)}}}
        r = requests.post(QUERY_URL, json=body, headers=headers)
        if r.status_code == 200:
            body = r.json()
            s = '```\n'
            embed = Embed(title='N League S{} Teams'.format(season_num))
            embed.set_author(name=f"{self.bot.user.display_name}", icon_url=self.bot.user.avatar)

            for team in body['dataItems']:
                embed.add_field(name=team['data']['name'], value='', inline=False)

            embed.set_thumbnail(url=NLEAGUE_LOGO_URL)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send('Error pulling scores')

    @app_commands.command(name="irl-stats", description="Pull irl stats")
    @app_commands.describe(name="Player name")
    async def irl_stats(self, interaction, name:str):
        await interaction.response.defer()

        headers = {'wix-site-id': self.wix_site_id, 'Authorization': self.wix_token,
                'Content-Type': 'application/json'}
        body = {"dataCollectionId": "Members", "query": {"filter": {"title": "{}".format(name)}, "paging": {"limit": 1}}}
        r = requests.post(QUERY_URL, json=body, headers=headers)
        if r.status_code == 200:
            body = r.json()

            if len(body['dataItems']) == 1:
                mem_id = body['dataItems'][0]['id']
                body = {"dataCollectionId": "Score", "query": {"filter": {"member": "{}".format(mem_id)}, "fields": ["Score", "uma", "penalty"], "paging": {"limit": 1000}}}

                r = requests.post(QUERY_URL, json=body, headers=headers)
                if r.status_code == 200:
                    body = r.json()

                    total = 0
                    count = 0
                    for score in body['dataItems']:
                        total += score['data']['Score'] + score['data']['uma'] + score['data']['penalty']
                        count += 1
                    
                    embed = Embed(description="IRL Scores")

                    if count == 0:
                        average = 'N/A'
                    else:
                        average = '{:.1f}'.format(total/count)

                    embed.set_author(name=f"{self.bot.user.display_name}", icon_url=self.bot.user.avatar)
                    embed.set_thumbnail(url='https://static.wixstatic.com/media/3f033d_06fbcec6270d431082ed5f820c0efd86~mv2.png/v1/fill/w_422,h_422,al_c,q_85,usm_0.66_1.00_0.01,enc_auto/RATCHINOMI_AV_med.png')

                    embed.add_field(name='Name', value=name, inline=True)
                    embed.add_field(name="Score", value="{:.1f}".format(total), inline=True)
                    embed.add_field(name="Games", value=count, inline=True)
                    embed.add_field(name="Average", value=average, inline=True)

                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send('Error pulling scores for {}'.format(name))
            else: 
                await interaction.followup.send('Error finding user {}'.format(name))
        else: 
            await interaction.followup.send('Error finding user {}'.format(name))




async def setup(bot):
    i = NLeague(bot)
    with open('servers.yaml', 'r') as file:
        config_raw = yaml.safe_load(file)

    servers = [Object(id=int(server['server_id'])) for server in config_raw['servers']]

    await bot.add_cog(NLeague(bot), guilds=servers)