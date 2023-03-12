# hive.py

from datetime import timedelta
import re
from typing import Dict, Optional

import discord

from cache import messages
from database import reminders, users
from resources import exceptions, functions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all hive related actions.

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
    """Creates a reminder on /hive claim-energy

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings_author = [
        'hive', #English
    ]
    search_strings_footer = [
        'use energy to raid', #English
    ]
    if (any(search_string in embed_data['author']['name'].lower() for search_string in search_strings_author)
        and any(search_string in embed_data['footer']['text'].lower() for search_string in search_strings_footer)):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_name_match = re.search(r"^(.+?)'s ", embed_data['author']['name'])
                user_name = user_name_match.group(1)
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_HIVE_CLAIM_ENERGY,
                                                user_name=user_name)
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.reminder_hive_energy.enabled: return add_reaction
        user_command = await functions.get_game_command(user_settings, 'hive claim energy')
        time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'hive-energy')
        if time_left < timedelta(0): return add_reaction
        reminder_message = user_settings.reminder_hive_energy.message.replace('{command}', user_command)
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(user.id, 'hive-energy', time_left,
                                            message.channel.id, reminder_message)
        )
        if user_settings.reactions_enabled and reminder.record_exists:
            add_reaction = True
        if user_settings.helper_context_enabled:
            await message.reply(f"➜ {strings.SLASH_COMMANDS['raid']}")
    return add_reaction