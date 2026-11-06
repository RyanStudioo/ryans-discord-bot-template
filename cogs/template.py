from discord.ext import commands



class Template(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="template")
    async def template(self, ctx: commands.Context):
        await ctx.send("This is a template command.")