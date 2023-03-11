# profile.py

from datetime import timedelta
import re
from typing import Dict, Optional

import discord
from datetime import timedelta

from cache import messages
from database import errors, reminders, users
from resources import exceptions, functions, regex, strings


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
        if embed_data['field3']['value'] != '':
            cooldowns = []
            ready_commands = []
            if user_settings.reminder_research.enabled:
                timestring_match = re.search(r"researching: `(.+?)` remaining", embed_data['field3']['value'].lower())
                if timestring_match:
                    user_command = await functions.get_game_command(user_settings, 'laboratory')
                    reminder_message = user_settings.reminder_research.message.replace('{command}', user_command)
                    cooldowns.append(['research', timestring_match.group(1).lower(), reminder_message])
                else:
                    ready_commands.append('research')
            if user_settings.reminder_upgrade.enabled:
                timestring_match = re.search(r"upgrading: `(.+?)` remaining", embed_data['field3']['value'].lower())
                if timestring_match:
                    user_command = await functions.get_game_command(user_settings, 'tool')
                    reminder_message = user_settings.reminder_upgrade.message.replace('{command}', user_command)
                    cooldowns.append(['upgrade', timestring_match.group(1).lower(), reminder_message])
                else:
                    ready_commands.append('upgrade')

            for cooldown in cooldowns:
                cd_activity = cooldown[0]
                cd_timestring = cooldown[1]
                cd_message = cooldown[2]
                time_left = await functions.parse_timestring_to_timedelta(cd_timestring)
                if time_left < timedelta(0): continue
                reminder: reminders.Reminder = (
                    await reminders.insert_reminder(interaction_user.id, cd_activity, time_left,
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