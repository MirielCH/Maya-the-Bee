# detection.py
"""Collects and parses Elder Arborium messages"""

from datetime import timedelta
import re
from typing import Dict, Union

import discord
from discord import utils
from discord.ext import commands

from database import users
from processing import bonuses, calendar, easter, chests, clean, cooldowns, daily, fusion, halloween, hive, incubator, inventory
from processing import laboratory, patreon, profile, prune, quests, raid, rebirth, shop, tool, tracking, use, vote
from resources import exceptions, functions, logs, regex, settings

seen_messages = {}  

class DetectionCog(commands.Cog):
    """Cog that contains the detection events"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, message_before: discord.Message, message_after: discord.Message) -> None:
        """Runs when a message is edited in a channel."""
        if message_after.author.id not in [settings.TREE_ID, settings.TREE_BETA_ID, settings.TESTY_ID]: return

        embed_data_before = await parse_embed(message_before)
        embed_data = await parse_embed(message_after)
        text_displays = await functions.parse_text_displays(message_after)
        if (message_before.content == message_after.content and embed_data_before == embed_data
            and message_before.components == message_after.components): return
        if await check_edited_message_never_allowed(message_before, message_after, embed_data, text_displays): return
        if await check_edited_message_always_allowed(message_before, message_after, embed_data, text_displays):
            await self.on_message(message_after)
            return
        if message_before.components and not message_after.components: return
        if await check_message_for_active_components(message_after):
            await self.on_message(message_after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.id not in [settings.TREE_ID, settings.TREE_BETA_ID, settings.TESTY_ID]: return
        user_settings = None
        embed_data = await parse_embed(message)
        text_displays = await functions.parse_text_displays(message)
        
        # Duplicate message handling
        if (message.id, message.content, str(embed_data), str(message.components)) in seen_messages:
            if 'a bunny is approaching!' in embed_data['title'].lower():
                logs.logger.info(
                    f'\nDuplicate message detected and ignored.\n'
                    f'Message ID: {message.id}\n'
                    f'Message created at: {message.created_at}\n'
                    f'Message edited at: {message.edited_at}\n'
                    f'Message content: {message.content}\n'
                    f'Message embed: {str(embed_data)}\n'
                    f'Message components: {str(message.components)}\n'
                    f'Message nonce: {message.nonce}\n'
                )
            return
        expired_message_keys = [seen_key for seen_key, seen_time in seen_messages.items() if utils.utcnow() - seen_time > timedelta(minutes=1)]
        for seen_key in expired_message_keys:
            del seen_messages[seen_key]
        if len(seen_messages) > 10_000:
            seen_messages.clear()
            logs.logger.info('Cleared message cache to prevent memory issues. This should not happen often.')
        seen_messages[(message.id, message.content, str(embed_data), str(message.components))] = utils.utcnow()

        embed_data['embed_user'] = None
        embed_data['embed_user_settings'] = None
        interaction_user = await functions.get_interaction_user(message)
        user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, embed_data['author']['icon_url'])
        if user_id_match:
            embed_data['embed_user'] = message.guild.get_member(int(user_id_match.group(1)))
        if interaction_user is not None:
            try:
                user_settings: users.User = await users.get_user(interaction_user.id)
            except exceptions.FirstTimeUserError:
                if not 'queen bees fusion' in embed_data['author']['name'].lower(): return
            if user_settings is not None:
                if not user_settings.bot_enabled: return
        if embed_data['embed_user'] is not None:
            if interaction_user is not None and embed_data['embed_user'] == interaction_user:
                embed_user_settings = user_settings
            else:
                try:
                    embed_user_settings: users.User = await users.get_user(embed_data['embed_user'].id)
                except exceptions.FirstTimeUserError:
                    embed_user_settings = None
            embed_data['embed_user_settings'] = embed_user_settings
        return_values = []

        # Bonuses
        add_reaction = await bonuses.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)

        # Bunnies
        add_reaction = await easter.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)

         # Calendar
        add_reaction = await calendar.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            

        # Cooldowns
        add_reaction = await cooldowns.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Chests
        add_reaction = await chests.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Clean
        add_reaction = await clean.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Daily
        add_reaction = await daily.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)

        # Fusion
        add_reaction = await fusion.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)

        # Halloween
        add_reaction = await halloween.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
                
        # Hive
        add_reaction = await hive.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Incubator
        add_reaction = await incubator.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
        
        # Inventory
        add_reaction = await inventory.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Prune
        add_reaction = await prune.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Laboratory
        add_reaction = await laboratory.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Patreon
        add_reaction = await patreon.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Profile & Stats
        add_reaction = await profile.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)

        # Quests
        add_reaction = await quests.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Raid
        add_reaction = await raid.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Rebirth
        add_reaction = await rebirth.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Tool upgrade
        add_reaction = await tool.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Tracking
        add_reaction = await tracking.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)

        # Use items
        add_reaction = await use.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Vote
        add_reaction = await vote.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)
            
        # Shop
        add_reaction = await shop.process_message(message, embed_data, text_displays, interaction_user, user_settings)
        return_values.append(add_reaction)

        if any(return_values): await functions.add_logo_reaction(message)

# Initialization
def setup(bot):
    bot.add_cog(DetectionCog(bot))


# Functions
async def parse_embed(message: discord.Message) -> Dict[str, str]:
    """Parses all data from an embed into a dictionary.
    All keys are guaranteed to exist and have an empty string as value if not set in the embed.
    """    
    embed_data = {
        'author': {'icon_url': '', 'name': ''},
        'description': '',
        'field0': {'name': '', 'value': ''},
        'field1': {'name': '', 'value': ''},
        'field2': {'name': '', 'value': ''},
        'field3': {'name': '', 'value': ''},
        'field4': {'name': '', 'value': ''},
        'field5': {'name': '', 'value': ''},
        'footer': {'icon_url': '', 'text': ''},
        'title': '',
    }
    if message.embeds:
        embed = message.embeds[0]
        if embed.author:
            if embed.author.icon_url is not None:
                embed_data['author']['icon_url'] = embed.author.icon_url
            if embed.author.name is not None:
                embed_data['author']['name'] = embed.author.name
        if embed.description is not None:
            embed_data['description'] = embed.description
        if embed.fields:
            try:
                embed_data['field0']['name'] = embed.fields[0].name
                embed_data['field0']['value'] = embed.fields[0].value
            except IndexError:
                pass
            try:
                embed_data['field1']['name'] = embed.fields[1].name
                embed_data['field1']['value'] = embed.fields[1].value
            except IndexError:
                pass
            try:
                embed_data['field2']['name'] = embed.fields[2].name
                embed_data['field2']['value'] = embed.fields[2].value
            except IndexError:
                pass
            try:
                embed_data['field3']['name'] = embed.fields[3].name
                embed_data['field3']['value'] = embed.fields[3].value
            except IndexError:
                pass
            try:
                embed_data['field4']['name'] = embed.fields[4].name
                embed_data['field4']['value'] = embed.fields[4].value
            except IndexError:
                pass
            try:
                embed_data['field5']['name'] = embed.fields[5].name
                embed_data['field5']['value'] = embed.fields[5].value
            except IndexError:
                pass
        if embed.footer is not None:
            if embed.footer.icon_url is not None:
                embed_data['footer']['icon_url'] = embed.footer.icon_url
            if embed.footer.text is not None:
                embed_data['footer']['text'] = embed.footer.text
        if embed.title is not None:
            embed_data['title'] = embed.title
    return embed_data


async def check_message_for_active_components(message: discord.Message) -> Union[bool, None]:
    """Checks if the message has any active components.
    
    Returns
    -------
    - False if all components are disabled
    - True if at least one component is not disabled OR the message doesn't have any components
    """
    if not message.components: return True
    active_component = False
    for row in message.components:
        for component in getattr(row, 'children', []):
            if not component.disabled:
                active_component = True
                break
    return active_component


async def check_edited_message_always_allowed(message_before: discord.Message,
                                             message_after: discord.Message, embed_data: Dict, text_displays: list) -> Union[bool, None]:
    """Check if the edited message should be allowed to process regardless of its components.
    
    Returns
    -------
    - True if allowed
    - False if not affected by this check
    """
    search_strings = [
        'captcha', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings):
        captcha_solved = False
        for component in message_after.components[0].children:
            if component.style == discord.ButtonStyle.success:
                captcha_solved = True
                break
        return captcha_solved
    search_strings = [
        'queen bees fusion', #English
    ]
    if any(search_string in embed_data['author']['name'].lower() for search_string in search_strings):
        return True
    search_strings = [
        'chests inventory', #English
    ]
    if any(search_string in embed_data['field1']['name'].lower() for search_string in search_strings):
        return True
    search_strings = [
        'chests inventory', #English
    ]
    if any(search_string in embed_data['field1']['name'].lower() for search_string in search_strings):
        return True
    search_strings = [
        '** used rebirth!', #English
    ]
    if any(search_string in embed_data['description'].lower() for search_string in search_strings):
        return True
    search_strings = [
        'contributing on defeating the spooky biome hives!', #English
    ]
    if any(search_string in text_display.lower() for text_display in text_displays for search_string in search_strings):
        return True
    return False


async def check_edited_message_never_allowed(message_before: discord.Message,
                                             message_after: discord.Message, embed_data: Dict, text_displays: list) -> Union[bool, None]:
    """Check if the edited message should never be allowed to process.
    
    Returns
    -------
    - True if never allowed
    - False if not affected by this check
    """
    if message_before.pinned != message_after.pinned: return True
    return False