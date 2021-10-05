from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.context import SlashContext

class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    ping_kwargs = {
        'name': 'ping',
        'description': 'ping機器人'
    }
    @cog_ext.cog_slash(**ping_kwargs)
    async def _ping(self, ctx: SlashContext) -> None:
        await ctx.send(f'Pong! ({self.bot.latency*1000}ms)', hidden=True)

def setup(bot: commands.Bot) -> None:
    bot.add_cog( Misc(bot) )