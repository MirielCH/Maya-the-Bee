# prune.py

from datetime import timedelta
import re

import discord
from discord import utils
from discord.ext import commands

from cache import messages
from database import errors, reminders, tracking, users
from resources import emojis, exceptions, functions, regex, settings


class PruneCog(commands.Cog):
    """Cog that contains the prune detection commands"""
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
        if message.embeds: return

        # Prune
        search_strings = [
            'you have pruned your tree', #English
        ]
        if any(search_string in message.content.lower() for search_string in search_strings):
            user = await functions.get_interaction_user(message)
            if user is None:
                user_name_match = re.search(regex.NAME_FROM_MESSAGE_START, message.content)
                if user_name_match:
                    user_name = user_name_match.group(1)
                    user_command_message = (
                        await messages.find_message(message.channel.id, regex.COMMAND_PRUNE, user_name=user_name)
                    )
                if not user_name_match or user_command_message is None:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('User not found in prune message.', message)
                    return
                user = user_command_message.author
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return
            if not user_settings.bot_enabled: return
            if user_settings.tracking_enabled:
                current_time = utils.utcnow().replace(microsecond=0)
                await tracking.insert_log_entry(user.id, message.guild.id, 'prune', current_time)
            if not user_settings.reminder_prune.enabled: return
            user_command = await functions.get_game_command(user_settings, 'prune')
            pruner_type_match = re.search(r'> (.+?) pruner', message.content, re.IGNORECASE)
            if pruner_type_match:
                await user_settings.update(pruner_type=pruner_type_match.group(1).lower())
            else:
                await functions.add_warning_reaction(message)
                await errors.log_error('Pruner type not found in prune message.', message)
            time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'prune')
            if time_left < timedelta(0): return
            pruner_emoji = getattr(emojis, f'PRUNER_{user_settings.pruner_type.upper()}', '')
            reminder_message = (
                user_settings.reminder_prune.message
                .replace('{command}', user_command)
                .replace('{pruner_emoji}', pruner_emoji)
                .replace('  ', ' ')
            )
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, 'prune', time_left,
                                                        message.channel.id, reminder_message)
            )
            await functions.add_reminder_reaction(message, reminder, user_settings)


# Initialization
def setup(bot):
    bot.add_cog(PruneCog(bot))