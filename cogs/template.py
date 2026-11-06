import discord
from discord import app_commands
from discord.ext import commands

class Template(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong!\nLatency: {latency}ms")

async def setup(bot: commands.Bot):
    await bot.add_cog(Template(bot))