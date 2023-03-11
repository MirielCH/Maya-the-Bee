# tool.py

from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import reminders, users
from resources import exceptions, functions, regex


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all tool related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_reminder_when_active(message, embed_data, user, user_settings))
    return_values.append(await delete_reminder_on_cancel(message, embed_data, user, user_settings))
    return_values.append(await delete_reminder_on_skip(message, embed_data, user, user_settings))
    return any(return_values)


async def create_reminder_when_active(message: discord.Message, embed_data: Dict, interaction_user: Optional[discord.User],
                                   user_settings: Optional[users.User]) -> bool:
    """Creates a reminder when having an upgrade active. This also includes starting an upgrade.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'upgrading to level', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        if embed_data['embed_user'] is not None and interaction_user is not None:
            if interaction_user != embed_data['embed_user'] != interaction_user:
                return add_reaction
        embed_users = []
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_TOOL)
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
            if not user_settings.bot_enabled or not user_settings.reminder_upgrade.enabled: return add_reaction
        user_command = await functions.get_game_command(user_settings, 'tool')
        upgrade_end_match = re.search(r'<t:(\d+?):f>', embed_data['field0']['value'].lower())
        end_time = datetime.fromtimestamp(int(upgrade_end_match.group(1)), timezone.utc).replace(microsecond=0)
        current_time = utils.utcnow().replace(microsecond=0)
        time_left = end_time - current_time
        if time_left < timedelta(0): return add_reaction
        reminder_message = user_settings.reminder_upgrade.message.replace('{command}', user_command)
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(interaction_user.id, 'upgrade', time_left,
                                            message.channel.id, reminder_message)
        )
        if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    return add_reaction


async def delete_reminder_on_cancel(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                    user_settings: Optional[users.User]) -> bool:
    """Deletes a reminder when canceling an upgrade.

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
        and 'coin' in embed_data['description'].lower()):
        if user is None: user = message.mentions[0]
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
            if not user_settings.bot_enabled: return add_reaction
        try:
            reminder: reminders.Reminder = await reminders.get_reminder(user.id, 'upgrade')
            await reminder.delete()
        except exceptions.NoDataFoundError:
            return add_reaction
        if user_settings.reactions_enabled: add_reaction = True
    return add_reaction


async def delete_reminder_on_skip(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                  user_settings: Optional[users.User]) -> bool:
    """Deletes a reminder when skipping an upgrade.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'you have skipped the upgrade', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_name_match = re.search(r"^\*\*(.+?)\*\*, ", embed_data['description'])
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_TOOL,
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
            reminder: reminders.Reminder = await reminders.get_reminder(user.id, 'upgrade')
            await reminder.delete()
        except exceptions.NoDataFoundError:
            return add_reaction
        if user_settings.reactions_enabled: add_reaction = True
    return add_reaction