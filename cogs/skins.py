# skins.py

import discord
from discord.commands import slash_command, Option
from discord.ext import commands

from content import skins

from resources import strings

class SkinsCog(commands.Cog):
    """Cog with skins commands"""
    def __init__(self, bot):
        self.bot = bot

    # Commands
    @slash_command(name='skins', description='A list of all obtainable Tree skins')
    async def command_skins(
        self,
        ctx: discord.ApplicationContext,
        skin: Option(str, 'The skin you want to view',
                     choices=list(skins.SKINS_NAMES.values()), default=strings.SKIN_DEFAULT)
    ) -> None:
        """Skins list"""
        active_skin: str = strings.SKIN_DEFAULT
        for skin_value, skin_name in skins.SKINS_NAMES.items():
            if skin_name == skin:
                active_skin = skin_value
                break
        await skins.command_skins(self.bot, ctx, active_skin=active_skin)


# Initialization
def setup(bot):
    bot.add_cog(SkinsCog(bot))
