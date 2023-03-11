# tracking.py
"""Contains commands related to command tracking"""

from typing import Dict, Optional

import discord
from discord import utils

from database import users, tracking
from resources import exceptions


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all tracking related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await track_captcha(message, embed_data, user, user_settings))
    #return_values.append(await track_rebirth(message, embed_data, user, user_settings))
    return any(return_values)


async def track_captcha(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                        user_settings: Optional[users.User]) -> bool:
    """Tracks captchas

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    search_strings_title = [
        'verification required!', #English
    ]
    search_strings_content = [
        'captcha solved successfully', #English
    ]
    if (any(search_string in embed_data['title'].lower() for search_string in search_strings_title)
        and any(search_string in message.content.lower() for search_string in search_strings_content)):        
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user = message.mentions[0]
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return
            if not user_settings.tracking_enabled or not user_settings.bot_enabled: return False
        current_time = utils.utcnow().replace(microsecond=0)
        await tracking.insert_log_entry(user.id, message.guild.id, 'captcha', current_time)
    return False


async def track_rebirth(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                        ser_settings: Optional[users.User]) -> bool:
    """Tracks rebirth

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    search_strings = [
        'i have absolutely no idea whatsoever lol', #English
    ]
    pass