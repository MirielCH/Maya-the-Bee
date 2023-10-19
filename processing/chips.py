# chips.py

from typing import Dict, Optional

import discord

from cache import messages
from database import users
from resources import exceptions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all chips related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await call_context_helper_on_chips_fusion(message, embed_data, user, user_settings))
    return_values.append(await call_context_helper_on_chips_list(message, embed_data, user, user_settings))
    return any(return_values)


async def call_context_helper_on_chips_fusion(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                              user_settings: Optional[users.User]) -> bool:
    """Call the context helper after a chips fusion

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'fusion results', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_CHIPS_FUSION,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.helper_context_enabled: return add_reaction
        await message.reply(
            f"➜ {strings.SLASH_COMMANDS['chips fusion']}\n"
            f"➜ {strings.SLASH_COMMANDS['chips show']}\n"
            f"➜ {strings.SLASH_COMMANDS['hive equip']}\n"
        )
    return add_reaction


async def call_context_helper_on_chips_list(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                              user_settings: Optional[users.User]) -> bool:
    """Call the context helper after opening the chips list

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'hull chips', #English
        'aerodynamic chips', #English
        'attack chips', #English
        'extension chips', #English
    ]
    if (any(search_string in embed_data['title'].lower() for search_string in search_strings)
        and message.edited_at is None):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_CHIPS,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.helper_context_enabled: return add_reaction
        await message.reply(
            f"➜ {strings.SLASH_COMMANDS['chips fusion']}\n"
            f"➜ {strings.SLASH_COMMANDS['hive equip']}"
        )
    return add_reaction