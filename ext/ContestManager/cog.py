import asyncio
import random

from discord.ext import commands
from discord import Embed

from modules.pymjsoul import mjsoul
from modules.pymjsoul.channel import MajsoulChannel
from modules.pymjsoul.client import ContestManagerClient
from modules.pymjsoul.proto.combined import lq_dhs_pb2 as lq_dhs

class ContestManagerInterface(commands.Cog):
    """Tournament Lobby"""
    def __init__(self, bot):
        self.bot = bot 
        self.cog_display_name = "Tournament Lobby"

        self.client = ContestManagerClient(lq_dhs)
        self.contest = None
        
        self.main_channel = None
        self.list_message = None
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if self.list_message and reaction.message.id != self.list_message.id:
            return
        
        await reaction.remove(user)

        if str(reaction.emoji) == '\U0001F3B2':
            await self.shuffle(reaction.message.channel)
    
    @commands.command(name='rules')
    async def display_tournament_rules(self, ctx):
        '''
        Displays the game rules.

        Usage: `ms/rules`

        Displays a summary of the game rules that the current tournament lobby implements.
        '''
        if not self.client.websocket or not self.client.websocket.open:
                await ctx.send('Client not connected.')
                return

        embed = Embed(title=self.contest.contest_name, description='Ruleset Summary:')

        embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/740078597351538768/802301149427794020/ichihime-0.png')

        res = await self.client.call('fetchContestGameRule')

        rules = res.game_rule_setting

        if rules.dora_count == 0:
            embed.add_field(name='Red Fives', value=False)
        else:
            embed.add_field(name='Red Fives', value=rules.dora_count)

        if rules.thinking_type == 1:
            embed.add_field(name='Thinking Time', value='3+5s')
        elif rules.thinking_type == 2:
            embed.add_field(name='Thinking Time', value='5+10s')
        elif rules.thinking_type == 3:
            embed.add_field(name='Thinking Time', value='5+20s')
        elif rules.thinking_type == 4:
            embed.add_field(name='Thinking Time', value='60+0s')

        if res.game_rule_setting.use_detail_rule:
            rules = res.game_rule_setting.detail_rule_v2.game_rule
            #Starting Points
            embed.add_field(name='Starting Points', value=rules.init_point)
            #Uma Calculation
            shunweima_1 = (int)(-1*(rules.shunweima_2 + rules.shunweima_3 + rules.shunweima_4))
            embed.add_field(name='Uma', value=f'{shunweima_1}/{rules.shunweima_2}/{rules.shunweima_3}/{rules.shunweima_4}')
            #Agari Yame
            embed.add_field(name='Agari Yame', value=rules.have_helezhongju)
            #Busting On
            embed.add_field(name='Busting On', value=rules.can_jifei)
            #Nagashi Mangan
            embed.add_field(name='Nagashi Mangan', value=rules.have_liujumanguan)
            #Kiriage Mangan
            embed.add_field(name='Kiriage Mangan', value=rules.have_qieshangmanguan)
            #Four Winds Abort
            embed.add_field(name='Four Wind Abort', value=rules.have_sifenglianda)
            #Four Kan Abort
            embed.add_field(name='Four Kan Abort', value=rules.have_sigangsanle)
            #Four Riichi Abort
            embed.add_field(name='Four Riichi Abort', value=rules.have_sijializhi)
            #Nine Terminals Honors Abort
            embed.add_field(name='Nine Terminals Honors Abort', value=rules.have_jiuzhongjiupai)
            #Triple Ron Abort
            embed.add_field(name='Triple Ron Abort', value=rules.have_sanjiahele)
            #Head Bump
            embed.add_field(name='Head Bump', value=rules.have_toutiao)
            #Multiple Yakuman
            embed.add_field(name='Multiple Yakuman', value=not rules.disable_multi_yukaman)
        
        await ctx.send(embed=embed)

        
    @commands.command(name='connect', hidden=True)
    async def dhs_connect(self, ctx):
        '''Test Doc
        
        Second Line
        '''
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

    @commands.command(name='login', hidden=True)
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
    async def dhs_pause(self, ctx, nickname:str = None):
        '''Pauses the game.
        
        Usage: `ms/pause <majsoul-user>`

        Pauses an ongoing game for `<majsoul-user>`. If the command is invoked without any arguments, the bot will use the Majsoul name registered to the Discord user who invoked the command.
        '''
        
        async with ctx.channel.typing():
            if not self.client.websocket or not self.client.websocket.open:
                await ctx.send('Client not connected.')
                return

            if nickname is None:
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
    async def dhs_unpause(self, ctx, nickname:str = None):
        '''Resumes the game.

        Usage: `ms/unpause <majsoul-user>`

        Resumes an ongoing game for `<majsoul-user>`. If the command is invoked without any arguments, the bot will use the Majsoul name registered to the Discord user who invoked the command.
        '''

        async with ctx.channel.typing():
            if not self.client.websocket or not self.client.websocket.open:
                await ctx.send('Client not connected.')
                return

            if nickname is None:
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
    
    
    @commands.command(name='manage', hidden=True)
    async def dhs_manage_contest(self, ctx, lobbyID:int):

        async with ctx.channel.typing():
            if not self.client.websocket or not self.client.websocket.open:
                await ctx.send('Client not connected.')
                return
            
            try:
                res = await self.client.call('manageContest', unique_id=lobbyID)
                self.contest = res.contest
            except Exception as e:
                print(e)
                await ctx.send(f'Unable to manage {lobbyID}')
                return
            
            await ctx.send(f"Entered lobby management for lobby {lobbyID}.")


    @commands.command(name='list')
    async def dhs_show_active_players(self, ctx):
        '''Displays the lobby.
        
        Usage: `ms/list`

        Displays the names of all players who are currently queued up in the Majsoul tournament lobby.
        '''

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
        '''Starts randomly matched games.
        
        Usage: `ms/shuffle`

        Selects four random players who are queued up in the tournament lobby and starts a game for them. Does this repeatedly until there are no longer enough players for a full table.
        '''

        async with ctx.channel.typing():
            await self.shuffle(ctx.channel)

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
