# main.py
"""Contains error handling and the help and about commands"""

from datetime import datetime
from humanfriendly import format_timespan
import psutil
import sys
from typing import Union

import discord
from discord import utils
from discord.ext import commands

from database import guilds, users
from database import settings as settings_db
from resources import emojis, functions, settings, strings


class LinksView(discord.ui.View):
    """View with link buttons."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Invite", style=discord.ButtonStyle.link,
                                        url=strings.LINK_INVITE, emoji=emojis.INVITE))
        self.add_item(discord.ui.Button(label="Github", style=discord.ButtonStyle.link,
                                        url=strings.LINK_GITHUB, emoji=emojis.GITHUB))
        self.add_item(discord.ui.Button(label="Privacy policy", style=discord.ButtonStyle.link,
                                        url=strings.LINK_PRIVACY_POLICY, emoji=emojis.PRIVACY_POLICY))


# --- Commands ---
async def command_help(bot: discord.Bot, ctx: Union[discord.ApplicationContext, commands.Context, discord.Message]) -> None:
    """Help command"""
    view = LinksView()
    img_logo, embed = await embed_help(bot, ctx)
    if isinstance(ctx, discord.ApplicationContext):
        await ctx.respond(embed=embed, view=view, file=img_logo)
    else:
        await ctx.reply(embed=embed, view=view, file=img_logo)


async def command_about(bot: discord.Bot, ctx: discord.ApplicationContext) -> None:
    """About command"""
    start_time = utils.utcnow()
    interaction = await ctx.respond('Testing API latency...')
    end_time = utils.utcnow()
    api_latency = end_time - start_time
    img_logo, embed = await embed_about(bot, api_latency)
    view = LinksView()
    await functions.edit_interaction(interaction, content=None, embed=embed, view=view, file=img_logo)


# --- Embeds ---
async def embed_help(bot: discord.Bot, ctx: discord.ApplicationContext) -> discord.Embed:
    """Main menu embed"""
    prefix = await guilds.get_prefix(ctx)
    commands_reminders = (
        f'{emojis.BP} {await functions.get_maya_slash_command(bot, "reminders list")} : Check all active reminders\n'
        f'{emojis.DETAIL} _Aliases: `{prefix}list`, `{prefix}cd`_\n'
        f'{emojis.BP} {await functions.get_maya_slash_command(bot, "reminders add")} : Add a custom reminder\n'
        f'{emojis.DETAIL} _Aliases: `{prefix}reminder`, `{prefix}rm`_\n'

    )
    commands_tracking = (
        f'{emojis.BP} {await functions.get_maya_slash_command(bot, "stats")} : Check your command stats\n'
        f'{emojis.DETAIL} _Aliases: `{prefix}stats`, `{prefix}st`_\n'
    )
    commands_settings = (
        f'{emojis.BP} {await functions.get_maya_slash_command(bot, "on")} : Turn on Maya\n'
        f'{emojis.BP} {await functions.get_maya_slash_command(bot, "off")} : Turn off Maya\n'
        f'{emojis.BP} {await functions.get_maya_slash_command(bot, "settings messages")} : Manage reminder messages\n'
        f'{emojis.BP} {await functions.get_maya_slash_command(bot, "settings reminders")} : Enable/disable reminders\n'
        f'{emojis.BP} {await functions.get_maya_slash_command(bot, "settings user")} : Manage user settings\n'
        f'{emojis.BP} {await functions.get_maya_slash_command(bot, "settings server")} : Manage server settings\n'
        f'{emojis.DETAIL} _Requires `Manage server` permission._\n'
    )
    img_logo = discord.File(settings.IMG_LOGO, filename='logo.png')
    image_url = 'attachment://logo.png'
    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = 'Hi! I\'m Maya the Bee!',
    )
    embed.add_field(name='Reminder management', value=commands_reminders, inline=False)
    embed.add_field(name='Settings', value=commands_settings, inline=False)
    embed.add_field(name='Tracking', value=commands_tracking, inline=False)
    embed.set_thumbnail(url=image_url)
    return (img_logo, embed)


async def embed_about(bot: commands.Bot, api_latency: datetime) -> discord.Embed:
    """Bot info embed"""
    user_count = await users.get_user_count()
    all_settings = await settings_db.get_settings()
    uptime = utils.utcnow().replace(microsecond=0) - datetime.fromisoformat(all_settings['startup_time'])
    general = (
        f'{emojis.BP} {len(bot.guilds):,} servers\n'
        f'{emojis.BP} {user_count:,} users\n'
        f'{emojis.BP} {round(bot.latency * 1000):,} ms bot latency\n'
        f'{emojis.BP} {round(api_latency.total_seconds() * 1000):,} ms API latency\n'
        f'{emojis.BP} Online for {format_timespan(uptime)}'
    )
    creator = f'{emojis.BP} Miriel#0001 (yeah sorry, me again)'
    dev_stuff = (
        f'{emojis.BP} Version: {settings.VERSION}\n'
        f'{emojis.BP} Language: Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n'
        f'{emojis.BP} Library: Pycord {discord.__version__}\n'
        f'{emojis.BP} System CPU usage: {psutil.cpu_percent()}%\n'
        f'{emojis.BP} System RAM usage: {psutil.virtual_memory()[2]}%\n'
    )
    img_logo = discord.File(settings.IMG_LOGO, filename='logo.png')
    image_url = 'attachment://logo.png'
    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = 'Hi! I\'m Maya the Bee!',
        description = '_There\'s an old bee saying: "Don\'t make clubs with strange bugs."_'
    )
    embed.add_field(name='Bot stats', value=general, inline=False)
    embed.add_field(name='Creator', value=creator, inline=False)
    embed.add_field(name='Dev stuff', value=dev_stuff, inline=False)
    embed.set_thumbnail(url=image_url)
    return (img_logo, embed)