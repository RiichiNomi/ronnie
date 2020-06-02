import os
import sqlite3
import random
from discord.ext import commands
from dotenv import load_dotenv

class Lobby():
    def __init__(self):
        self.numPlayers = 0
        self.numTables = 0

        self.players = []
        self.tables = []

    def clear(self):
        self.numPlayers = 0
        self.players.clear()
        self.tables.clear()

    def add(self, member):
        self.players.append(member)
        self.numPlayers += 1

    def remove(self, member):
        if self.exists(member):
            if (member in self.players):
                self.players.remove(member)
            else: 
                for t in self.tables:
                    if member in t:
                        t.remove(member)
                    if not t:
                        self.tables.remove(t)

            self.numPlayers -= 1

    def exists(self, member):
        if (member in self.players):
            return True
        
        for t in self.tables:
            if member in t:
                return True
        
        return False
    
    def shuffle(self):
        n = 0
        table_players = []
        while (self.players):
            p = random.choice(self.players)
            self.players.remove(p)
            table_players.append(p)

            n += 1
            if (n == 4 or not self.players):
                self.tables.append(table_players)
                self.numTables += 1
                n = 0
                table_players = []
    
    def table_end(self, member):
        P = []
        for t in self.tables:
            if member in t:
                for player in t:
                    self.players.append(player)
                    P.append(player)
                
                self.tables.remove(t)
                self.numTables -= 1
        
        return P
        
    
class LobbyInterface(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lobby = Lobby()

    @commands.command(name='shuffle')
    async def list_shuffle(self, ctx):
        if (self.lobby.numPlayers == 0):
            await ctx.send("No players at the moment.")
        else:
            response = f'''Creating tables:\n'''

            self.lobby.shuffle()

            tableNumber = 0
            for table in self.lobby.tables:
                tableNumber += 1
                t = f'====== Table {tableNumber} ======\n'
                l = len(t)
                for player in table:
                    name = player.nick if player.nick != None else player.name
                    t += f'{name}\n'
                
                t += '==================\n'
                
                response += t
            
            await ctx.send(response)
                
    @commands.command(name='join')
    async def member_join_list(self, ctx):
        if (self.lobby.exists(ctx.author)):
            await ctx.send(f'<@{ctx.author.id}> already in the lobby.')
        else:
            self.lobby.add(ctx.author)

            name = ctx.author.nick if ctx.author.nick != None else ctx.author.name

            await ctx.send(f'{name} joined the lobby ({self.lobby.numPlayers})')

    @commands.command(name='leave')
    async def member_leave_list(self, ctx):
        if (self.lobby.exists(ctx.author)):
            self.lobby.remove(ctx.author)
            await ctx.send(f'<@{ctx.author.id}> left the lobby. ({self.lobby.numPlayers})')
        else:
            await ctx.send(f'<@{ctx.author.id}> not in the lobby.')

    @commands.command(name='list')
    async def display_lobby_state(self, ctx):
        response = f'There are currently {self.lobby.numPlayers} player(s) in the lobby:\n'

        playerNum = 0
        for table in self.lobby.tables:
            t = ""
            for player in table:
                playerNum += 1
                name = player.nick if player.nick != None else player.name
                t += f'{playerNum}. **(In Game) {name}\n**'
            
            response += t

        for player in self.lobby.players:
            playerNum += 1

            name = player.nick if player.nick != None else player.name

            response += f'{playerNum}. {name}\n'

        await ctx.send(response)

        # await ctx.send(f'{self.lobby.players}')
        # await ctx.send(f'{self.lobby.tables}')
    
    @commands.command(name='tablegg', aliases=['gg'])
    async def table_gg(self, ctx):
        if (self.lobby.exists(ctx.author)):
            if ctx.author in self.lobby.players:
                await ctx.send(f"<@{ctx.author.id}> not in a table.")
            else:
                members_removed = self.lobby.table_end(ctx.author)

                response = ""
                for player in members_removed:
                    response += f'<@{player.id}>'
                
                response += ' marked as done playing.'

                await ctx.send(response)

    @commands.command(name='tables')
    async def display_tables(self, ctx):
        if (self.lobby.numTables > 0):
            response = f'Current list of {self.lobby.numTables} tables: \n'

            tableNumber = 0
            for t in self.lobby.tables:
                tableNumber += 1
                response += '='*5 + f' Table {tableNumber} ' + '='*5 + '\n'
                for player in t:
                    name = player.nick if player.nick != None else player.name
                    response += f'{name}\n'
            
            await ctx.send(response)
        else:
            await ctx.send("No tables at the moment.")
            


def setup(bot):
    bot.add_cog(LobbyInterface(bot))