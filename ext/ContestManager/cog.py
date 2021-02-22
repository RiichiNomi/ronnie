import asyncio
import csv
from itertools import islice, chain, repeat
import os
import random

from discord.ext import commands
from discord import Embed

from modules.pymjsoul import mjsoul
from modules.pymjsoul.channel import MajsoulChannel, GeneralMajsoulError
from modules.pymjsoul.client import ContestManagerClient
from modules.pymjsoul.proto.combined import lq_dhs_pb2 as lq_dhs

WINDS = [
    'East \U0001F000',
    'South \U0001F001',
    'West \U0001F002',
    'North \U0001F003',
]

ROUND_TYPES = [
    None,
    '4-Player East',
    '4-Player South',
    '4-Player (vs AI)',
    '4-Player (1 Game)',
    None,
    None,
    None,
    None,
    None,
    None,
    '3-Player East', # index 11
    '3-Player South',
    '3-Player (vs AI)',
    '3-Player (1 Game)',
]

THINKING_TIMES = [
    None,
    '3+5s',
    '5+10s',
    '5+20s',
    '60+0s',
]

REACTION_BOT = '\U0001F916'
REACTION_HUMAN = '\U0001F3B2'

EMOJI_MAHJONG_TILE = '\U0001F004'
EMOJI_RED_CIRCLE = '\U0001F534'
EMOJI_GREEN_CIRCLE = '\U0001F7E2'

# A Player-like object which has nickname and account_ids set.
class AI():
    def __init__(self):
        self.nickname = 'Computer'
        self.account_id = 0

class ContestManagerInterface(commands.Cog):
    """Tournament Lobby"""
    def __init__(self, bot):
        self.bot = bot
        self.cog_display_name = "Tournament Lobby"
        self.layout = []

        access_token = os.environ.get('mahjong_soul_access_token')
        if access_token is None:
            raise Exception("missing mahjong_soul_access_token in environment / config.env")

        trusted_user_ids = [int(x) for x in os.environ.get('trusted_user_ids', '').split(',')]
        self.trusted_user_ids = trusted_user_ids

        self.client = ContestManagerClient(lq_dhs, access_token)
        self.contest = None

        self.main_channel = None
        self.list_message = None

    async def async_setup(self):
        "Perform launch setup steps to allow usability right after restarting."
        await self.connect()
        await self.login()

        # Attempt to manage the default contest, if specified in config
        contest_id = int(os.environ.get('mahjong_soul_contest_id', '0'))
        if contest_id:
            await self.manage_contest(contest_id)

    # Helpers for common tasks that can be either invoked by command or
    # automatically upon startup.
    async def manage_contest(self, contest_id):
        res = await self.client.call('manageContest', unique_id=contest_id)
        self.contest = res.contest

    async def connect(self):
        servers = await mjsoul.get_contest_management_servers()

        if len(servers) == 0:
            raise Exception('No contest management servers found')

        await self.client.connect(servers[0])

    async def login(self):
        await self.client.login()
        asyncio.create_task(self.notify_listener())

    async def is_admin(self, ctx):
        if ctx.author.id not in self.trusted_user_ids:
            await ctx.send("Only administrators may use that command.")
            return False
        return True

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if self.list_message and reaction.message.id != self.list_message.id:
            return

        await reaction.remove(user)

        if str(reaction.emoji) == REACTION_HUMAN:
            await self.shuffle(reaction.message.channel, False)
        elif str(reaction.emoji) == REACTION_BOT:
            await self.shuffle(reaction.message.channel, True)

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

        embed.add_field(name='Game Type', value=ROUND_TYPES[res.game_rule_setting.round_type])
        embed.add_field(name='Thinking Time', value=THINKING_TIMES[rules.thinking_type])

        if rules.dora_count == 0:
            embed.add_field(name='Red Fives', value=False)
        else:
            embed.add_field(name='Red Fives', value=rules.dora_count)

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
            if not self.is_admin(ctx):
                return

            try:
                await self.connect()
            except Exception as e:
                await ctx.send(f'Failed to connect to DHS: {e}')

            await ctx.send(f'Connected to DHS.')

    @commands.command(name='login', hidden=True)
    async def dhs_login(self, ctx):
        async with ctx.channel.typing():
            if not self.is_admin(ctx):
                return

            if not self.client.websocket or not self.client.websocket.open:
                await self.dhs_connect(ctx)

            try:
                await self.login()
            except Exception as e:
                print(e)
                await ctx.send('Unable to login.')
                return

            await ctx.send('Logged in to contest manager.')

    @commands.command(name='tournament', hidden=True)
    async def load_table(self, ctx, path:str = None):
        """
        Loads a tournament multi-table layout from a local file formatted as a CSV.

        Usage: `ms/tournament <localfile.csv>`
        Each row represents a table and is a comma separated list of Mahjong Soul nicknames.
        In each row, the first person is East, the second is South and so on.

        To prevent path traversal the path is basename'd. The file must exist in the cwd
        of the bot and end in .csv. '.' and '..' are automatically rejected.
        """
        async with ctx.channel.typing():
            if not self.is_admin(ctx):
                return

            base = os.path.basename(path)
            if base == '.' or base == '..' or os.path.splitext(base)[1] != '.csv':
                await ctx.send("Invalid path {path}")
                return

            # We can make sure all CSV players are registered in the tournament lobby.
            registered = {p.nickname for p in await self.client.contest_players}

            self.layout = []
            with open(base) as csvfile:
                c = csv.reader(csvfile)
                for row in c:
                    if len(row) != 4:
                        await ctx.send(f"Invalid row (not 4 players): {row}")
                        return

                    for person in row:
                        if person == "":
                            await ctx.send(f"Invalid player in row: {row}")
                            return
                        elif person not in registered:
                            await ctx.send(f"Player is not registered with tournament lobby: {p}")

                    # TODO(joshk): Check the nickname is valid against the lobby whitelist
                    self.layout.append(row)

            await ctx.send(f"Tournament mode enabled with {len(self.layout)} tables!")
            await self.dhs_show_active_players(ctx)

    @commands.command(name='setrule')
    async def set_rule(self, ctx, rule:str = None, value:str = None):
        '''
        Sets various tournament rules.

        Supported rule ids and values:
        * gametype: east, south, single (All 4-player)
        * turntime: 3+5, 5+10, 5+20, 60

        Usage: `ms/setrule <ruleid> <value>`
        '''

        async with ctx.channel.typing():
            if not self.is_admin(ctx):
                return

            if not self.client.websocket or not self.client.websocket.open:
                await ctx.send('Client not connected.')
                return

            # Get current rules
            res = await self.client.call('fetchContestGameRule')
            rules = res.game_rule_setting

            if rule == 'turntime':
                mapping = {'3+5': 1, '5+10': 2, '5+20': 3, '60': 4}
                mapped = mapping.get(value)

                if not mapped:
                    await ctx.send(f'Invalid value for {rule}. Valid: {", ".join(mapping.keys())}')
                    return

                rules.thinking_type = mapped
            elif rule == 'gametype':
                mapping = {'east': 1, 'south': 2, 'single': 4}
                mapped = mapping.get(value)

                if not mapped:
                    await ctx.send(f'Invalid value for {rule}. Valid: {", ".join(mapping.keys())}')
                    return

                rules.round_type = mapped
            else:
                await ctx.send(f'Unrecognized rule to set. Valid: gametype, turntime')
                return

            # might throw an exception
            await self.client.call('updateContestGameRule', game_rule_setting = rules)
            await ctx.send(f'Rules updated!')

            # Show the new rules
            await self.display_tournament_rules(ctx)

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

    @commands.command(name='terminate')
    async def dhs_terminate(self, ctx, nickname:str = None):
        '''Aborts the game that the user is in.

        Usage: `ms/terminate <majsoul-user>`

        Terminates an ongoing game for `<majsoul-user>`. If the command is invoked without any arguments, the bot will use the Majsoul name registered to the Discord user who invoked the command.
        '''

        async with ctx.channel.typing():
            if not self.is_admin(ctx):
                return

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

            await self.client.terminate(game_uuid)
            await ctx.send(f'Game terminated for {nickname}')

    @commands.command(name='manage', hidden=True)
    async def dhs_manage_contest(self, ctx, lobbyID:int):
        async with ctx.channel.typing():
            if not self.is_admin(ctx):
                return

            if not self.client.websocket or not self.client.websocket.open:
                await ctx.send('Client not connected.')
                return

            try:
                await self.manage_contest(lobbyID)
            except Exception as e:
                print(e)
                await ctx.send(f'Unable to manage {lobbyID}')
                return

            await ctx.send(f"Entered lobby management for lobby {lobbyID}.")


    @commands.command(name='casual')
    async def cmd_casual(self, ctx):
        "Revert the bot to casual mode."

        async with ctx.channel.typing():
            if not self.is_admin(ctx):
                return

            if self.layout:
                await ctx.send('Tournament mode disabled!')
            else:
                await ctx.send('Casual mode already enabled. No changes made.')

            self.layout = []
            await self.dhs_show_active_players(ctx)

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
                await self.list_message.delete()

            games, queued = await self.client.display_players()
            list_display = self.render_lobby_output(games, queued)

            self.list_message = await self.main_channel.send(list_display)
            await self.list_message.add_reaction(REACTION_HUMAN)
            await self.list_message.add_reaction(REACTION_BOT)

    async def shuffle(self, discord_channel, withBots=False):
        if self.layout:
            return await self.perform_layout_assignment(discord_channel)
        else:
            return await self.random_assignment(discord_channel, withBots)

    async def perform_layout_assignment(self, discord_channel):
        players = await self.client.active_players

        # Ensure that all members of the layout are present
        queued_player_set = {p.nickname for p in players}
        layout_set = set()

        for table in self.layout:
            for player in table:
                if player != '':
                    layout_set.add(player)

        # Lookup as we go thru the layout so we can create tables
        player_lookup = {p.nickname: p for p in players}

        # Allow the use of bots
        player_lookup[''] = 0

        if layout_set not in queued_player_set:
            await discord_channel.send(f"Can't start without these players: {', '.join(list(layout_set - queued_player_set))}")
            return

        for table in self.layout:
            # This should work well because of the set comparison from earlier
            player_table = [player_lookup[nick] for nick in table]
            await self.create_game_helper(discord_channel, player_table)

    async def random_assignment(self, discord_channel, withBots=False):
        # This no-op list comprehension turns a special protobuf field type into a list.
        players = [p for p in await self.client.active_players]

        if withBots:
            remainder = len(players) % 4
            for _ in range(remainder):
                players.append(AI())

            random.shuffle(players)
            tables = chunk_pad(players, 4, AI())
        else:
            random.shuffle(players)
            tables = chunk(players, 4)

        for table in tables:
            if len(table) == 4:
                await self.create_game_helper(discord_channel, table)

        await self.refresh_message()

    async def refresh_message(self, res=None):
        games, queued = await self.client.display_players(res)
        list_display = self.render_lobby_output(games, queued)
        await self.list_message.edit(content=list_display)

    async def create_game_helper(self, discord_channel, table):
        id_table = [p.account_id for p in table]
        await self.client.create_game(id_table)
        await discord_channel.send(f"Game starting for {table[0].nickname} | {table[1].nickname} | {table[2].nickname} | {table[3].nickname}")


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
            name, msg = await self.client.Notifications.get()

            if name == 'NotifyContestMatchingPlayer':
                await self.on_NotifyContestMatchingPlayer(msg)
            elif name == 'NotifyContestGameEnd':
                await self.on_NotifyContestGameEnd(msg)
            else:
                print(f"Unexpected notification type {name}")

    async def on_NotifyContestGameEnd(self, msg):
        uuid = msg.game_uuid

        MajsoulClientInterface = self.bot.get_cog('MajsoulClientInterface')

        try:
            log = await MajsoulClientInterface.client.fetch_game_log(uuid)

            # We get here only if it worked.
            seats = [player.seat for player in log.head.result.players]
            points = [player.part_point_1 for player in log.head.result.players]
            player_seat_lookup = {a.seat: (a.account_id, a.nickname) for a in log.head.accounts}

            # If AIs are being used, this will not be of size 4
            if len(player_seat_lookup) == 4:
                players = [(log.head.accounts[s].account_id, log.head.accounts[s].nickname) for s in seats]
                TournamentScoreTracker = self.bot.get_cog('TournamentScoreTracker')
                scores = await TournamentScoreTracker.record_game(players, points)

                response = f'Game concluded for {players[0][1]}({scores[0]}) | {players[1][1]}({scores[1]}) | {players[2][1]}({scores[2]}) | {players[3][1]}({scores[3]})'
            else:
                # Don't show tournament style scores
                player_scores_rendered = [
                    f'{player_seat_lookup.get(p.seat, (0, "Computer"))[1]}({p.part_point_1})'
                    for p in log.head.result.players]
                response = f'Game concluded for {" | ".join(player_scores_rendered)}'

            await self.main_channel.send(response)

        except GeneralMajsoulError as e:
            print(f'NotifyContestGameEnd but could not retrieve log ({e}). Skipping score recording.')

        if self.list_message != None:
            await self.refresh_message()

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
            await self.refresh_message(res)

    def render_lobby_output(self, games, queued):
        if self.layout:
            content = self.render_lobby_output_with_layout(games, queued)
        else:
            content = self.render_lobby_output_casual(games, queued)

        content += f'{REACTION_HUMAN} Click the die to start games with humans only.\n'
        content += f'{REACTION_BOT} Click the robot to start games with humans and AI.\n'

        return content

    def render_lobby_output_with_layout(self, games, queued):
        in_game_player_set = set()

        for game in games:
            for player in game.players:
                in_game_player_set.add(player.nickname)

        queued_player_set = {p.nickname for p in queued}

        response = f'**[Tournament: {self.contest.contest_name}]**\n'
        response += f'Join the Tournament Lobby: {self.contest.contest_id} and press _Prepare for Match_\n\n'

        for (i, table) in enumerate(self.layout):
            response += f'**Table {i+1}**:\n'
            for (j, player) in enumerate(table):
                if player in in_game_player_set:
                    emoji = EMOJI_MAHJONG_TILE
                elif player in queued_player_set:
                    emoji = EMOJI_GREEN_CIRCLE
                else:
                    emoji = EMOJI_RED_CIRCLE
                response += f'{emoji} {WINDS[j]}: {player or "COMPUTER"}\n'
            response += '\n'

        return response

    def render_lobby_output_casual(self, games, queued):
        numPlaying = sum([len(game.players) for game in games])
        numReady = len(queued)

        response = f'**[Casual Games: {self.contest.contest_name}]**\n'
        response += f'Join the Tournament Lobby: {self.contest.contest_id} and press _Prepare for Match_\n'
        response += f'{numReady} Ready, {numPlaying} In Game\n\n'

        if (numReady + numPlaying == 0):
            response += '_[No players in lobby]_\n\n'

        for (i, game) in enumerate(games):
            if i == 0:
                response += '**[Games in Progress]**\n'

            response += f'**Table {i+1}**:\n'
            for (j, player) in enumerate(game.players):
                response += f'{EMOJI_MAHJONG_TILE} {WINDS[j]}: {player.nickname or "_Computer_"}\n'
        if len(games) > 0:
            response += '\n'

        for (j, player) in enumerate(queued):
            if j == 0:
                response += '**[Waiting to Start]**\n'
            response += f'{EMOJI_GREEN_CIRCLE} {j+1}. {player.nickname or "_Computer_"}\n'
        if len(queued) > 0:
            response += '\n'

        return response

def setup(bot):
    i = ContestManagerInterface(bot)
    asyncio.create_task(i.async_setup())
    bot.add_cog(i)

# https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
def chunk_pad(it, size, padval=None):
    it = chain(iter(it), repeat(padval))
    return iter(lambda: tuple(islice(it, size)), (padval,) * size)

def chunk(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())

if __name__ == "__main__":
    server = asyncio.run(mjsoul.get_contest_management_servers())[0]
    client = ContestManagerClient(server, dhs)

    asyncio.run(client.login())
