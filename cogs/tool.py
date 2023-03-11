# tool.py

from datetime import datetime, timedelta, timezone
import re

import discord
from discord import utils
from discord.ext import commands

from cache import messages
from database import errors, reminders, users
from resources import emojis, exceptions, functions, regex, settings


class ToolCog(commands.Cog):
    """Cog that contains the tool detection commands"""
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
            embed_author = icon_url = embed_field_0 = ''
            if embed.author:
                embed_author = embed.author.name
                icon_url = embed.author.icon_url
            embed_description = embed.description if embed.description else ''
            if embed.fields:
                embed_field_0 = embed.fields[0].value

            # Start upgrade
            search_strings = [
                'upgrading to level', #English
            ]
            if any(search_string in embed_description.lower() for search_string in search_strings):
                interaction_user = await functions.get_interaction_user(message)
                embed_users = []
                if interaction_user is None:
                    user_command_message = (
                        await messages.find_message(message.channel.id, regex.COMMAND_TOOL)
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
                if not user_settings.bot_enabled or not user_settings.reminder_upgrade.enabled: return
                user_command = await functions.get_game_command(user_settings, 'tool')
                upgrade_end_match = re.search(r'<t:(\d+?):f>', embed_field_0.lower())
                if not upgrade_end_match:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Upgrade end time not found in tool upgrade message.', message)
                    return
                end_time = datetime.fromtimestamp(int(upgrade_end_match.group(1)), timezone.utc).replace(microsecond=0)
                current_time = utils.utcnow().replace(microsecond=0)
                time_left = end_time - current_time
                if time_left < timedelta(0): return
                reminder_message = user_settings.reminder_upgrade.message.replace('{command}', user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_reminder(interaction_user.id, 'upgrade', time_left,
                                                    message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)

            # Cancel upgrade
            search_strings = [
                'you have been refund', #English
            ]
            if any(search_string in embed_description.lower() for search_string in search_strings):
                user = await functions.get_interaction_user(message)
                if user is None: user = message.mentions[0]
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reminder_upgrade.enabled: return
                try:
                    reminder: reminders.Reminder = await reminders.get_reminder(user.id, 'upgrade')
                    await reminder.delete()
                except exceptions.NoDataFoundError:
                    return
                if user_settings.reactions_enabled:
                    await message.add_reaction(emojis.LOGO)

            # Skip upgrade
            search_strings = [
                'you have skipped the upgrade', #English
            ]
            if any(search_string in embed_description.lower() for search_string in search_strings):
                user = await functions.get_interaction_user(message)
                if user is None:
                    user_name_match = re.search(r"^\*\*(.+?)\*\*, ", embed_description)
                    if user_name_match:
                        user_command_message = (
                            await messages.find_message(message.channel.id, regex.COMMAND_TOOL,
                                                        user_name=user_name_match.group(1))
                        )
                    if not user_name_match or user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in tool skip message.', message)
                        return
                    user = user_command_message.author

                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reminder_upgrade.enabled: return
                try:
                    reminder: reminders.Reminder = await reminders.get_reminder(user.id, 'upgrade')
                    await reminder.delete()
                except exceptions.NoDataFoundError:
                    return
                if user_settings.reactions_enabled:
                    await message.add_reaction(emojis.LOGO)


# Initialization
def setup(bot):
    bot.add_cog(ToolCog(bot))