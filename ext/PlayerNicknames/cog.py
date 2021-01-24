import asyncio
import random

import pandas as pd
import pickle

from discord.ext import commands
from discord import Embed

PICKLE_FILE = 'ext/PlayerNicknames/NAMES.pickle'

class PlayerNicknames(commands.Cog):
    """Player IDs"""
    fields_formatted = ['Discord ID', 'Discord Name', 'Majsoul', 'Tenhou']
    fields = ['discord_id', 'discord_name', 'mahjsoul_name', 'tenhou_name']
    index = 'discord_id'
    def __init__(self, bot):
        self.bot = bot
        self.players = None

        self.initialize_database()

    def initialize_database(self):
        try:
            with open(PICKLE_FILE, 'rb') as f:
                self.players = pickle.load(f)
        except FileNotFoundError:
            self.players = pd.DataFrame(columns=self.fields)
            self.players.set_index(self.index, drop=True, inplace=True)
            with open(PICKLE_FILE, 'wb') as f:
                pickle.dump(self.players, f)
    
    def save(self):
        with open(PICKLE_FILE, 'wb') as f:
            pickle.dump(self.players, f)
    
    def check(self, user):
        if user.id not in self.players['discord_id'].values:
            self.players.loc[user.id] = [user.id, user.name, None, None]
        
        self.players['discord_name'][user.id] = user.name
    
    def exists(self, user):
        return user.id in self.players['discord_id'].values
    
    @commands.command(name='who')
    async def display_player_names(self, ctx):
        '''Displays your registered names.
        
        Usage: `ms/who`

        Displays the Majsoul and Tenhou names that have been registered for the Discord user.
        '''

        self.check(ctx.author)

        embed = Embed(description="Registered account names:")

        embed.set_author(name=f"{ctx.author.name}", icon_url=ctx.author.avatar_url)
        embed.set_thumbnail(url=ctx.author.avatar_url)

        embed.add_field(name="Majsoul", value=self.players['mahjsoul_name'][ctx.author.id])
        embed.add_field(name="Tenhou", value=self.players['tenhou_name'][ctx.author.id])

        await ctx.send(embed=embed)
        self.save()

    @commands.command(name='majsoul-name', aliases=['mahjsoul-name'])
    async def register_mahjsoul_name(self, ctx, name:str):
        '''Registers your majsoul name.
        
        Usage: `ms/majsoul-name <name>`

        Links your majsoul name to your Discord account. This is a prerequisite for being able to use `ms/pause` or `ms/unpause`.
        '''

        self.check(ctx.author)

        self.players['mahjsoul_name'][ctx.author.id] = name

        await ctx.send(f'Majsoul nickname registered for {ctx.author.mention}.')
        self.save()
    
    @commands.command(name='tenhou-name')
    async def register_tenhou_name(self, ctx, name:str):
        '''Registers your tenhou name.
        
        Usage: `ms/tenhou-name <name>`
        
        Linkes your tenhou name to your Discord account. Currently this has no use.
        '''

        self.check(ctx.author)

        self.players['tenhou_name'][ctx.author.id] = name

        await ctx.send(f'Tenhou nickname registered for {ctx.author.mention}.')
        self.save()
    
    @commands.command(name='display-names', hidden=True)
    async def display_names(self, ctx):
        '''Displays all names.'''
        print(self.players)


def setup(bot):
    bot.add_cog(PlayerNicknames(bot))