# settings.py
"""Contains settings commands"""

import discord
from discord.commands import SlashCommandGroup, slash_command
from discord.ext import commands

from content import settings as settings_cmd
from resources import functions


class SettingsCog(commands.Cog):
    """Cog with user settings commands"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Slash commands
    @slash_command()
    async def on(self, ctx: discord.ApplicationContext) -> None:
        """Activate Maya"""
        await settings_cmd.command_on(self.bot, ctx)

    @slash_command()
    async def off(self, ctx: discord.ApplicationContext) -> None:
        """Disable Maya"""
        await settings_cmd.command_off(self.bot, ctx)

    cmd_purge = SlashCommandGroup(
        "purge",
        "Purge commands",
    )

    @cmd_purge.command()
    async def data(self, ctx: discord.ApplicationContext) -> None:
        """Purges your user data from Maya"""
        await settings_cmd.command_purge_data(self.bot, ctx)

    cmd_settings = SlashCommandGroup(
        "settings",
        "Settings commands",
    )

    @cmd_settings.command()
    async def alerts(self, ctx: discord.ApplicationContext) -> None:
        """Manage alert settings"""
        await settings_cmd.command_settings_alerts(self.bot, ctx)
        
    @cmd_settings.command()
    async def helpers(self, ctx: discord.ApplicationContext) -> None:
        """Manage helpers"""
        await settings_cmd.command_settings_helpers(self.bot, ctx)
        
    @cmd_settings.command()
    async def messages(self, ctx: discord.ApplicationContext) -> None:
        """Manage reminder messages"""
        await settings_cmd.command_settings_messages(self.bot, ctx)

    @cmd_settings.command()
    async def reminders(self, ctx: discord.ApplicationContext) -> None:
        """Manage reminder settings"""
        await settings_cmd.command_settings_reminders(self.bot, ctx)

    @commands.guild_only()
    @cmd_settings.command()
    async def server(self, ctx: discord.ApplicationContext) -> None:
        """Manage server settings"""
        if (not ctx.author.guild_permissions.manage_guild
            and not (ctx.guild.id == 713541415099170836 and ctx.author.id == 619879176316649482)):
            raise commands.MissingPermissions(['manage_guild',])
            # This is to give me (Miriel) server settings access in RPG ARMY. This does NOT give me backdoor access
            # in any other server.
        await settings_cmd.command_settings_server(self.bot, ctx)

    @cmd_settings.command()
    async def user(self, ctx: discord.ApplicationContext) -> None:
        """Manage user settings"""
        await settings_cmd.command_settings_user(self.bot, ctx)

    #Prefix commands
    @commands.command(name='on', aliases=('register', 'activate', 'start'))
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def prefix_on(self, ctx: commands.Context, *args: str) -> None:
        """Turn on Navi (prefix version)"""
        await ctx.reply(f'Bzzt! Please use {await functions.get_maya_slash_command(self.bot, "on")} to activate me.')

    @commands.command(name='off', aliases=('deactivate','stop'))
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def prefix_off(self, ctx: commands.Context, *args: str) -> None:
        """Turn off Navi (prefix version)"""
        await ctx.reply(f'Bzzt! Please use {await functions.get_maya_slash_command(self.bot, "off")} to deactivate me.')

    aliases_settings_user = (
        'slashmentions','donor','donator','dnd','dnd-mode','last_rebirth','last-rebirth',
        'lastrebirth','tracking','track'
    )
    @commands.command(name='slash-mentions', aliases=aliases_settings_user)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def prefix_settings_user(self, ctx: commands.Context, *args: str) -> None:
        """User settings (prefix version)"""
        await ctx.reply(
            f'Bzzt! Please use {await functions.get_maya_slash_command(self.bot, "settings user")} '
            f'to change user settings.'
        )

    @commands.command(name='message', aliases=('messages',))
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def prefix_settings_messages(self, ctx: commands.Context, *args: str) -> None:
        """Message settings (prefix version)"""
        await ctx.reply(
            f'Bzzt! Please use {await functions.get_maya_slash_command(self.bot, "settings messages")} '
            f'to change your reminder messages.'
        )

    @commands.command(name='server')
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def prefix_settings_server(self, ctx: commands.Context, *args: str) -> None:
        """Server settings (prefix version)"""
        await ctx.reply(
            f'Bzzt! Please use {await functions.get_maya_slash_command(self.bot, "settings server")} '
            f'to change server settings.'
        )

    @commands.command(name='settings', aliases=('me','setting','set'))
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def prefix_settings(self, ctx: commands.Context, *args: str) -> None:
        """Settings (prefix version)"""
        await ctx.reply(
            f'➜ {await functions.get_maya_slash_command(self.bot, "settings helpers")}\n'
            f'➜ {await functions.get_maya_slash_command(self.bot, "settings messages")}\n'
            f'➜ {await functions.get_maya_slash_command(self.bot, "settings reminders")}\n'
            f'➜ {await functions.get_maya_slash_command(self.bot, "settings server")}\n'
            f'➜ {await functions.get_maya_slash_command(self.bot, "settings user")}\n'
        )


# Initialization
def setup(bot):
    bot.add_cog(SettingsCog(bot))
