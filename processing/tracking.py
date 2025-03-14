# tracking.py
"""Contains commands related to command tracking"""

import re
from typing import Dict, Optional

import discord
from discord import utils

from database import users, tracking
from resources import exceptions, functions


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
        'captcha', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings_title):
        captcha_solved = False
        for component in message.components[0].children:
            if component.style == discord.ButtonStyle.success:
                captcha_solved = True
                break
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_name_match = re.search(r'hey \*\*(.+?)\*\*!', embed_data['description'].lower())
                user_name = user_name_match.group(1)
                guild_members = await functions.get_guild_member_by_name(message.guild, user_name)
                user = guild_members[0]
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return
        if not user_settings.bot_enabled: return False
        if not captcha_solved:
            await message.reply(
                f'{user.mention} Bzzt! A **CAPTCHA** appeared!'
            )
            return False
        if not user_settings.tracking_enabled: return False
        current_time = utils.utcnow().replace(microsecond=0)
        await tracking.insert_log_entry(user.id, message.guild.id, 'captcha', current_time)
    return False