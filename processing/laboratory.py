# laboratory.py

from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import reminders, users
from resources import exceptions, functions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, text_displays: list, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all laboratory related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_reminders_on_lab_page(message, embed_data, text_displays, user, user_settings))
    return_values.append(await create_reminders_on_produce_page(message, embed_data, text_displays, user, user_settings))
    return_values.append(await create_reminders_on_pruner_page(message, embed_data, text_displays, user, user_settings))
    return any(return_values)


async def create_reminders_on_lab_page(message: discord.Message, embed_data: Dict, text_displays: list, interaction_user: Optional[discord.User],
                                       user_settings: Optional[users.User]) -> bool:
    """Creates a reminder when a research is active on the laboratory page.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'laboratory', #English
        'overview', #English
    ]
    if all(any(search_string in text_display.lower() for text_display in text_displays) for search_string in search_strings):
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_LABORATORY)
            )
            interaction_user = user_command_message.author
        user_name = ''
        for text_display in text_displays:    
            user_name_match = re.search(r'\*\*(.+?)\*\*\'s laboratory', text_display.lower())
            if user_name_match:
                user_name = user_name_match.group(1)
                break
        if user_name != interaction_user.name: return add_reaction
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(interaction_user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction
        if user_settings.reminder_research.enabled or user_settings.ready_show_pruner:
            cooldowns = []
            ready_commands = []
            timestring_text_display = ''
            for text_display in text_displays:
                if 'researching:' in text_display.lower():
                    timestring_text_display = text_display
                    break
            for line in timestring_text_display.split('\n'):
                if 'researching:' in line.lower():
                    end_time_match = re.search(r'<t:(\d+?):r>', line.lower())
                    if not end_time_match:
                        ready_commands.append('pruner-research')
                    else:                    
                        user_command = await functions.get_game_command(user_settings, 'laboratory')
                        reminder_message = user_settings.reminder_research.message.replace('{command}', user_command)
                        cooldowns.append(['pruner-research', end_time_match.group(1), reminder_message])

            current_time = utils.utcnow().replace(microsecond=0)
            for cooldown in cooldowns:
                cd_activity = cooldown[0]
                cd_timestamp = cooldown[1]
                cd_message = cooldown[2]
                end_time = datetime.fromtimestamp(int(cd_timestamp), timezone.utc).replace(microsecond=0)
                time_left = end_time - current_time
                if time_left <= timedelta(seconds=1): continue
                reminder: reminders.Reminder = (
                    await reminders.insert_reminder(interaction_user.id, cd_activity, time_left,
                                                    message.channel.id, cd_message)
                )
                if user_settings.reactions_enabled: add_reaction = True
            for activity in ready_commands:
                try:
                    reminder: reminders.Reminder = await reminders.get_reminder(interaction_user.id, activity)
                    await reminder.delete()
                    if user_settings.reactions_enabled: add_reaction = True
                except exceptions.NoDataFoundError:
                    continue
                
    return add_reaction


async def create_reminders_on_produce_page(message: discord.Message, embed_data: Dict, text_displays: list, interaction_user: Optional[discord.User],
                                           user_settings: Optional[users.User]) -> bool:
    """Creates a reminder when a research is active on the produce page.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'laboratory', #English
        'power every', #English
    ]
    if all(any(search_string in text_display.lower() for text_display in text_displays) for search_string in search_strings):
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_LABORATORY)
            )
            interaction_user = user_command_message.author
        user_name = ''
        for text_display in text_displays:    
            user_name_match = re.search(r'\*\*(.+?)\*\*\'s laboratory', text_display.lower())
            if user_name_match:
                user_name = user_name_match.group(1)
                break
        if user_name != interaction_user.name: return add_reaction
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(interaction_user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction
        
        if user_settings.reminder_produce.enabled or user_settings.ready_show_produce:
            queue_text_display = booster_text_display = ''
            for text_display in text_displays:
                if 'queue' in text_display.lower():
                    queue_text_display = text_display

                if 'active boosters' in text_display.lower():
                    booster_text_display = text_display

            if 'nothing brewing' in queue_text_display:
                try:
                    reminder: reminders.Reminder = await reminders.get_reminder(interaction_user.id, 'produce')
                    await reminder.delete()
                    if user_settings.reactions_enabled: add_reaction = True
                except exceptions.NoDataFoundError:
                    pass

            # Producing
            end_time_match = re.search(r'<t:(\d+?):r>', queue_text_display.lower())
            if end_time_match:
                end_time = datetime.fromtimestamp(int(end_time_match.group(1)), timezone.utc).replace(microsecond=0)
                current_time = utils.utcnow().replace(microsecond=0)
                time_left = end_time - current_time
                if time_left <= timedelta(seconds=1): return add_reaction
                produce_name = produce_emoji = ''
                produce_name_match = re.search(r'\*\*(.+?)\*\*', queue_text_display.lower())
                if produce_name_match:
                    produce_name = produce_name_match.group(1)
                    if produce_name in strings.PRODUCE_FULL_NAMES:
                        produce_name = strings.PRODUCE_FULL_NAMES[produce_name]
                    produce_emoji = strings.PRODUCE_EMOJIS.get(produce_name, '')
                    
                user_command = await functions.get_game_command(user_settings, 'laboratory')
                reminder_message = (
                    user_settings.reminder_produce.message
                    .replace('{command}', user_command)
                    .replace('{produce_name}', produce_name)
                    .replace('{produce_emoji}', produce_emoji)
                ).strip()
                reminder: reminders.Reminder = (
                    await reminders.insert_reminder(interaction_user.id, 'produce', time_left,
                                                    message.channel.id, reminder_message)
                )
                if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True

            # Active boosters
            for line in booster_text_display.lower().split('\n'):    
                end_time_match = re.search(r'<t:(\d+?):r>', line)
                if end_time_match:
                    end_time = datetime.fromtimestamp(int(end_time_match.group(1)), timezone.utc).replace(microsecond=0)
                    current_time = utils.utcnow().replace(microsecond=0)
                    time_left = end_time - current_time
                    if time_left <= timedelta(seconds=1): continue
                    
                    boost_name = boost_emoji = category_name = category_tier = ''
                    category_name_match = re.search(r'cat_(\w+):', line)
                    category_tier_match = re.search(r'tier_(\d):', line)
                    if not category_name_match or not category_tier_match: continue
                    boost_name = strings.PRODUCE_CATEGORIES_ITEMS[f'{category_name_match.group(1)}{category_tier_match.group(1)}']
                    boost_emoji = strings.PRODUCE_EMOJIS.get(boost_name, '')
                        
                    reminder_message = (
                        user_settings.reminder_boosts.message
                        .replace('{boost_name}', boost_name)
                        .replace('{boost_emoji}', boost_emoji)
                    ).strip()
                    reminder: reminders.Reminder = (
                        await reminders.insert_reminder(interaction_user.id, boost_name.replace(' ','-'), time_left,
                                                        message.channel.id, reminder_message)
                    )
                    if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
                
    return add_reaction


async def create_reminders_on_pruner_page(message: discord.Message, embed_data: Dict, text_displays: list, interaction_user: Optional[discord.User],
                                          user_settings: Optional[users.User]) -> bool:
    """Creates a reminder when a research is active on the pruner page.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'laboratory', #English
        'pruner', #English
    ]
    if all(any(search_string in text_display.lower() for text_display in text_displays) for search_string in search_strings):
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_LABORATORY)
            )
            interaction_user = user_command_message.author
        user_name = ''
        for text_display in text_displays:    
            user_name_match = re.search(r'\*\*(.+?)\*\*\'s laboratory', text_display.lower())
            if user_name_match:
                user_name = user_name_match.group(1)
                break
        if user_name != interaction_user.name: return add_reaction
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(interaction_user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction
        if user_settings.reminder_research.enabled or user_settings.ready_show_pruner:
            timestring_text_display = ''
            for text_display in text_displays:
                if 'researching:' in text_display.lower():
                    timestring_text_display = text_display
                    break

            if not timestring_text_display:
                try:
                    reminder: reminders.Reminder = await reminders.get_reminder(interaction_user.id, 'pruner-research')
                    await reminder.delete()
                    if user_settings.reactions_enabled: add_reaction = True
                except exceptions.NoDataFoundError:
                    pass
                return add_reaction
            
            end_time_match = re.search(r'<t:(\d+?):r>', timestring_text_display.lower())
            end_time = datetime.fromtimestamp(int(end_time_match.group(1)), timezone.utc).replace(microsecond=0)
            current_time = utils.utcnow().replace(microsecond=0)
            time_left = end_time - current_time
            if time_left <= timedelta(seconds=1): return add_reaction
            user_command = await functions.get_game_command(user_settings, 'laboratory')
            reminder_message = user_settings.reminder_research.message.replace('{command}', user_command)
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(interaction_user.id, 'pruner-research', time_left,
                                                message.channel.id, reminder_message)
            )
            if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
                
    return add_reaction