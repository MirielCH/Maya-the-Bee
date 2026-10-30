# halloween.py

from datetime import datetime, timedelta, timezone
import random
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import reminders, users
from resources import exceptions, functions, regex, strings
from resources.enums import ReadyPopupMode


async def process_message(message: discord.Message, embed_data: Dict, text_displays: list, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all halloween related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_reminder_from_afterlife_overview(message, embed_data, text_displays, user, user_settings))
    return_values.append(await create_reminder_from_afterlife_attack(message, embed_data, text_displays, user, user_settings))
    return_values.append(await update_reminders_from_potions(message, embed_data, text_displays, user, user_settings))
    return any(return_values)


async def create_reminder_from_afterlife_overview(message: discord.Message, embed_data: Dict, text_displays: list, user: Optional[discord.User],
                                                  user_settings: Optional[users.User]) -> bool:
    """Create reminder from the halloween afterlife message.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'next attack **', #English
    ]
    if any(search_string in text_display.lower() for text_display in text_displays for search_string in search_strings):
        if user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_HAL_AFTERLIFE)
            )
            user = user_command_message.author
        if user_settings is None:
            try: 
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction
        if not user_settings.reminder_hal_afterlife.enabled and not user_settings.ready_show_hal_afterlife: return add_reaction

        timestring_match = re.search(r'next attack \*\*`(.+?)`\*\*', text_displays[1].lower())
        if not timestring_match:
            try:
                reminder: reminders.Reminder = await reminders.get_reminder(user.id, 'afterlife')
                await reminder.delete()
            except exceptions.NoDataFoundError:
                pass
            return add_reaction

        time_left = await functions.parse_timestring_to_timedelta(timestring_match.group(1))
        user_command = await functions.get_game_command(user_settings, 'halloween afterlife')
        reminder_message = user_settings.reminder_hal_afterlife.message.replace('{command}', user_command)
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(user.id, 'afterlife', time_left,
                                        message.channel.id, reminder_message)
        )
        if user_settings.reactions_enabled: add_reaction = True
            
    return add_reaction


async def create_reminder_from_afterlife_attack(message: discord.Message, embed_data: Dict, text_displays: list, user: Optional[discord.User],
                                                user_settings: Optional[users.User]) -> bool:
    """Create reminder from the halloween afterlife attack message.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'contributing on defeating the spooky biome hives!', #English
        'soldiers! never mind', #English
    ]
    if any(search_string in text_display.lower() for text_display in text_displays for search_string in search_strings):
        if user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_HAL_AFTERLIFE)
            )
            user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction
        if not user_settings.reminder_hal_afterlife.enabled and not user_settings.ready_show_hal_afterlife: return add_reaction

        time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'afterlife')
        user_command = await functions.get_game_command(user_settings, 'halloween afterlife')
        reminder_message = user_settings.reminder_hal_afterlife.message.replace('{command}', user_command)
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(user.id, 'afterlife', time_left,
                                        message.channel.id, reminder_message)
        )
        if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True

        if user_settings.ready_popup_mode > ReadyPopupMode.MANUAL:
            ready_embed = await functions.design_embed_ready_list(user, user_settings)
            if ready_embed:
                await message.reply(embed=ready_embed)
            
    return add_reaction


async def update_reminders_from_potions(message: discord.Message, embed_data: Dict, text_displays: list, user: Optional[discord.User],
                                        user_settings: Optional[users.User]) -> bool:
    """Update active reminders when using halloween potions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'and the clocks flinched.', #English, blood potion
        'the clocks gave up,', #English, radioactive potion
        'bulbs are coaching the tree,', #English, bulbs potion
        'soldiers found a second stinger', #English, skull potion
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        if user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_HAL_USE_POTIONS)
            )
            user = user_command_message.author
        if user_settings is None:
            try: 
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction

        cooldown_field = None
        boost_field = None
        for field in message.embeds[0].fields:
            if field.name.lower() == 'cooldowns':
                cooldown_field = field
                continue
            if field.name.lower() == 'current boost':
                boost_field = field
                continue
        if not cooldown_field and not boost_field: return add_reaction

        if boost_field:
            boost_end_match = re.search(r'<t:(\d+?):r>', boost_field.value.lower())
            end_time = datetime.fromtimestamp(int(boost_end_match.group(1)), timezone.utc).replace(microsecond=0)
            current_time = utils.utcnow().replace(microsecond=0)
            time_left = end_time - current_time

            boost_name_match = re.search(r"> (.+?)$", embed_data['title'].lower())
            if not boost_name_match: return add_reaction
            boost_name = boost_name_match.group(1)
            activity = strings.ACTIVITIES_NAME_BOOSTS[boost_name]
            boost_emoji = strings.ACTIVITIES_BOOSTS_EMOJIS.get(activity, '') 
            reminder_message = (
                user_settings.reminder_boosts.message
                .replace('{boost_emoji}', boost_emoji)
                .replace('{boost_name}', boost_name)
                .replace('  ',' ')
            )
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, activity, time_left,
                                                message.channel.id, reminder_message)
            )
            if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True

        if cooldown_field:
            cooldowns = []
            ready_commands = []

            cooldown_names_activities = {
                'hive claim energy': 'hive-energy',
            }

            for line in cooldown_field.value.splitlines():
                activity_match = re.search(r"\*\*(.+?)\*\*", line.lower())
                if activity_match.group(1).lower() in cooldown_names_activities:
                    activity = cooldown_names_activities[activity_match.group(1).lower()]
                else:
                    activity = activity_match.group(1).lower()
                
                timestring_match = re.search(r"\*\* • \*\*`(.+?)`\*\*", line.lower())
                if timestring_match:
                    cooldowns.append([activity, timestring_match.group(1).lower()])
                else:
                    ready_commands.append(activity)
                
            for cooldown in cooldowns:
                cd_activity = cooldown[0]
                cd_timestring = cooldown[1]
                time_left = await functions.parse_timestring_to_timedelta(cd_timestring)
                if cd_activity == 'hive-energy':
                    time_left = time_left + timedelta(seconds=random.randint(0, 300))
                if time_left <= timedelta(seconds=1):
                    ready_commands.append(cd_activity)
                    continue

                try:
                    reminder: reminders.Reminder = await reminders.get_reminder(user.id, activity)
                    await reminder.update(end_time=utils.utcnow() + time_left)
                    if user_settings.reactions_enabled: add_reaction = True
                except exceptions.NoDataFoundError:
                    continue        

            for activity in ready_commands:
                try:
                    reminder: reminders.Reminder = await reminders.get_reminder(user.id, activity)
                    await reminder.delete()
                    if user_settings.reactions_enabled: add_reaction = True
                except exceptions.NoDataFoundError:
                    continue        

            if user_settings.ready_popup_mode > ReadyPopupMode.MANUAL and ready_commands:
                ready_embed = await functions.design_embed_ready_list(user, user_settings)
                if ready_embed:
                    await message.reply(embed=ready_embed)
            
    return add_reaction