import asyncio
import json
import random

from discord.ext import commands
from discord import Embed

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
        player = self.players.get(user.id, {
            'majsoul_name': None,
            'tenhou_name': None,
        })

        player['discord_name'] = user.name
        self.players[user.id] = player
    
    def exists(self, user):
        return user.id in self.players['discord_id'].values
    
    @commands.command(name='who')
    async def display_player_names(self, ctx):
        '''Displays your registered names.
        
        Usage: `ms/who`

        Displays the Majsoul and Tenhou names that have been registered for the Discord user.
        '''

        self.ensure(ctx.author)
        self.save()

        embed = Embed(description="Registered account names:")

        embed.set_author(name=f"{ctx.author.name}", icon_url=ctx.author.avatar_url)
        embed.set_thumbnail(url=ctx.author.avatar_url)

        embed.add_field(name="Majsoul", value=self.players[ctx.author.id]['majsoul_name'])
        embed.add_field(name="Tenhou", value=self.players[ctx.author.id]['tenhou_name'])

        await ctx.send(embed=embed)

    @commands.command(name='majsoul-name', aliases=['mahjsoul-name'])
    async def register_mahjsoul_name(self, ctx, name:str):
        '''Registers your majsoul name.
        
        Usage: `ms/majsoul-name <name>`

        Links your majsoul name to your Discord account. This is a prerequisite
        for being able to use `ms/pause` or `ms/unpause` without specifying
        that name.
        '''

        self.ensure(ctx.author)
        self.players[ctx.author.id]['majsoul_name'] = name
        self.save()

        await ctx.send(f'Majsoul nickname registered for {ctx.author.mention}.')
    
    @commands.command(name='tenhou-name')
    async def register_tenhou_name(self, ctx, name:str):
        '''Registers your tenhou name.
        
        Usage: `ms/tenhou-name <name>`
        
        Linkes your tenhou name to your Discord account. Currently this has no use.
        '''

        self.ensure(ctx.author)
        self.players[ctx.author.id]['tenhou_name'] = name
        self.save()

        await ctx.send(f'Tenhou nickname registered for {ctx.author.mention}.')
    
    @commands.command(name='display-names', hidden=True)
    async def display_names(self, ctx):
        '''Displays all names.'''
        print(self.players)

def setup(bot):
    bot.add_cog(PlayerNicknames(bot))
