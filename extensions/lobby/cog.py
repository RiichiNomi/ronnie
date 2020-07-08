import os
import random
from discord.ext import commands
from discord.utils import get
from extensions.lobby.emojis import role_emojis
from extensions.lobby.emojis import button_emojis

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
        if not self.exists(member):
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
        tablePlayers = []
        while (self.numReady > 0):
            p = random.choice(self.ready)

            self.ready.remove(p)
            self.numReady -= 1
            self.numInGame += 1

            tablePlayers.append(p)

            n += 1
            if (n == table_size):
                self.tables.append(tablePlayers)
                self.numTables += 1

                n = 0
                tablePlayers = []
        
        #returns list of leftover players
        for player in tablePlayers:
            self.ready.append(player)
            self.numReady += 1
            self.numInGame -= 1

        return tablePlayers

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
        name = f'{member.display_name} '
        for role in member.roles:
            if role.name in role_emojis:
                name += f'{role_emojis[role.name]}'
        
        return name
    
    def list_display(self):
        response = f'''There are currently {self.size} player(s) in the lobby:\n'''
        response += f'{self.numPlayers} Waiting, {self.numReady} Ready, {self.numInGame} In Game\n'
        response += '='*25 + '\n'

        if (self.size == 0):
            response += 'Wow, such empty...\n'

        playerNum = 0
        for table in self.tables:
            t = "-"*40 + '\n'

            for player in table:
                playerNum += 1
                name = self.display(player)
                t += f'{playerNum}. **(In Game) {name}\n**'

            response += t
        
        if self.numTables > 0:
            response += "-"*40 + '\n'
        
        for player in self.ready:
            playerNum += 1
            name = self.display(player)
            response += f'{playerNum}. **(Ready) {name}**\n'

        for player in self.players:
            playerNum += 1
            name = self.display(player)
            response += f'{playerNum}. {name}\n'

        response += "="*25 + '\n' + \
                    "Join  Leave  Ready  Unready  Shuffle"

        
        response += '\n   | \t\t  |  \t\t  |\t\t   |\t\t\t|'
        
        return response
                 
class LobbyInterface(commands.Cog, name='lobby'):
    def __init__(self, bot):
        self.bot = bot
        self.lobby = Lobby()
        self.debug_mode = False
        self.mostRecentListDisplayMessage = None
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # if reaction.message != self.mostRecentListDisplayMessage:
        #     return
        #print(str(reaction.emoji))
        if user.bot:
            return
        if self.mostRecentListDisplayMessage and reaction.message.id != self.mostRecentListDisplayMessage.id:
            return
        if str(reaction.emoji) not in button_emojis.keys():
            return
        
        await reaction.remove(user)

        emoji = str(reaction.emoji)
        action = button_emojis[emoji]

        if action == 'join':
            self.lobby.add(user)
        elif action == 'leave':
            self.lobby.remove(user)
        elif action == 'ready':
            if not self.lobby.exists(user):
                self.lobby.add(user)
            self.lobby.set_ready(user)
        elif action == 'unready':
            self.lobby.unset_ready(user)
        elif action == 'shuffle':
            self.lobby.shuffle(4)
            
        response = self.lobby.list_display()
        await self.mostRecentListDisplayMessage.edit(content=response)
            
    
    @commands.command(name='list')
    async def display_lobby_state(self, ctx):
        '''
        Display the current status of the lobby.
        '''
        response = self.lobby.list_display()

        if self.debug_mode:
            response += f"\n {self.lobby.size} {self.lobby.numPlayers} {self.lobby.numReady} {self.lobby.numInGame} {self.lobby.numTables}"

        if self.mostRecentListDisplayMessage:
            try:
                await self.mostRecentListDisplayMessage.delete()
            except Exception as e:
                await ctx.send(str(e))

        self.mostRecentListDisplayMessage = await ctx.send(response)

        for emoji in button_emojis.keys():
            await self.mostRecentListDisplayMessage.add_reaction(emoji)

        # await ctx.send(f'{self.lobby.players}')
        # await ctx.send(f'{self.lobby.tables}')


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
        
        if self.mostRecentListDisplayMessage:
            response = self.lobby.list_display()
            await self.mostRecentListDisplayMessage.edit(content=response)
    
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
        
        if self.mostRecentListDisplayMessage:
            response = self.lobby.list_display()
            await self.mostRecentListDisplayMessage.edit(content=response)

    @commands.command(name='ready', aliases=['repaldy', 'ydaer'])
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
        
        if self.mostRecentListDisplayMessage:
            response = self.lobby.list_display()
            await self.mostRecentListDisplayMessage.edit(content=response)
        
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
        
        if self.mostRecentListDisplayMessage:
            response = self.lobby.list_display()
            await self.mostRecentListDisplayMessage.edit(content=response)
    
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
                for player in table:
                    name = self.lobby.display(player)
                    t += f'{name}\n'
                
                response += t
            
            response += '==================\n'
            
            for player in leftover:
                name = self.lobby.display(player)
                response += f'{name}\n'
            
            await ctx.send(response)
        
        if self.mostRecentListDisplayMessage:
            response = self.lobby.list_display()
            await self.mostRecentListDisplayMessage.edit(content=response)
    
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
        
        if self.mostRecentListDisplayMessage:
            response = self.lobby.list_display()
            await self.mostRecentListDisplayMessage.edit(content=response)

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
        
        if self.mostRecentListDisplayMessage:
            response = self.lobby.list_display()
            await self.mostRecentListDisplayMessage.edit(content=response)

    @commands.command(name='clearlist', hidden=True)
    async def clear_list(self, ctx):
        self.lobby.clear()

        await ctx.send(f'List cleared.')

        if self.mostRecentListDisplayMessage:
            response = self.lobby.list_display()
            await self.mostRecentListDisplayMessage.edit(content=response)

    @commands.command(name='debug', hidden=True)
    async def set_debug_mode(self, ctx, arg):
        if arg == 'on':
            self.debug_mode = True
        else:
            self.debug_mode = False

            
def setup(bot):
    bot.add_cog(LobbyInterface(bot))