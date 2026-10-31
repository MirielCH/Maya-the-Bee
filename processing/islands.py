# islands.py

from datetime import timedelta
import re
from typing import Dict, Optional

import discord

from cache import messages
from database import reminders, users
from resources import exceptions, functions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, text_displays: list, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all island related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_travel_reminder(message, embed_data, text_displays, user, user_settings))
    return any(return_values)


async def create_travel_reminder(message: discord.Message, embed_data: Dict, text_displays: list, interaction_user: Optional[discord.User],
                                 user_settings: Optional[users.User]) -> bool:
    """Creates a reminder when travelling to another island.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'travels', #English
        'traveling', #English
    ]
    if all(any(search_string in text_display.lower() for text_display in text_displays) for search_string in search_strings):
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_ISLAND)
            )
            interaction_user = user_command_message.author
        user_name = ''
        for text_display in text_displays:    
            user_name_match = re.search(r'\*\*(.+?)\*\*\'s travels', text_display.lower())
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
        if not user_settings.reminder_island_travel.enabled: return add_reaction

        
        island_name = island_emoji = ''
        time_left = timedelta(seconds=0)
        for text_display in text_displays:
            if 'traveling' in text_display.lower():
                for line in text_display.lower().split('\n'):
                    if 'destination' in line:
                        island_name_match = re.search(r'\*\*\s+\*\*(.+?)\*\*', line)
                        if island_name_match:
                            island_name = island_name_match.group(1)
                            island_emoji = strings.ISLAND_EMOJIS.get(island_name, '')
                    if 'traveling' in line:
                        timestring_match = re.search(r'`(.+?)`', line)
                        if not timestring_match: return add_reaction
                        time_left = await functions.parse_timestring_to_timedelta(timestring_match.group(1))

        if time_left <= timedelta(seconds=1): return add_reaction
        user_command = await functions.get_game_command(user_settings, 'island travel')
        reminder_message = (
            user_settings.reminder_island_travel.message
            .replace('{command}', user_command)
            .replace('{island_name}', island_name)
            .replace('{island_emoji}', island_emoji)
        ).strip()
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(interaction_user.id, 'island-travel', time_left,
                                            message.channel.id, reminder_message)
        )
        if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
            
    return add_reaction