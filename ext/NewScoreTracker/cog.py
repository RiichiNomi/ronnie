import asyncio
from logging import exception
import math
import os
import pandas as pd
import pickle
import pytz
import unicodedata
import json

from datetime import date, datetime
from dateutil.relativedelta import relativedelta, MO, FR

from discord.ext import commands

from tabulate import tabulate

RECORDS_FOLDER = 'ext/NewScoreTracker/records'

DEFAULT_RECORDS_NAME = 'log'

# 2000 Minus extra characters for fixed formatting: ```\n$FOO\n```\n
DISCORD_MAX_CHAR_LIMIT = 1990


class GameLogFilter():
    def __init__(self, datetime_start=datetime.min, datetime_end=datetime.max):
        self.datetime_start = datetime_start
        self.datetime_end = datetime_end

    def match(self, dt):
        return dt >= self.datetime_start and dt <= self.datetime_end


class TournamentScoreTracker(commands.Cog):
    "Score Tracking"
    field_majsoul_name = 'Majsoul Name'
    field_total_score = 'Total Score'
    field_average_score = 'Average Score'
    field_matches_played = 'Matches Played'
    field_first = '1'
    field_second = '2'
    field_third = '3'
    field_fourth = '4'

    score_table_display_fields = ['', 'Name', 'Total\nScore',
                                  'Average\nScore', 'Matches\nPlayed', '1st', '2nd', '3rd', '4th']
    score_table_fields = [field_majsoul_name, field_total_score, field_average_score,
                          field_matches_played, field_first, field_second, field_third, field_fourth]
    score_table_index = 'Majsoul Name'

    yonma_player_name_fields = ['1st', '2nd', '3rd', '4th']
    yonma_player_point_fields = ['Points 1', 'Points 2', 'Points 3', 'Points 4']
    
    sanma_player_name_fields = ['1st', '2nd', '3rd']
    sanma_player_point_fields = ['Points 1', 'Points 2', 'Points 3']

    field_game_end_time = 'End Time'
    game_record_index = 'uuid'
    yonma_game_record_fields = [game_record_index, field_game_end_time, *yonma_player_name_fields, *yonma_player_point_fields]
    sanma_game_record_fields = [game_record_index, field_game_end_time, *sanma_player_name_fields, *sanma_player_point_fields]

    json_config = None

    def __init__(self, bot):
        with open("ext/NewScoreTracker/config.json", "r") as f:
            self.json_config = json.loads(f.read())

        self.bot = bot

        self.SANMA_GAME_RECORDS = None
        self.YONMA_GAME_RECORDS = None
        self.game_records_lock = asyncio.Lock()
        self.game_records_filename = None

        # automatically determine filter start/end
        now = datetime.now().replace(hour=0, minute=0)
        first_monday_date = (now + relativedelta(day=1, weekday=MO(1)))
        last_friday_date = (now + relativedelta(day=31, weekday=FR(-1)))
        self.game_log_filter = GameLogFilter(first_monday_date, last_friday_date)

        this_monday_date = (now + relativedelta(weekday=MO(-1)))
        this_friday_date = (this_monday_date + relativedelta(weekday=FR(1)))

        self.weekly_filter = GameLogFilter(this_monday_date, this_friday_date)

        self.event_stop_log_search = asyncio.Event()

        self.initialize_dataframe()

    def initialize_dataframe(self):
        self.SANMA_GAME_RECORDS = pd.DataFrame(columns=self.sanma_game_record_fields)
        self.SANMA_GAME_RECORDS = self.SANMA_GAME_RECORDS.set_index(
            self.game_record_index, drop=False)
        pd.set_option("display.unicode.east_asian_width", True)
        
        self.YONMA_GAME_RECORDS = pd.DataFrame(columns=self.yonma_game_record_fields)
        self.YONMA_GAME_RECORDS = self.YONMA_GAME_RECORDS.set_index(
            self.game_record_index, drop=False)
        pd.set_option("display.unicode.east_asian_width", True)

    async def record_game(self, log):
        if is_sanma(log.config.mode.mode):
            records = self.SANMA_GAME_RECORDS
            fields = self.sanma_game_record_fields
        else:
            records = self.YONMA_GAME_RECORDS
            fields = self.yonma_game_record_fields

        if log.uuid in records.index:
            print(f'Game {log.uuid} already recorded.')
            return

        points = [player.part_point_1 for player in log.result.players]
        seats = [player.seat for player in log.result.players]
        players = [log.accounts[s].nickname for s in seats if s <
                   len(log.accounts)]

        entry = [log.uuid, log.end_time, *players, *points]

        game = pd.DataFrame(entry, columns=fields)
        game = game.set_index(self.game_record_index, drop=False)

        async with self.game_records_lock:
            if is_sanma(log.config.mode.mode):
                self.SANMA_GAME_RECORDS = self.SANMA_GAME_RECORDS.append(game)
            else:
                self.YONMA_GAME_RECORDS = self.YONMA_GAME_RECORDS.append(game)

        print(f"Recorded game {log.uuid}")

    async def record_multiple_games(self, logs):
        if len(logs) == 0:
            return

        entries = []
        for game_log in logs:
            if is_sanma(game_log.config.mode.mode):
                records = self.SANMA_GAME_RECORDS
                fields = self.sanma_game_record_fields
            else:
                records = self.YONMA_GAME_RECORDS
                fields = self.yonma_game_record_fields

            if game_log.uuid in records.index:
                print(f'Game {game_log.uuid} already recorded.')
                return

            points = [player.part_point_1 for player in game_log.result.players]
            seats = [player.seat for player in game_log.result.players]
            players = [game_log.accounts[s].nickname for s in seats]

            entries.append(
                [game_log.uuid, game_log.end_time, *players, *points])

        games = pd.DataFrame(entries, columns=fields)
        games = games.set_index(self.game_record_index, drop=False)

        async with self.game_records_lock:
            if is_sanma(game_log.config.mode.mode):
                self.SANMA_GAME_RECORDS = self.SANMA_GAME_RECORDS.append(games)
            else:
                self.YONMA_GAME_RECORDS = self.YONMA_GAME_RECORDS.append(games)

    async def create_score_table(self, starting_points, return_points, uma, sanma=False, custom_filter=None):
        '''
        Processes all the stored game logs

        Returns: A score table that displays cumulative and average scores for each player
        Return Type: Pandas DataFrame
        '''

        df = pd.DataFrame(columns=self.score_table_fields)
        df = df.set_index(self.score_table_index, drop=False)

        async with self.game_records_lock:
            if sanma:
                records = self.SANMA_GAME_RECORDS
            else:
                records = self.YONMA_GAME_RECORDS

            for index, row in records.iterrows():
                end_time = datetime.fromtimestamp(row.loc[self.field_game_end_time])
                if not custom_filter or custom_filter.match(end_time):
                    df = await self.update_score_table(df, records, index, starting_points, return_points, uma, sanma, custom_filter)

        return df

    async def update_score_table(self, df, records, index, starting_points, return_points, uma, sanma, custom_filter):
        '''
        Updates the score table with a game record
        '''
        if sanma:
            name_fields = self.sanma_player_name_fields
            point_fields = self.sanma_player_point_fields
        else:
            name_fields = self.yonma_player_name_fields
            point_fields = self.yonma_player_point_fields

        PLAYERS = [records.loc[index, n] for n in name_fields]
        POINTS = [records.loc[index, s] for s in point_fields]

        assert(len(PLAYERS) == len(POINTS))

        ScoreCalculator = self.bot.get_cog('ScoreCalculator')
        if self.json_config["use_floating_uma"]:
            SCORES = ScoreCalculator.calculate_scores(
                POINTS, starting_points, return_points, uma, use_floating_uma=True, floating_uma_one=self.json_config["floating_uma_one"], floating_uma_two=self.json_config["floating_uma_two"], floating_uma_three=self.json_config["floating_uma_three"])
        else:
            SCORES = ScoreCalculator.calculate_scores(
                POINTS, starting_points, return_points, uma)

        for i in range(0, len(PLAYERS)):
            name = PLAYERS[i]
            score = SCORES[i]
            placement = i+1

            if name not in df[self.score_table_index]:
                new_player = pd.DataFrame(
                    [[name, *[0]*7]], columns=self.score_table_fields)
                new_player = new_player.set_index(
                    self.score_table_index, drop=False)
                df = df.append(new_player)

            df.loc[name, self.field_matches_played] += 1
            df.loc[name, self.field_total_score] += score
            df.loc[name, self.field_average_score] = df.loc[name,
                                                            self.field_total_score] / df.loc[name, self.field_matches_played]
            df.loc[name, f'{placement}'] += 1

        return df


    async def convert_to_multiple_strings(self, df, fields, numalign='right', stralign='right'):
        table = df
        table_list = [table]

        digested = [[index, row.loc[self.field_total_score], f'{row.loc[self.field_first]}-{row.loc[self.field_second]}-{row.loc[self.field_third]}-{row.loc[self.field_fourth]}', row.loc[self.field_majsoul_name]] for index, row in df.iterrows()]

        table_string = tabulate(digested, headers=['#', 'Total', 'Record', 'Name'], floatfmt="+.1f", numalign=numalign)

        messages = []
        current_msg = ''
        for line in table_string.splitlines():
            if len(line) > DISCORD_MAX_CHAR_LIMIT:
                raise Exception('really long message which you could handle more intelligently')
            elif len(line) + len(current_msg) < DISCORD_MAX_CHAR_LIMIT:
                current_msg += line + "\n"
            else:
                messages.append(f"```\n{current_msg}```\n")
                current_msg = line + "\n"

        if current_msg:
            messages.append(f"```\n{current_msg}```\n")

        return messages

    @commands.command(name='set-datetime-filter', aliases=['set-filter'])
    async def command_set_datetime_filter(self, ctx, start: str = "", end: str = ""):
        try:
            datetime_start = datetime.fromisoformat(start)
        except ValueError as e:
            datetime_start = datetime.min

        try:
            datetime_end = datetime.fromisoformat(end)
        except ValueError as e:
            datetime_end = datetime.max

        self.game_log_filter = GameLogFilter(datetime_start, datetime_end)

        await ctx.send(f"{datetime_start.isoformat()} to {datetime_end.isoformat()}")

    @commands.command(name="stop-log-search", aliases=['stop-search', 'stop'])
    async def command_stop_log_search(self, ctx):
        self.event_stop_log_search.set()

    @commands.command(name="retrieve-logs", aliases=["get-logs"])
    async def command_retrieve_logs(self, ctx):
        num_found = await self.get_logs()
        await ctx.send(f"Found {num_found} games.")

    async def get_logs(self):
        ContestManager = self.bot.get_cog('ContestManagerInterface')

        next_index = 0
        continueSearch = True
        hits = []
        self.initialize_dataframe()

        while continueSearch:
            if self.event_stop_log_search.is_set():
                self.event_stop_log_search.clear()
                break

            res = await ContestManager.client.call('fetchContestGameRecords', last_index=next_index)
            next_index = res.next_index

            for item in res.record_list:
                if self.game_log_filter != None:
                    if self.game_log_filter.match(datetime.fromtimestamp(item.record.end_time)):
                        hits.append(item.record)

                    if datetime.fromtimestamp(item.record.end_time) < self.game_log_filter.datetime_start:
                        continueSearch = False
                else:
                    hits.append(item.record)

            # Response was only one page long.
            if next_index == 0:
                break

        await self.record_multiple_games(hits)
        return len(hits)

    @commands.command(name='scores', aliases=['score'])
    async def command_display_table(self, ctx):
        """
        Displays the score table.

        Usage: `ms/scores`

        Displays a score table that automatically updates with the latest scores whenever a Majsoul game in the tournament lobby concludes.
        """

        ContestManager = self.bot.get_cog('ContestManagerInterface')
        res = await ContestManager.client.call('fetchContestGameRule')

        rules = res.game_rule_setting.detail_rule_v2.game_rule

        starting_points = rules.init_point
        target_points = rules.fandian
        sanma = is_sanma(res.game_rule_setting.round_type)

        if sanma:
            shunweima_1 = (int)(-1*(rules.shunweima_2 + rules.shunweima_3))
            uma = [shunweima_1, rules.shunweima_2, rules.shunweima_3]
        else:
            shunweima_1 = (int)(-1*(rules.shunweima_2 +
                                    rules.shunweima_3 + rules.shunweima_4))
            uma = [shunweima_1, rules.shunweima_2, rules.shunweima_3, rules.shunweima_4]

        # Monthly scores
        if self.game_log_filter != None:
            dt_start = self.game_log_filter.datetime_start.date()
            dt_end = self.game_log_filter.datetime_end.date()
            await ctx.send(f"MONTHLY scores ({dt_start} to {dt_end})")

        df = await self.create_score_table(starting_points, target_points, uma, sanma)
        df = df.sort_values(by=self.field_total_score, ascending=False)
        df = df.reset_index(drop=True)
        df.index += 1

        scores = await self.convert_to_multiple_strings(df, self.score_table_display_fields)

        for s in scores:
            await ctx.send(s)

        # Weekly scores
        if self.weekly_filter != None:
            dt_start = self.weekly_filter.datetime_start.date()
            dt_end = self.weekly_filter.datetime_end.date()
            await ctx.send(f"WEEKLY scores ({dt_start} to {dt_end})")

        df = await self.create_score_table(starting_points, target_points, uma, sanma, self.weekly_filter)
        df = df.sort_values(by=self.field_total_score, ascending=False)
        df = df.reset_index(drop=True)
        df.index += 1

        scores = await self.convert_to_multiple_strings(df, self.score_table_display_fields)

        for s in scores:
            await ctx.send(s)

def setup(bot):
    t = TournamentScoreTracker(bot)
    bot.add_cog(t)

def is_sanma(round_type):
    return round_type in [11, 12, 13, 14]

def first_monday(year, month):
    day = (8 - datetime.date(year, month, 1).weekday()) % 7
    return datetime.date(year, month, day)

def final_wednesday(year, month):
    day = ((8+2) - datetime.date(year, month, 31).weekday()) % 7
    return datetime.date(year, month, day)
