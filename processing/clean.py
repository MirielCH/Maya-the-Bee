# clean.py

from datetime import timedelta
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import reminders, tracking, users
from resources import exceptions, functions, regex


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                           user_settings: Optional[users.User]) -> bool:
    """Processes the message for all clean related actions.

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
    """Creates a reminder on /clean

    Returns
    -------
    - False
    """
    add_reaction = False
    search_strings = [
        'your tree has been cleaned!', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_CLEAN,
                                                user_name=embed_data['author']['name'])
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
            await tracking.insert_log_entry(user.id, message.guild.id, 'clean', current_time)
            if user_settings.reactions_enabled: add_reaction = True
        if not user_settings.reminder_clean.enabled: return add_reaction
        user_command = await functions.get_game_command(user_settings, 'clean')
        time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'clean')
        if time_left < timedelta(0): return add_reaction
        reminder_message = user_settings.reminder_clean.message.replace('{command}', user_command)
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(user.id, 'clean', time_left,
                                            message.channel.id, reminder_message)
        )
        if reminder.record_exists and user_settings.reactions_enabled: add_reaction = True
    return add_reaction