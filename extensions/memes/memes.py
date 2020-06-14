from discord.ext import commands
import discord
import json
import random

link_file = 'extensions/memes/links.json'
meme_approval_channel = 718225883403386941

class MemesInterface(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.link_file = link_file
        self.memes_list = {}
        self.memes_awaiting_approval = {}

        self.guild = self.bot.guilds[0]
        self.approval_channel = self.bot.guilds[0].get_channel(meme_approval_channel)
        
        self.load_memes()
    
    def load_memes(self):
        with open(self.link_file, 'r') as f:
            self.memes_list = json.load(f)
    
    def save_memes(self):
        with open(self.link_file, 'w') as f:
            json.dump(self.memes_list, f)
    
    #USER COMMANDS
    
    @commands.command(name='meme', aliases=['memes'])
    async def user_get_meme(self, ctx, meme_name=None):
        if ctx.prefix != 'd/':
            return

        if meme_name == None:
            meme_name = random.choice(list(self.memes_list.keys()))
            meme_link = self.memes_list[meme_name]
            await ctx.send(f'"{meme_name}" \n{meme_link}')
            return
        
        if meme_name not in self.memes_list.keys():
            await ctx.send(f'{ctx.author.mention} "{meme_name}" not in list of memes.')
            return
        
        meme_link = self.memes_list[meme_name]

        await ctx.send(f'Meme: "{meme_name}" \n{meme_link}')
    
    @commands.command(name='meme-list', aliases=['memes-list', 'memelist', 'memeslist'])
    async def user_get_meme_list(self, ctx):
        response = f'{ctx.author.mention} Here are the available memes: \n\n'

        names = list(self.memes_list.keys())
        names.sort()

        for meme_name in names:
            response += f'{meme_name} | '
        
        response += f'\n\nTo select a meme, type !meme <meme-name>\nTo select a random meme, type !meme'
        
        await ctx.send(response)
    
    @commands.command(name='submit-meme')
    async def user_upload_meme(self, ctx, meme_name=None, meme_link=None):
        '''
        Submits a meme to be approved by the mods.
        '''


        if meme_name == None or meme_link == None:
            response = f'{ctx.author.mention} Command format: !submit <name> <link>'
            await ctx.send(response)
            return

        if meme_name in self.memes_list.keys():
            response = f'{ctx.author.mention} Meme with that name already exists.'
            await ctx.send(response)
            return
        
        if meme_name in self.memes_awaiting_approval.keys():
            response = f'{ctx.author.mention} Meme with that name already submitted for approval.'
            await ctx.send(response)
            return
        
        self.memes_awaiting_approval[meme_name] = meme_link

        await ctx.send(f'{ctx.author.mention} Meme "{meme_name}" submitted for approval.')

        response = f'''{ctx.author.display_name} submitted a meme for approval. \n Meme Name: {meme_name} \n {meme_link}
        '''

        await self.approval_channel.send(response)

    #ADMIN COMMANDS

    @commands.command(name='approve')
    @commands.has_permissions(administrator=True)
    async def admin_approve_meme(self, ctx, *args):
        if not args:
            await ctx.send(f'{ctx.author.mention} No memes selected for approval.')
            return

        for meme_name in args:
            if meme_name == None:
                await ctx.send(f'{ctx.author.mention} Command format: !approve <meme-name>')
                return
            
            if meme_name not in self.memes_awaiting_approval.keys():
                await ctx.send(f'{ctx.author.mention}"{meme_name}" not in approval list.')
                return
            
            self.memes_list[meme_name] = self.memes_awaiting_approval[meme_name]
            self.memes_awaiting_approval.pop(meme_name)

            self.save_memes()

            await ctx.send(f'{ctx.author.mention} "{meme_name}" approved')
    
    @commands.command(name='reject')
    @commands.has_permissions(administrator=True)
    async def admin_reject_meme(self, ctx, *args):
        if not args:
            await ctx.send(f'{ctx.author.mention} No memes selected for rejection.')
            return

        for meme_name in args:
            if meme_name == None:
                await ctx.send(f'{ctx.author.mention} No meme selected for rejection.')
                return
            
            self.memes_awaiting_approval.pop(meme_name)

            await ctx.send(f'{ctx.author.mention} "{meme_name}" rejected.')
    
    @commands.command(name='approve-all')
    @commands.has_permissions(administrator=True)
    async def admin_approve_all(self, ctx):
        if not self.memes_awaiting_approval:
            await ctx.send(f'{ctx.author.mention} No memes awaiting approval.')
            return

        num_approved = 0
        memes_approved = []

        for meme_name in list(self.memes_awaiting_approval.keys()):
            self.memes_list[meme_name] = self.memes_awaiting_approval[meme_name]
            self.memes_awaiting_approval.pop(meme_name)
            memes_approved.append(meme_name)
            num_approved += 1
        
        self.save_memes()

        response = f'{ctx.author.mention} Approved the following ({num_approved}) memes: {memes_approved}'

        await ctx.send(response)
    
    
    @commands.command(name='approval-list')
    @commands.has_permissions(administrator=True)
    async def admin_show_approval_list(self, ctx):
        N = len(self.memes_awaiting_approval)
        response = f'There are ({N}) memes awaiting approval.'

        if (N > 0):
            response += '\n'
            for meme_name in self.memes_awaiting_approval:
                meme_link = self.memes_awaiting_approval[meme_name]

                response += f'"{meme_name}"\n{meme_link}\n'

        await ctx.send(response)
    
    @commands.command(name='clear-approval-list', aliases=['reject-all'])
    @commands.has_permissions(administrator=True)
    async def admin_clear_approval_list(self, ctx):
        self.memes_awaiting_approval.clear()

        await ctx.send(f'Approval list cleared.')
    
    @commands.command(name='delete-meme', aliases=['remove-meme'])
    @commands.has_permissions(administrator=True)
    async def admin_delete_meme(self, ctx, *args):
        for meme_name in args:
            if meme_name in self.memes_list.keys():
                self.memes_list.pop(meme_name)
                await ctx.send(f'{ctx.author.mention} Deleted "{meme_name}"')

        self.save_memes()

    @commands.command(name='upload-meme', aliases=['admin-upload', 'admin-upload-meme'], hidden=True)
    @commands.has_permissions(administrator=True)
    async def admin_upload_meme(self, ctx, meme_name=None, meme_link=None):
        if meme_name == None or meme_link == None:
            response = 'Command format: !upload <name> <link>'
            await ctx.send(response)
            return

        if meme_name in self.memes_list.keys():
            response = f'Meme with that name already exists.'
            await ctx.send(response)
            return
    
        self.memes_list[meme_name] = meme_link

        self.save_memes()
        
        await ctx.send(f'{ctx.author.display_name} Uploaded "{meme_name}"')

def setup(bot):
    bot.add_cog(MemesInterface(bot))