# rebirth.py

import re
from typing import Dict, Optional

import discord
from discord import utils
from humanfriendly import format_timespan

from cache import messages
from database import tracking, users
from resources import emojis, exceptions, functions, regex, settings, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all rebirth related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await update_rebirth_on_summary(message, embed_data, user, user_settings))
    return_values.append(await update_rebirth_on_cancel(message, embed_data, user, user_settings))
    return_values.append(await track_rebirth_and_show_summary(message, embed_data, user, user_settings))
    return any(return_values)


async def update_rebirth_on_summary(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Increase rebirth count on rebirth summary message

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'are you sure you want to rebirth?', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        if user is not None: return add_reaction
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_REBIRTH,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled and not user_settings.helper_prune_enabled: return add_reaction
        await user_settings.update(rebirth=user_settings.rebirth + 1, 
                                   xp_prune_count=0)
        await message.reply(
            f'➜ Use {strings.SLASH_COMMANDS["profile"]} or {strings.SLASH_COMMANDS["stats"]} to to start XP tracking '
            f'after rebirthing!'
        )
    return add_reaction


async def update_rebirth_on_cancel(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                   user_settings: Optional[users.User]) -> bool:
    """Decrease rebirth count on rebirth cancel message

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'the rebirth has been canceled!', #English
    ]
    if any(search_string in message.content.lower() for search_string in search_strings):
        if user is None:
            user = message.mentions[0]
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled and not user_settings.helper_prune_enabled: return add_reaction
        await user_settings.update(rebirth=user_settings.rebirth - 1)
    return add_reaction


async def track_rebirth_and_show_summary(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                         user_settings: Optional[users.User]) -> bool:
    """Tracks rebirth and shows a summary if enabled

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        '** used rebirth!', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        rebirth_string, user_id_string = embed_data['footer']['text'].split('\n')
        if user is None:
            user_id_match = re.search(r'^user id: (.+?)$', user_id_string.lower())
            user = message.guild.get_member(int(user_id_match.group(1)))
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return
        if not user_settings.bot_enabled: return False
        rebirth_match = re.search(r'^total rebirths: (.+?)$', rebirth_string.lower())
        rebirth = int(re.sub(r'\D', '', rebirth_match.group(1)))

        if user_settings.helper_rebirth_enabled:
            if user_settings.rebirth <= 10:
                level_target = 5 + rebirth
            else:
                level_target = 15 + ((rebirth - 10) // 2)
            current_time = utils.utcnow().replace(microsecond=0)
            report: tracking.LogReport = await tracking.get_log_report(user.id, current_time - user_settings.last_rebirth)
            embed = discord.Embed(
                color = settings.EMBED_COLOR,
                title = 'Rebirth summary',
            )
            progress = (
                f'{emojis.BP} Rebirth reached: **{rebirth:,}**\n'
                f'{emojis.BP} Level required for next rebirth: **{level_target:,}**\n'
            )
            last_rebirth_stats = (
                f'{emojis.BP} Started on {utils.format_dt(user_settings.last_rebirth)}\n'
                f'{emojis.BP} `prune`: {report.prune_amount:,}\n'
                f'{emojis.DETAIL2} {emojis.NUGGET_WOODEN} {report.nugget_wooden_amount:,} '
                f'({await functions.calculate_percentage(report.nugget_wooden_amount, report.prune_amount):g}%)\n'
                f'{emojis.DETAIL2} {emojis.NUGGET_COPPER} {report.nugget_copper_amount:,} '
                f'({await functions.calculate_percentage(report.nugget_copper_amount, report.prune_amount):g}%)\n'
                f'{emojis.DETAIL2} {emojis.NUGGET_SILVER} {report.nugget_silver_amount:,} '
                f'({await functions.calculate_percentage(report.nugget_silver_amount, report.prune_amount):g}%)\n'
                f'{emojis.DETAIL2} {emojis.NUGGET_GOLDEN} {report.nugget_golden_amount:,} '
                f'({await functions.calculate_percentage(report.nugget_golden_amount, report.prune_amount):g}%)\n'
                f'{emojis.DETAIL} {emojis.NUGGET_DIAMOND} {report.nugget_diamond_amount:,} '
                f'({await functions.calculate_percentage(report.nugget_diamond_amount, report.prune_amount):g}%)\n'
                f'{emojis.BP} `clean`: {report.clean_amount:,}\n'
                f'{emojis.BP} `captcha`: {report.captcha_amount:,}\n'
            )
            embed.add_field(name = 'Progress', value = progress, inline=False)
            embed.add_field(name = 'Last rebirth', value = last_rebirth_stats, inline=False)
            await message.reply(embed=embed)
            
        await user_settings.update(level=1, xp=0, xp_gain_average=0, xp_prune_count=0, xp_target=150, rebirth=rebirth,
                                   last_rebirth=current_time)
        add_reaction = True
    return add_reaction