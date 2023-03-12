# use.py

from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import reminders, users
from resources import emojis, exceptions, regex


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all /use related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_reminder_on_insecticide(message, embed_data, user, user_settings))
    return_values.append(await create_reminder_on_sweet_apple(message, embed_data, user, user_settings))
    return any(return_values)


async def create_reminder_on_insecticide(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                         user_settings: Optional[users.User]) -> bool:
    """Create a reminder when an insecticide is used.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'insecticide active!', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_USE_INSECTICIDE,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.reminder_boosts.enabled: return add_reaction
        boost_end_match = re.search(r'<t:(\d+?):r>', embed_data['description'].lower())
        end_time = datetime.fromtimestamp(int(boost_end_match.group(1)), timezone.utc).replace(microsecond=0)
        current_time = utils.utcnow().replace(microsecond=0)
        time_left = end_time - current_time
        if time_left < timedelta(0): return add_reaction
        
        reminder_message = (
            user_settings.reminder_boosts.message
            .replace('{boost_emoji}', emojis.INSECTICIDE)
            .replace('{boost_name}', 'insecticide')
        )
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(user.id, 'insecticide', time_left,
                                            message.channel.id, reminder_message)
        )
        if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    return add_reaction


async def create_reminder_on_sweet_apple(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                         user_settings: Optional[users.User]) -> bool:
    """Create a reminder when a sweet apple is used.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'you have thrown a sweet apple to your tree!', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_USE_SWEET_APPLE,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.reminder_boosts.enabled: return add_reaction
        boost_end_match = re.search(r'<t:(\d+?):r>', embed_data['description'].lower())
        end_time = datetime.fromtimestamp(int(boost_end_match.group(1)), timezone.utc).replace(microsecond=0)
        current_time = utils.utcnow().replace(microsecond=0)
        time_left = end_time - current_time
        if time_left < timedelta(0): return add_reaction
        
        reminder_message = (
            user_settings.reminder_boosts.message
            .replace('{boost_emoji}', emojis.SWEET_APPLE)
            .replace('{boost_name}', 'sweet apple')
        )
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(user.id, 'sweet-apple', time_left,
                                            message.channel.id, reminder_message)
        )
        if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    return add_reaction