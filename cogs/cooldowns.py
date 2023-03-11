# cooldowns.py

from datetime import timedelta
import re
import unicodedata

import discord
from discord.ext import commands
from datetime import timedelta

from cache import messages
from database import errors, reminders, users
from resources import emojis, exceptions, functions, regex, settings, strings


class CooldownsCog(commands.Cog):
    """Cog that contains the cooldowns detection commands"""
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

        # All cooldowns
        search_strings = [
            '\'s cooldowns', #English
        ]
        if any(search_string in embed_data['author']['name'].lower() for search_string in search_strings):
            interaction_user = await functions.get_interaction_user(message)
            embed_users = []
            if interaction_user is None:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_COOLDOWNS)
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
            embed_field_commands = unicodedata.normalize('NFKD', embed_data['field0']['value'])
            embed_field_quests = unicodedata.normalize('NFKD', embed_data['field1']['value'])
            embed_field_raid = unicodedata.normalize('NFKD', embed_data['field2']['value'])
            embed_field_tool = unicodedata.normalize('NFKD', embed_data['field3']['value'])
            cooldowns = []
            ready_commands = []
            if user_settings.reminder_clean.enabled:
                timestring_match = re.search(r"clean\*\* • \*\*`(.+?)`\*\*", embed_field_commands.lower())
                if timestring_match:
                    user_command = await functions.get_game_command(user_settings, 'clean')
                    reminder_message = user_settings.reminder_clean.message.replace('{command}', user_command)
                    cooldowns.append(['clean', timestring_match.group(1).lower(), reminder_message])
                else:
                    ready_commands.append('clean')
            if user_settings.reminder_fusion.enabled:
                timestring_match = re.search(r"fusion\*\* • \*\*`(.+?)`\*\*", embed_field_commands.lower())
                if timestring_match:
                    user_command = await functions.get_game_command(user_settings, 'fusion')
                    reminder_message = user_settings.reminder_fusion.message.replace('{command}', user_command)
                    cooldowns.append(['fusion', timestring_match.group(1).lower(), reminder_message])
                else:
                    ready_commands.append('fusion')
            if user_settings.reminder_daily.enabled:
                timestring_match = re.search(r"daily\*\* • \*\*`(.+?)`\*\*", embed_field_commands.lower())
                if timestring_match:
                    user_command = await functions.get_game_command(user_settings, 'daily')
                    reminder_message = user_settings.reminder_daily.message.replace('{command}', user_command)
                    cooldowns.append(['daily', timestring_match.group(1).lower(), reminder_message])
                else:
                    ready_commands.append('daily')
            if user_settings.reminder_hive_energy.enabled:
                timestring_match = re.search(r"energy\*\* • \*\*`(.+?)`\*\*", embed_field_raid.lower())
                if timestring_match:
                    user_command = await functions.get_game_command(user_settings, 'hive claim energy')
                    reminder_message = user_settings.reminder_hive_energy.message.replace('{command}', user_command)
                    cooldowns.append(['hive-energy', timestring_match.group(1).lower(), reminder_message])
                else:
                    ready_commands.append('hive-energy')
            if user_settings.reminder_prune.enabled:
                timestring_match = re.search(r"prune\*\* • \*\*`(.+?)`\*\*", embed_field_commands.lower())
                if timestring_match:
                    user_command = await functions.get_game_command(user_settings, 'prune')
                    pruner_emoji = getattr(emojis, f'PRUNER_{user_settings.pruner_type.upper()}', '')
                    reminder_message = (
                        user_settings.reminder_prune.message
                        .replace('{command}', user_command)
                        .replace('{pruner_emoji}', pruner_emoji)
                        .replace('  ', ' ')
                    )
                    cooldowns.append(['prune', timestring_match.group(1).lower(), reminder_message])
                else:
                    ready_commands.append('prune')
            if user_settings.reminder_quests.enabled:
                timestring_daily_match = re.search(r"daily\*\* • `(.+?)`", embed_field_quests.lower())
                timestring_weekly_match = re.search(r"weekly\*\* • `(.+?)`", embed_field_quests.lower())
                timestring_monthly_match = re.search(r"monthly\*\* • `(.+?)`", embed_field_quests.lower())
                user_command = await functions.get_game_command(user_settings, 'quests')
                if timestring_daily_match:
                    reminder_message = (
                        user_settings.reminder_quests.message
                        .replace('{command}', user_command)
                        .replace('{quest_type}', 'daily')
                    )
                    cooldowns.append(['quest-daily', timestring_daily_match.group(1).lower(), reminder_message])
                else:
                    ready_commands.append('quest-daily')
                if timestring_weekly_match:
                    reminder_message = (
                        user_settings.reminder_quests.message
                        .replace('{command}', user_command)
                        .replace('{quest_type}', 'weekly')
                    )
                    cooldowns.append(['quest-weekly', timestring_weekly_match.group(1).lower(), reminder_message])
                else:
                    ready_commands.append('quest-weekly')
                if timestring_monthly_match:
                    reminder_message = (
                        user_settings.reminder_quests.message
                        .replace('{command}', user_command)
                        .replace('{quest_type}', 'monthly')
                    )
                    cooldowns.append(['quest-monthly', timestring_monthly_match.group(1).lower(), reminder_message])
                else:
                    ready_commands.append('quest-monthly')
            if user_settings.reminder_research.enabled:
                timestring_match = re.search(r"researching: `(.+?)` remaining", embed_field_tool.lower())
                if timestring_match:
                    user_command = await functions.get_game_command(user_settings, 'laboratory')
                    reminder_message = user_settings.reminder_research.message.replace('{command}', user_command)
                    cooldowns.append(['research', timestring_match.group(1).lower(), reminder_message])
                else:
                    ready_commands.append('research')
            if user_settings.reminder_upgrade.enabled:
                timestring_match = re.search(r"upgrading: `(.+?)` remaining", embed_field_tool.lower())
                if timestring_match:
                    user_command = await functions.get_game_command(user_settings, 'tool')
                    reminder_message = user_settings.reminder_upgrade.message.replace('{command}', user_command)
                    cooldowns.append(['upgrade', timestring_match.group(1).lower(), reminder_message])
                else:
                    ready_commands.append('upgrade')
            if user_settings.reminder_vote.enabled:
                timestring_match = re.search(r"vote\*\* • \*\*`(.+?)`\*\*", embed_field_commands.lower())
                if timestring_match:
                    user_command = await functions.get_game_command(user_settings, 'vote')
                    reminder_message = user_settings.reminder_fusion.message.replace('{command}', user_command)
                    cooldowns.append(['vote', timestring_match.group(1).lower(), reminder_message])
                else:
                    ready_commands.append('vote')

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
            for activity in ready_commands:
                try:
                    reminder: reminders.Reminder = await reminders.get_reminder(interaction_user.id, activity)
                except exceptions.NoDataFoundError:
                    continue
                await reminder.delete()
                if reminder.record_exists:
                    await functions.add_warning_reaction(message)
                    await errors.log_error(f'Had an error deleting the reminder with activity "{activity}".', message)
            if user_settings.reactions_enabled: await message.add_reaction(emojis.LOGO)

        # Command cooldown
        search_strings = [
            'you can use this command again in', #English
        ]
        if any(search_string in embed_data['title'].lower() for search_string in search_strings):
            user = await functions.get_interaction_user(message)
            user_command = ''
            interaction = await functions.get_interaction(message)
            if user is not None:
                user_command = interaction.name
            if user is None:
                user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, embed_data['author']['icon_url'])
                if user_id_match:
                    user = message.guild.get_member(int(user_id_match.group(1)))
                user_command_message = (
                    await messages.find_message(message.channel.id, user_name=embed_data['author']['name'])
                )
                if user_command_message is None: return
                user = user_command_message.author
                user_command = user_command_message.content
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return
            if not user_settings.bot_enabled: return
            timestring_match = re.search(r'in \*\*`(.+?)`\*\*$', embed_data['title'].lower())
            if not timestring_match:
                await functions.add_warning_reaction(message)
                await errors.log_error('Timestring not found in command cooldown message.', message)
                return
            if (re.search(regex.COMMAND_CLEAN, user_command.lower() or user_command == 'clean')
                and user_settings.reminder_clean.enabled):
                activity = 'clean'
                user_command = await functions.get_game_command(user_settings, activity)
                reminder_message = user_settings.reminder_clean.message.replace('{command}', user_command)
            elif (re.search(regex.COMMAND_DAILY, user_command.lower() or user_command == 'daily')
                and user_settings.reminder_daily.enabled):
                activity = 'daily'
                user_command = await functions.get_game_command(user_settings, activity)
                reminder_message = user_settings.reminder_daily.message.replace('{command}', user_command)
            elif (re.search(regex.COMMAND_PRUNE, user_command.lower() or user_command == 'prune')
                and user_settings.reminder_prune.enabled):
                activity = 'prune'
                user_command = await functions.get_game_command(user_settings, activity)
                pruner_emoji = getattr(emojis, f'PRUNER_{user_settings.pruner_type.upper()}', '')
                reminder_message = (
                    user_settings.reminder_prune.message
                    .replace('{command}', user_command)
                    .replace('{pruner_emoji}', pruner_emoji)
                    .replace('  ', ' ')
                )
            elif (re.search(regex.COMMAND_HIVE_CLAIM_ENERGY, user_command.lower() or user_command == 'hive')
                and user_settings.reminder_hive_energy.enabled):
                activity = 'hive-energy'
                user_command = await functions.get_game_command(user_settings, 'hive claim energy')
                reminder_message = user_settings.reminder_hive_energy.message.replace('{command}', user_command)
            else:
                return
            time_left = await functions.calculate_time_left_from_timestring(message, timestring_match.group(1))
            if time_left < timedelta(0): return
            reminder: reminders.Reminder = (
                await reminders.insert_reminder(user.id, activity, time_left,
                                                message.channel.id, reminder_message)
            )
            await functions.add_reminder_reaction(message, reminder, user_settings)


# Initialization
def setup(bot):
    bot.add_cog(CooldownsCog(bot))