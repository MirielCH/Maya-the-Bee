# inventory.py
"""Contains inventory commands"""

import discord
from discord.commands import SlashCommandGroup
from discord.ext import commands

from content import inventory as content_inventory


class InventoryCog(commands.Cog):
    """Cog with inventory commands"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    cmd_inventory = SlashCommandGroup(
        "inventory",
        "Inventory commands",
    )

    # Slash commands
    @cmd_inventory.command()
    async def calculator(self, ctx: discord.ApplicationContext) -> None:
        """Inventory calculator"""
        await content_inventory.command_inventory_calculator(ctx, ctx.author, self.bot)

# Initialization
def setup(bot):
    bot.add_cog(InventoryCog(bot))