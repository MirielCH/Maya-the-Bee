# clean.py

from datetime import timedelta
import re

import discord
from discord import utils
from discord.ext import commands

from cache import messages
from database import errors, reminders, tracking, users
from resources import exceptions, functions, regex, settings


class CleanCog(commands.Cog):
    """Cog that contains the clean detection commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, message_before: discord.Message, message_after: discord.Message) -> None:
        """Runs when a message is edited in a channel."""
        if message_before.pinned != message_after.pinned: return
        if message_before.components and not message_after.components: return
        active_component = await functions.check_message_for_active_components(message_after)
        if active_component: await self.on_message(message_after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.id not in [settings.GAME_ID, settings.TESTY_ID]: return
        if not message.embeds: return
        embed_data = await functions.parse_embed(message)

        # Clean
        search_strings = [
            'your tree has been cleaned!', #English
        ]
        if any(search_string in embed_data['description'].lower() for search_string in search_strings):
            user = await functions.get_interaction_user(message)
            if user is None:
                user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, embed_data['author']['icon_url'])
                if user_id_match:
                    user = message.guild.get_member(int(user_id_match.group(1)))
                else:
                    user_command_message = (
                        await messages.find_message(message.channel.id, regex.COMMAND_CLEAN,
                                                    user_name=embed_data['author']['name'])
                    )
                    if user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in clean message.', message)
                        return
                    user = user_command_message.author
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return
            if not user_settings.bot_enabled: return
            if user_settings.tracking_enabled:
                current_time = utils.utcnow().replace(microsecond=0)
                await tracking.insert_log_entry(user.id, message.guild.id, 'clean', current_time)
            if not user_settings.reminder_clean.enabled: return
            user_command = await functions.get_game_command(user_settings, 'clean')
            time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'clean')
            if time_left < timedelta(0): return
            reminder_message = user_settings.reminder_clean.message.replace('{command}', user_command)
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, 'clean', time_left,
                                                message.channel.id, reminder_message)
            )
            await functions.add_reminder_reaction(message, reminder, user_settings)


# Initialization
def setup(bot):
    bot.add_cog(CleanCog(bot))