# chests.py

import asyncio
import re
from typing import Dict, Optional

import discord

from cache import messages
from database import reminders, users
from resources import emojis, exceptions, functions, regex, settings, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all chests related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await call_context_helper_on_chest_open(message, embed_data, user, user_settings))
    return_values.append(await create_reminder(message, embed_data, user, user_settings))
    return any(return_values)


async def call_context_helper_on_chest_open(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                              user_settings: Optional[users.User]) -> bool:
    """Call the context helper after opening a chest

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings_title = [
        'chest opened!', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings_title):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_CHESTS,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try: 
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction
        embeds = []
        if user_settings.alert_nugget_enabled:
            dropped_nuggets = {}
            nugget_wooden_match = re.search(r'`(.+?)`.+?\*\*wooden nugget', embed_data['field0']['value'].lower())
            nugget_copper_match = re.search(r'`(.+?)`.+?\*\*copper nugget', embed_data['field0']['value'].lower())
            nugget_silver_match = re.search(r'`(.+?)`.+?\*\*silver nugget', embed_data['field0']['value'].lower())
            nugget_golden_match = re.search(r'`(.+?)`.+?\*\*golden nugget', embed_data['field0']['value'].lower())
            nugget_diamond_match = re.search(r'`(.+?)`.+?\*\*diamond nugget', embed_data['field0']['value'].lower())
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
                            f'{amount:,} {strings.NUGGETS[name]} {name} nuggets'
                        )
                if nuggets_found:
                    if user_settings.alert_nugget_dm:
                        asyncio.ensure_future(user.send(
                            f'**Nuggets found!**\n'
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
                        embeds.insert(0, embed)
                        await message.reply(user.mention, embed=embed)
        if user_settings.helper_context_enabled and 'chip' in embed_data['field0']['value'].lower():
            await message.reply(
                f"➜ {strings.SLASH_COMMANDS['chips fusion']}\n"
                f"➜ {strings.SLASH_COMMANDS['chips show']}\n"
            )
    return add_reaction


async def create_reminder(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Creates a reminder on /chests

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'chests inventory', #English
    ]
    if any(search_string in embed_data['field1']['name'].lower() for search_string in search_strings) and message.components:
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_CHESTS,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.reminder_chests.enabled: return add_reaction
        user_command = await functions.get_game_command(user_settings, 'chests')
        regex_timestring = re.compile(r'\.\.\. \((.+?)\)')
        for index, button in enumerate(message.components[0].children):
            activity = f'chest-{index + 1}'
            if button.emoji is None or button.label.lower() in ('empty slot', 'open'):
                try:
                    reminder = await reminders.get_reminder(user.id, activity)
                    await reminder.delete()
                except exceptions.NoDataFoundError:
                    pass
                continue
            if 'silver' in button.emoji.name:
                chest_type = 'silver'
                chest_emoji = emojis.CHEST_SILVER
            elif 'gold' in button.emoji.name:
                chest_type = 'golden'
                chest_emoji = emojis.CHEST_GOLDEN
            elif 'pumpkin' in button.emoji.name:
                chest_type = 'pumpkin'
                chest_emoji = emojis.PUMPKIN
            else:
                chest_type = 'wooden'
                chest_emoji = emojis.CHEST_WOODEN
            timestring_match = re.search(regex_timestring, button.label.lower())
            if not timestring_match: return add_reaction
            reminder_message = (
                user_settings.reminder_chests.message
                .replace('{command}', user_command)
                .replace('{chest_emoji}', chest_emoji)
                .replace('{chest_type}', chest_type)
            )
            time_left = await functions.parse_timestring_to_timedelta(timestring_match.group(1).lower())
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, activity, time_left,
                                                message.channel.id, reminder_message)
            )
            if user_settings.reactions_enabled and reminder.record_exists: add_reaction = True
    return add_reaction