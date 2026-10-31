# profile.py

from datetime import timedelta
import re
from typing import Dict, Optional

import discord

from cache import messages
from database import errors, reminders, users
from resources import emojis, exceptions, functions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, text_displays: list, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all profile or stats related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_reminders_from_stats(message, embed_data, text_displays, user, user_settings))
    return any(return_values)



async def create_reminders_from_stats(message: discord.Message, embed_data: Dict, text_displays: list, interaction_user: Optional[discord.User],
                                      user_settings: Optional[users.User]) -> bool:
    """Creates research and upgrade reminders from "tree stats" and "tree profile"

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = updated_reminder = False
    cooldowns = []
    ready_commands = []
    search_strings = [
        '\'s tree', #English
        '\'s profile', #English
    ]
    if (any(search_string in embed_data['author']['name'].lower() for search_string in search_strings)
        or any(search_string in text_display.lower() for text_display in text_displays for search_string in search_strings)):
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_PROFILE_STATS)
            )
            interaction_user = user_command_message.author
        user_name = ''
        for text_display in text_displays:    
            user_name_match = re.search(r'### (.+?)\'s profile', text_display)
            if user_name_match:
                user_name = user_name_match.group(1)
                break
        if user_name != interaction_user.name: return add_reaction
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(interaction_user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction

        # Raid shield boost reminder
        # Store level, xp and rebirth
        level = rebirth = xp = xp_target = -1
        text_display_statistics = ''
        for text_display in text_displays:
            if 'statistics' in text_display.lower():
                text_display_statistics = text_display
                break
        for line in text_display_statistics.split('\n'):
            if 'raid shield' in line.lower():
                timestring_match = re.search(r"\*\*`(.+?)`\*\*", line.lower())
                activity = 'raid-shield'
                if timestring_match:
                    time_left = await functions.calculate_time_left_from_timestring(message,
                                                                                    timestring_match.group(1).lower())
                    reminder_message = (
                        user_settings.reminder_boosts.message
                        .replace('{boost_emoji}', emojis.BOOST_RAID_SHIELD)
                        .replace('{boost_name}', 'raid shield')
                    )
                    cooldowns.append([activity, time_left, reminder_message])
                else:
                    ready_commands.append(activity)

            elif 'level:' in line.lower():
                level_match = re.search(r'\) (.+?)\*\*', line.lower())
                level = int(re.sub(r'\D', '', level_match.group(1)))
            elif 'exp:' in line.lower():
                xp_match = re.search(r'\) (.+?)\*\*\/\*\*(.+?)\*\*', line.lower())
                xp = int(re.sub(r'\D', '', xp_match.group(1)))
                xp_target = int(re.sub(r'\D', '', xp_match.group(2)))
            elif 'rebirths:' in line.lower():
                rebirth_match = re.search(r'\) (\d+?)\*\*', line.lower())
                rebirth = int(rebirth_match.group(1))
        if level == -1 or rebirth == -1 or xp == -1 or xp_target == -1:
            await functions.add_warning_reaction(message)
            await errors.log_error(
                f'Unable to detect level, rebirth, xp or xp target\n'
                f'Level: {level}, Rebirth: {rebirth}, XP: {xp}, XP target: {xp_target}',
                message
            )
        await user_settings.update(level=level, rebirth=rebirth, xp=xp, xp_target=xp_target)
        if user_settings.reactions_enabled: add_reaction = True

        for cooldown in cooldowns:
            cd_activity = cooldown[0]
            cd_time_left = cooldown[1]
            cd_message = cooldown[2]
            if cd_time_left < timedelta(0): continue
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(interaction_user.id, cd_activity, cd_time_left,
                                                message.channel.id, cd_message)
            )
            if not reminder.record_exists:
                await message.channel.send(strings.MSG_ERROR)
                return add_reaction
            updated_reminder = True
        for activity in ready_commands:
            try:
                reminder: reminders.Reminder = await reminders.get_reminder(interaction_user.id, activity)
            except exceptions.NoDataFoundError:
                continue
            await reminder.delete()
            if reminder.record_exists:
                await functions.add_warning_reaction(message)
                await errors.log_error(
                    f'Had an error in the profile, deleting the reminder with activity "{activity}".',
                    message
                )
        if updated_reminder and user_settings.reactions_enabled: add_reaction = True
    return add_reaction