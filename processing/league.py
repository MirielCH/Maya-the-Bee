# league.py

import asyncio
import re
from typing import Dict, Optional

import discord

from cache import messages
from content import rebirth
from database import users
from resources import exceptions, functions, regex


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                           user_settings: Optional[users.User]) -> bool:
    """Processes the message for all league related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await update_progress_and_call_helper(message, embed_data, user, user_settings))
    return any(return_values)


async def update_progress_and_call_helper(message: discord.Message, embed_data: Dict, interaction_user: Optional[discord.User],
                                          user_settings: Optional[users.User]) -> bool:
    """Updates progress and calls the trophy summary

    Returns
    -------
    - False
    """
    add_reaction = False
    if interaction_user is not None: return add_reaction
    search_strings = [
        'next cap increase requirement', #English
    ]
    if any(search_string in embed_data['field1']['value'].lower() for search_string in search_strings):
        if embed_data['embed_user'] is not None and interaction_user is not None:
            if interaction_user != embed_data['embed_user']:
                return add_reaction
        embed_users = []
        user_command_message = (
            await messages.find_message(message.channel.id, regex.COMMAND_LEAGUE)
        )
        if interaction_user is None:
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

        league_beta = True if 'beta' in embed_data['title'].lower() else False

        trophies_match = re.search(r' ([\d,]+)$', embed_data['title'])
        trophies = int(re.sub(r'\D', '', trophies_match.group(1)))

        diamond_rings_match = re.search(r'\*\*(.+?)\*\*\/(.+?)$', embed_data['field1']['value'].split('\n')[0])
        diamond_rings = int(re.sub(r'\D', '', diamond_rings_match.group(1)))
        diamond_rings_cap = int(re.sub(r'\D', '', diamond_rings_match.group(2)))

        rebirth_match = re.search(r'rebirths: \*\*(.+?)\*\*', embed_data['field1']['value'], re.IGNORECASE)
        rebirth = int(re.sub(r'\D', '', rebirth_match.group(1)))

        beta_pass_match = re.search(r'beta passes available: \*\*(.+?)\*\*\/', embed_data['field1']['value'], re.IGNORECASE)
        beta_pass_available = int(re.sub(r'\D', '', beta_pass_match.group(1)))

        await user_settings.update(trophies=trophies, diamond_rings=diamond_rings, diamond_rings_cap=diamond_rings_cap,
                                   rebirth=rebirth, beta_pass_available=beta_pass_available, league_beta=league_beta)

        if user_settings.helper_trophies_enabled:
            embed = await functions.design_trophy_summary(user_settings)
            await message.reply(embed=embed)
        
        
    return add_reaction