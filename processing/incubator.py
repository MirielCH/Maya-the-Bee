# incubator.py

import asyncio
from datetime import timedelta
import re
from typing import Dict, Optional

import discord

from cache import messages
from database import reminders, users
from resources import exceptions, functions, regex, settings, strings


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
    return_values.append(await create_nugget_alert(message, embed_data, user, user_settings))
    return_values.append(await create_upgrade_reminder(message, embed_data, user, user_settings))
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
            reminder_message = (
                    user_settings.reminder_larva.message
                    .replace('{command}', user_command)
                    .replace('{larva_emoji}', strings.LARVAE_EMOJIS[larva_type])
                    .replace('{larva_name}', f'{larva_type} larva')
                )
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, activity, time_left,
                                                message.channel.id, reminder_message)
            )
            if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    
    return add_reaction


async def create_larva_reminders_from_overview(message: discord.Message, embed_data: Dict, interaction_user: Optional[discord.User],
                                               user_settings: Optional[users.User]) -> bool:
    """Creates reminders when opening the incubator overview

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings_title = [
        'incubator', #English
    ]
    search_strings_description = [
        'level:', #English
    ]
    if (any(search_string in embed_data['title'].lower() for search_string in search_strings_title)
        and any(search_string in embed_data['description'].lower() for search_string in search_strings_description)):
        if embed_data['embed_user'] is not None and interaction_user is not None:
            if interaction_user != embed_data['embed_user']:
                return add_reaction
        embed_users = []
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_INCUBATOR)
            )
            interaction_user = user_command_message.author
        if embed_data['embed_user'] is None:
            user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, embed_data['author']['icon_url'])
            if user_id_match:
                user_id = int(user_id_match.group(1))
                embed_users.append(message.guild.get_member(user_id))
            else:
                user_name_match = re.search(regex.USERNAME_FROM_EMBED_AUTHOR, embed_data['author']['name'])
                user_name = user_name_match.group(1)
                embed_users = await functions.get_guild_member_by_name(message.guild, user_name)
        else:
            embed_users.append(embed_data['embed_user'])
        if interaction_user not in embed_users: return add_reaction
        if user_settings is None:
            try: 
                user_settings: users.User = await users.get_user(interaction_user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction

        if user_settings.reminder_larva.enabled:
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
                reminder_message = (
                    user_settings.reminder_larva.message
                    .replace('{command}', user_command)
                    .replace('{larva_emoji}', strings.LARVAE_EMOJIS[larva_type])
                    .replace('{larva_name}', f'{larva_type} larva')
                )
                reminder: reminders.Reminder = (
                    await reminders.insert_reminder(interaction_user.id, activity, time_left,
                                                    message.channel.id, reminder_message)
                )
                if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True

        if user_settings.reminder_incubator_upgrade.enabled:
            incubator_upgrade_match = re.search(r"cooldown:.+`(.+?)`", embed_data['description'].lower())
            if incubator_upgrade_match:
                user_command = await functions.get_game_command(user_settings, 'incubator upgrade')
                time_left = await functions.calculate_time_left_from_timestring(message, incubator_upgrade_match.group(1))
                if time_left <= timedelta(0): return add_reaction
                reminder_message = user_settings.reminder_incubator_upgrade.message.replace('{command}', user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_reminder(interaction_user.id, 'incubator-upgrade', time_left,
                                                    message.channel.id, reminder_message)
                )
                if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    
    return add_reaction


async def create_nugget_alert(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                              user_settings: Optional[users.User]) -> bool:
    """Sends a nugget alert when claiming larvae if nuggets are found

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings_description = [
        'claimed **', #English
        'larva(e)!', #English
    ]
    search_strings_field = [
        'drops', #English
    ]
    fields = f'{embed_data['field0']['name']}\n{embed_data['field0']['value']}\n{embed_data['field1']['name']}\n{embed_data['field1']['value']}'
    if (all(search_string in embed_data['description'].lower() for search_string in search_strings_description)
        and any(search_string in fields.lower() for search_string in search_strings_field)):
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
        if not user_settings.bot_enabled or not user_settings.alert_nugget_enabled: return add_reaction

        dropped_nuggets = {}
        nugget_wooden_match = re.search(r'\*\*`(.+?)`\*\*.+woodennugget', fields.lower())
        nugget_copper_match = re.search(r'\*\*`(.+?)`\*\*.+coppernugget', fields.lower())
        nugget_silver_match = re.search(r'\*\*`(.+?)`\*\*.+silvernugget', fields.lower())
        nugget_golden_match = re.search(r'\*\*`(.+?)`\*\*.+goldennugget', fields.lower())
        nugget_diamond_match = re.search(r'\*\*`(.+?)`\*\*.+diamondnugget', fields.lower())
        if nugget_wooden_match:
            nugget_wooden_amount = int(re.sub(r'\D', '', nugget_wooden_match.group(1)))
            dropped_nuggets['Wooden'] = nugget_wooden_amount
        if nugget_copper_match:
            nugget_copper_amount = int(re.sub(r'\D', '', nugget_copper_match.group(1)))
            dropped_nuggets['Copper'] = nugget_copper_amount
        if nugget_silver_match:
            nugget_silver_amount = int(re.sub(r'\D', '', nugget_silver_match.group(1)))
            dropped_nuggets['Silver'] = nugget_silver_amount
        if nugget_golden_match:
            nugget_golden_amount = int(re.sub(r'\D', '', nugget_golden_match.group(1)))
            dropped_nuggets['Golden'] = nugget_golden_amount
        if nugget_diamond_match:
            nugget_diamond_amount = int(re.sub(r'\D', '', nugget_diamond_match.group(1)))
            dropped_nuggets['Diamond'] = nugget_diamond_amount
    
        if dropped_nuggets:
            nugget_names = list(strings.NUGGETS.keys())
            threshold_index = nugget_names.index(user_settings.alert_nugget_threshold)
            nuggets_found = ''
            for name, amount in dropped_nuggets.items():
                if nugget_names.index(name) >= threshold_index:
                    nuggets_found = (
                        f'{nuggets_found}\n'
                        f'**{amount:,}** {strings.NUGGETS[name]} {name} nuggets'
                    )
            if nuggets_found:
                if user_settings.alert_nugget_dm:
                    asyncio.ensure_future(user.send(
                        f'Bzzt! **Nuggets** found!\n'
                        f'{nuggets_found.strip()}\n'
                        f'➜ {message.jump_url}'
                    ))
                else:
                    embed = discord.Embed(
                        color = settings.EMBED_COLOR,
                        title = 'Nuggets found!',
                        description = nuggets_found,
                    ) 
                    embed.set_footer(text='Use "/settings alerts" to change this')
                    await message.reply(embed=embed)
            
    return add_reaction


async def create_upgrade_reminder(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                  user_settings: Optional[users.User]) -> bool:
    """Creates reminder when starting an incubator upgrade

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'you have upgraded your incubator', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
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
        if not user_settings.bot_enabled or not user_settings.reminder_incubator_upgrade.enabled: return add_reaction

        user_command = await functions.get_game_command(user_settings, 'incubator upgrade')
        time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'incubator-upgrade')
        if time_left < timedelta(0): return add_reaction
        reminder_message = user_settings.reminder_incubator_upgrade.message.replace('{command}', user_command)
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(user.id, 'incubator-upgrade', time_left,
                                            message.channel.id, reminder_message)
        )
        if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    
    return add_reaction