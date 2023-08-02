# tracking.py
"""Contains commands related to command tracking"""

from datetime import timedelta
from typing import Optional, Union

import discord
from discord import utils
from discord.ext import commands
from humanfriendly import format_timespan

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
    user_settings: users.User = await users.get_user(user.id)
    current_time = utils.utcnow().replace(microsecond=0)
    field_last_1h = await design_field(timedelta(hours=1), user)
    field_last_12h = await design_field(timedelta(hours=12), user)
    field_last_24h = await design_field(timedelta(hours=24), user)
    field_last_7d = await design_field(timedelta(days=7), user)
    field_last_4w = await design_field(timedelta(days=28), user)
    field_last_1y = await design_field(timedelta(days=365), user)
    field_last_rebirth = await design_field(current_time-user_settings.last_rebirth, user)
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
    return embed


async def embed_stats_timeframe(ctx: commands.Context, user: discord.Member, time_left: timedelta) -> discord.Embed:
    """Stats timeframe embed"""
    user_settings: users.User = await users.get_user(user.id)
    field_content = await design_field(time_left, user)
    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{user.name}\'s stats',
        description = '**Command tracking is currently turned off!**' if not user_settings.tracking_enabled else ''
    )
    embed.add_field(name=f'Last {format_timespan(time_left)}', value=field_content, inline=False)
    return embed


# --- Functions ---
async def design_field(timeframe: timedelta, user: discord.Member) -> str:
    """Designs a stats field and returns it"""
    async def calculate_percentage(item_amount: int, total_amount: int) -> int:
        try:
            percentage = round(item_amount / total_amount * 100, 2)
        except ZeroDivisionError:
            percentage = 0
        return percentage
    
    report: tracking.LogReport = await tracking.get_log_report(user.id, timeframe)
    field_content = (
        f'{emojis.BP} `prune`: {report.prune_amount:,}\n'
        f'{emojis.DETAIL2} {emojis.NUGGET_WOODEN} {report.nugget_wooden_amount:,} '
        f'({await calculate_percentage(report.nugget_wooden_amount, report.prune_amount):g}%)\n'
        f'{emojis.DETAIL2} {emojis.NUGGET_COPPER} {report.nugget_copper_amount:,} '
        f'({await calculate_percentage(report.nugget_copper_amount, report.prune_amount):g}%)\n'
        f'{emojis.DETAIL2} {emojis.NUGGET_SILVER} {report.nugget_silver_amount:,} '
        f'({await calculate_percentage(report.nugget_silver_amount, report.prune_amount):g}%)\n'
        f'{emojis.DETAIL} {emojis.NUGGET_GOLDEN} {report.nugget_golden_amount:,} '
        f'({await calculate_percentage(report.nugget_golden_amount, report.prune_amount):g}%)\n'
        f'{emojis.BP} `clean`: {report.clean_amount:,}\n'
        f'{emojis.BP} `captcha`: {report.captcha_amount:,}\n'
    )
    return field_content