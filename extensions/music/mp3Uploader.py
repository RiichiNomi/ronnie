from discord.ext import commands
import discord

sounds_folder = 'extensions/music/sounds/'

class mp3Uploader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='upload-mp3', aliases=['admin-upload-mp3'])
    @commands.has_permissions(administrator=True)
    async def admin_upload_mp3(self, ctx):
        if ctx.message.attachments:
            attchmnt = ctx.message.attachments[0]
        
        with open(sounds_folder+attchmnt.filename, 'wb') as f:
            r = await attchmnt.read()
            f.write(r)

def setup(bot):
    bot.add_cog(mp3Uploader(bot))

