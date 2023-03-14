# tracking.py
"""Contains commands related to command tracking"""

from datetime import timedelta
from typing import Optional, Union

import discord
from discord import utils
from discord.ext import commands

from database import users, tracking
from resources import emojis, functions, exceptions, settings, strings, views


# --- Commands ---
async def command_stats(
    bot: discord.Bot,
    ctx: Union[commands.Context, discord.ApplicationContext, discord.Message],
    timestring: Optional[str] = None,
    user: Optional[discord.User] = None,
) -> None:
    """Lists all stats"""
    if user is None: user = ctx.author
    try:
        user_settings: users.User = await users.get_user(user.id)
    except exceptions.FirstTimeUserError:
        if user == ctx.author:
            raise
        else:
            await functions.reply_or_respond(ctx, 'This user is not registered with this bot.', True)
            return
    if timestring is None:
        embed = await embed_stats_overview(ctx, user)
    else:
        try:
            timestring = await functions.check_timestring(timestring)
        except exceptions.InvalidTimestringError as error:
            msg_error = (
                f'{error}\n'
                f'Supported time codes: `w`, `d`, `h`, `m`, `s`\n\n'
                f'Examples:\n'
                f'{emojis.BP} `30s`\n'
                f'{emojis.BP} `1h30m`\n'
                f'{emojis.BP} `7d`\n'
            )
            await functions.reply_or_respond(ctx, msg_error, True)
            return
        try:
            time_left = await functions.parse_timestring_to_timedelta(timestring)
        except OverflowError as error:
            await ctx.reply(error)
            return
        if time_left.days > 28: time_left = timedelta(days=time_left.days)
        if time_left.days > 365:
            await ctx.reply('The maximum time is 365d, sorry.')
            return
        embed = await embed_stats_timeframe(ctx, user, time_left)
    view = views.StatsView(ctx, user, user_settings)
    if isinstance(ctx, discord.ApplicationContext):
        interaction_message = await ctx.respond(embed=embed, view=view)
    else:
        interaction_message = await ctx.reply(embed=embed, view=view)
    view.interaction_message = interaction_message
    await view.wait()


# --- Embeds ---
async def embed_stats_overview(ctx: commands.Context, user: discord.User) -> discord.Embed:
    """Stats overview embed"""

    async def command_count(command: str, timeframe: timedelta) -> str:
        try:
            report = await tracking.get_log_report(user.id, command, timeframe)
            amount = report.amount
            text = f'{emojis.BP} `{report.command_or_drop}`: {report.amount:,}'
        except exceptions.NoDataFoundError:
            text = f'{emojis.BP} `{command}`: 0'
            amount = 0
        if command == 'prune':
            for drop in strings.TRACKED_PRUNE_DROPS:
                last_item = True if drop == strings.TRACKED_PRUNE_DROPS[-1] else False
                text_drop = await drop_count(drop, timeframe, amount, last_item)
                text = f'{text}\n{text_drop}'
        return text
    
    async def drop_count(drop: str, timeframe: timedelta, command_count: int, last_item: bool) -> str:
        try:
            emoji = emojis.DETAIL if last_item else emojis.DETAIL2
            report = await tracking.get_log_report(user.id, drop, timeframe)
            try:
                percentage = round(report.amount / command_count * 100, 2)
            except ZeroDivisionError:
                percentage = 0
            text = f'{emoji} {strings.TRACKED_DROPS_EMOJIS[report.command_or_drop]} {report.amount:,} ({percentage:g}%)'
        except exceptions.NoDataFoundError:
            text = f'{emoji} {strings.TRACKED_DROPS_EMOJIS[drop]} 0 (0%)'

        return text

    user_settings: users.User = await users.get_user(user.id)
    field_last_1h = field_last_12h = field_last_24h = field_last_7d = field_last_4w = field_last_1y = ''
    field_last_rebirth = ''
    current_time = utils.utcnow().replace(microsecond=0)
    for command in strings.TRACKED_COMMANDS:
        last_1h = await command_count(command, timedelta(hours=1))
        field_last_1h = f'{field_last_1h}\n{last_1h}'
        last_12h = await command_count(command, timedelta(hours=12))
        field_last_12h = f'{field_last_12h}\n{last_12h}'
        last_24h = await command_count(command, timedelta(hours=24))
        field_last_24h = f'{field_last_24h}\n{last_24h}'
        last_7d = await command_count(command, timedelta(days=7))
        field_last_7d = f'{field_last_7d}\n{last_7d}'
        last_4w = await command_count(command, timedelta(days=28))
        field_last_4w = f'{field_last_4w}\n{last_4w}'
        last_1y = await command_count(command, timedelta(days=365))
        field_last_1y = f'{field_last_1y}\n{last_1y}'
        last_rebirth = await command_count(command, current_time-user_settings.last_rebirth)
        field_last_rebirth = f'{field_last_rebirth}\n{last_rebirth}'
    field_last_rebirth = (
        f'{field_last_rebirth.strip()}\n\nYour last rebirth was on {utils.format_dt(user_settings.last_rebirth)}.'
    )

    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{user.name}\'s stats',
        description = '**Command tracking is currently turned off!**' if not user_settings.tracking_enabled else ''
    )
    embed.add_field(name='Last hour', value=field_last_1h, inline=True)
    embed.add_field(name='Last 12 hours', value=field_last_12h, inline=True)
    embed.add_field(name='Last 24 hours', value=field_last_24h, inline=True)
    embed.add_field(name='Last 7 days', value=field_last_7d, inline=True)
    embed.add_field(name='Last 4 weeks', value=field_last_4w, inline=True)
    embed.add_field(name='Last year', value=field_last_1y, inline=True)
    embed.add_field(name='Since last rebirth', value=field_last_rebirth, inline=True)
    embed.set_footer(text=f'To see drop amounts, use "{ctx.prefix}st [timeframe]".')
    return embed


async def embed_stats_timeframe(ctx: commands.Context, user: discord.Member, time_left: timedelta) -> discord.Embed:
    """Stats timeframe embed"""
    field_timeframe = ''
    user_settings: users.User = await users.get_user(user.id)
    for command in strings.TRACKED_COMMANDS:
        try:
            report = await tracking.get_log_report(user.id, command, time_left)
            amount = report.amount
            field_timeframe = f'{field_timeframe}\n{emojis.BP} `{report.command_or_drop}`: {amount:,}'
        except exceptions.NoDataFoundError:
            amount = 0
            field_timeframe = f'{field_timeframe}\n{emojis.BP} `{command}`: 0'
        if command == 'prune':
            for drop in strings.TRACKED_PRUNE_DROPS:
                last_item = True if drop == strings.TRACKED_PRUNE_DROPS[-1] else False
                emoji = emojis.DETAIL if last_item else emojis.DETAIL2
                try:
                    report_drop = await tracking.get_log_report(user.id, drop, time_left)
                    try:
                        percentage = round(report_drop.amount / amount * 100, 2)
                    except ZeroDivisionError:
                        percentage = 0
                    field_timeframe = (
                        f'{field_timeframe}\n{emoji} '
                        f'{strings.TRACKED_DROPS_EMOJIS[report_drop.command_or_drop]} {report_drop.amount:,} ({percentage:g}%)'
                    )
                except exceptions.NoDataFoundError:
                    field_timeframe = f'{field_timeframe}\n{emoji} {strings.TRACKED_DROPS_EMOJIS[drop]} 0 (0%)'

    time_left_seconds = int(time_left.total_seconds())
    days = time_left_seconds // 86400
    hours = (time_left_seconds % 86400) // 3600
    minutes = (time_left_seconds % 3600) // 60
    seconds = time_left_seconds % 60
    timeframe = ''
    if days > 0: timeframe = f'{days} days'
    if hours > 0: timeframe = f'{timeframe}, {hours} hours'
    if minutes > 0: timeframe = f'{timeframe}, {minutes} minutes'
    if seconds > 0: timeframe = f'{timeframe}, {seconds} seconds'
    timeframe = timeframe.strip(',').strip()

    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{user.name}\'s stats',
        description = '**Command tracking is currently turned off!**' if not user_settings.tracking_enabled else ''
    )
    embed.add_field(name=f'Last {timeframe}', value=field_timeframe, inline=False)
    return embed