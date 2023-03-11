# quests.py

from datetime import datetime, timedelta, timezone
import re

import discord
from discord import utils
from discord.ext import commands

from cache import messages
from database import errors, reminders, users
from resources import emojis, exceptions, functions, regex, settings


class QuestsCog(commands.Cog):
    """Cog that contains the quest detection commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, message_before: discord.Message, message_after: discord.Message) -> None:
        """Runs when a message is edited in a channel."""
        if message_before.pinned != message_after.pinned: return
        all_buttons_disabled = True
        for row in message_after.components:
            for component in row.children:
                if not component.disabled:
                    all_buttons_disabled = False
                    break
        if all_buttons_disabled: return
        await self.on_message(message_after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.id not in [settings.GAME_ID, settings.TESTY_ID]: return

        if message.embeds:
            embed = message.embeds[0]
            embed_author = icon_url = embed_field = ''
            if embed.author:
                embed_author = embed.author.name
                icon_url = embed.author.icon_url
            embed_title = embed.title if embed.title else ''
            embed_description = embed.description if embed.description else ''
            for field in embed.fields:
                if '<t:' in field.value:
                    embed_field = field.value
                    break

            # Available quests overview
            search_strings = [
                'available quests', #English
            ]
            if any(search_string in embed_title.lower() for search_string in search_strings):
                user = await functions.get_interaction_user(message)
                if user is None:
                    user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, icon_url)
                    if user_id_match:
                        user = message.guild.get_member(int(user_id_match.group(1)))
                    else:
                        user_command_message = (
                            await messages.find_message(message.channel.id, regex.COMMAND_QUESTS,
                                                        user_name=embed_author)
                        )
                        if user_command_message is None:
                            await functions.add_warning_reaction(message)
                            await errors.log_error('User not found in quest overview message.', message)
                            return
                        user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reminder_quests.enabled: return
                user_command = await functions.get_game_command(user_settings, 'quests')
                regex_timestring = re.compile(r'\| (.+?)$')
                index_activities = {
                    1: 'daily',
                    2: 'weekly',
                    3: 'monthly',
                }
                for index, button in enumerate(message.components[0].children):
                    if index not in index_activities: continue
                    activity = f'quest-{index_activities[index]}'
                    timestring_match = re.search(regex_timestring, button.label.lower())
                    if not timestring_match: continue
                    reminder_message = (
                        user_settings.reminder_quests.message
                        .replace('{command}', user_command)
                        .replace('{quest_type}', index_activities[index])
                    )
                    time_left = await functions.parse_timestring_to_timedelta(timestring_match.group(1).lower())
                    reminder: reminders.Reminder = (
                        await reminders.insert_reminder(user.id, activity, time_left,
                                                        message.channel.id, reminder_message)
                    )
                    if user_settings.reactions_enabled and reminder.record_exists:
                        add_reaction = True
                if add_reaction: await message.add_reaction(emojis.LOGO)

            # Active quest
            search_strings = [
                '\'s quest', #English
            ]
            if any(search_string in embed_author.lower() for search_string in search_strings):
                user = await functions.get_interaction_user(message)
                if user is None:
                    user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, icon_url)
                    if user_id_match:
                        user = message.guild.get_member(int(user_id_match.group(1)))
                    else:
                        user_name_match = re.search(r"^(.+?)'s ")
                        if user_name_match:
                            user_name = user_name_match.group(1)
                            user_command_message = (
                                await messages.find_message(message.channel.id, regex.COMMAND_QUESTS,
                                                            user_name=user_name)
                            )
                        if not user_name_match or user_command_message is None:
                            await functions.add_warning_reaction(message)
                            await errors.log_error('User not found in active quest message.', message)
                            return
                        user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reminder_quests.enabled: return
                user_command = await functions.get_game_command(user_settings, 'quests')
                quest_type_match = re.search(r'> (.+?) quest', embed_description.lower())
                if not quest_type_match:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Quest type not found in quest message.', message)
                    return
                quest_start_match = re.search(r'<t:(\d+?):d>', embed_field.lower())
                if not quest_start_match:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Quest start time not found in active quest message.', message)
                    return
                quest_type = quest_type_match.group(1).lower()
                activity = f'quest-{quest_type}'
                quest_start = datetime.fromtimestamp(int(quest_start_match.group(1)), timezone.utc).replace(microsecond=0)
                reminder_time = await functions.calculate_time_left_from_cooldown(message, user_settings, activity)
                end_time = quest_start + reminder_time
                current_time = utils.utcnow().replace(microsecond=0)
                time_left = end_time - current_time
                if time_left < timedelta(0): return
                reminder_message = (
                    user_settings.reminder_quests.message
                    .replace('{command}', user_command)
                    .replace('{quest_type}', quest_type)
                )
                reminder: reminders.Reminder = (
                    await reminders.insert_reminder(user.id, activity, time_left,
                                                    message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)


# Initialization
def setup(bot):
    bot.add_cog(QuestsCog(bot))