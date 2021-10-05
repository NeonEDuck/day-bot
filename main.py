from threading import Thread
import discord
from discord.ext import commands
from discord_slash import SlashCommand
from typing import List
from variable import TOKEN
import error_handler
import app

intents: discord.Intents = discord.Intents.default()
intents.members = True
bot:     commands.Bot = commands.Bot(intents=intents, command_prefix='nebot:')
slash:   SlashCommand = SlashCommand(bot, sync_commands=True)
extensions: List[str] = ['cogs.vote', 'cogs.response', 'cogs.misc']

if __name__ == '__main__':
    error_handler.setup(bot)
    server: Thread = Thread(target=app.run)
    server.start()

    for ext in extensions:
        bot.load_extension(ext)

    bot.run(TOKEN)