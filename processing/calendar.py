# calendar.py

from collections import deque
from content import list_ready
from datetime import timedelta
import random
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import reminders, users
from resources import exceptions, functions, regex
from resources.enums import ReadyPopupMode


async def process_message(message: discord.Message, embed_data: Dict, text_displays: list, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all calendar related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_reminder_from_calendar(message, embed_data, text_displays, user, user_settings))
    return_values.append(await update_data_from_calendar_rewards(message, embed_data, user, user_settings))
    return any(return_values)


async def create_reminder_from_calendar(message: discord.Message, embed_data: Dict, text_displays: list, user: Optional[discord.User],
                                        user_settings: Optional[users.User]) -> bool:
    """Create reminder from the calendar.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'today\'s rewards', #English
    ]
    if any(search_string in text_display.lower() for text_display in text_displays for search_string in search_strings):
        if user is None:
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
        if not user_settings.reminder_calendar.enabled and not user_settings.ready_show_calendar: return add_reaction

        rewards_claimed = False
        queue = deque(message.components)
        while queue:
            component = queue.popleft()
            if isinstance(component, discord.Section):
                button_label = getattr(getattr(component, 'accessory', ''), 'label', '')
                if button_label.lower() == 'claimed':
                    rewards_claimed = True
                    break
            queue.extend(getattr(component, 'components', []))

        if rewards_claimed:
            current_time = utils.utcnow()
            midnight_today = current_time.replace(hour=0, minute=0, microsecond=0)
            end_time = midnight_today + timedelta(days=1, seconds=random.randint(0, 300))
            time_to_midnight = end_time - current_time
            user_command = await functions.get_game_command(user_settings, 'calendar')
            reminder_message = user_settings.reminder_calendar.message.replace('{command}', user_command)
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, 'calendar', time_to_midnight,
                                            message.channel.id, reminder_message)
            )
            if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
            
    return add_reaction


async def update_data_from_calendar_rewards(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                            user_settings: Optional[users.User]) -> bool:
    """Create reminder, and update rebirth count & cooldowns from the calendar.

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

        if user_settings.reminder_calendar.enabled or user_settings.ready_show_calendar:
            current_time = utils.utcnow()
            midnight_today = current_time.replace(hour=0, minute=0, microsecond=0)
            end_time = midnight_today + timedelta(days=1, seconds=random.randint(0, 300))
            time_to_midnight = end_time - current_time
            user_command = await functions.get_game_command(user_settings, 'calendar')
            reminder_message = user_settings.reminder_calendar.message.replace('{command}', user_command)
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, 'calendar', time_to_midnight,
                                            message.channel.id, reminder_message)
            )
            if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True

            if user_settings.ready_popup_mode == ReadyPopupMode.SHOW_AFTER_EVERY_COMMAND:
                ready_embed = await functions.design_embed_ready_list(user, user_settings)
                if ready_embed:
                    await message.reply(embed=ready_embed)
                    
    return add_reaction