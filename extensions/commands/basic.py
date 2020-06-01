from discord.ext import commands
import discord

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def marco(self, ctx):
        await ctx.send("polo")

    @commands.command()
    async def mention_user(self, ctx):
        await ctx.send(f'<@{ctx.author.id}>')

    @commands.command()
    async def display_nickname(self, ctx):
        await ctx.send(ctx.author.nick)

    @commands.command()
    async def display_author(self, ctx):
        response = f'''
            {ctx.author}
        '''
        await ctx.send(response)
    
    @commands.command()
    async def display_roles(self, ctx):
        response = f'''
            Roles for @{ctx.author}: {ctx.author.roles}
        '''
        await ctx.send(response)
    
    @commands.command()
    async def display_id(self, ctx):
        response = f'''
            Discord ID for @{ctx.author}: {ctx.author.id}
        '''

        await ctx.send(response)

def setup(bot):
    bot.add_cog(BasicCommands(bot))

