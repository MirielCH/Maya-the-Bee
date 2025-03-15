# rebirth.py
"""Contains rebirth commands"""

import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands

from content import rebirth
from resources import settings


class RebirthCog(commands.Cog):
    """Cog with user settings commands"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    cmd_rebirth = SlashCommandGroup(
        "rebirth",
        "Rebirth commands",
    )

    # Slash commands
    @cmd_rebirth.command()
    async def guide(self, ctx: discord.ApplicationContext) -> None:
        """Rebirth guide"""
        await rebirth.command_rebirth_guide(ctx, ctx.author, False, self.bot)

# Initialization
def setup(bot):
    bot.add_cog(RebirthCog(bot))