# tool.py

from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import reminders, users
from resources import exceptions, functions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, text_displays: list, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all tool related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await call_context_helper_on_upgrade_claim(message, embed_data, text_displays, user, user_settings))
    return_values.append(await create_reminder_when_active(message, embed_data, text_displays, user, user_settings))
    return_values.append(await delete_reminder_on_cancel(message, embed_data, user, user_settings))
    return_values.append(await delete_reminder_on_skip(message, embed_data, user, user_settings))
    return any(return_values)


async def call_context_helper_on_upgrade_claim(message: discord.Message, embed_data: Dict, text_displays: list[str], user: Optional[discord.User],
                                              user_settings: Optional[users.User]) -> bool:
    """Call the context helper after claiming n upgrade

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'upgrade ended: **', #English
        'upgrade cancelled, refunded', #English
    ]
    if any(search_string in text_display.lower() for search_string in search_strings for text_display in text_displays):
        if user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_TOOL)
            )
            user = user_command_message.author
        user_name = ''
        for text_display in text_displays:
            user_name_match = re.search(r'\*\*(.+?)\*\*\'s pruner', text_display.lower())
            if user_name_match:
                user_name = user_name_match.group(1)
                break
        if user_name != user.name: return add_reaction
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction
        for text_display in text_displays:
            level_match = re.search(r'level (\d+?) tier', text_display.lower())
            if level_match:
                pruner_level = int(level_match.group(1))
                break
        try:
            reminder = await reminders.get_reminder(user.id, 'pruner-upgrade')
            await reminder.delete()
        except exceptions.NoDataFoundError:
            pass

        if user_settings.helper_context_enabled and pruner_level == 10:
                await message.reply(f"➜ {strings.SLASH_COMMANDS['laboratory pruner']}")
    return add_reaction


async def create_reminder_when_active(message: discord.Message, embed_data: Dict, text_displays: list[str], interaction_user: Optional[discord.User],
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
        'drop nuggets from pruning', #English
    ]
    if any(search_string in text_display.lower() for search_string in search_strings for text_display in text_displays):
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_TOOL)
            )
            interaction_user = user_command_message.author
        user_name = ''
        for text_display in text_displays:
            user_name_match = re.search(r'\*\*(.+?)\*\*\'s pruner', text_display.lower())
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

        pruner_level = pruner_tier = pruner_type = end_time = None
        for text_display in text_displays:
            level_tier_match = re.search(r'level (\d+?) tier (.+?) ', text_display.lower())
            if level_tier_match:
                pruner_level = int(level_tier_match.group(1))
                pruner_tier = int(level_tier_match.group(2))      
            type_match = re.search(r':[pr]{2}uner_(.+?):', text_display.lower())
            if type_match:
               pruner_type = type_match.group(1)        
            upgrade_end_match = re.search(r'<t:(\d+?):r>', text_display.lower())
            if upgrade_end_match:
                end_time = datetime.fromtimestamp(int(upgrade_end_match.group(1)), timezone.utc).replace(microsecond=0)
        if not pruner_level or not pruner_tier or not pruner_type: return add_reaction
        await user_settings.update(pruner_level=pruner_level, pruner_tier=pruner_tier, pruner_type=pruner_type)

        if (user_settings.reminder_upgrade.enabled or user_settings.ready_show_pruner) and end_time:
            user_command = await functions.get_game_command(user_settings, 'tool')
            current_time = utils.utcnow().replace(microsecond=0)
            time_left = end_time - current_time
            if time_left < timedelta(0): return add_reaction
            reminder_message = user_settings.reminder_upgrade.message.replace('{command}', user_command)
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(interaction_user.id, 'pruner-upgrade', time_left,
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
            reminder: reminders.Reminder = await reminders.get_reminder(user.id, 'pruner-upgrade')
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
                user_name = user_name_match.group(1)
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_TOOL,
                                                user_name=user_name)
                )
                if user_command_message is not None:
                    user = user_command_message.author
                else:
                    embed_users = await functions.get_guild_member_by_name(message.guild, user_name)
                    if len(embed_users) == 1:
                        user = embed_users[0]
                    else:
                        return add_reaction
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction
        if user_settings.reminder_upgrade.enabled or user_settings.ready_show_pruner:
            try:
                reminder: reminders.Reminder = await reminders.get_reminder(user.id, 'pruner-upgrade')
                await reminder.delete()
            except exceptions.NoDataFoundError:
                return add_reaction
            if user_settings.reactions_enabled: add_reaction = True
    return add_reaction