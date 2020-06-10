from discord.ext import commands
import discord

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message = None
        self.num = 0
    
    @commands.command()
    async def test(self, ctx):
        response = '<:1man:718313488161964054>\n<:1man:718313488161964054>\n<:1man:718313488161964054>\n<:1man:718313488161964054>\n<:1man:718313488161964054>\n<:1man:718313488161964054>\n<:1man:718313488161964054>\n<:1man:718313488161964054>\n<:1man:718313488161964054>\n'
        await ctx.send(response)
    
    @commands.command()
    async def edit(self, ctx):
        response = f'{self.message.content}' + f'||{self.num}||'
        self.num += 1
        await self.message.edit(content=response)

    @commands.command(name='dream-crasher')
    async def meme_claire(self, ctx):
        await ctx.send('https://cdn.discordapp.com/attachments/685471499691229269/717926706089820170/photo_2020-05-20_22-15-57.jpg')

    @commands.command(name='cogs')
    async def show_cogs(self, ctx):
        response = f''
        for name in self.bot.cogs:
            response += f'{name}:\n'
            for command in self.bot.cogs[name].get_commands():
                print(command.__doc__)
    
        await ctx.send(response)

    @commands.command()
    async def attachments(self, ctx):
        await ctx.send(f'{ctx.message.attachments}')
    
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

