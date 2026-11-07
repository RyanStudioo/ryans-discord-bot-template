import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.utils.embeds import build_help_pages
from src.utils.pagination import Paginator

logger = logging.getLogger(__name__)


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="List every command the bot provides.",
    )
    async def help(self, interaction: discord.Interaction):
        pages = build_help_pages(
            self.bot.tree.get_commands(),
            bot_name=self.bot.user.name if self.bot.user else "Bot",
        )

        if len(pages) == 1:
            await interaction.response.send_message(embed=pages[0])
            return

        logger.debug("Showing help menu with %d pages to %s", len(pages), interaction.user)
        await interaction.response.send_message(
            embed=pages[0],
            view=Paginator(pages, author_id=interaction.user.id),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
