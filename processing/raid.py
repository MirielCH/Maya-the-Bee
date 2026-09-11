# raid.py

import re
from typing import Dict, Optional

import discord

from cache import messages
from database import users
from resources import exceptions, functions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, text_displays: list, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all raid related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await call_helpers_on_failed_raid(message, embed_data, user, user_settings))
    return_values.append(await call_helpers_on_successful_raid(message, embed_data, user, user_settings))
    return_values.append(await call_context_helper_on_empty_energy(message, embed_data, user, user_settings))
    return any(return_values)


async def call_helpers_on_failed_raid(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                      user_settings: Optional[users.User]) -> bool:
    """Call the context helper on a failed raid

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings_title = [
        'raid failed!', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings_title) and not message.edited_at:
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_name = embed_data['author']['name']
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_RAID, user_name=user_name)
                )
                if user_command_message is None: return add_reaction
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction

        message_content = None
        if user_settings.helper_context_enabled:
            message_content = f"➜ {strings.SLASH_COMMANDS['raid']}"
            if 'chest' in embed_data['field0']['value'].lower():
                message_content = f"➜ {strings.SLASH_COMMANDS['chests']}\n{message_content}"
        if message_content:
            await message.reply(message_content)
            
    return add_reaction


async def call_helpers_on_successful_raid(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                          user_settings: Optional[users.User]) -> bool:
    """Call the context helper and tropy summary on a successful raid

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings_title = [
        'raid successful!', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings_title) and not message.edited_at:
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_name = embed_data['author']['name']
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_RAID, user_name=user_name)
                )
                if user_command_message is None: return add_reaction
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction

        if 'chest' in embed_data['field0']['value'].lower():
            await user_settings.update(chests_in_queue=user_settings.chests_in_queue + 1)
        
        message_content = None
        if user_settings.helper_context_enabled:
            message_content = f"➜ {strings.SLASH_COMMANDS['raid']}"
            if 'chest' in embed_data['field0']['value'].lower():
                message_content = f"➜ {strings.SLASH_COMMANDS['chests']}\n{message_content}"
        if message_content:
            await message.reply(message_content)
    return add_reaction


async def call_context_helper_on_empty_energy(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                              user_settings: Optional[users.User]) -> bool:
    """Call the context helper when trying to raid with no energy

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    if ('something went wrong...' in embed_data['title'].lower()
        and 'energy to start a raid' in embed_data['description'].lower()):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_name = re.search(r'> \*\*(.+?)\*\*, ', embed_data['description']).group(1)
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_RAID, user_name=user_name)
                )
                if user_command_message is None: return add_reaction
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.helper_context_enabled: return add_reaction
        answer = (
            f"➜ {strings.SLASH_COMMANDS['hive claim energy']}\n"
            f"➜ {strings.SLASH_COMMANDS['use']} `item: Energy Drink`"
        )
        await message.reply(answer)
    return add_reaction