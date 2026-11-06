import discord
from discord.ext import commands

class Bot(commands.Bot):
    def __init__(self, command_prefix: str, intents: discord.Intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def setup_hook(self):
        from cogs import load_cogs
        load_cogs(self)