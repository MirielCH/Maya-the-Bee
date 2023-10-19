# shop.py

from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import reminders, users
from resources import exceptions, functions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all /shop related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await create_reminder_on_buying_boost(message, embed_data, user, user_settings))
    return any(return_values)


async def create_reminder_on_buying_boost(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                         user_settings: Optional[users.User]) -> bool:
    """Create a reminder when a boost is bought.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'boost activated!', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_SHOP,
                                                user_name=embed_data['author']['name'])
                )
                if user_command_message is not None:
                    user = user_command_message.author
                else:
                    embed_users = await functions.get_guild_member_by_name(message.guild, embed_data['author']['name'])
                    if len(embed_users) == 1:
                        user = embed_users[0]
                    else:
                        return add_reaction
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.reminder_boosts.enabled: return add_reaction
        boost_name_match = re.search(r'bought a \*\*(.+?)\*\*!', embed_data['description'].lower()) 
        boost_name = boost_name_match.group(1)
        activity = strings.ACTIVITIES_NAME_BOOSTS[boost_name]
        boost_end_match = re.search(r'<t:(\d+?):r>', embed_data['description'].lower())
        end_time = datetime.fromtimestamp(int(boost_end_match.group(1)), timezone.utc).replace(microsecond=0)
        current_time = utils.utcnow().replace(microsecond=0)
        time_left = end_time - current_time
        if time_left < timedelta(0): return add_reaction
        reminder_message = (
            user_settings.reminder_boosts.message
            .replace('{boost_emoji}', strings.ACTIVITIES_BOOSTS_EMOJIS.get(activity, ''))
            .replace('{boost_name}', boost_name)
            .replace('  ',' ')
        )
        try:
            active_reminder: reminders.Reminder= await reminders.get_reminder(user.id, activity)
            if active_reminder.triggered:
                await user_settings.update(xp_gain_average=0)
        except exceptions.NoDataFoundError:
            await user_settings.update(xp_gain_average=0)
        reminder: reminders.Reminder = (
            await reminders.insert_reminder(user.id, activity, time_left,
                                            message.channel.id, reminder_message)
        )
        if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    return add_reaction