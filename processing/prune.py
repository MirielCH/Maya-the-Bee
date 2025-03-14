# prune.py

import asyncio
from datetime import timedelta
from math import ceil, floor
import random
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import reminders, tracking, users
from resources import emojis, exceptions, functions, regex, settings, strings


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
    if any(search_string in message.content.lower() for search_string in search_strings) and not message.embeds:
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
        dropped_nuggets = {}
        current_time = utils.utcnow().replace(microsecond=0)
        if user_settings.tracking_enabled:
            await tracking.insert_log_entry(user.id, message.guild.id, 'prune', current_time)
        league_beta = None
        nugget_wooden_match = re.search(r'woodennugget:\d+>\s*\*\*(.+?)\*\*', message.content.lower())
        nugget_copper_match = re.search(r'coppernugget:\d+>\s*\*\*(.+?)\*\*', message.content.lower())
        nugget_silver_match = re.search(r'silvernugget:\d+>\s*\*\*(.+?)\*\*', message.content.lower())
        nugget_golden_match = re.search(r'goldennugget:\d+>\s*\*\*(.+?)\*\*', message.content.lower())
        nugget_diamond_match = re.search(r'diamondnugget:\d+>\s*\*\*(.+?)\*\*', message.content.lower())
        if nugget_wooden_match:
            nugget_wooden_amount = int(re.sub(r'\D', '', nugget_wooden_match.group(1)))
            league_beta = True if nugget_wooden_amount > 1 else False
            if user_settings.tracking_enabled:
                await tracking.insert_log_entry(user.id, message.guild.id, 'wooden-nugget', current_time,
                                                nugget_wooden_amount)
            dropped_nuggets['Wooden'] = nugget_wooden_amount
        if nugget_copper_match:
            nugget_copper_amount = int(re.sub(r'\D', '', nugget_copper_match.group(1)))
            league_beta = True if nugget_copper_amount > 1 else False
            if user_settings.tracking_enabled:
                await tracking.insert_log_entry(user.id, message.guild.id, 'copper-nugget', current_time,
                                                nugget_copper_amount)
            dropped_nuggets['Copper'] = nugget_copper_amount
        if nugget_silver_match:
            nugget_silver_amount = int(re.sub(r'\D', '', nugget_silver_match.group(1)))
            league_beta = True if nugget_silver_amount > 1 else False
            if user_settings.tracking_enabled:
                await tracking.insert_log_entry(user.id, message.guild.id, 'silver-nugget', current_time,
                                                nugget_silver_amount)
            dropped_nuggets['Silver'] = nugget_silver_amount
        if nugget_golden_match:
            nugget_golden_amount = int(re.sub(r'\D', '', nugget_golden_match.group(1)))
            league_beta = True if nugget_golden_amount > 1 else False
            if user_settings.tracking_enabled:
                await tracking.insert_log_entry(user.id, message.guild.id, 'golden-nugget', current_time,
                                                nugget_golden_amount)
            dropped_nuggets['Golden'] = nugget_golden_amount
        if nugget_diamond_match:
            nugget_diamond_amount = int(re.sub(r'\D', '', nugget_diamond_match.group(1)))
            league_beta = True if nugget_diamond_amount > 1 else False
            if user_settings.tracking_enabled:
                await tracking.insert_log_entry(user.id, message.guild.id, 'diamond-nugget', current_time,
                                                nugget_diamond_amount)
            dropped_nuggets['Diamond'] = nugget_diamond_amount
        if league_beta is not None and user_settings.tracking_enabled:
            if (league_beta and not user_settings.league_beta) or (not league_beta and user_settings.league_beta):
                await user_settings.update(league_beta=league_beta)
        if user_settings.reminder_prune.enabled:
            user_command = await functions.get_game_command(user_settings, 'prune')
            pruner_type_match = re.search(r'> \*\*(.+?) pruner', message.content, re.IGNORECASE)
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
            if reminder.record_exists and user_settings.reactions_enabled: add_reaction = True
        if user_settings.reactions_enabled:
            if 'goldennugget' in message.content.lower() or 'diamondnugget' in message.content.lower():
                await message.add_reaction(emojis.PAN_WOOHOO)
        message_content = ''
        embeds = []
        rebirth_target = False
        if user_settings.level > 0 and user_settings.xp_target > 0:
            xp_gain_match = re.search(r'got \*\*(.+?)\*\* <', message.content.lower())
            xp_gain = int(re.sub(r'\D', '', xp_gain_match.group(1)))
            if user_settings.league_beta: xp_gain = ceil(xp_gain * 1.33)
            if user_settings.xp_gain_average > 0:
                xp_gain_average = (
                    (user_settings.xp_prune_count * user_settings.xp_gain_average + xp_gain)
                    / (user_settings.xp_prune_count + 1)
                )
            else:
                xp_gain_average = xp_gain
            xp_left = user_settings.xp_target - user_settings.xp - xp_gain
            if user_settings.rebirth <= 10:
                level_target = 5 + user_settings.rebirth
            else:
                level_target = 15 + ((user_settings.rebirth - 10) // 2)
            if xp_left < 0:
                next_level = user_settings.level
                while True:
                    next_level += 1
                    new_xp_target = (next_level ** 3) * 150
                    if new_xp_target <= (xp_left * -1):
                        xp_left = xp_left + new_xp_target
                    else:
                        break
                current_level = user_settings.level
                await user_settings.update(xp_gain_average=0, xp=xp_left * -1, xp_prune_count=0, xp_target=new_xp_target,
                                           level=next_level)
                if user_settings.alert_rebirth_enabled and current_level < level_target and next_level >= level_target:
                    rebirth_target = True
            else:
                await user_settings.update(xp_gain_average=round(xp_gain_average, 5), xp=(user_settings.xp + xp_gain),
                                           xp_prune_count=(user_settings.xp_prune_count + 1))
            if user_settings.helper_prune_enabled:
                xp_percentage = user_settings.xp / user_settings.xp_target * 100
                progress = 6 / 100 * xp_percentage
                progress_fractional = progress % 1
                progress_emojis_full = floor(progress)
                progress_emojis_empty = 6 - progress_emojis_full - 1
                if user_settings.helper_prune_progress_bar_color == 'random':
                    color25 = color50 = color75 = color100 = random.choice(strings.PROGRESS_BAR_COLORS)
                else:
                    color25 = color50 = color75 = color100 = user_settings.helper_prune_progress_bar_color
                progress_25_emoji = getattr(emojis,f'PROGRESS_25_{color25.upper()}', emojis.PROGRESS_25_GREEN)
                progress_50_emoji = getattr(emojis, f'PROGRESS_50_{color50.upper()}', emojis.PROGRESS_50_GREEN)
                progress_75_emoji = getattr(emojis, f'PROGRESS_75_{color75.upper()}', emojis.PROGRESS_75_GREEN)
                progress_100_emoji = getattr(emojis, f'PROGRESS_100_{color100.upper()}', emojis.PROGRESS_100_GREEN)
                if 0 <= progress_fractional < 0.25:
                    progress_emoji_fractional = emojis.PROGRESS_0
                elif 0.25 <= progress_fractional < 0.5:
                    progress_emoji_fractional = progress_25_emoji
                elif 0.5 <= progress_fractional < 0.75:
                    progress_emoji_fractional = progress_50_emoji
                elif 0.75 <= progress_fractional < 1:
                    progress_emoji_fractional = progress_75_emoji
                else:
                    progress_emoji_fractional = progress_100_emoji
                progress_bar = ''
                for x in range(progress_emojis_full):
                    progress_bar = f'{progress_bar}{progress_100_emoji}'
                progress_bar = f'{progress_bar}{progress_emoji_fractional}'
                for x in range(progress_emojis_empty):
                    progress_bar = f'{progress_bar}{emojis.PROGRESS_0}'
                xp_left = user_settings.xp_target - user_settings.xp
                xp_gain_average = floor(user_settings.xp_gain_average) if user_settings.xp_gain_average > 0 else xp_gain
                try:
                    prunes_until_level_up = f'{ceil(xp_left / xp_gain_average):,}'
                except ZeroDivisionError:
                    prunes_until_level_up = f'{ceil(xp_left / xp_gain_average):,}'
                embed = discord.Embed(
                    title = progress_bar,
                    description = (
                        f'**{xp_left:,}** {emojis.STAT_XP}until level **{user_settings.level + 1:,}**\n'
                        f'➜ **{prunes_until_level_up}** prunes at **{xp_gain_average:,}** '
                        f'{emojis.XP} average\n'
                    )
                )
                footer = f'Rebirth {user_settings.rebirth} • Level {user_settings.level:,}/{level_target:,}'
                if user_settings.level >= level_target:
                    footer = f'{footer} • Ready for rebirth'
                embed.set_footer(text = footer)
                embeds.append(embed)
            nugget_alert = False
            if user_settings.alert_nugget_enabled and dropped_nuggets:
                nugget_names = list(strings.NUGGETS.keys())
                threshold_index = nugget_names.index(user_settings.alert_nugget_threshold)
                nuggets_found = ''
                for name, amount in dropped_nuggets.items():
                    if nugget_names.index(name) >= threshold_index:
                        nuggets_found = (
                            f'{nuggets_found}\n'
                            f'{amount:,} {strings.NUGGETS[name]} {name} nuggets'
                        )
                if nuggets_found:
                    if user_settings.alert_nugget_dm:
                        asyncio.ensure_future(user.send(
                            f'**Nuggets found!**\n'
                            f'{nuggets_found.strip()}\n'
                            f'➜ {message.jump_url}'
                        ))
                    else:
                        embed = discord.Embed(
                            color = settings.EMBED_COLOR,
                            title = 'Nuggets found!',
                            description = nuggets_found,
                        ) 
                        embed.set_footer(text='Use "/settings alerts" to change this')
                        embeds.insert(0, embed)
                    nugget_alert = True
                    
            if embeds or message_content:
                if nugget_alert and not user_settings.alert_nugget_dm:
                    message_content = f'{user.mention}\n{message_content}'
                await message.reply(content=message_content.strip(), embeds=embeds)

            if rebirth_target:
                if user_settings.alert_rebirth_dm:
                    asyncio.ensure_future(user.send(
                        f'Bzzt! You reached level **{next_level:,}** and are now ready for rebirth!\n'
                        f'➜ {message.jump_url}'
                    ))
                else:
                    await asyncio.sleep(1)
                    await message.reply(
                        f'{user.mention}\n'
                        f'Bzzt! You reached level **{next_level:,}** and are now ready for rebirth!'
                    )
    return add_reaction