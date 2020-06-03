from discord.ext import commands
import discord

class Meme():
    def __init__(self, name):
        self.name = name
        self.filename = None

class MemesInterface(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.memes_list = []
    
    @commands.command(name='meme')
    async def send_meme(self, ctx):
        pass

def setup(bot):
    bot.add_cog(MemesInterface(bot))