import os
import sqlite3
import random
from discord.ext import commands
from dotenv import load_dotenv

class Lobby():
    def __init__(self):
        self.size = 0
        self.numPlayers = 0
        self.numReady = 0
        self.numInGame = 0
        self.numTables = 0

        self.players = []
        self.ready = []
        self.tables = []

    def clear(self):
        self.size = 0
        self.numPlayers = 0
        self.numReady = 0
        self.numInGame = 0
        self.numTables = 0
        
        self.players.clear()
        self.ready.clear()
        self.tables.clear()

    def exists(self, member):
        if (member in self.players or member in self.ready):
            return True
        
        for t in self.tables:
            if member in t:
                return True
        
        return False

    def add(self, member):
        self.players.append(member)
        self.numPlayers += 1
        self.size += 1

    def remove(self, member):
        if self.exists(member):
            if member in self.players:
                self.players.remove(member)
                self.numPlayers -= 1
            elif member in self.ready:
                self.ready.remove(member)
                self.numReady -= 1
            else: 
                for t in self.tables:
                    if member in t:
                        t.remove(member)
                    if not t:
                        self.tables.remove(t)
                        self.numTables -= 1
                self.numInGame -= 1

            self.size -= 1
    
    def shuffle(self, table_size):
        n = 0
        table_players = []
        while (self.numReady > 0):
            p = random.choice(self.ready)

            self.ready.remove(p)
            self.numReady -= 1
            self.numInGame += 1

            table_players.append(p)

            n += 1
            if (n == table_size):
                self.tables.append(table_players)
                self.numTables += 1
                n = 0
                table_players = []
        
        #returns list of leftover players
        for player in table_players:
            self.ready.append(player)
            self.numReady += 1
            self.numInGame -= 1

        return table_players

    def table_end(self, member):
        P = []
        for t in self.tables:
            if member in t:
                for player in t:
                    self.players.append(player)
                    self.numInGame -= 1
                    self.numPlayers += 1
                    P.append(player)
                
                self.tables.remove(t)
                self.numTables -= 1
        
        return P
    
    def set_ready(self, member):
        if member in self.players:
            self.ready.append(member)
            self.numReady += 1

            self.players.remove(member)
            self.numPlayers -= 1
    
    def unset_ready(self, member):
        if member in self.ready:
            self.players.append(member)
            self.numPlayers += 1

            self.ready.remove(member)
            self.numReady -= 1
    
    def display(self, member):
            return f'{member.display_name}'

                
class LobbyInterface(commands.Cog, name='lobby'):
    def __init__(self, bot):
        self.bot = bot
        self.lobby = Lobby()
        self.debug_mode = False

    @commands.command(name='join')
    async def member_join_list(self, ctx):
        '''
        Join the lobby. 
        '''
        if (self.lobby.exists(ctx.author)):
            await ctx.send(f'<@{ctx.author.id}> already in the lobby.')
        else:
            self.lobby.add(ctx.author)

            await ctx.send(f'{ctx.author.mention} joined the lobby ({self.lobby.size})')
    
    @commands.command(name='leave', aliases=['rme', 'removeme'])
    async def member_leave_list(self, ctx):
        '''
        Leave the lobby.
        '''
        if (self.lobby.exists(ctx.author)):
            self.lobby.remove(ctx.author)
            await ctx.send(f'{ctx.author.mention} left the lobby. ({self.lobby.size})')
        else:
            await ctx.send(f'{ctx.author.mention} not in the lobby.')

    @commands.command(name='ready')
    async def member_set_status_ready(self, ctx):
        '''
        Set status as ready. 
        '''
        if (self.lobby.exists(ctx.author)):
            self.lobby.set_ready(ctx.author)

            await ctx.send(f'{ctx.author.mention} marked as ready! (Ready: {self.lobby.numReady})')
        else:
            self.lobby.add(ctx.author)
            self.lobby.set_ready(ctx.author)
            await ctx.send(f'{ctx.author.mention} marked as ready! (Ready: {self.lobby.numReady})')
        
    @commands.command(name='unready')
    async def member_set_status_not_ready(self, ctx):
        '''
        Set status as not ready.
        '''
        if self.lobby.exists(ctx.author):
            self.lobby.unset_ready(ctx.author)

            await ctx.send(f'{ctx.author.mention} marked as not ready! (Ready: {self.lobby.numReady})')
        else:
            await ctx.send(f'{ctx.author.mention} not in the lobby.')
    
    @commands.command(name='shuffle', aliases=['shuggle'])
    async def list_shuffle(self, ctx, arg=None):
        '''
        Creates random tables of players who have readied up.
        '''
        table_size = 3 if arg == 'sanma' else 4

        if self.lobby.numReady == 0:
            await ctx.send(f"{ctx.author.mention} No players ready at the moment. Type !ready to ready up.")
        elif self.lobby.numReady < table_size:
            await ctx.send(f"{ctx.author.mention} Not enough ready players for a full table. Current number: {self.lobby.numReady}")
        else:
            response = f'''Creating tables:\n'''

            leftover = self.lobby.shuffle(table_size)

            tableNumber = 0
            for table in self.lobby.tables:
                tableNumber += 1
                t = f'====== Table {tableNumber} ======\n'
                l = len(t)
                for player in table:
                    name = self.lobby.display(player)
                    t += f'{name}\n'
                
                response += t
            
            response += '==================\n'
            
            for player in leftover:
                response += f'{player.display_name}\n'
            
            await ctx.send(response)
    
    @commands.command(name='tablegg', aliases=['gg'])
    async def table_gg(self, ctx):
        '''
        Places all players in a table back in the lobby.
        '''
        if (self.lobby.exists(ctx.author)):
            if ctx.author in self.lobby.players or ctx.author in self.lobby.ready:
                await ctx.send(f"<@{ctx.author.id}> not in a table.")
            else:
                members_removed = self.lobby.table_end(ctx.author)

                response = ""
                for player in members_removed:
                    response += f'{player.mention} '
                
                response += 'marked as done playing.'

                await ctx.send(response)
        else:
            await ctx.send(f'{ctx.author.mention} not in the lobby.')

    @commands.command(name='remove')
    async def member_remove_other(self, ctx):
        '''
        Removes a mentioned player in the lobby.
        '''
        removed = []
        notPresent = []
        for member in ctx.message.mentions:
            if self.lobby.exists(member):
                self.lobby.remove(member)
                removed.append(member)
            else:
                notPresent.append(member)
        
        response = f''

        for member in removed:
            response += f'{member.mention} '
        
        if removed:
            response += f'removed from the lobby (Current: {self.lobby.size})'
        else:
            response += f"{ctx.author.mention} No players marked for removal."

        await ctx.send(response)

        if notPresent:
            response = ''

            for member in notPresent:
                response += f'{member.mention} '

            response += 'not in the lobby'

            await ctx.send(response)

    @commands.command(name='list')
    async def display_lobby_state(self, ctx):
        '''
        Display the current status of the lobby.
        '''
        response = f'''There are currently {self.lobby.size} player(s) in the lobby:\n'''
        response += f'{self.lobby.numPlayers} Waiting, {self.lobby.numReady} Ready, {self.lobby.numInGame} In Game\n'
        response += '='*25 + '\n'

        if (self.lobby.size == 0):
            response += 'Wow, such empty...\n'

        playerNum = 0
        for table in self.lobby.tables:
            t = "-"*40 + '\n'

            for player in table:
                playerNum += 1
                name = self.lobby.display(player)
                t += f'{playerNum}. **(In Game) {name}\n**'

            response += t
        
        if self.lobby.numTables > 0:
            response += "-"*40 + '\n'
        
        for player in self.lobby.ready:
            playerNum += 1
            name = self.lobby.display(player)
            response += f'{playerNum}. **(Ready) {name}**\n'

        for player in self.lobby.players:
            playerNum += 1
            name = self.lobby.display(player)
            response += f'{playerNum}. {name}\n'

        response += "="*25 + '\n' + \
                    f"Commands: !list, !join, !leave, !ready, !unready, !shuffle, !tablegg"
        # Type !ready to ready up for shuffling. 
        # Type !shuffle to randomly select from those who have readied up.

        if self.debug_mode:
            response += f"\n {self.lobby.size} {self.lobby.numPlayers} {self.lobby.numReady} {self.lobby.numInGame} {self.lobby.numTables}"

        await ctx.send(response)

        # await ctx.send(f'{self.lobby.players}')
        # await ctx.send(f'{self.lobby.tables}')

    @commands.command(name='clearlist', hidden=True)
    async def clear_list(self, ctx):
        self.lobby.clear()

        await ctx.send(f'List cleared.')

    @commands.command(name='debug', hidden=True)
    async def set_debug_mode(self, ctx, arg):
        if arg == 'on':
            self.debug_mode = True
        else:
            self.debug_mode = False

            
def setup(bot):
    bot.add_cog(LobbyInterface(bot))