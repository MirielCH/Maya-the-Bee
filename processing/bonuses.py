# bonuses.py

from datetime import timedelta
import re
from typing import Dict, Optional

import discord

from cache import messages
from database import errors, reminders, users
from resources import emojis, exceptions, functions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all /bonuses related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_reminders(message, embed_data, user, user_settings))
    return any(return_values)



async def create_reminders(message: discord.Message, embed_data: Dict, interaction_user: Optional[discord.User],
                                   user_settings: Optional[users.User]) -> bool:
    """Creates boost remindesr from /bonuses

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = updated_reminder = False
    cooldowns = []
    ready_commands = []
    search_strings = [
        'buffs, bonuses and reductions', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings):
        if embed_data['embed_user'] is not None and interaction_user is not None:
            if interaction_user != embed_data['embed_user'] != interaction_user:
                return add_reaction
        embed_users = []
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_BONUSES)
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
            if not user_settings.bot_enabled or not user_settings.reminder_boosts.enabled: return add_reaction
        
        activity = ''
        boost_name = ''
        boost_fields = f"{embed_data['field1']['value']}\n{embed_data['field2']['value']}"
        for line in boost_fields.split('\n'):
            for boost_name in strings.ACTIVITIES_NAME_BOOSTS.keys():
                if boost_name in line.lower():
                    activity = strings.ACTIVITIES_NAME_BOOSTS[boost_name]
                    break
            timestring_match = re.search(r"ends in \*\*(.+?)\*\*", line.lower())
            if timestring_match:
                time_left = await functions.calculate_time_left_from_timestring(message,
                                                                                timestring_match.group(1).lower())
                reminder_message = (
                    user_settings.reminder_boosts.message
                    .replace('{boost_emoji}', strings.ACTIVITIES_BOOSTS_EMOJIS[activity])
                    .replace('{boost_name}', boost_name)
                )
                cooldowns.append([activity, time_left, reminder_message])
            else:
                ready_commands.append(activity)

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
                    f'Had an error in the bonuses, deleting the reminder with activity "{activity}".',
                    message
                )
        if updated_reminder and user_settings.reactions_enabled: add_reaction = True
    return add_reaction