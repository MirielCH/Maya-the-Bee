# easter.py

import re
import sqlite3
from typing import Dict, Optional

import discord
from discord import utils

from cache import messages
from database import bunnies, users
from resources import emojis, exceptions, functions, regex, settings, strings, logs


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all incubator related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await call_bunny_helper(message, embed_data, user, user_settings))
    return_values.append(await send_notification_on_catch(message, embed_data, user, user_settings))
    return_values.append(await update_bunnies_from_hutch(message, embed_data, user, user_settings))
    return_values.append(await update_bunny_from_fusion(message, embed_data, user, user_settings))
    return_values.append(await update_rebirth_from_calendar(message, embed_data, user, user_settings))
    return any(return_values)


async def call_bunny_helper(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                            user_settings: Optional[users.User]) -> bool:
    """Shows the bunny helper when encountering an new bunny.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'bunny is approaching to your tree', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_PRUNE,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try: 
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.helper_bunny_enabled: return add_reaction

        fertility = embed_data['field0']['value'].lower().count(':fertility:')
        epicness = embed_data['field0']['value'].lower().count(':epicness:')

        try:
            user_bunnies = await bunnies.get_bunnies_by_user_id(user.id)
        except exceptions.NoDataFoundError:
            if user_settings.last_bunny_update is not None:
                await user_settings.update(last_bunny_update=None)
            return add_reaction

        if len(user_bunnies) < 9:
            return add_reaction
        
        if user_settings.last_bunny_update is None:
            await message.reply(
                f"My bunny data is outdated.\n"
                f"➜ Use {strings.SLASH_COMMANDS['easter hutch']} before the next prune to update it!\n"
            )
            return add_reaction

        replacable_bunnies = []
        fusable_bunnies = []
        recommendation = ''
        recommendation_stats_improvement = (0, 0)
        maxed_bunnies = 0

        for bunny in user_bunnies:
            if bunny.epicness >= 5 and bunny.fertility >= 5:
                maxed_bunnies += 1
                continue
            if bunny.epicness < epicness:
                replacable_bunnies.append(bunny)
            if bunny.epicness == epicness and bunny.fertility < fertility:
                replacable_bunnies.append(bunny)
            if bunny.fertility == fertility:
                fusable_bunnies.append(bunny)

        if maxed_bunnies >= 9:
            return add_reaction
        
        field_replacable_bunnies = ''
        for bunny in replacable_bunnies:
            fertility_improvement = fertility - bunny.fertility
            epicness_improvement = epicness - bunny.epicness
            if epicness_improvement > recommendation_stats_improvement[1]:
                recommendation = f"Replace **{bunny.name}**"
                recommendation_stats_improvement = (fertility_improvement, epicness_improvement)
            elif epicness_improvement == recommendation_stats_improvement[1] and fertility_improvement > recommendation_stats_improvement[0]:
                recommendation = f"Replace **{bunny.name}**"
                recommendation_stats_improvement = (fertility_improvement, epicness_improvement)
            field_replacable_bunnies = (
                f'{field_replacable_bunnies}\n- **{bunny.name}** '
                f'`{fertility_improvement:+}`{emojis.FERTILITY} `{epicness_improvement:+}`{emojis.EPICNESS}'
            )
        if not field_replacable_bunnies:
            field_replacable_bunnies = '- None'

        field_fusable_bunnies = ''
        for bunny in fusable_bunnies:
            if fertility== 5:
                fertility_improvement = 1 - bunny.fertility
                epicness_improvement = 1
            else:
                fertility_improvement = 1
                epicness_improvement = max(epicness, bunny.epicness) - bunny.epicness
            if epicness_improvement > recommendation_stats_improvement[1]:
                recommendation = f"Fuse with **{bunny.name}**"
                recommendation_stats_improvement = (fertility_improvement, epicness_improvement)
            elif epicness_improvement == recommendation_stats_improvement[1] and fertility_improvement > recommendation_stats_improvement[0]:
                recommendation = f"Fuse with **{bunny.name}**"
                recommendation_stats_improvement = (fertility_improvement, epicness_improvement)
            field_fusable_bunnies = (
                f'{field_fusable_bunnies}\n- **{bunny.name}** '
                f'`{fertility_improvement:+}`{emojis.FERTILITY} `{epicness_improvement:+}`{emojis.EPICNESS}'
            )
        if not field_fusable_bunnies:
            field_fusable_bunnies = '- None'

        if not recommendation:
            recommendation = 'Release'

        embed = discord.Embed(
            color = settings.EMBED_COLOR,
            title = f'{emojis.BUNNY} Bunny detected!',
        )
        embed.add_field(name="Replaceable bunnies", value=field_replacable_bunnies, inline=False)
        embed.add_field(name="Fusable bunnies", value=field_fusable_bunnies, inline=False)
        embed.add_field(name="Recommendation", value=f'- {recommendation}', inline=False)
        embed.set_footer(text="Make sure to check the stats yourself before making a decision.")
        if not user_settings.dnd_mode_enabled:
            message_content = user.mention
        else:
            message_content = None
        await message.reply(content=message_content, embed=embed)

        # Debug double replies
        if user_settings.user_id in (350875703580819457, 347400890149240842, 151096364867125249):
            logs.logger.info(
                f'\nDouble post debugging for user {user_settings.user_id}.\n'
                f'Reply sent: {utils.utcnow()}\n'
                f'Message ID: {message.id}\n'
                f'Message created at: {message.created_at}\n'
                f'Message edited at: {message.edited_at}\n'
                f'Message content: {message.content}\n'
                f'Message embed: {str(embed_data)}\n'
                f'Message components: {str(message.components)}\n'
                f'Message nonce: {message.nonce}\n'
            )
            
    return add_reaction


async def update_bunnies_from_hutch(message: discord.Message, embed_data: Dict, interaction_user: Optional[discord.User],
                                    user_settings: Optional[users.User]) -> bool:
    """Updates bunnies in the database from the hutch.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'bunny hutch', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings):
        if embed_data['embed_user'] is not None and interaction_user is not None:
            if interaction_user != embed_data['embed_user']:
                return add_reaction
        embed_users = []
        if interaction_user is None:
            user_command_message = (
                await messages.find_message(message.channel.id, regex.COMMAND_EASTER_HUTCH)
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
        if not user_settings.bot_enabled or not user_settings.helper_bunny_enabled: return add_reaction

        try:
            user_bunnies = await bunnies.get_bunnies_by_user_id(interaction_user.id)
            for bunny in user_bunnies:
                await bunny.delete()
        except exceptions.NoDataFoundError:
            pass
        
        bunnies_updated = False
        for field in message.embeds[0].fields:
            if not 'fertility' in field.value.lower(): continue
            fertility = field.value.lower().count(':fertility:')
            epicness = field.value.lower().count(':epicness:')

            bunny: bunnies.Bunny = (
                await bunnies.insert_bunny(interaction_user.id, field.name, epicness,
                                           fertility)
            )
            if bunny.record_exists:
                bunnies_updated = True
                if user_settings.reactions_enabled:
                    add_reaction = True

        if bunnies_updated:
            await user_settings.update(last_bunny_update=utils.utcnow())
    
    return add_reaction


async def update_bunny_from_fusion(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                   user_settings: Optional[users.User]) -> bool:
    """Updates a bunny in the database from the fusion result embed.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'you fused', #English
    ]
    if (any(search_string in embed_data['description'].lower() for search_string in search_strings)
        and (':fertility:' in embed_data['field0']['value'].lower()) or 'crack crock' in embed_data['field0']['name'].lower()):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_PRUNE,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try: 
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.helper_bunny_enabled: return add_reaction

        bunny_names_match = re.search(r'\*\*(.+?)\*\* with \*\*(.+?)\*\*', embed_data['description'])
        new_bunny_name, old_bunny_name = bunny_names_match.groups()
        
        try:
            bunny = await bunnies.get_bunny(user.id, old_bunny_name)
        except exceptions.NoDataFoundError:
            await user_settings.update(last_bunny_update=None)
            return add_reaction

        if ':fertility:' in embed_data['field0']['value'].lower():
            fertility = embed_data['field0']['value'].lower().count(':fertility:')
            epicness = embed_data['field0']['value'].lower().count(':epicness:')
            try:
                await bunny.update(name=new_bunny_name, fertility=fertility, epicness=epicness)
            except sqlite3.Error:
                await user_settings.update(last_bunny_update=None)
                await message.reply(
                f"➜ Please use {strings.SLASH_COMMANDS['easter hutch']} to update my bunny data!\n"
                )
                return add_reaction
        else:
            await user_settings.update(last_bunny_update=None)
            await message.reply(
                f"➜ Please use {strings.SLASH_COMMANDS['easter hutch']} to update my bunny data!\n"
            )
            
        if user_settings.reactions_enabled and not bunny.record_exists:
            add_reaction = True
            
    return add_reaction


async def send_notification_on_catch(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                     user_settings: Optional[users.User]) -> bool:
    """Tells the user to manually update when a bunny gets caught or replaced.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'approach successful', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_PRUNE,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try: 
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled or not user_settings.helper_bunny_enabled: return add_reaction

        await user_settings.update(last_bunny_update=None)
        await message.reply(
            f"➜ Please use {strings.SLASH_COMMANDS['easter hutch']} to update my bunny data!\n"
        )
            
    return add_reaction


async def update_rebirth_from_calendar(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                       user_settings: Optional[users.User]) -> bool:
    """Update rebirth count from the easter calendar.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'you have claimed day', #English
    ]
    if (any(search_string in embed_data['description'].lower() for search_string in search_strings)
        and 'easter calendar' in embed_data['description'].lower()):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_EASTER_CALENDAR,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try: 
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction

        rebirth_amount = await functions.get_inventory_item(embed_data['field0']['value'], 'rebirth')
        if rebirth_amount > 0:
            await user_settings.update(rebirth=user_settings.rebirth + rebirth_amount)
            add_reaction = True
            
    return add_reaction