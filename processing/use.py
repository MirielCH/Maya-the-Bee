# use.py

from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import reminders, users
from resources import emojis, exceptions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all /use related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await call_context_helper_on_energy_drink(message, embed_data, user, user_settings))
    return_values.append(await create_reminder_on_insecticide(message, embed_data, user, user_settings))
    return_values.append(await create_reminder_on_sweet_apple(message, embed_data, user, user_settings))
    return_values.append(await update_xp_on_water_bottle(message, embed_data, user, user_settings))
    return any(return_values)


async def call_context_helper_on_energy_drink(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                              user_settings: Optional[users.User]) -> bool:
    """Call the context helper when using an energy drink

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings_1 = [
        'you drank', #English
    ]
    search_strings_2 = [
        'energy drink', #English
    ]
    if (any(search_string in embed_data['title'].lower() for search_string in search_strings_1)
        and any(search_string in embed_data['title'].lower() for search_string in search_strings_2)):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_name_match = re.search(regex.USERNAME_FROM_EMBED_AUTHOR, embed_data['author']['name'])
                user_name = user_name_match.group(1)
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_USE_ENERGY_DRINK, user_name=user_name)
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.helper_context_enabled: return add_reaction
        await message.reply(f"➜ {strings.SLASH_COMMANDS['raid']}")
    return add_reaction


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
        try:
            active_reminder: reminders.Reminder= await reminders.get_reminder(user.id, 'sweet-apple')
            if active_reminder.triggered:
                await user_settings.update(xp_gain_average=0)
        except exceptions.NoDataFoundError:
            await user_settings.update(xp_gain_average=0)
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(user.id, 'sweet-apple', time_left,
                                            message.channel.id, reminder_message)
        )
        if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    return add_reaction


async def update_xp_on_water_bottle(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                    user_settings: Optional[users.User]) -> bool:
    """Update XP when a water bottle is used.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'your tree has been hydrated!', #English
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
        if not user_settings.bot_enabled or not user_settings.helper_prune_enabled: return add_reaction
        xp_gain_end_match = re.search(r'gained \*\*(.+?)\*\* exp', embed_data['description'].lower())
        xp_gain = int(re.sub('\D', '', xp_gain_end_match.group(1)))
        if user_settings.xp_target == 0 or user_settings.level == 0: return add_reaction
        new_xp = user_settings.xp + xp_gain
        levels_gained = 0
        xp_target = user_settings.xp_target
        if new_xp > user_settings.xp_target:
            xp_rest = new_xp - user_settings.xp_target
            level = user_settings.level
            levels_gained += 1
            while True:
                level += 1
                xp_target = (level ** 3) * 150
                xp_rest = xp_rest - xp_target
                if xp_rest < 0:
                    new_xp = xp_rest + xp_target
                    break
                else:
                    levels_gained += 1
        xp_gain_average = 0 if levels_gained > 0 else user_settings.xp_gain_average
        await user_settings.update(xp=new_xp, level=(user_settings.level + levels_gained), xp_target=xp_target,
                                   xp_gain_average=xp_gain_average)

    return add_reaction