# profile.py

from datetime import timedelta
import re

import discord
from discord.ext import commands
from datetime import timedelta

from cache import messages
from database import errors, reminders, users
from resources import emojis, exceptions, functions, regex, settings, strings


class ProfileCog(commands.Cog):
    """Cog that contains the profile/stats detection commands"""
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

        # Profile & Stats
        search_strings = [
            '\'s tree', #English
        ]
        if any(search_string in embed_data['author']['name'].lower() for search_string in search_strings):
            interaction_user = await functions.get_interaction_user(message)
            updated_reminder = False
            embed_users = []
            if interaction_user is None:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_PROFILE_STATS)
                )
                if user_command_message is None:
                    await functions.add_warning_reaction(message)
                    return
                interaction_user = user_command_message.author
            user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, embed_data['author']['icon_url'])
            if user_id_match:
                user_id = int(user_id_match.group(1))
                embed_users.append(message.guild.get_member(user_id))
            else:
                user_name_match = re.search(regex.USERNAME_FROM_EMBED_AUTHOR, embed_data['author']['name'])
                if user_name_match:
                    user_name = user_name_match.group(1)
                    embed_users = await functions.get_guild_member_by_name(message.guild, user_name)
                if not user_name_match or not embed_users:
                    await functions.add_warning_reaction(message)
                    return
            if interaction_user not in embed_users: return
            try:
                user_settings: users.User = await users.get_user(interaction_user.id)
            except exceptions.FirstTimeUserError:
                return
            if not user_settings.bot_enabled: return
            if embed_data['field3']['value'] != '':
                cooldowns = []
                ready_commands = []
                if user_settings.reminder_research.enabled:
                    timestring_match = re.search(r"researching: `(.+?)` remaining", embed_data['field3']['value'].lower())
                    if timestring_match:
                        user_command = await functions.get_game_command(user_settings, 'laboratory')
                        reminder_message = user_settings.reminder_research.message.replace('{command}', user_command)
                        cooldowns.append(['research', timestring_match.group(1).lower(), reminder_message])
                    else:
                        ready_commands.append('research')
                if user_settings.reminder_upgrade.enabled:
                    timestring_match = re.search(r"upgrading: `(.+?)` remaining", embed_data['field3']['value'].lower())
                    if timestring_match:
                        user_command = await functions.get_game_command(user_settings, 'tool')
                        reminder_message = user_settings.reminder_upgrade.message.replace('{command}', user_command)
                        cooldowns.append(['upgrade', timestring_match.group(1).lower(), reminder_message])
                    else:
                        ready_commands.append('upgrade')

                for cooldown in cooldowns:
                    cd_activity = cooldown[0]
                    cd_timestring = cooldown[1]
                    cd_message = cooldown[2]
                    time_left = await functions.parse_timestring_to_timedelta(cd_timestring)
                    if time_left < timedelta(0): continue
                    reminder: reminders.Reminder = (
                        await reminders.insert_reminder(interaction_user.id, cd_activity, time_left,
                                                        message.channel.id, cd_message)
                    )
                    if not reminder.record_exists:
                        await message.channel.send(strings.MSG_ERROR)
                        return
                    updated_reminder = True
                for activity in ready_commands:
                    try:
                        reminder: reminders.Reminder = await reminders.get_reminder(interaction_user.id, activity)
                    except exceptions.NoDataFoundError:
                        continue
                    await reminder.delete()
                    if reminder.record_exists:
                        await functions.add_warning_reaction(message)
                        await errors.log_error(
                            f'Had an error in the profile, deleting the reminder with activity "{activity}".',
                            message
                        )
            if updated_reminder and user_settings.reactions_enabled:
                await message.add_reaction(emojis.LOGO)


# Initialization
def setup(bot):
    bot.add_cog(ProfileCog(bot))