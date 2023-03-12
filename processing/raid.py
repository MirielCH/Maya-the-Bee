# raid.py

import re
from typing import Dict, Optional

import discord

from cache import messages
from database import users
from resources import exceptions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all raid related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await call_context_helper_on_raid_rewards(message, embed_data, user, user_settings))
    return any(return_values)


async def call_context_helper_on_raid_rewards(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                              user_settings: Optional[users.User]) -> bool:
    """Call the context helper for a chest reward from raid

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings_title = [
        'raid successful!', #English
        'raid failed!', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings_title):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_name_match = re.search(regex.USERNAME_FROM_EMBED_AUTHOR, embed_data['author']['name'])
                user_name = user_name_match.group(1)
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_RAID, user_name=user_name)
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.helper_context_enabled: return add_reaction
        answer = f"➜ {strings.SLASH_COMMANDS['raid']}"
        if 'chest' in embed_data['field0']['value'].lower():
            answer = f"➜ {strings.SLASH_COMMANDS['chests']}\n{answer}"
        await message.reply(answer)
    return add_reaction