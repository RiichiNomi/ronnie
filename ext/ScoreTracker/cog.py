import asyncio
import math
import pandas as pd
import pickle
import unicodedata

from discord.ext import commands

from tabulate import tabulate

PICKLE_FILE = 'ext/ScoreTracker/score-sheets/SCORES.pickle'

DISCORD_MAX_CHAR_LIMIT = 2000

class TournamentScoreTracker(commands.Cog):
    "Score Tracking"
    display_fields = ['', 'Name', 'Total\nScore', 'Average\nScore', 'Matches\nPlayed', '1st', '2nd', '3rd', '4th']
    fields = ['account_id', 'Majsoul Name', 'Total Score', 'Average Score', 'Matches Played', '1', '2', '3', '4']
    index = 'account_id'
    def __init__(self, bot):
        self.bot = bot
        self.players = None

        self.dataframe_lock = asyncio.Lock()

        self.mostRecentMessage = None

        self.initialize_database()

    def initialize_database(self):
        try:
            with open(PICKLE_FILE, 'rb') as f:
                self.players = pickle.load(f)
        except FileNotFoundError:
            self.players = pd.DataFrame(columns=self.fields)
            self.players.set_index(self.index, drop=True, inplace=True)
            with open(PICKLE_FILE, 'wb') as f:
                pickle.dump(self.players, f)
        except EOFError:
            self.players = pd.DataFrame(columns=self.fields)
            self.players.set_index(self.index, drop=True, inplace=True)
        
        pd.set_option("display.unicode.east_asian_width", True)
        
    async def save(self):
        with open(PICKLE_FILE, 'wb') as f:
            pickle.dump(self.players, f)
    
    def exists(self, account_id):
        return account_id in self.players.index
            
    async def register(self, account_id, majsoul_name):
        async with self.dataframe_lock:
            if not self.exists(account_id):
                entry = [0 for x in range(0, len(self.fields)-1)]

                entry[0] = unicodedata.normalize('NFC', majsoul_name)

                self.players.loc[account_id] = entry
    
    async def record_game(self, players, points, rules):
        '''
        Input:
            players - list of tuples (ID, name) where ID is the player's majsoul id 
                and name is their majsoul handle
            
            points - list of integers

            Assumes that the points are ordered from 1st place to 4th place and that 
            the order of the players in the list matches the order of the points
        '''

        ScoreCalculator = self.bot.get_cog('ScoreCalculator')

        uma = [
            -1 * (rules.shunweima_2 + rules.shunweima_3 + rules.shunweima_4),
            rules.shunweima_2, rules.shunweima_3, rules.shunweima_4
        ]

        scores = ScoreCalculator.calculate_scores(points, rules.init_point, rules.fandian, uma)

        if round_mode == 'round':
            scores = [round(p, 1) for p in scores]
        
        if round_mode == 'ceil' or round_mode == 'ceiling':
            scores = [math.ceil(p*10)/10 for p in scores]
        
        if round_mode == 'floor':
            scores = [math.floor(p*10)/10 for p in scores]
    
        position = 1
        for account_id, majsoul_name in players:
            if not self.exists(account_id):
                await self.register(account_id, majsoul_name)
            
            async with self.dataframe_lock:
                self.players['Majsoul Name'][account_id] = unicodedata.normalize('NFC', majsoul_name)
                
                pts = scores[position-1]

                self.players['Total Score'][account_id] += pts
                self.players['Matches Played'][account_id] += 1
                self.players['Average Score'][account_id] = self.players['Total Score'][account_id] / self.players['Matches Played'][account_id]

                self.players[str(position)][account_id] += 1

                rank_sum = 1*self.players['1'][account_id] + 2*self.players['2'][account_id] + 3*self.players['3'][account_id] + 4*self.players['4'][account_id]
                
                #self.players['Avg Pos'][account_id] = rank_sum / self.players['Matches Played'][account_id]

                position += 1
        
        await self.save()
        
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
    
    async def update_message(self, df):
        response = await self.convert_to_string(df)

        if self.mostRecentMessage != None:
            await self.mostRecentMessage.edit(content=response)
    
    @commands.command(name='scores', aliases=['score'])
    async def display_table(self, ctx):
        """
        Displays the score table.

        Usage: `ms/scores`

        Displays a score table that automatically updates with the latest scores whenever a Majsoul game in the tournament lobby concludes.
        """

        scores = await self.convert_to_multiple_strings(self.players)

        for s in scores:
            print(len(s))
            await ctx.send(s)
    
    @commands.command(name='record-game', hidden=True)
    async def command_record_game(self, ctx, uuid):
        MajsoulClientInterface = self.bot.get_cog('MajsoulClientInterface')

        log = await MajsoulClientInterface.client.fetch_game_log(uuid)

        points = [player.part_point_1 for player in log.head.result.players]

        seats = [player.seat for player in log.head.result.players]

        players = [(log.head.accounts[s].account_id, log.head.accounts[s].nickname) for s in seats]

        await self.record_game(players, points)

        await ctx.send(f'Game {uuid} recorded.')
    
    @commands.command(name='subtract', hidden=True)
    async def command_remove_points(self, ctx, points:float):
        self.players['Total Score'] -= points

def setup(bot):
    bot.add_cog(TournamentScoreTracker(bot))
