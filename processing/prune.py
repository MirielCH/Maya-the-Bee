# prune.py

from datetime import timedelta
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import errors, reminders, tracking, users
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
        user = await functions.get_interaction_user(message)
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
        if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    return add_reaction