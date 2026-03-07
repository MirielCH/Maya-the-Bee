# incubator.py

from datetime import timedelta
import re
from typing import Dict, Optional

import discord

from cache import messages
from database import reminders, users
from resources import exceptions, functions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all incubator related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_larva_reminders_from_feeding(message, embed_data, user, user_settings))
    return_values.append(await create_larva_reminders_from_overview(message, embed_data, user, user_settings))
    return any(return_values)


async def create_larva_reminders_from_feeding(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                              user_settings: Optional[users.User]) -> bool:
    """Creates reminders when feeding all larvae in the incubator

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'you have fed', #English
        'is now growing', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_INCUBATOR_FEED,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try: 
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.reminder_larva.enabled: return add_reaction

        single_feed = False
        slot_description_match = re.search(r"slot\s(\d+?)`", embed_data['description'].lower())
        if slot_description_match:
            slot = slot_description_match.group(1)
            single_feed = True
        if 'queen' in embed_data['description'].lower():
            larva_type = 'queen'
        elif 'soldier' in embed_data['description'].lower():
            larva_type = 'soldier'  
        elif 'worker' in embed_data['description'].lower():
            larva_type = 'worker' 
        else:
            larva_type = 'unknown'
        larvae_fed = embed_data['field0']['value'].split('\n')
        for line in larvae_fed:
            if not single_feed:
                slot_match = re.search(r"slot\s(\d+?)\)", line.lower())
                slot = slot_match.group(1)
                if 'queen' in line.lower():
                    larva_type = 'queen'
                elif 'soldier' in line.lower():
                    larva_type = 'soldier'  
                elif 'worker' in line.lower():
                    larva_type = 'worker' 
            timestring_match = re.search(r"`(.+?)`", line.lower())
            user_command = await functions.get_game_command(user_settings, 'incubator claim')
            time_left = await functions.calculate_time_left_from_timestring(message, timestring_match.group(1))
            if time_left < timedelta(0): continue
            activity = f'larva-{larva_type}-{slot}'
            reminder_message = user_settings.reminder_larva.message.replace('{command}', user_command)
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, activity, time_left,
                                                message.channel.id, reminder_message)
            )
            if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    
    return add_reaction


async def create_larva_reminders_from_overview(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                               user_settings: Optional[users.User]) -> bool:
    """Creates reminders when opening the incubator overview

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'incubator', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_INCUBATOR,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try: 
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.reminder_larva.enabled: return add_reaction

        for field in message.embeds[0].fields:
            if not 'loading' in field.value.lower(): continue
            slot_match = re.search(r"`slot\s(\d+?)`", field.name.lower())
            timestring_match = re.search(r"`(.+?)`", field.value.lower())
            
            if 'queen' in field.value.lower():
                larva_type = 'queen'
            elif 'soldier' in field.value.lower():
                larva_type = 'soldier'  
            elif 'worker' in field.value.lower():
                larva_type = 'worker'  
                
            user_command = await functions.get_game_command(user_settings, 'incubator claim')
            time_left = await functions.calculate_time_left_from_timestring(message, timestring_match.group(1))
            if time_left < timedelta(0): continue
            activity = f'larva-{larva_type}-{slot_match.group(1)}'
            reminder_message = user_settings.reminder_larva.message.replace('{command}', user_command)
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, activity, time_left,
                                                message.channel.id, reminder_message)
            )
            if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    
    return add_reaction