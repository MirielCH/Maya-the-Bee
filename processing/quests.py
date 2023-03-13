# quests.py

from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import errors, reminders, users
from resources import exceptions, functions, regex


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all quest related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_reminder_on_overview(message, embed_data, user, user_settings))
    return_values.append(await create_reminder_on_start(message, embed_data, user, user_settings))
    return_values.append(await create_reminder_when_active(message, embed_data, user, user_settings))
    return any(return_values)


async def create_reminder_on_overview(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                      user_settings: Optional[users.User]) -> bool:
    """Creates a reminder when using /quests with no quest active.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'tree quests', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_QUESTS,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
            if not user_settings.bot_enabled or not user_settings.reminder_quests.enabled: return add_reaction
        user_command = await functions.get_game_command(user_settings, 'quests')
        regex_quest = re.compile(r'^(.+?) \| (.+?)$')
        for button in message.components[0].children:
            quest_match = re.search(regex_quest, button.label)
            if not quest_match: continue
            quest_type = quest_match.group(1).lower()
            activity = f'quest-{quest_type}'
            reminder_message = (
                user_settings.reminder_quests.message
                .replace('{command}', user_command)
                .replace('{quest_type}', quest_type)
            )
            time_left = await functions.parse_timestring_to_timedelta(quest_match.group(2).lower())
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, activity, time_left,
                                                message.channel.id, reminder_message)
            )
            if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    return add_reaction


async def create_reminder_on_start(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                   user_settings: Optional[users.User]) -> bool:
    """Creates a reminder when starting a quest

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'quest started!', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_name_match = re.search(r"^\*\*(.+?)\*\*, ", embed_data['description'])
                user_name = user_name_match.group(1)
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_QUESTS,
                                                user_name=user_name)
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
            if not user_settings.bot_enabled or not user_settings.reminder_quests.enabled: return add_reaction
        user_command = await functions.get_game_command(user_settings, 'quests')
        quest_type_match = re.search(r'the (.+?) quest', embed_data['description'].lower())
        quest_type = quest_type_match.group(1).lower()
        activity = f'quest-{quest_type}'
        time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, activity)
        reminder_message = (
            user_settings.reminder_quests.message
            .replace('{command}', user_command)
            .replace('{quest_type}', quest_type)
        )
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(user.id, activity, time_left,
                                            message.channel.id, reminder_message)
        )
        if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    return add_reaction


async def create_reminder_when_active(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                      user_settings: Optional[users.User]) -> bool:
    """Creates a reminder when using /quests with an active quest.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        '\'s quest', #English
    ]
    if any(search_string in embed_data['author']['name'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_name_match = re.search(regex.USERNAME_FROM_EMBED_AUTHOR, embed_data['author']['name'])
                user_name = user_name_match.group(1)
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_QUESTS,
                                                user_name=user_name)
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
            if not user_settings.bot_enabled or not user_settings.reminder_quests.enabled: return add_reaction
        user_command = await functions.get_game_command(user_settings, 'quests')
        quest_type_match = re.search(r'> (.+?) quest', embed_data['description'].lower())
        quest_start_field = ''
        for value in embed_data.values():
            if isinstance(value, dict):
                try:
                    if '<t:' in value['value']:
                        quest_start_field = value['value']
                        break
                except KeyError:
                    continue
        quest_start_match = re.search(r'<t:(\d+?):d>', quest_start_field.lower())
        quest_type = quest_type_match.group(1).lower()
        activity = f'quest-{quest_type}'
        quest_start = datetime.fromtimestamp(int(quest_start_match.group(1)), timezone.utc).replace(microsecond=0)
        reminder_time = await functions.calculate_time_left_from_cooldown(message, user_settings, activity)
        end_time = quest_start + reminder_time
        current_time = utils.utcnow().replace(microsecond=0)
        time_left = end_time - current_time
        if time_left < timedelta(0): return add_reaction
        reminder_message = (
            user_settings.reminder_quests.message
            .replace('{command}', user_command)
            .replace('{quest_type}', quest_type)
        )
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(user.id, activity, time_left,
                                            message.channel.id, reminder_message)
        )
        if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    return add_reaction