# inventory.py

import asyncio
import re
from typing import Dict, Optional

import discord

from cache import messages
from content import rebirth
from database import users
from resources import exceptions, regex


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                           user_settings: Optional[users.User]) -> bool:
    """Processes the message for all clean related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await call_rebirth_guide(message, embed_data, user, user_settings))
    return any(return_values)


async def call_rebirth_guide(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                             user_settings: Optional[users.User]) -> bool:
    """Calls the rebirth guide if necessary

    Returns
    -------
    - False
    """
    add_reaction = False
    if user is not None: return add_reaction
    search_strings = [
        '\'s inventory', #English
    ]
    if any(search_string in embed_data['author']['name'].lower() for search_string in search_strings):
        if embed_data['embed_user'] is not None:
            user = embed_data['embed_user']
            user_settings = embed_data['embed_user_settings']
            user_name = user.name
        else:
            user_name_match = re.search(regex.USERNAME_FROM_EMBED_AUTHOR, embed_data['author']['name'])
            user_name = user_name_match.group(1)
        user_command_message = (
            await messages.find_message(message.channel.id, regex.COMMAND_INVENTORY,
                                        user_name=user_name)
        )
        rebirth_guide_match = re.search(regex.COMMAND_REBIRTH_GUIDE, user_command_message.content.lower())
        if not rebirth_guide_match:
            return add_reaction
        if user is None:
            user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction
        asyncio.ensure_future(rebirth.command_rebirth_guide(message, user))
    return add_reaction