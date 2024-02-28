import asyncio
import csv
from itertools import islice, chain, repeat
import json
import math
import os
import random
import yaml
import csv
import requests
import yaml

from discord.ext import commands
from discord import Embed, Object, Interaction, app_commands
from typing import Optional

from modules.pymjsoul import mjsoul
from modules.pymjsoul.channel import MajsoulChannel, GeneralMajsoulError
from modules.pymjsoul.client import ContestManagerClient
from modules.pymjsoul.proto.combined import lq_dhs_pb2 as lq_dhs

TAG_MESSAGES = [
    'Time for more MAHJONG!',
    'Ready to get some points back?',
    'Queue for more!',
    'QUEUE',
    'MOAR GAMES',
    'A tanyao can end it all. But QUEUEING is where it BEGINS.',
]

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

        self.client = ContestManagerClient(lq_dhs, access_token)
        self.contest = None
        config_file = os.environ.get('contests_configuration', 'contests.yaml')
        if config_file is None or not os.path.exists(config_file):
            raise Exception(f'please provide a contest configuration in {config_file}')

        with open(config_file, 'r') as f:
            config_raw = yaml.safe_load(f)

        self.config = config_raw
        self.contests = {contest['channel_id']: contest for contest in config_raw['contests']}
        self.active_games = {}

        # Pick the first contest as the default one
        self.main_channel_id = int(config_raw['contests'][0]['channel_id'])

        self.list_message = None
        self.rules = None

        self._started_event = None
        self._create_game_lock = asyncio.Lock()

    async def async_setup(self):
        "Perform launch setup steps to allow usability right after restarting."
        await self.connect()
        await self.login()
        await self.manage_contest(self.contests[self.main_channel_id]['contest_id'])

        for contest in self.contests.values():
            contest_posts = contest.get('posts', {})
            list_post_id = contest_posts.get('list')
            self.score_post_ids = contest_posts.get('scores', [])
            self.post_channel_id = contest_posts.get('channel_id')

            if self.post_channel_id:
                post_channel = self.bot.get_channel(self.post_channel_id)
            else:
                raise Exception('need to set contests[].posts.channel_id to make new list and score posts')

            if not self.score_post_ids:
                self.score_post_ids = [(await post_channel.send(f'Score Post {n}')).id for n in range(5)]
                print(f'New score posts created: {self.score_post_ids}')

            if list_post_id:
                self.list_message = await post_channel.fetch_message(list_post_id)
            else:
                self.list_message = await post_channel.send('List Post')
                print(f'New list post created: {self.list_message.id}')


        # relies on NewScoreTracker being loaded first
        ScoreTrackerCog = self.bot.get_cog('TournamentScoreTracker')
        await ScoreTrackerCog.get_logs()

        # update the scores post
        await ScoreTrackerCog.update_score_posts(self.post_channel_id, self.score_post_ids)

        # begin updating the list post now that self.list_message is set
        await self.refresh_message()

    # Helpers for common tasks that can be either invoked by command or
    # automatically upon startup.
    async def manage_contest(self, contest_id):
        res = await self.client.call('manageContest', unique_id=contest_id)
        self.contest = res.contest

        # retrieving rules useful for score tracking
        res = await self.client.call('fetchContestGameRule')
        self.rules = res.game_rule_setting

    async def connect(self):
        servers = await mjsoul.get_contest_management_servers()

        if len(servers) == 0:
            raise Exception('No contest management servers found')

        await self.client.connect(servers[0])

    async def login(self):
        await self.client.login()
        await self.client.subscribe('NotifyContestMatchingPlayer', self.on_NotifyContestMatchingPlayer)
        await self.client.subscribe('NotifyContestGameStart', self.on_NotifyContestGameStart)
        await self.client.subscribe('NotifyContestGameEnd', self.on_NotifyContestGameEnd)

    def is_admin(self, user_id, channel_id):
        contest = self.contests[channel_id]
        if user_id not in contest['administrator_user_ids']:
            return False
        return True

    def has_contest_role(self, user, channel_id):
        contest = self.contests.get(channel_id)
        if not contest:
            return False

        allow_roles = contest.get('allow_roles')
        if allow_roles is None:
            return False
        for role in user.roles:
            if role.id in allow_roles:
                return True
        return False

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        if not self.has_contest_role(user, reaction.message.channel.id):
            return

        # Only reactions to the list message would be handled
        if not self.list_message:
            return
        if reaction.message.id != self.list_message.id:
            return
        try:
            await reaction.remove(user)
        except:
            print(f"Couldn't remove reaction for {user.display_name}")

        if str(reaction.emoji) == REACTION_HUMAN:
            await self.shuffle(reaction.message.channel, False)
        elif str(reaction.emoji) == REACTION_BOT:
            await self.shuffle(reaction.message.channel, True)
        else:
            return

        print(f"{user.display_name} pressed the button.")

    @app_commands.command(name='rules', description='Displays the game rules')
    async def display_tournament_rules(self, interaction : Interaction):
        '''
        Displays the game rules.

        Usage: `/rules`

        Displays a summary of the game rules that the current tournament lobby implements.
        '''
        await interaction.response.defer()

        if not self.client.websocket or not self.client.websocket.open:
                await interaction.followup.send('Client not connected.')
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
            if is_sanma(res.game_rule_setting.round_type):
                #Uma Calculation
                shunweima_1 = (int)(-1*(rules.shunweima_2 + rules.shunweima_3))
                embed.add_field(name='Uma', value=f'{shunweima_1}/{rules.shunweima_2}/{rules.shunweima_3}')
            else:
                #Uma Calculation
                shunweima_1 = (int)(-1*(rules.shunweima_2 + rules.shunweima_3 + rules.shunweima_4))
                embed.add_field(name='Uma', value=f'{shunweima_1}/{rules.shunweima_2}/{rules.shunweima_3}/{rules.shunweima_4}')
            #Kuitan
            if not is_sanma(res.game_rule_setting.round_type):
                embed.add_field(name='Open Tanyao', value=res.game_rule_setting.shiduan)
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
            #Local Yaku
            embed.add_field(name='Local Yaku', value=(rules.guyi_mode == 1))

        await interaction.followup.send(embed=embed)

    @app_commands.command(name='tournament', description='Loads a tournament layout from a local CSV file')
    @app_commands.describe(path='Path to the tournament CSV file')
    @app_commands.default_permissions(administrator=True)
    async def load_table(self, interaction, path: Optional[str]):
        """
        Loads a tournament multi-table layout from a local file formatted as a CSV.

        Usage: `/tournament <localfile.csv>`
        Each row represents a table and is a comma separated list of Mahjong Soul nicknames.
        In each row, the first person is East, the second is South and so on.

        To prevent path traversal the path is basename'd. The file must exist in the cwd
        of the bot and end in .csv. '.' and '..' are automatically rejected.
        """
        await interaction.response.defer()

        if interaction.channel_id != self.main_channel_id:
            await interaction.followup.send('Wrong channel')
            return

        if not self.has_contest_role(interaction.user, interaction.channel_id):
            await interaction.followup.send('Only contest roles may use that command.')
            return

        if not self.is_admin(interaction.user.id, interaction.channel_id):
            await interaction.followup.send('Only administrators may use that command.')
            return

        base = os.path.basename(path)
        if base == '.' or base == '..' or os.path.splitext(base)[1] != '.csv':
            await interaction.followup.send(f'Invalid path {path}')
            return

        # We can make sure all CSV players are registered in the tournament lobby.
        # registered = {p.nickname for p in await self.client.contest_players}

        # table size depends on the game setting
        if is_sanma(self.rules.round_type):
            table_size = 3
        else:
            table_size = 4

        self.layout = []
        with open(os.path.join('brackets', base)) as csvfile:
            c = csv.reader(csvfile)
            for row in c:
                if len(row) != table_size:
                    await interaction.followup.send(f"Invalid row (not 4 players): {row}")
                    return

                for person in row:
                    if person == "":
                        await interaction.followup.send(f"Invalid player in row: {row}")
                        return
                    # elif person not in registered:
                    #    await ctx.send(f"Player is not registered with tournament lobby: {person}")
                    #    return

                self.layout.append(row)

        await interaction.followup.send(f"Tournament mode enabled with {len(self.layout)} tables!")
        await self.dhs_show_active_players(interaction)

    @app_commands.command(name='register', description='Register user in the lobby')
    @app_commands.describe(friend_id='User ID')
    async def register(self, interaction : Interaction, friend_id:int):
        '''
        Registers the user in the associated channel's lobby. Pass in a friend ID

        Usage: `/register <friend_id>`
        '''

        await interaction.response.defer()

        if interaction.channel.id != self.main_channel_id:
            await interaction.followup.send('Wrong Channel for this command')
            return

        if not self.has_contest_role(interaction.user, interaction.channel.id):
            await interaction.followup.send('Only contest members may use that command.')
            return

        res = await self.client.call('searchAccountByEid', eids=[friend_id])

        # it's a success if we get here
        if res.search_result:
            nickname = res.search_result[0].nickname
            account_id = res.search_result[0].account_id

            res = await self.client.call('updateContestPlayer',
                    setting_type=2, # add a player ignoring whats already there
                    nicknames=[nickname],
                    account_ids=[account_id])

            await interaction.followup.send(f'Registered player into lobby: {nickname}')
        else:
            await interaction.followup.send(f"Couldn't look up friend code: {friend_id}")

    @app_commands.command(name='pause', description='Pauses game for user')
    @app_commands.describe(nickname='Player nickname')
    async def dhs_pause(self, interaction : Interaction, nickname:Optional[str]):
        '''Pauses the game.

        Usage: `ms/pause <majsoul-user>`

        Pauses an ongoing game for `<majsoul-user>`. If the command is invoked without any arguments, the bot will use the Majsoul name registered to the Discord user who invoked the command.
        '''

        await interaction.response.defer()

        if interaction.channel_id != self.main_channel_id:
            await interaction.followup.send('Wrong Channel for this command')
            return

        if not self.has_contest_role(interaction.user, interaction.channel_id):
            await interaction.followup.send('Only contest members can use that command')
            return


        if not self.client.websocket or not self.client.websocket.open:
            await interaction.followup.send('Client not connected.')
            return

        if nickname is None:
            PlayerNicknamesCog = self.bot.get_cog('PlayerNicknames')
            p = PlayerNicknamesCog.players

            if str(interaction.user.id) not in p.keys() or p[str(interaction.user.id)]['majsoul_name'] == None:
                await interaction.followup.send(f'No Mahjsoul name registered for {interaction.user.mention}. Type ms/mahjsoul-name <your-mahjsoul-name> to register.')
                return
            else:
                nickname = p[str(interaction.user.id)]['majsoul_name']

        game_uuid = await self.client.get_game_id(nickname)

        if game_uuid == None:
            await interaction.followup.send(f'Unable to find in-progress game for {nickname}')
            return

        try:
            await self.client.pause(game_uuid)
        except Exception as e:
            await interaction.followup.send('Unable to pause game.')
            return

        await interaction.followup.send(f'Game paused for {nickname}')

    @app_commands.command(name='unpause', description='Unpause game for player')
    @app_commands.describe(nickname='Player to unpause')
    async def dhs_unpause(self, interaction : Interaction, nickname: Optional[str]):
        '''Resumes the game.

        Usage: `/unpause <majsoul-user>`

        Resumes an ongoing game for `<majsoul-user>`. If the command is invoked without any arguments, the bot will use the Majsoul name registered to the Discord user who invoked the command.
        '''
        await interaction.response.defer()

        if interaction.channel_id != self.main_channel_id:
            await interaction.followup.send('Wrong channel for that command')
            return

        if not self.has_contest_role(interaction.user, interaction.channel_id):
            await interaction.followup.send('Only contest members may use that command.')
            return

        if not self.client.websocket or not self.client.websocket.open:
            await interaction.followup.send('Client not connected.')
            return

        if nickname is None:
            PlayerNicknamesCog = self.bot.get_cog('PlayerNicknames')
            p = PlayerNicknamesCog.players

            if str(interaction.user.id) not in p.keys() or p[str(interaction.user.id)]['majsoul_name'] == None:
                await interaction.followup.send(f'No Mahjsoul name registered for {interaction.user.mention}. Type ms/mahjsoul-name <your-mahjsoul-name> to register.')
                return
            else:
                nickname = p[str(interaction.user.id)]['majsoul_name']

        game_uuid = await self.client.get_game_id(nickname)

        if game_uuid == None:
            await interaction.followup.send(f'Unable to find in-progress game for {nickname}')
            return

        try:
            result = await self.client.unpause(game_uuid)
        except Exception as e:
            await interaction.followup.send('Unable to unpause game.')
            return

        await interaction.followup.send(f'Game unpaused for {nickname}')

    @app_commands.command(name='terminate', description='End game for user')
    @app_commands.describe(nickname='Nickname to end game for')
    async def dhs_terminate(self, interaction : Interaction, nickname: Optional[str]):
        '''Aborts the game that the user is in.

        Usage: `/terminate <majsoul-user>`

        Terminates an ongoing game for `<majsoul-user>`. If the command is invoked without any arguments, the bot will use the Majsoul name registered to the Discord user who invoked the command.
        '''
        await interaction.response.defer()

        if interaction.channel_id != self.main_channel_id:
            await interaction.followup.send('Wrong channel for command.')
            return

        if not self.has_contest_role(interaction.user, interaction.channel_id):
            await interaction.followup.send('Only contest members may use that command.')
            return

        if not self.is_admin(interaction.user.id, interaction.channel_id):
            await interaction.followup.send('Only administrators may use that command.')
            return

        if not self.client.websocket or not self.client.websocket.open:
            await interaction.followup.send('Client not connected.')
            return

        if nickname is None:
            PlayerNicknamesCog = self.bot.get_cog('PlayerNicknames')
            p = PlayerNicknamesCog.players

            if str(interaction.user.id) not in p.keys() or p[str(interaction.user.id)]['majsoul_name'] == None:
                await interaction.followup.send(f'No Mahjsoul name registered for {interaction.user.mention}. Type ms/mahjsoul-name <your-mahjsoul-name> to register.')
                return
            else:
                nickname = p[str(interaction.user.id)]['majsoul_name']

        game_uuid = await self.client.get_game_id(nickname)

        if game_uuid == None:
            await interaction.followup.send(f'Unable to find in-progress game for {nickname}')
            return

        await self.client.terminate(game_uuid)
        await interaction.followup.send(f'Game terminated for {nickname}')

    @app_commands.command(name='manage', description='Manage the contest in this channel')
    @app_commands.default_permissions(administrator=True)
    async def dhs_manage_contest(self, interaction: Interaction):
        await interaction.response.defer()

        if not self.is_admin(interaction.user.id, interaction.channel_id):
            await interaction.followup.send('Only administrators may use that command.')
            return
        elif interaction.channel_id not in self.contests:
            await interaction.followup.send('Unrecognized channel to manage a mahjong contest in.')
        elif interaction.channel_id == self.main_channel_id:
            await interaction.followup.send('Already managing contest in this channel!')
        else:
            if self.list_message != None:
                await self.list_message.delete()
                self.list_message = None

            await self.manage_contest(self.contests[interaction.channel_id]['contest_id'])
            self.main_channel_id = interaction.channel_id
            await interaction.followup.send('Now managing games in this channel!')

    @app_commands.command(name='casual', description='Revert the bot to casual mode')
    async def cmd_casual(self, interaction : Interaction):
        "Revert the bot to casual mode."
        await interaction.response.defer()

        if interaction.channel_id != self.main_channel_id:
            await interaction.followup.send('Wrong channel for this command.')
            return

        if not self.is_admin(interaction.user.id, interaction.channel_id):
            await interaction.followup.send('Only administrators can use this command.')
            return

        if self.layout:
            await interaction.followup.send('Tournament mode disabled!')
        else:
            await interaction.followup.send('Shuffle mode already enabled. No changes made.')

        self.layout = []
        await self.dhs_show_active_players(interaction)

    @app_commands.command(name='list', description='No longer does anything.')
    async def deprecated_list(self, interaction : Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send('This slash command is now disabled. Please check #online-queue-scores', ephemeral=True)

    @app_commands.command(name='scores', description='No longer does anything.')
    async def deprecated_scores(self, interaction : Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send('This slash command is now disabled. Please check #online-queue-scores', ephemeral=True)

#    @app_commands.command(name='list', description='Displays the lobby')
    async def dhs_show_active_players(self, interaction : Interaction):
        '''Displays the lobby.

        Usage: `/list`

        Displays the names of all players who are currently queued up in the Majsoul tournament lobby.
        '''
        await interaction.response.defer(ephemeral=True)
        if interaction.channel_id != self.main_channel_id:
            await interaction.followup.send('Wrong channel for this command.')
            return

        if not self.has_contest_role(interaction.user, interaction.channel_id):
            await interaction.followup.send('Only contest roles can use this command.')
            return

        if not self.client.websocket or not self.client.websocket.open:
            await interaction.followup.send('Client not connected.')
            return

        if self.list_message != None:
            await self.list_message.delete()
            self.list_message = None

        games, queued = await self.client.display_players()
        list_display = self.render_lobby_output(games, queued)

        await interaction.followup.send('Sending list', ephemeral=True)
        self.list_message = await self.bot.get_channel(self.main_channel_id).send(list_display)

    async def shuffle(self, discord_channel, withBots=False):
        if self.layout:
            return await self.perform_layout_assignment(discord_channel)
        else:
            return await self.random_assignment(discord_channel, withBots)

    @app_commands.command(name='shuffle', description='Shuffles all queued players into games')
    async def shuffle_command(self, interaction : Interaction):
        await interaction.response.defer()

        if self.layout:
            await self.perform_layout_assignment(interaction.channel)
        else:
            await self.random_assignment(interaction.channel, False)

        await interaction.followup.send('Starting games...')

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

        if layout_set != queued_player_set:
            await discord_channel.send(f"Can't start without these players: {', '.join(list(layout_set - queued_player_set))}")
            return

        for table in self.layout:
            # This should work well because of the set comparison from earlier
            player_table = [player_lookup[nick] for nick in table]
            await self.create_game_helper(discord_channel, player_table)

    async def random_assignment(self, discord_channel, withBots=False):
        # This no-op list comprehension turns a special protobuf field type into a list.
        players = [p for p in await self.client.active_players]

        # table size depends on the game setting
        if is_sanma(self.rules.round_type):
            table_size = 3
        else:
            table_size = 4

        if withBots:
            # Get number of partial tables (e.g. 1.25 tables with 5 players),
            # round that up to the next integer number of tables. Multiply
            # by players per table. subtract players.
            # if len(players) % 4 == 0, remainder should be 0
            remainder = math.ceil(len(players) / (table_size*1.0)) * table_size - len(players)
            for _ in range(remainder):
                players.append(AI())

        random.shuffle(players)
        tables = chunk(players, table_size)

        for table in tables:
            if len(table) == table_size:
                await self.create_game_helper(discord_channel, table)

        await self.refresh_message()

    async def refresh_message(self, res=None):
        games, queued = await self.client.display_players(res)
        list_display = self.render_lobby_output(games, queued)
        await self.list_message.edit(content=list_display)
        return games, queued

    async def create_game_helper(self, discord_channel, table):
        async with self._create_game_lock:
            self._started_event = asyncio.Event()

            id_table = [p.account_id for p in table]
            game_uuid = await self.client.create_game(id_table)
            await self._started_event.wait()

            nicknames = ' | '.join([p.nickname for p in table])
            await discord_channel.send(f"Battle starting for {nicknames}")

    async def locate_completed_game(self, game_uuid):
        res = await self.client.call('fetchContestGameRecords')
        for item in res.record_list:
            if item.record.uuid == game_uuid:
                return item.record
        return None

    # @commands.command(name='record_one')
    # async def XXX_record_one(self, ctx, game_uuid:str):
    #     record = await self.locate_completed_game(game_uuid)
    #     ScoreTrackerCog = self.bot.get_cog('TournamentScoreTracker')
    #     await ScoreTrackerCog.record_multiple_games([record])

    async def on_NotifyContestGameEnd(self, _, msg):
        # It takes some time for the results to register into the log
        await asyncio.sleep(5)

        try:
            record = await self.locate_completed_game(msg.game_uuid)
        except Exception as e:
            await self.login()
            record = await self.locate_completed_game(msg.game_uuid)

        response = None

        if record:
            player_seat_lookup = {a.seat: (a.account_id, a.nickname) for a in record.accounts}

            player_scores_rendered = [
                f'{player_seat_lookup.get(p.seat, (0, "Computer"))[1]} ({p.part_point_1})'
                for p in record.result.players]
            response = f'Game concluded for {" | ".join(player_scores_rendered)}'

            ScoreTrackerCog = self.bot.get_cog('TournamentScoreTracker')
            await ScoreTrackerCog.record_multiple_games([record])

        if msg.game_uuid in self.active_games:
            nicknames = self.active_games[msg.game_uuid]
            del self.active_games[msg.game_uuid]

            # In case we couldn't obtain scoring information.
            if not response:
                response = f'Game concluded for {nicknames}'
        elif not record:
            response = f'An unknown game concluded: {msg.game_uuid}'

        channel = self.bot.get_channel(self.main_channel_id)
        await channel.send(response)

        if self.list_message != None:
            games, queued = await self.refresh_message()
        else:
            games, queued = await self.client.display_players()

        # update the durable score post
        await ScoreTrackerCog.update_score_posts(self.post_channel_id, self.score_post_ids)

        # If a game ended, and we observe there are now 0 games,
        # and the contest has a ping, ping it!
        contest = self.contests[self.main_channel_id]
        notify_roles = contest.get('notify_roles', [])

        if len(games) == 0 and notify_roles:
            msg = ' '.join([f'<@&{role_id}>' for role_id in notify_roles]) + ' ' + random.choice(TAG_MESSAGES)
            await channel.send(msg)

    async def on_NotifyContestGameStart(self, _, msg):
        if not self._started_event:
            print(f'NotifyContestGameStart received but not waiting for a game!')
            return

        nicknames = ' | '.join([p.nickname or 'Computer' for p in msg.game_info.players])
        self.active_games[msg.game_info.game_uuid] = nicknames

        self._started_event.set()
        self._started_event = None

    async def on_NotifyContestMatchingPlayer(self, name, msg):

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

        response = f'**[Shuffled Games: {self.contest.contest_name}]**\n'
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

async def setup(bot):
    i = ContestManagerInterface(bot)
    asyncio.create_task(i.async_setup())
    with open('servers.yaml', 'r') as file:
        config_raw = yaml.safe_load(file)

    servers = [Object(id=int(server['server_id'])) for server in config_raw['servers']]

    await bot.add_cog(i, guilds=servers)

# https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
def chunk_pad(it, size, padval=None):
    it = chain(iter(it), repeat(padval))
    return iter(lambda: tuple(islice(it, size)), (padval,) * size)

def chunk(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())

def is_sanma(round_type):
    return round_type in [11, 12, 13, 14]

if __name__ == "__main__":
    server = asyncio.run(mjsoul.get_contest_management_servers())[0]
    client = ContestManagerClient(server, dhs)

    asyncio.run(client.login())
