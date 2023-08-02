# vote.py

from datetime import timedelta
import re
from typing import Dict, Optional

import discord

from cache import messages
from database import reminders, users
from resources import exceptions, functions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all vote related actions.

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
    """Create a reminder on /daily

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'click here to vote', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        reminder = None
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_VOTE,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.reminder_vote.enabled: return add_reaction
        if user_settings.helper_context_enabled:
            streak_match = re.search(r'\*\*(\d)\*\*/7', embed_data['field1']['value'])
            if streak_match:
                await user_settings.update(streak_vote=int(streak_match.group(1)))
        if 'cooldown ready!' in embed_data['title'].lower():
            if reminder is None:
                try:
                    reminder = await reminders.get_reminder(user.id, 'vote')
                except exceptions.NoDataFoundError:
                    pass
            if reminder is not None:
                await reminder.delete()
        else:
            user_command = await functions.get_game_command(user_settings, 'vote')
            timestring_match = re.search(r'\*\*`(.+?)`\*\*', embed_data['title'], re.IGNORECASE)
            time_left = await functions.calculate_time_left_from_timestring(message, timestring_match.group(1))
            if time_left < timedelta(0): return add_reaction
            reminder_message = user_settings.reminder_vote.message.replace('{command}', user_command)
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, 'vote', time_left,
                                                message.channel.id, reminder_message)
            )
            if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
        if user_settings.helper_context_enabled:
            if reminder is None:
                try:
                    reminder = await reminders.get_reminder(user.id, 'vote')
                except exceptions.NoDataFoundError:
                    pass
            if user_settings.streak_vote >= 6:
                if reminder is None:
                    await message.reply(f"➜ {strings.SLASH_COMMANDS['claim']}")
                elif reminder.triggered:
                    await message.reply(f"➜ {strings.SLASH_COMMANDS['claim']}")
    return add_reaction