# Extension for displaying the bot's help message(s)

@commands.command(name='help')
async def display_help_message(ctx):
    pass

def setup(bot):
    bot.add_cog(display_help_message)