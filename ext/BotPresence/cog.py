import asyncio

import discord
from discord.ext import commands

class BotPresenceInterface(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name='set-bot-activity', hidden=True)
    @commands.has_permissions(administrator=True)
    async def set_bot_activity_name(self, ctx):
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="ms/help"))

async def setup(bot):
    await bot.add_cog(BotPresenceInterface(bot))