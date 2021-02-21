import asyncio
import os

from discord.ext import commands

from modules.pymjsoul import mjsoul
from modules.pymjsoul.channel import MajsoulChannel
from modules.pymjsoul.client import MajsoulClient
from modules.pymjsoul.proto.combined import lq_dhs_pb2 as lq_dhs

class MajsoulClientInterface(commands.Cog):
    "Majsoul Client"
    def __init__(self, bot):
        self.bot = bot

        access_token = os.environ.get('mahjong_soul_access_token')
        if access_token is None:
            raise Exception('MajsoulClientInterface: missing mahjong_soul_access_token')

        self.client = MajsoulClient(lq_dhs, access_token)

    async def async_setup(self):
        servers = await mjsoul.get_recommended_servers()
        await self.client.connect(servers[0])
        await self.client.login()

    @commands.command(name='lq-connect', hidden=True)
    async def lq_connect(self, ctx):
        async with ctx.channel.typing():
            servers = await mjsoul.get_recommended_servers()
            
            if len(servers) == 0:
                await ctx.send('No game servers found.')
                return

            try:
                await self.client.connect(servers[0])
            except Exception as e:
                await ctx.send(f'Failed to connect to game server {servers[0]}')
            
            await ctx.send(f'Connected to game server {servers[0]}')
    
    @commands.command(name='lq-login', hidden=True)
    async def lq_login(self, ctx):
        async with ctx.channel.typing():
            if not self.client.websocket or not self.client.websocket.open:
                await self.lq_connect(ctx)
            
            try:
                result = await self.client.login()
            except Exception as e:
                print(e)
                await ctx.send('Unable to login to game server.')
                return
            
            await ctx.send('Logged in to game server.')

def setup(bot):
    i = MajsoulClientInterface(bot)
    bot.add_cog(i)
    asyncio.create_task(i.async_setup())
