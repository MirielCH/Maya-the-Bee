# calendar.py

import re
from typing import Dict, Optional

import discord

from cache import messages
from database import reminders, users
from resources import exceptions, functions, regex


async def process_message(message: discord.Message, embed_data: Dict, text_displays: list, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all calendar related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await update_data_from_calendar_rewards(message, embed_data, user, user_settings))
    return any(return_values)


async def update_data_from_calendar_rewards(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                            user_settings: Optional[users.User]) -> bool:
    """Update rebirth count & cooldowns from the calendar.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'you have claimed **day', #English
    ]
    if (any(search_string in embed_data['description'].lower() for search_string in search_strings)):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_CALENDAR)
                )
                user = user_command_message.author
        if user_settings is None:
            try: 
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction

        rebirth_amount = await functions.get_inventory_item(embed_data['field0']['value'], 'rebirth')
        cooldowns_reset_match = re.search(r'cooldowns reset', embed_data['field0']['value'], re.IGNORECASE)
        if rebirth_amount > 0:
            await user_settings.update(rebirth=user_settings.rebirth + rebirth_amount)
            add_reaction = True

        if cooldowns_reset_match:
            activities = ['daily', 'clean', 'fusion', 'prune']
            await reminders.reduce_reminder_time_percentage(user_settings, 100, activities)
            add_reaction = True
            
    return add_reaction