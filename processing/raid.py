# raid.py

import re
from typing import Dict, Optional

import discord

from cache import messages
from database import users
from resources import exceptions, functions, logs, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
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
    return_values.append(await update_trophies_on_raid_start(message, embed_data, user, user_settings))
    return any(return_values)


async def call_helpers_on_failed_raid(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                      user_settings: Optional[users.User]) -> bool:
    """Call the context helper and trophy summary on a failed raid

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings_title = [
        'raid failed!', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings_title):
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

        diamond_trophies_lost = 0
        trophies_lost_match = re.search(r'\[trophies:\].+\*\*([\d-]+)\*\*\n', embed_data['field0']['value'],
                                        re.IGNORECASE)
        trophies_lost = int(trophies_lost_match.group(1).replace(',',''))
        diamond_trophies_lost_match = re.search(r'\[diamond trophies:\].+\*\*([\d-]+)\*\*\n', embed_data['field0']['value'],
                                               re.IGNORECASE)
        if diamond_trophies_lost_match:
            diamond_trophies_lost = int(diamond_trophies_lost_match.group(1).replace(',',''))

        trophies = user_settings.trophies + trophies_lost
        if trophies < 0: trophies = 0
        diamond_trophies = user_settings.diamond_trophies + diamond_trophies_lost
        if diamond_trophies < 0: diamond_trophies = 0
        
        await user_settings.update(trophies=trophies, diamond_trophies=diamond_trophies)

        message_content = None
        embed = None
        if user_settings.helper_trophies_enabled:
            embed = await functions.design_trophy_summary(user_settings)
        if user_settings.helper_context_enabled:
            message_content = f"➜ {strings.SLASH_COMMANDS['raid']}"
            if 'chest' in embed_data['field0']['value'].lower():
                message_content = f"➜ {strings.SLASH_COMMANDS['chests']}\n{message_content}"
        if message_content or embed:
            await message.reply(content=message_content, embed=embed)
            
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
    if any(search_string in embed_data['title'].lower() for search_string in search_strings_title):
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

        kwargs = {}
        diamond_trophies_gained = diamond_trophies_gain_average = 0
        trophies_gained_match = re.search(r'\[trophies:\].+\*\*([\d-]+)\*\*\n', embed_data['field0']['value'],
                                        re.IGNORECASE)
        trophies_gained = int(trophies_gained_match.group(1).replace(',',''))

        current_league = ''
        for trophy_amount, league_data in strings.LEAGUES.items():
            if user_settings.trophies >= trophy_amount:
                current_league, _ = league_data
            else:
                break

        new_league = ''
        for trophy_amount, league_data in strings.LEAGUES.items():
            if user_settings.trophies + trophies_gained >= trophy_amount:
                new_league, _ = league_data
            else:
                break

        if current_league != new_league:
            await user_settings.update(trophies_raid_count=0, diamond_trophies_raid_count=0)

        trophies_gain_average = user_settings.trophies_gain_average
        if trophies_gain_average == 0: trophies_gain_average = trophies_gained
        if user_settings.trophies_raid_count > 1:
            trophies_gain_average = (
                (user_settings.trophies_raid_count * user_settings.trophies_gain_average + trophies_gained)
                / (user_settings.trophies_raid_count + 1)
            )
        elif user_settings.trophies_raid_count == 1:
            trophies_gain_average = trophies_gained
        kwargs['trophies_raid_count'] = user_settings.trophies_raid_count + 1
        kwargs['trophies_gain_average'] = round(trophies_gain_average, 5)
        
        diamond_trophies_gained_match = re.search(r'\[diamond trophies:\].+\*\*([\d-]+)\*\*\n', embed_data['field0']['value'],
                                               re.IGNORECASE)
        if diamond_trophies_gained_match:
            diamond_trophies_gained = int(diamond_trophies_gained_match.group(1).replace(',',''))
            diamond_trophies_gain_average = user_settings.diamond_trophies_gain_average
            if user_settings.diamond_trophies_raid_count > 1:
                diamond_trophies_gain_average = (
                    (user_settings.diamond_trophies_raid_count * user_settings.diamond_trophies_gain_average + diamond_trophies_gained)
                    / (user_settings.diamond_trophies_raid_count + 1)
                )
            elif user_settings.diamond_trophies_raid_count == 1:
                diamond_trophies_gain_average = diamond_trophies_gained
            kwargs['diamond_trophies_raid_count'] = user_settings.diamond_trophies_raid_count + 1
            kwargs['diamond_trophies_gain_average'] = round(diamond_trophies_gain_average, 5)

        trophies = user_settings.trophies + trophies_gained
        diamond_trophies = user_settings.diamond_trophies + diamond_trophies_gained
        kwargs['trophies'] = trophies
        kwargs['diamond_trophies'] = diamond_trophies

        if trophies >= 86_000 and not user_settings.league_beta and user_settings.beta_pass_available > 0:
            kwargs['league_beta'] = True
            kwargs['beta_pass_available'] = user_settings.beta_pass_available - 1
            kwargs['diamond_rings_cap'] = user_settings.diamond_rings_cap + 1_350

        await user_settings.update(**kwargs)

        message_content = None
        embed = None
        if user_settings.helper_trophies_enabled:
            embed = await functions.design_trophy_summary(user_settings)
        if user_settings.helper_context_enabled:
            message_content = f"➜ {strings.SLASH_COMMANDS['raid']}"
            if 'chest' in embed_data['field0']['value'].lower():
                message_content = f"➜ {strings.SLASH_COMMANDS['chests']}\n{message_content}"
        if message_content or embed:
            await message.reply(content=message_content, embed=embed)
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


async def update_trophies_on_raid_start(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                        user_settings: Optional[users.User]) -> bool:
    """Update trophy count when starting a raid

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'you have 5 minutes to start the raid', #English
    ]
    if any(search_string in embed_data['footer']['text'].lower() for search_string in search_strings):
        if user is None:
            user_name_match = re.search(r'^(.+?),', embed_data['footer']['text'])
            user_name = user_name_match.group(1)
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

        kwargs = {}
        trophies_match = re.search(r'trophies: (.+?)$', embed_data['title'], re.IGNORECASE)
        trophies = int(re.sub(r'\D', '', trophies_match.group(1)))
        kwargs['trophies'] = trophies
        
        current_league = ''
        for trophy_amount, league_data in strings.LEAGUES.items():
            if user_settings.trophies >= trophy_amount:
                current_league, _ = league_data
            else:
                break

        new_league = ''
        for trophy_amount, league_data in strings.LEAGUES.items():
            if trophies >= trophy_amount:
                new_league, _ = league_data
            else:
                break

        if current_league != new_league:
            kwargs['trophies_raid_count'] = 0
            kwargs['trophies_gain_average'] = 0
            kwargs['diamond_trophies_raid_count'] = 0
            kwargs['diamond_trophies_gain_average'] = 0

        if trophies < 86_000:
            kwargs['league_beta'] = False
            
        if user_settings.trophies != trophies:    
            logs.logger.info(
                f'User {user_settings.user_id} had {user_settings.trophies:,} in the database, found {trophies:,} trophies.\n'
                f'{embed_data}'
            )
            
        await user_settings.update(**kwargs)
        
    return add_reaction