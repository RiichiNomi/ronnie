import asyncio
import math
import pandas as pd
import pickle
import unicodedata

from discord.ext import commands

from tabulate import tabulate

DISCORD_MAX_CHAR_LIMIT = 2000

class TournamentScoreTracker(commands.Cog):
    "Score Tracking"
    display_fields = ['', 'Name', 'Total\nScore', 'Average\nScore', 'Matches\nPlayed', '1st', '2nd', '3rd', '4th']
    fields = ['account_id', 'Majsoul Name', 'Total Score', 'Average Score', 'Matches Played', '1', '2', '3', '4']
    index = 'account_id'
    def __init__(self, bot):
        self.bot = bot

    def load(self, score_key):
        name = self.pickle_file(score_key)

        try:
            with open(name, 'rb') as f:
                data = pickle.load(f)
        except FileNotFoundError:
            data = pd.DataFrame(columns=self.fields)
            data.set_index(self.index, drop=True, inplace=True)
            with open(name, 'wb') as f:
                pickle.dump(data, f)
        except EOFError:
            data = pd.DataFrame(columns=self.fields)
            data.set_index(self.index, drop=True, inplace=True)

        pd.set_option("display.unicode.east_asian_width", True)
        return data

    async def save(self, score_key, data):
        with open(self.pickle_file(score_key), 'wb') as f:
            pickle.dump(data, f)

    def exists(self, data, account_id):
        return account_id in data.index

    async def register(self, data, account_id, majsoul_name):
        if not self.exists(data, account_id):
            entry = [0 for x in range(0, len(self.fields)-1)]
            entry[0] = unicodedata.normalize('NFC', majsoul_name)
            data.loc[account_id] = entry

    async def record_game(self, score_key, players, points, rules, round_mode='round'):
        '''
        Input:
            players - list of tuples (ID, name) where ID is the player's majsoul id
                and name is their majsoul handle

            points - list of integers

            Assumes that the points are ordered from 1st place to 4th place and that
            the order of the players in the list matches the order of the points
        '''

        ScoreCalculator = self.bot.get_cog('ScoreCalculator')

        game_rule = rules.detail_rule_v2.game_rule
        uma = [
            -1 * (game_rule.shunweima_2 + game_rule.shunweima_3 + game_rule.shunweima_4),
            game_rule.shunweima_2, game_rule.shunweima_3, game_rule.shunweima_4
        ]

        scores = ScoreCalculator.calculate_scores(points, game_rule.init_point, game_rule.jingsuanyuandian, uma)

        if round_mode == 'round':
            scores = [round(p, 1) for p in scores]

        if round_mode == 'ceil' or round_mode == 'ceiling':
            scores = [math.ceil(p*10)/10 for p in scores]

        if round_mode == 'floor':
            scores = [math.floor(p*10)/10 for p in scores]

        data = self.load(score_key)
        position = 1
        for account_id, majsoul_name in players:
            if not self.exists(data, account_id):
                await self.register(data, account_id, majsoul_name)

            data['Majsoul Name'][account_id] = unicodedata.normalize('NFC', majsoul_name)

            pts = scores[position-1]

            data['Total Score'][account_id] += pts
            data['Matches Played'][account_id] += 1
            data['Average Score'][account_id] = data['Total Score'][account_id] / data['Matches Played'][account_id]

            data[str(position)][account_id] += 1

            rank_sum = 1*data['1'][account_id] + 2*data['2'][account_id] + 3*data['3'][account_id] + 4*data['4'][account_id]

            #data['Avg Pos'][account_id] = rank_sum / data['Matches Played'][account_id]

            position += 1

        await self.save(score_key, data)
        return scores

    async def convert_to_string(self, df):
        table = df.reset_index(drop=True)

        table = table.sort_values(by='Total Score', ascending=False)
        table = table.reset_index(drop=True)

        table.index += 1

        response = f'```{tabulate(table, headers=self.display_fields, floatfmt=".1f")}```'

        return response

    async def convert_to_multiple_strings(self, df):
        table = df.reset_index(drop=True)

        table = table.sort_values(by='Total Score', ascending=False)
        table = table.reset_index(drop=True)

        table.index += 1

        table_list = [table]

        while True:
            table_string = await self.convert_to_string(table_list[0])

            if len(table_string) > DISCORD_MAX_CHAR_LIMIT:
                temp_list = []
                for t in table_list:
                    index = round(len(t)/2)
                    temp_list.append(t[0:index])
                    temp_list.append(t[index:])

                table_list = temp_list
            else:
                break

        return [f'```{tabulate(table, headers=self.display_fields, floatfmt=".1f")}```' for table in table_list]

    @commands.command(name='scores', aliases=['score'])
    async def display_table(self, ctx):
        """
        Displays the score table.

        Usage: `ms/scores`

        Displays a score table that automatically updates with the latest scores whenever a Majsoul game in the tournament lobby concludes.
        """

        data = self.load(str(ctx.channel.id))
        scores = await self.convert_to_multiple_strings(data)

        for s in scores:
            await ctx.send(s)

    @commands.command(name='record-game', hidden=True)
    async def command_record_game(self, ctx, uuid):
        MajsoulClientInterface = self.bot.get_cog('MajsoulClientInterface')

        # XXX(joshk): You have to record the game of the tournament you're currently managing
        ContestManager = self.bot.get_cog('ContestManagerInterface')

        log = await MajsoulClientInterface.client.fetch_game_log(uuid)

        # retrieving rules useful for score tracking
        res = await ContestManager.client.call('fetchContestGameRule')
        rules = res.game_rule_setting

        points = [player.part_point_1 for player in log.head.result.players]

        seats = [player.seat for player in log.head.result.players]

        players = [(log.head.accounts[s].account_id, log.head.accounts[s].nickname) for s in seats]

        await self.record_game(str(ctx.channel.id), players, points, rules)

        await ctx.send(f'Game {uuid} recorded.')

    @staticmethod
    def pickle_file(channel_id):
        return f'ext/ScoreTracker/score-sheets/{channel_id}.pickle'

def setup(bot):
    bot.add_cog(TournamentScoreTracker(bot))
