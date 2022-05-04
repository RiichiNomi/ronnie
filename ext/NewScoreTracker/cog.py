import asyncio
from logging import exception
import math
import os
import pandas as pd
import pickle
import unicodedata
import json

from datetime import date, datetime

from discord.ext import commands

from tabulate import tabulate

RECORDS_FOLDER = 'ext/NewScoreTracker/records'

DEFAULT_RECORDS_NAME = 'log'

DISCORD_MAX_CHAR_LIMIT = 2000


class GameLogFilter():
    def __init__(self, datetime_start=datetime.min, datetime_end=datetime.max):
        self.datetime_start = datetime_start
        self.datetime_end = datetime_end

    def filter_log(self, game_log):
        if datetime.fromtimestamp(game_log.start_time) < self.datetime_start:
            return False
        if datetime.fromtimestamp(game_log.end_time) > self.datetime_end:
            return False

        return True


class TournamentScoreTracker(commands.Cog):
    "Score Tracking"
    field_best_consecutive_score = 'Best\nRun'

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

        self.game_log_filter = None

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

    async def create_score_table(self, starting_points, return_points, uma, sanma=False):
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
                df = await self.update_score_table(df, records, index, starting_points, return_points, uma, sanma)

        return df

    async def update_score_table(self, df, records, index, starting_points, return_points, uma, sanma):
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

    async def convert_to_string(self, df, fields, numalign='right', stralign='right'):
        response = f'```{tabulate(df, headers=fields, floatfmt=".1f", numalign=numalign)}```'

        return response

    async def convert_to_multiple_strings(self, df, fields, numalign='right', stralign='right'):
        table = df
        table_list = [table]

        while True:
            table_string = await self.convert_to_string(table_list[0], fields, numalign, stralign)

            if len(table_string) > DISCORD_MAX_CHAR_LIMIT:
                temp_list = []
                for t in table_list:
                    index = round(len(t)/2)
                    temp_list.append(t[0:index])
                    temp_list.append(t[index:])

                table_list = temp_list
            else:
                break

        return [f'```{tabulate(table, headers=fields, floatfmt=".1f", numalign=numalign, stralign=stralign)}```' for table in table_list]

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
        if self.game_log_filter == None:
            await ctx.send("Log filter not set. If you wish to retrieve all logs, enter a filter with no parameters set.")
            return

        ContestManager = self.bot.get_cog('ContestManagerInterface')

        next_index = 0
        num_found = 0
        continueSearch = True
        hits = []
        self.initialize_dataframe()

        response_text = f"Found {num_found} games."
        response_msg = await ctx.send(response_text)

        while continueSearch:
            if self.event_stop_log_search.is_set():
                self.event_stop_log_search.clear()
                await ctx.send("Stopping search...")
                break

            res = await ContestManager.client.call('fetchContestGameRecords', last_index=next_index)
            next_index = res.next_index

            for item in res.record_list:
                if self.game_log_filter != None:
                    if self.game_log_filter.filter_log(item.record):
                        num_found += 1
                        hits.append(item.record)

                    if datetime.fromtimestamp(item.record.end_time) < self.game_log_filter.datetime_start:
                        continueSearch = False
                else:
                    hits.append(item.record)

            if num_found > 0:
                response_text = f"Found {num_found} games."
                await response_msg.edit(content=response_text)

            # Response was only one page long.
            if next_index == 0:
                break

        await ctx.send("Finished.")
        await self.record_multiple_games(hits)

    @commands.command(name='scores', aliases=['score'])
    async def command_display_table(self, ctx):
        """
        Displays the score table.

        Usage: `ms/scores`

        Displays a score table that automatically updates with the latest scores whenever a Majsoul game in the tournament lobby concludes.
        """

        if self.game_log_filter != None:
            dt_start = self.game_log_filter.datetime_start.date()
            dt_end = self.game_log_filter.datetime_end.date()

            if dt_start == date.min:
                dt_start = "Past"
            else:
                dt_start = dt_start.isoformat()

            if dt_end == date.max:
                dt_end = "Present"
            else:
                dt_end = dt_end.isoformat()

            await ctx.send(f"Displaying scores from {dt_start} to {dt_end}")

        ContestManager = self.bot.get_cog('ContestManagerInterface')
        res = await ContestManager.client.call('fetchContestGameRule')

        rules = res.game_rule_setting.detail_rule_v2.game_rule

        starting_points = rules.init_point
        target_points = rules.fandian
        sanma = is_sanma(res.game_rule_setting.round_type)

        if sanma:
            shunweima_1 = (int)(-1*(rules.shunweima_2 +
                                    rules.shunweima_3 + rules.shunweima_4))
            uma = [shunweima_1, rules.shunweima_2, rules.shunweima_3, rules.shunweima_4]
        else:
            shunweima_1 = (int)(-1*(rules.shunweima_2 + rules.shunweima_3))
            uma = [shunweima_1, rules.shunweima_2, rules.shunweima_3]

        df = await self.create_score_table(starting_points, target_points, uma, sanma)
        df = df.sort_values(by=self.field_total_score, ascending=False)
        df = df.reset_index(drop=True)
        df.index += 1

        scores = await self.convert_to_multiple_strings(df, self.score_table_display_fields)

        for s in scores:
            await ctx.send(s)

    @commands.command(name='best-5')
    async def command_best_consecutive_scores(self, ctx):
        ContestManager = self.bot.get_cog('ContestManagerInterface')
        res = await ContestManager.client.call('fetchContestGameRule')

        rules = res.game_rule_setting.detail_rule_v2.game_rule

        starting_points = rules.init_point
        target_points = rules.fandian
        shunweima_1 = (int)(-1*(rules.shunweima_2 +
                                rules.shunweima_3 + rules.shunweima_4))

        df = await self.best_consecutive_score_table(5, starting_points, target_points, [shunweima_1, rules.shunweima_2, rules.shunweima_3, rules.shunweima_4])

        df = df.sort_values(
            by=self.field_best_consecutive_score, ascending=False)
        df = df.reset_index(drop=True)
        df.index += 1

        df = df.fillna(value='n/a')

        scores = await self.convert_to_multiple_strings(df, fields=df.columns)

        for s in scores:
            await ctx.send(s)

    async def best_consecutive_score_table(self, n, starting_points, target_points, uma, sanma=False):
        df = pd.DataFrame(columns=[self.field_majsoul_name])

        records = {}

        ScoreCalculator = self.bot.get_cog('ScoreCalculator')

        async with self.game_records_lock:
            if sanma:
                records = self.SANMA_GAME_RECORDS
                name_fields = self.sanma_player_name_fields
                point_fields = self.sanma_player_point_fields
            else:
                records = self.YONMA_GAME_RECORDS
                name_fields = self.yonma_player_name_fields
                point_fields = self.yonma_player_point_fields

            for i in records.index:
                PLAYERS = [records.loc[i, n] for n in name_fields]
                POINTS = [records.loc[i, s] for s in point_fields]
                SCORES = ScoreCalculator.calculate_scores(
                    POINTS, starting_points, target_points, uma)

                for name, score in list(zip(PLAYERS, SCORES)):
                    if name not in records:
                        records[name] = []

                    records[name].append(score)

        for name in records:
            best_total, best_scores = self.best_consecutive_n(records[name], n)

            df.loc[name, self.field_majsoul_name] = name
            df.loc[name, self.field_best_consecutive_score] = best_total

            i = 1
            for score in best_scores:
                df.loc[name, f'{i}'] = score
                i += 1

        return df

    def best_consecutive_n(self, scores, n):
        if len(scores) <= n or n <= 0:
            return sum(scores), scores

        best_start_index = 0
        best_sum = sum(scores[0:n])

        for i in range(1, len(scores)):
            if i > len(scores) - n:
                break

            current_sum = sum(scores[i:i+n])

            if current_sum > best_sum:
                best_start_index = i
                best_sum = current_sum

        return best_sum, scores[best_start_index:best_start_index+n]

def setup(bot):
    bot.add_cog(TournamentScoreTracker(bot))

def is_sanma(round_type):
    return round_type in [11, 12, 13, 14]
