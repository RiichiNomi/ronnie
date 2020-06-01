import os

import sqlite3

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv('var.env')

MEMBERS_FILE = os.environ.get('MEMBERS_FILE')

class Lobby():
    def __init__(self):
        self.size = 0

        self.players = []
        self.playersInLobby = []
        self.playersInGame = []

        self.locked = False

    def clear(self):
        self.size = 0

        self.players.clear()
        self.playersInLobby.clear()
        self.playersInGame.clear()

    def add(self, user):
        self.players.append(user)
        self.size += 1

    def remove(self, user):
        self.players.remove(user)
        self.size -= 1
    
class LobbyInterface(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lobby = Lobby()

    @commands.command(name='join')
    async def member_join_list(self, ctx):
        self.lobby.add(ctx.author)

    @commands.command(name='leave')
    async def member_leave_list(self, ctx):
        self.lobby.remove(ctx.author)

    @commands.command(name='list')
    async def display_lobby_state(self, ctx):
        response = f'''There are currently {self.lobby.size} player(s) in the lobby: \n'''

        for i in range(0, len(self.lobby.players)):
            player = self.lobby.players[i]
            response += f'''{i+1}. {player.nick}\n'''

        await ctx.send(response)
    
class MemberInterface(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.members_file = 'extensions/club/members.db'
        self.db_connection = None

        self.db_connect()
    
    def __exit__(self):
        self.db_connection.close()
    
    @commands.command(name='join-club')
    async def member_join(self, ctx):
        try:
            if (not self.member_exists(ctx.author.id)):
                insertion_query = f'''
                    INSERT into Members (ID, username) \
                    VALUES ({ctx.author.id}, '{ctx.author.name}');
                '''

                self.db_connection.execute(insertion_query)
                self.db_connection.commit()

                response = f'''
                    New member <@{ctx.author.id}> with Discord ID #{ctx.author.id} added to members list.
                '''
            else:
                response = f'''
                    Member <@{ctx.author.id}> with Discord ID #{ctx.author.id} already exists.
                '''
            await ctx.send(response)
        except Exception as e:
            print(e)
            await ctx.send(f"Error: {e}")
    
    @commands.command(name='leave-club')
    async def member_leave(self, ctx):
        try:
            query = f'''
                DELETE from Members where ID = {ctx.author.id}
            '''

            self.db_connection.execute(query)
            self.db_connection.commit()

            response = f'''
                Member <@{ctx.author.id}> with Discord ID #{ctx.author.id} removed from members list.
            '''

            await ctx.send(response)
        except Exception as e:
            print(e)
            await ctx.send(f"Error: {e}")

    @commands.command(name='update-first-name')
    async def member_update_name_first(self, ctx, arg):
        if (self.member_exists(ctx.author.id)):
            arg = (arg,)
            query = f'''
                UPDATE Members 
                SET firstName = ?
                WHERE id = {ctx.author.id}
            '''
            self.db_connection.execute(query, arg)
            self.db_connection.commit()
        else:
            await ctx.send(f'''
                <@{ctx.author.id}> not in member list. Type !join-club to join the list.
            ''')

    def db_connect(self):
        try:
            self.db_connection = sqlite3.connect(self.members_file)
        except Exception as e:
            print(e)
    
    def member_exists(self, userid):
        try:
            search = f'''
                SELECT COUNT(*) FROM Members WHERE ID = {userid};
            '''

            num_match = self.db_connection.execute(search).fetchone()[0]

            return num_match > 0
        except Exception as e:
            print(e)


def setup(bot):
    bot.add_cog(MemberInterface(bot))
    bot.add_cog(LobbyInterface(bot))