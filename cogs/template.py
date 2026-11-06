import discord
from discord import app_commands
from discord.ext import commands

class Template(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="template")
    async def template(self, interaction: discord.Interaction):
        await interaction.response.send_message("This is a template command.")