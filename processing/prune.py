# prune.py

from datetime import timedelta
from math import ceil, floor
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import reminders, tracking, users
from resources import emojis, exceptions, functions, regex


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all prune related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_reminder(message, embed_data, user, user_settings))
    return any(return_values)


async def create_reminder(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Creates a reminder when using /prune. Also adds an entry to the tracking log and updates the pruner type.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'you have pruned your tree', #English
    ]
    if any(search_string in message.content.lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_name_match = re.search(regex.NAME_FROM_MESSAGE_START, message.content)
                user_name = user_name_match.group(1)
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_PRUNE, user_name=user_name)
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction
        if user_settings.tracking_enabled:
            current_time = utils.utcnow().replace(microsecond=0)
            await tracking.insert_log_entry(user.id, message.guild.id, 'prune', current_time)
            nugget_drops = {}
            nugget_wooden_match = re.search(r'<:woodennugget:\d+>\s\*\*(.+?)\*\*', message.content.lower())
            nugget_copper_match = re.search(r'<:coppernugget:\d+>\s\*\*(.+?)\*\*', message.content.lower())
            nugget_silver_match = re.search(r'<:silvernugget:\d+>\s\*\*(.+?)\*\*', message.content.lower())
            nugget_golden_match = re.search(r'<:goldennugget:\d+>\s\*\*(.+?)\*\*', message.content.lower())
            if nugget_wooden_match:
                await tracking.insert_log_entry(user.id, message.guild.id, 'wooden-nugget', current_time,
                                                int(nugget_wooden_match.group(1).replace(',','')))
            if nugget_copper_match:
                await tracking.insert_log_entry(user.id, message.guild.id, 'copper-nugget', current_time,
                                                int(nugget_copper_match.group(1).replace(',','')))
            if nugget_silver_match:
                await tracking.insert_log_entry(user.id, message.guild.id, 'silver-nugget', current_time,
                                                int(nugget_silver_match.group(1).replace(',','')))
            if nugget_golden_match:
                await tracking.insert_log_entry(user.id, message.guild.id, 'golden-nugget', current_time,
                                                int(nugget_golden_match.group(1).replace(',','')))
            if nugget_drops:
                await user_settings.update(**nugget_drops)
        if not user_settings.reminder_prune.enabled: return add_reaction
        user_command = await functions.get_game_command(user_settings, 'prune')
        pruner_type_match = re.search(r'> (.+?) pruner', message.content, re.IGNORECASE)
        await user_settings.update(pruner_type=pruner_type_match.group(1).lower())
        time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'prune')
        if time_left < timedelta(0): return add_reaction
        pruner_emoji = getattr(emojis, f'PRUNER_{user_settings.pruner_type.upper()}', '')
        reminder_message = (
            user_settings.reminder_prune.message
            .replace('{command}', user_command)
            .replace('{pruner_emoji}', pruner_emoji)
            .replace('  ', ' ')
        )
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(user.id, 'prune', time_left,
                                                    message.channel.id, reminder_message)
        )
        if user_settings.reactions_enabled:
            if reminder.record_exists: add_reaction = True
            if 'goldennugget' in message.content.lower():
                await message.add_reaction(emojis.PAN_WOOHOO)
        if (user_settings.helper_prune_enabled and user_settings.level > 0 and user_settings.xp_target > 0):
            xp_gain_match = re.search(r'got \*\*(.+?)\*\* <', message.content.lower())
            xp_gain = int(xp_gain_match.group(1).replace(',',''))
            if user_settings.xp_gain_average > 0:
                xp_gain_average = (
                    (user_settings.xp_prune_count * user_settings.xp_gain_average + xp_gain)
                    / (user_settings.xp_prune_count + 1)
                )
            else:
                xp_gain_average = xp_gain
            await user_settings.update(xp_gain_average=round(xp_gain_average, 5), xp=(user_settings.xp + xp_gain),
                                       xp_prune_count=(user_settings.xp_prune_count + 1))
            xp_left = user_settings.xp_target - user_settings.xp
            if xp_left < 0:
                next_level = user_settings.level + 1
                new_xp = user_settings.xp - user_settings.xp_target
                if new_xp < 0: new_xp = 0
                new_xp_target = (next_level ** 3) * 150
                await user_settings.update(xp_gain_average=0, xp=new_xp, xp_prune_count=0, xp_target=new_xp_target,
                                           level=next_level)
            else:
                xp_percentage = user_settings.xp / user_settings.xp_target * 100
                progress = 6 / 100 * xp_percentage
                progress_fractional = progress % 1
                progress_emojis_full = floor(progress)
                progress_emojis_empty = 6 - progress_emojis_full - 1
                if 0 <= progress_fractional < 0.25:
                    progress_emoji_fractional = emojis.PROGRESS_0
                elif 0.25 <= progress_fractional < 0.5:
                    progress_emoji_fractional = emojis.PROGRESS_25
                elif 0.5 <= progress_fractional < 0.75:
                    progress_emoji_fractional = emojis.PROGRESS_50
                elif 0.75 <= progress_fractional < 1:
                    progress_emoji_fractional = emojis.PROGRESS_75
                else:
                    progress_emoji_fractional = emojis.PROGRESS_100
                progress_bar = ''
                for x in range(progress_emojis_full):
                    progress_bar = f'{progress_bar}{emojis.PROGRESS_100}'
                progress_bar = f'{progress_bar}{progress_emoji_fractional}'
                for x in range(progress_emojis_empty):
                    progress_bar = f'{progress_bar}{emojis.PROGRESS_0}'
                if user_settings.rebirth <= 10:
                    level_target = 5 + user_settings.rebirth
                else:
                    level_target = 15 + ((user_settings.rebirth - 10) // 2)
                try:
                    prunes_until_level_up = f'{ceil(xp_left / floor(user_settings.xp_gain_average)):,}'
                except ZeroDivisionError:
                    prunes_until_level_up = 'N/A'
                embed = discord.Embed(
                    title = progress_bar,
                    description = (
                        f'**{xp_left:,}** {emojis.STAT_XP}until level **{user_settings.level + 1}**\n'
                        f'➜ **{prunes_until_level_up}** prunes at **{floor(user_settings.xp_gain_average):,}** '
                        f'{emojis.XP} average\n'
                    )
                )
                footer = f'Rebirth {user_settings.rebirth} • Level {user_settings.level}/{level_target}'
                if user_settings.level >= level_target:
                    footer = f'{footer} • Ready for rebirth'
                embed.set_footer(text = footer)
                await message.channel.send(embed=embed)
    return add_reaction