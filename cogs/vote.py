# vote.py

from datetime import timedelta
import re

import discord
from discord.ext import commands

from cache import messages
from database import errors, reminders, users
from resources import exceptions, functions, regex, settings


class VoteCog(commands.Cog):
    """Cog that contains the vote detection commands"""
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

        # Vote on cooldown
        search_strings = [
            'click here to vote', #English
        ]
        if any(search_string in embed_data['description'].lower() for search_string in search_strings):
            user = await functions.get_interaction_user(message)
            if user is None:
                user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, embed_data['author']['icon_url'])
                if user_id_match:
                    user = message.guild.get_member(int(user_id_match.group(1)))
                else:
                    user_command_message = (
                        await messages.find_message(message.channel.id, regex.COMMAND_VOTE,
                                                    user_name=embed_data['author']['name'])
                    )
                    if user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in vote message.', message)
                        return
                    user = user_command_message.author
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return
            if not user_settings.bot_enabled or not user_settings.reminder_vote.enabled: return
            if 'cooldown ready!' in embed_data['title'].lower():
                try:
                    reminder = await reminders.get_reminder(user.id, 'vote')
                    await reminder.delete()
                    return
                except exceptions.NoDataFoundError:
                    pass
                return
            user_command = await functions.get_game_command(user_settings, 'vote')
            timestring_match = re.search(r'\*\*`(.+?)`\*\*', embed_data['title'], re.IGNORECASE)
            if not timestring_match:
                await functions.add_warning_reaction(message)
                await errors.log_error('Timestring not found in vote message.', message)
                return
            time_left = await functions.calculate_time_left_from_timestring(message, timestring_match.group(1))
            if time_left < timedelta(0): return
            reminder_message = user_settings.reminder_vote.message.replace('{command}', user_command)
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, 'vote', time_left,
                                                message.channel.id, reminder_message)
            )
            await functions.add_reminder_reaction(message, reminder, user_settings)


# Initialization
def setup(bot):
    bot.add_cog(VoteCog(bot))