# laboratory.py

from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import errors, reminders, users
from resources import exceptions, functions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all laboratory related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await call_context_helper_on_research_claim(message, embed_data, user, user_settings))
    return_values.append(await create_reminder_on_start(message, embed_data, user, user_settings))
    return_values.append(await create_reminder_when_active(message, embed_data, user, user_settings))
    return_values.append(await delete_reminder_on_skip(message, embed_data, user, user_settings))
    return_values.append(await delete_reminder_on_cancel(message, embed_data, user, user_settings))
    return_values.append(await store_research_time(message, embed_data, user, user_settings))
    return any(return_values)


async def call_context_helper_on_research_claim(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                              user_settings: Optional[users.User]) -> bool:
    """Call the context helper after claiming a research

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'research ended!', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_LABORATORY,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.helper_context_enabled: return add_reaction
        await message.reply(f"➜ {strings.SLASH_COMMANDS['tool']}")
    return add_reaction


async def create_reminder_on_start(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                   user_settings: Optional[users.User]) -> bool:
    """Creates a reminder when starting a research.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'you have started a research', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_name_match = re.search(regex.NAME_FROM_MESSAGE_START, embed_data['description'])
                user_name = user_name_match.group(1)
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_LABORATORY, user_name=user_name)
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
            if not user_settings.bot_enabled or not user_settings.reminder_research.enabled: return add_reaction
        user_command = await functions.get_game_command(user_settings, 'laboratory')
        if user_settings.research_time == 0:
            await functions.add_warning_reaction(message)
            await errors.log_error('Research time is 0 for some reason.', message)
            return add_reaction
        time_left = timedelta(seconds=user_settings.research_time)
        reminder_message = user_settings.reminder_research.message.replace('{command}', user_command)
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(user.id, 'research', time_left,
                                            message.channel.id, reminder_message)
        )
        if reminder.record_exists and user_settings.reactions_enabled: add_reaction = True
    return add_reaction


async def create_reminder_when_active(message: discord.Message, embed_data: Dict, interaction_user: Optional[discord.User],
                                      user_settings: Optional[users.User]) -> bool:
    """Creates a reminder for an active research.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'researching: tier', #English
    ]
    if any(search_string in embed_data['field0']['name'].lower() for search_string in search_strings):
        if embed_data['embed_user'] is not None and interaction_user is not None:
            if interaction_user != embed_data['embed_user'] != interaction_user:
                return add_reaction
        embed_users = []
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_LABORATORY)
            )
            interaction_user = user_command_message.author
        if embed_data['embed_user'] is None:
            user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, embed_data['author']['icon_url'])
            if user_id_match:
                user_id = int(user_id_match.group(1))
                embed_users.append(message.guild.get_member(user_id))
            else:
                embed_users = await functions.get_guild_member_by_name(message.guild, embed_data['author']['name'])
        else:
            embed_users.append(embed_data['embed_user'])
        if interaction_user not in embed_users: return add_reaction
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(interaction_user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
            if not user_settings.bot_enabled or not user_settings.reminder_research.enabled: return add_reaction
        user_command = await functions.get_game_command(user_settings, 'laboratory')
        research_end_match = re.search(r'<t:(\d+?):f>', embed_data['field0']['value'].lower())
        end_time = datetime.fromtimestamp(int(research_end_match.group(1)), timezone.utc).replace(microsecond=0)
        current_time = utils.utcnow().replace(microsecond=0)
        time_left = end_time - current_time
        if time_left < timedelta(0): return add_reaction
        reminder_message = user_settings.reminder_research.message.replace('{command}', user_command)
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(interaction_user.id, 'research', time_left,
                                            message.channel.id, reminder_message)
        )
        if reminder.record_exists and user_settings.reactions_enabled: add_reaction = True
    return add_reaction


async def delete_reminder_on_cancel(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                    user_settings: Optional[users.User]) -> bool:
    """Deletes a reminder when canceling a research.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'you have been refund', #English
    ]
    if (any(search_string in embed_data['description'].lower() for search_string in search_strings)
        and 'nugget' in embed_data['description'].lower()):
        if user is None: user = message.mentions[0]
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
            if not user_settings.bot_enabled or not user_settings.reminder_upgrade.enabled: return add_reaction
        try:
            reminder: reminders.Reminder = await reminders.get_reminder(user.id, 'research')
            await reminder.delete()
        except exceptions.NoDataFoundError:
            return add_reaction
        if user_settings.reactions_enabled: add_reaction = True
    return add_reaction


async def delete_reminder_on_skip(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                  user_settings: Optional[users.User]) -> bool:
    """Deletes a reminder when skipping a research.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'you have skipped the research', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_name_match = re.search(r"^\*\*(.+?)\*\*, ", embed_data['description'])
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_LABORATORY,
                                                user_name=user_name_match.group(1))
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
            if not user_settings.bot_enabled or not user_settings.reminder_upgrade.enabled: return add_reaction
        try:
            reminder: reminders.Reminder = await reminders.get_reminder(user.id, 'research')
            await reminder.delete()
        except exceptions.NoDataFoundError:
            return add_reaction
        if user_settings.reactions_enabled: add_reaction = True
    return add_reaction


async def store_research_time(message: discord.Message, embed_data: Dict, interaction_user: Optional[discord.User],
                              user_settings: Optional[users.User]) -> bool:
    """Extracts and stores the time required for the next research.

    Returns
    -------
    - False
    """
    if re.search(r'level \d+ laboratory', embed_data['description'], re.IGNORECASE):
        if embed_data['embed_user'] is not None and interaction_user is not None:
            if interaction_user != embed_data['embed_user'] != interaction_user:
                return False
        embed_users = []
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_LABORATORY)
            )
            interaction_user = user_command_message.author
        if embed_data['embed_user'] is None:
            user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, embed_data['author']['icon_url'])
            if user_id_match:
                user_id = int(user_id_match.group(1))
                embed_users.append(message.guild.get_member(user_id))
            else:
                embed_users = await functions.get_guild_member_by_name(message.guild, embed_data['author']['name'])
        else:
            embed_users.append(embed_data['embed_user'])
        if interaction_user not in embed_users: return False
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(interaction_user.id)
            except exceptions.FirstTimeUserError:
                return False
            if not user_settings.bot_enabled: return
        for line in embed_data['field0']['value'].split('\n'):
            if not 'time needed' in line.lower(): continue
            timestring_match = re.search('\)\*\* (.+?)$', line)
            research_time = await functions.calculate_time_left_from_timestring(message, timestring_match.group(1))
            await user_settings.update(research_time=research_time.total_seconds())
    return False