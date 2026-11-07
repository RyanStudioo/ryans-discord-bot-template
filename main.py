import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from src.utils.logging import setup_logging
from src.utils.tree import BotTree

load_dotenv()
setup_logging()

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not set. Please set it in your .env file.")

class Bot(commands.Bot):
    def __init__(self, command_prefix: str, intents: discord.Intents):
        super().__init__(command_prefix=command_prefix, intents=intents, tree_cls=BotTree)

    async def setup_hook(self):
        from cogs import load_cogs
        from src.utils.reloader import CogReloader

        await load_cogs(self)
        await self.tree.sync()
        CogReloader(self).start()

client = Bot(command_prefix="!", intents=discord.Intents.all())
client.run(token=TOKEN, log_handler=None)
