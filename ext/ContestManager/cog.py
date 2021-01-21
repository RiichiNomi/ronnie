import asyncio
import random

from discord.ext import commands

from modules.pymjsoul import mjsoul
from modules.pymjsoul.channel import MajsoulChannel
from modules.pymjsoul.client import ContestManagerClient
from modules.pymjsoul.proto.combined import lq_dhs_pb2 as lq_dhs

class ContestManagerInterface(commands.Cog):
    PAUSE_COOLDOWN_DURATION = 5
    def __init__(self, bot):
        self.bot = bot 
        self.client = ContestManagerClient(lq_dhs)
        
        self.main_channel = None
        self.list_message = None

        self.pause_trackers = []
        self.pause_tracker_lock = asyncio.Lock()
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if self.list_message and reaction.message.id != self.list_message.id:
            return
        
        await reaction.remove(user)

        if str(reaction.emoji) == '\U0001F3B2':
            await self.shuffle(reaction.message.channel)
        
    @commands.command(name='connect')
    async def dhs_connect(self, ctx):
        async with ctx.channel.typing():
            servers = await mjsoul.get_contest_management_servers()
            
            if len(servers) == 0:
                await ctx.send('No servers found.')
                return

            try:
                await self.client.connect(servers[0])
            except Exception as e:
                await ctx.send(f'Failed to connect to {servers[0]}')
            
            await ctx.send(f'Connected to {servers[0]}')


    @commands.command(name='login')
    async def dhs_login(self, ctx):
        async with ctx.channel.typing():
            if not self.client.websocket or not self.client.websocket.open:
                await self.dhs_connect(ctx)
            
            try:
                result = await self.client.login()
            except Exception as e:
                print(e)
                await ctx.send('Unable to login.')
                return
            
            await ctx.send('Logged in to contest manager.')

        
        asyncio.create_task(self.notify_listener())
    
    @commands.command(name='pause')
    async def dhs_pause(self, ctx):
        async with ctx.channel.typing():
            if not self.client.websocket or not self.client.websocket.open:
                await ctx.send('Client not connected.')
                return

            PlayerNicknamesCog = self.bot.get_cog('PlayerNicknames')
            p = PlayerNicknamesCog.players

            if ctx.author.id not in p['discord_id'].values or p['mahjsoul_name'][ctx.author.id] != None:
                nickname = p['mahjsoul_name'][ctx.author.id]
            else:
                await ctx.send(f'No Mahjsoul name registered for {ctx.author.mention}. Type ms/mahjsoul-name <your-mahjsoul-name> to register.')
                return
            
            game_uuid = await self.client.get_game_id(nickname)

            if game_uuid == None:
                await ctx.send(f'Unable to find in-progress game for {nickname}')
                return
            
            try:
                await self.client.pause(game_uuid)
            except Exception as e:
                await ctx.send('Unable to pause game.')
                return
            
            await ctx.send(f'Game paused for {nickname}')
    
    @commands.command(name='unpause', aliases=['resume'])
    async def dhs_unpause(self, ctx):
        async with ctx.channel.typing():
            if not self.client.websocket or not self.client.websocket.open:
                await ctx.send('Client not connected.')
                return

            PlayerNicknamesCog = self.bot.get_cog('PlayerNicknames')
            p = PlayerNicknamesCog.players

            if ctx.author.id not in p['discord_id'].values or p['mahjsoul_name'][ctx.author.id] != None:
                nickname = p['mahjsoul_name'][ctx.author.id]
            else:
                await ctx.send(f'No Mahjsoul name registered for {ctx.author.mention}. Type ms/mahjsoul-name <your-mahjsoul-name> to register.')
                return
            
            game_uuid = await self.client.get_game_id(nickname)

            if game_uuid == None:
                await ctx.send(f'Unable to find in-progress game for {nickname}')
                return
            
            try:
                result = await self.client.unpause(game_uuid)
            except Exception as e:
                await ctx.send('Unable to unpause game.')
                return
            
            await ctx.send(f'Game unpaused for {nickname}')
    
    
    @commands.command(name='manage')
    async def dhs_manage_contest(self, ctx, lobbyID:int):
        async with ctx.channel.typing():
            if not self.client.websocket or not self.client.websocket.open:
                await ctx.send('Client not connected.')
                return
            
            try:
                await self.client.call('manageContest', unique_id=lobbyID)
            except Exception as e:
                print(e)
                await ctx.send(f'Unable to manage {lobbyID}')
                return
            
            await ctx.send(f"Entered lobby management for lobby {lobbyID}.")


    @commands.command(name='list')
    async def dhs_show_active_players(self, ctx):
        self.main_channel = ctx.channel
        async with ctx.channel.typing():
            if not self.client.websocket or not self.client.websocket.open:
                await ctx.send('Client not connected.')
                return

            if self.list_message != None:
                await self.list_message.edit(content=f'*{self.list_message.content}*')
            
            list_display = await self.client.display_players()

            list_display += '\n    \U000021E9 Click here to shuffle.'

            self.list_message = await self.main_channel.send(list_display)

            await self.list_message.add_reaction('\U0001F3B2')
    
    async def shuffle(self, discord_channel):
        while True:
            players = await self.client.active_players
            if len(players) >= 4:
                table = []
                for i in range(0, 4):
                    p = random.choice(players)
                    players.remove(p)
                    table.append(p)
                
                await self.client.create_game([p.account_id for p in table])
                await discord_channel.send(f"Game starting for {table[0].nickname} | {table[1].nickname} | {table[2].nickname} | {table[3].nickname}")
            else:
                break

            list_display = await self.client.display_players()
            list_display += '\n    \U000021E9 Click here to shuffle.'
            await self.list_message.edit(content=list_display)
    
    @commands.command(name='shuffle')
    async def dhs_create_random_games(self, ctx):
        async with ctx.channel.typing():
            await self.shuffle(ctx.channel)
    
    @commands.command(name='test')
    async def test_record_game(self, ctx):
        players = [(1, 'AAAA'), (2, 'BBBB'), (3, 'CCCC'), (4, 'DDDD')]
        points = [47200, 46500, 13800, 12500]

        TournamentScoreTracker = self.bot.get_cog('TournamentScoreTracker')

        await TournamentScoreTracker.record_game(players, points)

    async def notify_listener(self):
        while True:
            await self.client.NotifyReceivedEvent.wait()
            name, msg = self.client.MostRecentNotify

            self.client.NotifyReceivedEvent.clear()

            if name == 'NotifyContestMatchingPlayer':
                await self.on_NotifyContestMatchingPlayer(msg)
            elif name == 'NotifyContestGameEnd':
                await self.on_NotifyContestGameEnd(msg)
    
    async def on_NotifyContestGameEnd(self, msg):
        uuid = msg.game_uuid

       
        MajsoulClientInterface = self.bot.get_cog('MajsoulClientInterface')

        log = await MajsoulClientInterface.client.fetch_game_log(uuid)

        points = [player.part_point_1 for player in log.head.result.players]

        seats = [player.seat for player in log.head.result.players]

        players = [(log.head.accounts[s].account_id, log.head.accounts[s].nickname) for s in seats]
        TournamentScoreTracker = self.bot.get_cog('TournamentScoreTracker')

        scores = await TournamentScoreTracker.record_game(players, points)

        response = f'Game concluded for {players[0][1]}({scores[0]}) | {players[1][1]}({scores[1]}) | {players[2][1]}({scores[2]}) | {players[3][1]}({scores[3]})'
        await self.main_channel.send(response)

        if self.list_message != None:
            list_display = await self.client.display_players()
            await self.list_message.edit(content=list_display)
    
    async def on_NotifyContestMatchingPlayer(self, msg):
        if self.main_channel == None:
            return

        prev_active = set([p.nickname for p in self.client._active_players])
        prev_playing = set([p.nickname for g in self.client._ongoing_games for p in g.players])
        PREV = prev_active #| prev_playing

        res = await self.client.call('startManageGame')

        now_active = set([p.nickname for p in res.players])
        now_playing = set([p.nickname for g in res.games for p in g.players])
        NOW = now_active #| now_playing

        changes = PREV ^ NOW   #symmetric difference; elements in old or new, but not both

        for player in changes:
            if player in PREV:
                #player left the lobby
                '''
                if player in prev_active:
                    await self.main_channel.send(f"{player} left the lobby.")
                '''
            else:
                #player joined the lobby
                #await self.main_channel.send(f"{player} joined the lobby.")
                pass
        
        if self.list_message != None:
            list_display = await self.client.display_players(res)
            list_display += '\n    \U000021E9 Click here to shuffle.'
            await self.list_message.edit(content=list_display)
            

def setup(bot):
    bot.add_cog(ContestManagerInterface(bot))

if __name__ == "__main__":
    server = asyncio.run(mjsoul.get_contest_management_servers())[0]
    client = ContestManagerClient(server, dhs)

    asyncio.run(client.login())
