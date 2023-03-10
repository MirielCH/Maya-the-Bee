# chests.py

import re

import discord
from discord.ext import commands

from cache import messages
from database import errors, reminders, users
from resources import emojis, exceptions, functions, regex, settings


class ChestsCog(commands.Cog):
    """Cog that contains the chest detection commands"""
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
            embed_author = icon_url = embed_field_1_name = ''
            if embed.author:
                embed_author = embed.author.name
                icon_url = embed.author.icon_url
            if len(embed.fields) > 1:
                embed_field_1_name = embed.fields[1].name

            # Chests
            search_strings = [
                'chests inventory', #English
            ]
            if any(search_string in embed_field_1_name.lower() for search_string in search_strings) and message.components:
                add_reaction = False
                user = await functions.get_interaction_user(message)
                if user is None:
                    user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, icon_url)
                    if user_id_match:
                        user = message.guild.get_member(int(user_id_match.group(1)))
                    else:
                        user_command_message = (
                            await messages.find_message(message.channel.id, regex.COMMAND_CHESTS, user_name=embed_author)
                        )
                        if user_command_message is None:
                            await functions.add_warning_reaction(message)
                            await errors.log_error('User not found in chest message.', message)
                            return
                        user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reminder_chests.enabled: return
                user_command = await functions.get_game_command(user_settings, 'chests')
                regex_timestring = re.compile(r'\.\.\. \((.+?)\)')
                for index, button in enumerate(message.components[0].children):
                    activity = f'chest-{index + 1}'
                    if button.emoji is None or button.label.lower() in ('empty slot', 'open'):
                        try:
                            reminder = await reminders.get_reminder(user.id, activity)
                            await reminder.delete()
                        except exceptions.NoDataFoundError:
                            pass
                        continue
                    if 'silver' in button.emoji.name:
                        chest_type = 'silver'
                        chest_emoji = emojis.CHEST_SILVER
                    elif 'golden' in button.emoji.name:
                        chest_type = 'golden'
                        chest_emoji = emojis.CHEST_GOLDEN
                    else:
                        chest_type = 'wooden'
                        chest_emoji = emojis.CHEST_WOODEN
                    timestring_match = re.search(regex_timestring, button.label.lower())
                    if not timestring_match:
                        await functions.add_warning_reaction(message)
                        await errors.log_error(f'Timestring not found on chest button with index {index}.', message)
                        return
                    reminder_message = (
                        user_settings.reminder_chests.message
                        .replace('{command}', user_command)
                        .replace('{chest_emoji}', chest_emoji)
                        .replace('{chest_type}', chest_type)
                    )
                    time_left = await functions.calculate_time_left_from_timestring(message, timestring_match.group(1))
                    reminder: reminders.Reminder = (
                        await reminders.insert_reminder(user.id, activity, time_left,
                                                        message.channel.id, reminder_message)
                    )
                    if user_settings.reactions_enabled and reminder.record_exists:
                        add_reaction = True
                if add_reaction: await message.add_reaction(emojis.LOGO)


# Initialization
def setup(bot):
    bot.add_cog(ChestsCog(bot))