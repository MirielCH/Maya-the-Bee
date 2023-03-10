# fusion.py

from datetime import timedelta
import re

import discord
from discord.ext import commands

from cache import messages
from database import errors, reminders, users
from resources import emojis, exceptions, functions, regex, settings


class FusionCog(commands.Cog):
    """Cog that contains the fusion detection commands"""
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
            embed_field_0_name = embed_field_0_value = ''
            if embed.fields:
                embed_field_0_name = embed.fields[0].name
                embed_field_0_value = embed.fields[0].value

            # Fusion
            search_strings = [
                'fusion results', #English
            ]
            if any(search_string in embed_field_0_name.lower() for search_string in search_strings):
                user1 = await functions.get_interaction_user(message)
                user2 = None
                add_reaction = False
                fusion_users = embed_field_0_value.split('\n')
                regex_user_name = re.compile(r'> \*\*(.+?)\*\*\'s')
                user1_name_match = re.search(regex_user_name, fusion_users[0])
                user2_name_match = re.search(regex_user_name, fusion_users[1])
                if not user1_name_match or not user2_name_match:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('User names not found in fusion message.', message)
                    return
                if user1 is None:
                    user_command_message = (
                        await messages.find_message(message.channel.id, regex.COMMAND_FUSION,
                                                    user_name=user1_name_match.group(1))
                    )
                    if user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User 1 not found in fusion message.', message)
                        return
                    user1 = user_command_message.author
                    if user_command_message.mentions:
                        user2 = user_command_message.mentions[0]
                if user2 is None:
                    guild_members = await functions.get_guild_member_by_name(message.guild, user2_name_match.group(1))
                    if len(guild_members) == 1:
                        user2 = guild_members[0]
                try:
                    user1_settings: users.User = await users.get_user(user1.id)
                except exceptions.FirstTimeUserError:
                    user1_settings = None
                if user2 is not None:
                    try:
                        user2_settings: users.User = await users.get_user(user2.id)
                    except exceptions.FirstTimeUserError:
                        user2_settings = None
                if user1_settings is not None:
                    if user1_settings.bot_enabled and user1_settings.reminder_fusion.enabled:
                        user_command = await functions.get_game_command(user1_settings, 'fusion')
                        time_left = await functions.calculate_time_left_from_cooldown(message, user1_settings, 'fusion')
                        if time_left < timedelta(0): return
                        reminder_message = user1_settings.reminder_fusion.message.replace('{command}', user_command)
                        reminder: reminders.Reminder = (
                            await reminders.insert_reminder(user1.id, 'fusion', time_left,
                                                            message.channel.id, reminder_message)
                        )
                        if user1_settings.reactions_enabled and reminder.record_exists: add_reaction = True
                if user2_settings is not None:
                    if user2_settings.bot_enabled and user2_settings.reminder_fusion.enabled:
                        user_command = await functions.get_game_command(user2_settings, 'fusion')
                        time_left = await functions.calculate_time_left_from_cooldown(message, user2_settings, 'fusion')
                        if time_left < timedelta(0): return
                        reminder_message = user2_settings.reminder_fusion.message.replace('{command}', user_command)
                        reminder: reminders.Reminder = (
                            await reminders.insert_reminder(user2.id, 'fusion', time_left,
                                                            message.channel.id, reminder_message)
                        )
                        if user2_settings.reactions_enabled and reminder.record_exists: add_reaction = True

                if add_reaction:
                    await message.add_reaction(emojis.LOGO)


# Initialization
def setup(bot):
    bot.add_cog(FusionCog(bot))