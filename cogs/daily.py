# daily.py

from datetime import timedelta
import re

import discord
from discord.ext import commands

from cache import messages
from database import errors, reminders, users
from resources import exceptions, functions, regex, settings


class DailyCog(commands.Cog):
    """Cog that contains the daily detection commands"""
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

        # Daily
        search_strings = [
            'daily rewards', #English
        ]
        if any(search_string in embed_data['title'].lower() for search_string in search_strings):
            user = await functions.get_interaction_user(message)
            if user is None:
                user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, embed_data['author']['icon_url'])
                if user_id_match:
                    user = message.guild.get_member(int(user_id_match.group(1)))
                else:
                    user_command_message = (
                        await messages.find_message(message.channel.id, regex.COMMAND_DAILY,
                                                    user_name=embed_data['author']['name'])
                    )
                    if user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in daily message.', message)
                        return
                    user = user_command_message.author
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return
            if not user_settings.bot_enabled or not user_settings.reminder_daily.enabled: return
            user_command = await functions.get_game_command(user_settings, 'daily')
            time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'daily')
            if time_left < timedelta(0): return
            reminder_message = user_settings.reminder_daily.message.replace('{command}', user_command)
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, 'daily', time_left,
                                                message.channel.id, reminder_message)
            )
            await functions.add_reminder_reaction(message, reminder, user_settings)


# Initialization
def setup(bot):
    bot.add_cog(DailyCog(bot))