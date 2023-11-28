# rebirth.py

from typing import Dict, Optional

import discord

from cache import messages
from database import users
from resources import exceptions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all rebirth related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await update_rebirth_on_summary(message, embed_data, user, user_settings))
    return_values.append(await update_rebirth_on_cancel(message, embed_data, user, user_settings))
    return any(return_values)


async def update_rebirth_on_summary(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Increase rebirth count on rebirth summary message

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'are you sure you want to rebirth?', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_REBIRTH,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled and not user_settings.helper_prune_enabled: return add_reaction
        await user_settings.update(rebirth=user_settings.rebirth + 1, 
                                   xp_prune_count=0)
        await message.reply(
            f'➜ Use {strings.SLASH_COMMANDS["profile"]} to to start XP tracking after rebirthing!'
        )
    return add_reaction


async def update_rebirth_on_cancel(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Decrease rebirth count on rebirth cancel message

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'the rebirth has been canceled!', #English
    ]
    if any(search_string in message.content.lower() for search_string in search_strings):
        if user is None:
            user = message.mentions[0]
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled and not user_settings.helper_prune_enabled: return add_reaction
        await user_settings.update(rebirth=user_settings.rebirth - 1)
    return add_reaction