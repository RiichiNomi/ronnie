from discord.ext import commands
import discord
import os

startup_channel = "General"
sounds_folder = 'extensions/music/sounds/'

class MusicPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def display_vclients(self, ctx):
        await ctx.send(f'{self.bot.voice_clients}')
    
    @commands.command(name='voice-connect', aliases=['connect'])
    async def vc_connect(self, ctx, channelName='General'):
        vclient = self.bot.voice_clients[0] if self.bot.voice_clients else None
        
        if vclient:
            await ctx.send(f'{ctx.author.mention} Bot already connected to voice channel.')
            return
        
        channel = [vc for vc in ctx.guild.voice_channels if vc.name == channelName][0] if ctx.guild.voice_channels else None

        print(channel)

        if channel == None:
            await ctx.send(f'{ctx.author.mention} Voice channel "{channelName}" not found.')
            return

        try:
            await channel.connect()
            await ctx.send(f'{ctx.author.mention} Bot is connected to voice channel "{channelName}".')
        except Exception as e:
            print(e)
            await ctx.send(f'ERROR: Unable to connect to voice channel. See log output.')

    @commands.command(name='voice-disconnect', aliases=['disconnect'])
    async def vc_disconnect(self, ctx):
        vclient = self.bot.voice_clients[0] if self.bot.voice_clients else None

        if not vclient:
            await ctx.send(f'{ctx.author.mention} Bot not connected to any voice channel.')
            return

        try:
            await vclient.disconnect()
            await ctx.send(f'{ctx.author.mention} Bot disconnected from voice channel.')
        except Exception as e:
            print(e)
            await ctx.send(f'ERROR: Unable to disconnect from voice channel. See log output.')

    
    @commands.command(name='play')
    async def play(self, ctx, songName=None):
        vclient = self.bot.voice_clients[0] if self.bot.voice_clients else None

        if not vclient or not vclient.is_connected():
            await ctx.send(f'{ctx.author.mention} Bot is not in any voice channel.')
            return
        
        if songName == None:
            await ctx.send(f'{ctx.author.mention} No soundbite selected.')
            return

        try:
            source = discord.FFmpegPCMAudio(sounds_folder+f'{songName}.mp3')

            if not vclient.is_playing():
                vclient.play(source, after=None)
        except Exception as e:
            print(e)


    @commands.command(name='stop')
    async def stop(self, ctx):
        vclient = self.bot.voice_clients[0] if self.bot.voice_clients else None

        if not vclient or not vclient.is_connected():
            await ctx.send(f'{ctx.author.mention} Bot is not connected to any voice channel.')
            return
        
        if vclient.is_playing():
            vclient.stop()
            await ctx.send(f'{ctx.author.mention} Stopped.')
        else:
            await ctx.send(f'{ctx.author.mention} No soundbite currently playing.')
    
    @commands.command(name='sound-list', aliases=['soundlist'])
    async def display_sound_list(self, ctx):
        soundlist = os.listdir(sounds_folder)
        response = f'There are currently ({len(soundlist)}) available soundbites:\n\n'
        soundlist.sort()
        for sound in soundlist:
            sound = sound.replace('.mp3', '')
            response += f'{sound} | '
        
        response += f'\n\nTo make the bot connect to a voice channel, type !connect <voice-channel-name>\n'
        response += f'To make the bot play a soundbite, type !play <soundbite-name>\n'
        response += f'To make the bot stop playing, type !stop'
        
        await ctx.send(response)

def setup(bot):
    bot.add_cog(MusicPlayer(bot))

