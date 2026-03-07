# fusion.py

from datetime import timedelta
import re
from typing import Dict, Optional

import discord

from cache import messages
from database import reminders, users
from resources import exceptions, functions, regex


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all fusion related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_reminder(message, embed_data, user, user_settings))
    return any(return_values)


async def create_reminder(message: discord.Message, embed_data: Dict, interaction_user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Creates a reminder on /fusion

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'there was a fusion', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        user1 = interaction_user
        user1_settings = user_settings
        user2 = user2_settings = None
        if user1 is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_FUSION,
                                            user_name=embed_data['field0']['name'])
            )
            user1 = user_command_message.author
            if user_command_message.mentions:
                user2 = user_command_message.mentions[0]
        if user2 is None:
            guild_members = await functions.get_guild_member_by_name(message.guild,
                                                                     embed_data['field1']['name'])
            if len(guild_members) == 1:
                user2 = guild_members[0]
        if user1_settings is None:
            try:
                user1_settings: users.User = await users.get_user(user1.id)
            except exceptions.FirstTimeUserError:
                user1_settings = None
        if user2 is not None:
            try:
                user2_settings: users.User = await users.get_user(user2.id)
            except exceptions.FirstTimeUserError:
                user2_settings = None
        if user1_settings is not None:
            if user1_settings.bot_enabled:
                if user1_settings.reminder_fusion.enabled:
                    user_command = await functions.get_game_command(user1_settings, 'fusion')
                    time_left = await functions.calculate_time_left_from_cooldown(message, user1_settings, 'fusion')
                    if time_left < timedelta(0): return add_reaction
                    reminder_message = user1_settings.reminder_fusion.message.replace('{command}', user_command)
                    reminder: reminders.Reminder = (
                        await reminders.insert_reminder(user1.id, 'fusion', time_left,
                                                        message.channel.id, reminder_message)
                    )
                    if user1_settings.reactions_enabled and reminder.record_exists: add_reaction = True
        if user2_settings is not None:
            if user2_settings.bot_enabled:
                if user2_settings.reminder_fusion.enabled:
                    user_command = await functions.get_game_command(user2_settings, 'fusion')
                    time_left = await functions.calculate_time_left_from_cooldown(message, user2_settings, 'fusion')
                    if time_left < timedelta(0): return add_reaction
                    reminder_message = user2_settings.reminder_fusion.message.replace('{command}', user_command)
                    reminder: reminders.Reminder = (
                        await reminders.insert_reminder(user2.id, 'fusion', time_left,
                                                        message.channel.id, reminder_message)
                    )
                    if user2_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    return add_reaction