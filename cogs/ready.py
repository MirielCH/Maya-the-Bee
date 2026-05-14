# ready.py
"""Contains ready commands"""

import discord
from discord.commands import SlashCommandGroup, Option
from discord.ext import commands

from content import list_ready, reminders_custom
from resources import functions


class ReadyListCog(commands.Cog):
    """Cog with ready commands"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    cmd_ready = SlashCommandGroup(
        "ready",
        "Ready commands",
    )

    @cmd_ready.command(name='list')
    async def ready_list(
        self,
        ctx: discord.ApplicationContext,
        user: Option(discord.User, 'User you want to check ready activities for', default=None),
    ) -> None:
        """Lists all ready activities"""
        await list_ready.command_ready(self.bot, ctx, user)

    @commands.command(name='ready', aliases=('rd',))
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def prefix_ready_list(self, ctx: commands.Context, *args: str) -> None:
        """Lists all ready activities (prefix version)"""
        for mentioned_user in ctx.message.mentions.copy():
            if mentioned_user == self.bot.user:
                ctx.message.mentions.remove(mentioned_user)
                break
        if ctx.message.mentions:
            user = ctx.message.mentions[0]
        if not args:
            user = ctx.author
        else:
            arg = args[0].lower().replace('<@!','').replace('<@','').replace('>','')
            if not arg.isnumeric():
                await ctx.reply('Invalid user.')
                return
            user_id = int(arg)
            user = await functions.get_discord_user(self.bot, user_id)
            if user is None:
                await ctx.reply('This user doesn\'t exist.')
                return
        if user.bot:
            await ctx.reply('Imagine trying to check the ready activities of a bot.')
            return
        await list_ready.command_ready(self.bot, ctx, user)


# Initialization
def setup(bot):
    bot.add_cog(ReadyListCog(bot))