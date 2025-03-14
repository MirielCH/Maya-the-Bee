# bees.py

import re
from typing import Dict, Optional

import discord

from cache import messages
from database import users
from resources import exceptions, functions, regex


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all /bees related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await update_bee_levels_from_overview(message, embed_data, user, user_settings))
    return_values.append(await update_bee_level_from_upgrade(message, embed_data, user, user_settings))
    return any(return_values)


async def update_bee_levels_from_overview(message: discord.Message, embed_data: Dict, interaction_user: Optional[discord.User],
                                          user_settings: Optional[users.User]) -> bool:
    """Creates boost remindesr from /bees

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        '\'s bees', #English
    ]
    if any(search_string in embed_data['author']['name'].lower() for search_string in search_strings):
        if embed_data['embed_user'] is not None and interaction_user is not None:
            if interaction_user != embed_data['embed_user']:
                return add_reaction
        embed_users = []
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_BEES)
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
        if not user_settings.bot_enabled: return add_reaction

        queen_bee_level_match = re.search(r'level.+\*\*(.+?)\*\*', embed_data['field0']['value'].lower())
        queen_bee_level = int(re.sub(r'\D', '', queen_bee_level_match.group(1)))
        soldier_bee_level_match = re.search(r'level.+\*\*(.+?)\*\*', embed_data['field1']['value'].lower())
        soldier_bee_level = int(re.sub(r'\D', '', soldier_bee_level_match.group(1)))
        await user_settings.update(queen_bee_level=queen_bee_level, soldier_bee_level=soldier_bee_level)
        
        if user_settings.reactions_enabled: add_reaction = True
    return add_reaction


async def update_bee_level_from_upgrade(message: discord.Message, embed_data: Dict, interaction_user: Optional[discord.User],
                                        user_settings: Optional[users.User]) -> bool:
    """Creates boost remindesr from upgrading soldier bees

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'you have upgraded your soldier bees', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        if interaction_user is None:
            user_name_match = re.search(r' \*\*(.+?)\*\*, ', embed_data['description'])
            user_name = user_name_match.group(1)
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_BEES,
                                            user_name=user_name)
            )
            if user_command_message is not None:
                interaction_user = user_command_message.author
            else:
                guild_members = await functions.get_guild_member_by_name(message.guild, user_name)
                if len(guild_members) == 1:
                    interaction_user = guild_members[0]
                else:
                    return add_reaction
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(interaction_user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction

        soldier_bee_level_match = re.search(r'level \*\*(.+?)\*\* ', embed_data['description'].lower())
        soldier_bee_level = int(re.sub(r'\D', '', soldier_bee_level_match.group(1)))
        await user_settings.update(soldier_bee_level=soldier_bee_level)
    return add_reaction