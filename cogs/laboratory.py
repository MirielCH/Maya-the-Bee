# laboratory.py

from datetime import datetime, timedelta, timezone
import re

import discord
from discord import utils
from discord.ext import commands

from cache import messages
from database import errors, reminders, users
from resources import exceptions, functions, regex, settings


class LaboratoryCog(commands.Cog):
    """Cog that contains the laboratory detection commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, message_before: discord.Message, message_after: discord.Message) -> None:
        """Runs when a message is edited in a channel."""
        if message_before.pinned != message_after.pinned: return
        for row in message_after.components:
            for component in row.children:
                if component.disabled:
                    return
        await self.on_message(message_after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.id not in [settings.GAME_ID, settings.TESTY_ID]: return

        if message.embeds:
            embed = message.embeds[0]
            embed_author = icon_url = embed_field_0_value = embed_field_0_name = ''
            if embed.author:
                embed_author = embed.author.name
                icon_url = embed.author.icon_url
            embed_description = embed.description if embed.description else ''
            if embed.fields:
                embed_field_0_name = embed.fields[0].name
                embed_field_0_value = embed.fields[0].value

            # Store research time from Laboratory overview
            if re.search(r'level \d+ laboratory', embed_description, re.IGNORECASE):
                interaction_user = await functions.get_interaction_user(message)
                embed_users = []
                if interaction_user is None:
                    user_command_message = (
                        await messages.find_message(message.channel.id, regex.COMMAND_LABORATORY)
                    )
                    if user_command_message is None:
                        await functions.add_warning_reaction(message)
                        return
                    interaction_user = user_command_message.author
                user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, icon_url)
                if user_id_match:
                    user_id = int(user_id_match.group(1))
                    embed_users.append(message.guild.get_member(user_id))
                else:
                    embed_users = await functions.get_guild_member_by_name(message.guild, embed_author)
                    if not embed_users:
                        await functions.add_warning_reaction(message)
                        return
                if interaction_user not in embed_users: return
                try:
                    user_settings: users.User = await users.get_user(interaction_user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled: return
                timestring_found = False
                for line in embed_field_0_value.split('\n'):
                    if not 'time needed' in line.lower(): continue
                    timestring_match = re.search('\)\*\* (.+?)$', line)
                    if not timestring_match:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('Timestring not found in laboratory message.', message)
                        return
                    research_time = await functions.calculate_time_left_from_timestring(message, timestring_match.group(1))
                    await user_settings.update(research_time=research_time.total_seconds())
                    timestring_found = True
                    break
                if not timestring_found:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Timestring not found in laboratory message.', message)
                    return

            # Research start
            search_strings = [
                'you have started a research', #English
            ]
            if any(search_string in embed_description.lower() for search_string in search_strings):
                user = await functions.get_interaction_user(message)
                if user is None:
                    user_name_match = re.search(regex.NAME_FROM_MESSAGE_START, embed_description)
                    if user_name_match:
                        user_name = user_name_match.group(1)
                        user_command_message = (
                            await messages.find_message(message.channel.id, regex.COMMAND_LABORATORY, user_name=user_name)
                        )
                    if not user_name_match or user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in research start message.', message)
                        return
                    user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reminder_research.enabled: return
                user_command = await functions.get_game_command(user_settings, 'laboratory')
                if user_settings.research_time == 0:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Research time is 0 for some reason.', message)
                    return
                time_left = timedelta(seconds=user_settings.research_time)
                reminder_message = user_settings.reminder_research.message.replace('{command}', user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_reminder(user.id, 'research', time_left,
                                                    message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)

            # Research in progress
            search_strings = [
                'researching: tier', #English
            ]
            if any(search_string in embed_field_0_name.lower() for search_string in search_strings):
                interaction_user = await functions.get_interaction_user(message)
                embed_users = []
                if interaction_user is None:
                    user_command_message = (
                        await messages.find_message(message.channel.id, regex.COMMAND_LABORATORY)
                    )
                    if user_command_message is None:
                        await functions.add_warning_reaction(message)
                        return
                    interaction_user = user_command_message.author
                user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, icon_url)
                if user_id_match:
                    user_id = int(user_id_match.group(1))
                    embed_users.append(message.guild.get_member(user_id))
                else:
                    embed_users = await functions.get_guild_member_by_name(message.guild, embed_author)
                    if not embed_users:
                        await functions.add_warning_reaction(message)
                        return
                if interaction_user not in embed_users: return
                try:
                    user_settings: users.User = await users.get_user(interaction_user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reminder_research.enabled: return
                user_command = await functions.get_game_command(user_settings, 'laboratory')
                research_end_match = re.search(r'<t:(\d+?):f>', embed_field_0_value.lower())
                if not research_end_match:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Research end time not found in research progress message.', message)
                    return
                end_time = datetime.fromtimestamp(int(research_end_match.group(1)), timezone.utc).replace(microsecond=0)
                current_time = utils.utcnow().replace(microsecond=0)
                time_left = end_time - current_time
                if time_left < timedelta(0): return
                reminder_message = user_settings.reminder_research.message.replace('{command}', user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_reminder(interaction_user.id, 'research', time_left,
                                                    message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)


# Initialization
def setup(bot):
    bot.add_cog(LaboratoryCog(bot))