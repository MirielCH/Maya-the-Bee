# profile.py

from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import errors, reminders, users
from resources import emojis, exceptions, functions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all profile or stats related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_reminders_from_stats(message, embed_data, user, user_settings))
    return any(return_values)



async def create_reminders_from_stats(message: discord.Message, embed_data: Dict, interaction_user: Optional[discord.User],
                                   user_settings: Optional[users.User]) -> bool:
    """Creates research and upgrade remindesr from "tree stats"

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
    ]
    if any(search_string in embed_data['author']['name'].lower() for search_string in search_strings):
        if embed_data['embed_user'] is not None and interaction_user is not None:
            if interaction_user != embed_data['embed_user'] != interaction_user:
                return add_reaction
        embed_users = []
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_PROFILE_STATS)
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

        # Insecticide & Raid shield boost reminder
        # Store level, xp and rebirth
        level = rebirth = xp = xp_target = -1
        for line in embed_data['field0']['value'].split('\n'):
            if 'insecticide' in line.lower():
                boost_end_match = re.search(r'<t:(\d+?):r>', line.lower())
                activity = 'insecticide'
                if boost_end_match:
                    end_time = datetime.fromtimestamp(int(boost_end_match.group(1)), timezone.utc).replace(microsecond=0)
                    current_time = utils.utcnow().replace(microsecond=0)
                    time_left = end_time - current_time
                    reminder_message = (
                        user_settings.reminder_boosts.message
                        .replace('{boost_emoji}', emojis.INSECTICIDE)
                        .replace('{boost_name}', 'insecticide')
                    )
                    cooldowns.append([activity, time_left, reminder_message])
                else:
                    ready_commands.append(activity)

            elif 'raid shield' in line.lower():
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
                level_match = re.search(r'\) (\d+?)\*\*', line.lower())
                level = int(level_match.group(1))
            elif 'exp:' in line.lower():
                xp_match = re.search(r'\) (.+?)\*\*\/\*\*(.+?)\*\*', line.lower())
                xp = int(xp_match.group(1).replace(',',''))
                xp_target = int(xp_match.group(2).replace(',',''))
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

        # Sweet apple boost
        if 'boost active' in embed_data['description'].lower():
            boost_end_match = re.search(r'<t:(\d+?):r>', embed_data['description'].lower())
            activity = 'sweet-apple'
            if boost_end_match:
                end_time = datetime.fromtimestamp(int(boost_end_match.group(1)), timezone.utc).replace(microsecond=0)
                current_time = utils.utcnow().replace(microsecond=0)
                time_left = end_time - current_time
                reminder_message = (
                    user_settings.reminder_boosts.message
                    .replace('{boost_emoji}', emojis.SWEET_APPLE)
                    .replace('{boost_name}', 'sweet apple')
                )
                cooldowns.append([activity, time_left, reminder_message])
            else:
                ready_commands.append(activity)

        # Research & Upgrade cooldowns
        if embed_data['field3']['value'] != '':
            if user_settings.reminder_research.enabled:
                timestring_match = re.search(r"researching: `(.+?)` remaining", embed_data['field3']['value'].lower())
                if timestring_match:
                    user_command = await functions.get_game_command(user_settings, 'laboratory')
                    reminder_message = user_settings.reminder_research.message.replace('{command}', user_command)
                    time_left = await functions.calculate_time_left_from_timestring(message,
                                                                                    timestring_match.group(1).lower())
                    cooldowns.append(['research', time_left, reminder_message])
                else:
                    ready_commands.append('research')
            if user_settings.reminder_upgrade.enabled:
                timestring_match = re.search(r"upgrading: `(.+?)` remaining", embed_data['field3']['value'].lower())
                if timestring_match:
                    user_command = await functions.get_game_command(user_settings, 'tool')
                    reminder_message = user_settings.reminder_upgrade.message.replace('{command}', user_command)
                    time_left = await functions.calculate_time_left_from_timestring(message,
                                                                                    timestring_match.group(1).lower())
                    cooldowns.append(['upgrade', time_left, reminder_message])
                else:
                    ready_commands.append('upgrade')

        for cooldown in cooldowns:
            cd_activity = cooldown[0]
            cd_time_left = cooldown[1]
            cd_message = cooldown[2]
            if cd_time_left < timedelta(0): continue
            if cd_activity == 'sweet-apple':
                try:
                    active_reminder: reminders.Reminder= await reminders.get_reminder(interaction_user.id, 'sweet-apple')
                    if active_reminder.triggered:
                        await user_settings.update(xp_gain_average=0)
                except exceptions.NoDataFoundError:
                    await user_settings.update(xp_gain_average=0)
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