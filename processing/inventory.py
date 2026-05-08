# inventory.py

import asyncio
import re
from typing import Dict, Optional

import discord

from cache import messages
from content import rebirth
from database import users
from resources import exceptions, functions, regex


async def process_message(message: discord.Message, embed_data: Dict, text_displays: list, user: Optional[discord.User],
                           user_settings: Optional[users.User]) -> bool:
    """Processes the message for all clean related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await call_rebirth_guide(message, embed_data, text_displays, user, user_settings))
    return any(return_values)


async def call_rebirth_guide(message: discord.Message, embed_data: Dict, text_displays: list, interaction_user: Optional[discord.User],
                             user_settings: Optional[users.User]) -> bool:
    """Calls the rebirth guide if necessary

    Returns
    -------
    - False
    """
    add_reaction = False
    if interaction_user is not None: return add_reaction
    search_strings = [
        '\'s inventory', #English
    ]
    if (any(search_string in embed_data['author']['name'].lower() for search_string in search_strings)
        or any(search_string in text_display.lower() for text_display in text_displays for search_string in search_strings)):
        if embed_data['embed_user'] is not None and interaction_user is not None:
            if interaction_user != embed_data['embed_user']:
                return add_reaction
        embed_users = []
        user_command_message = (
            await messages.find_message(message.channel.id, regex.COMMAND_INVENTORY)
        )
        if interaction_user is None:
            interaction_user = user_command_message.author
        if embed_data['embed_user']:
            embed_users.append(embed_data['embed_user'])
        else:
            if text_displays:
                user_name_match = re.search(regex.USERNAME_FROM_TEXT_DISPLAY, text_displays[0])
            else:
                user_name_match = re.search(regex.USERNAME_FROM_EMBED_AUTHOR, embed_data['author']['name'])
            user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, embed_data['author']['icon_url'])
            if user_id_match:
                user_id = int(user_id_match.group(1))
                embed_users.append(message.guild.get_member(user_id))
            if user_name_match:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_INVENTORY,
                                                user_name=user_name_match.group(1))
                )
                if not embed_users:
                    embed_users.append(user_command_message.author)
            else:
                return add_reaction
        if interaction_user not in embed_users: return add_reaction
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(interaction_user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction

        field_items = ''
        for embed_element, element_data in embed_data.items():
            if not embed_element.startswith('field'):
                continue
            if element_data['name'] == 'Items':
                field_items = element_data['value']
                break
        for text_display in text_displays:
            if '### items' in text_display.lower():
                field_items = text_display
                break
        diamond_rings = await functions.get_inventory_item(field_items, 'diamondring')
        if user_settings.diamond_rings != diamond_rings:
            await user_settings.update(diamond_rings=diamond_rings)
        await user_settings.update(diamond_rings=diamond_rings)
            
        rebirth_guide_match = re.search(regex.COMMAND_REBIRTH_GUIDE, user_command_message.content.lower())
        if rebirth_guide_match:
            miri_mode = True if 'miri' in user_command_message.content.lower() else False
            asyncio.ensure_future(rebirth.command_rebirth_guide(message, interaction_user, miri_mode))

    return add_reaction