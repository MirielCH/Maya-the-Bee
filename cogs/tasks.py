# tasks.py
"""Contains task related stuff"""

import asyncio
from datetime import datetime, timedelta
from humanfriendly import format_timespan
import sqlite3
from typing import List

import discord
from discord import utils
from discord.ext import commands, tasks

from cache import messages
from database import errors, reminders, tracking, users
from resources import emojis, exceptions, functions, logs, settings, strings


running_tasks = {}


class TasksCog(commands.Cog):
    """Cog with tasks"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Task management
    async def background_task(self, reminders_list: List[reminders.Reminder]) -> None:
        """Background task for scheduling reminders"""
        first_reminder = reminders_list[0]
        current_time = utils.utcnow().replace(microsecond=0)
        def get_time_left() -> timedelta:
            time_left = first_reminder.end_time - current_time
            if time_left.total_seconds() < 0: time_left = timedelta(seconds=0)
            return time_left

        try:
            channel = await functions.get_discord_channel(self.bot, first_reminder.channel_id)
            if channel is None: return
            user = await functions.get_discord_user(self.bot, first_reminder.user_id)
            user_settings = await users.get_user(user.id)
            message_no = 1
            messages = {message_no: ''}
            for reminder in reminders_list:
                if reminder.activity == 'custom':
                    reminder_message = strings.DEFAULT_MESSAGE_CUSTOM_REMINDER.format(message=reminder.message)
                    if user_settings.dnd_mode_enabled:
                        message = f'**{user.name}** {reminder_message}\n'
                    else:
                        message = f'{user.mention} {reminder_message}\n'
                else:
                    reminder_message = reminder.message
                    if user_settings.dnd_mode_enabled:
                        message = f'{reminder_message.replace("{name}", f"**{user.name}**")}\n'
                    else:
                        message = f'{reminder_message.replace("{name}", user.mention)}\n'
                if len(f'{messages[message_no]}{message}') > 1900:
                    message_no += 1
                    messages[message_no] = ''
                messages[message_no] = f'{messages[message_no]}{message}'
            time_left = get_time_left()
            try:
                await asyncio.sleep(time_left.total_seconds())
                allowed_mentions = discord.AllowedMentions(users=[user,])
                for message in messages.values():
                    await channel.send(message.strip(), allowed_mentions=allowed_mentions)
            except asyncio.CancelledError:
                return
            except discord.errors.Forbidden:
                return
            running_tasks.pop(first_reminder.task_name, None)
        except discord.errors.Forbidden:
            return
        except Exception as error:
            await errors.log_error(error)

    async def create_task(self, reminders_list: List[reminders.Reminder]) -> None:
        """Creates a new background task"""
        await self.delete_task(reminders_list[0].task_name)
        task = self.bot.loop.create_task(self.background_task(reminders_list))
        running_tasks[reminders_list[0].task_name] = task

    async def delete_task(self, task_name: str) -> None:
        """Stops and deletes a running task if it exists"""
        if task_name in running_tasks:
            running_tasks[task_name].cancel()
            running_tasks.pop(task_name, None)
        return

    # Events
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Fires when bot has finished starting"""
        reminders.schedule_reminders.start()
        self.delete_old_reminders.start()
        self.schedule_tasks.start()
        self.consolidate_tracking_log.start()
        self.delete_old_messages_from_cache.start()

    # Tasks
    @tasks.loop(seconds=0.5)
    async def schedule_tasks(self):
        """Task that creates or deletes tasks from scheduled reminders.
        Reminders that fire at the same second for the same user in the same channel are combined into one task.
        """
        user_reminders = {}
        for reminder in reminders.scheduled_for_tasks.copy().values():
            reminders.scheduled_for_tasks.pop(reminder.task_name, None)
            reminder_user_channel = f'{reminder.user_id}-{reminder.channel_id}-{reminder.end_time}'
            if reminder_user_channel in user_reminders:
                user_reminders[reminder_user_channel].append(reminder)
            else:
                user_reminders[reminder_user_channel] = [reminder,]
        for reminder in reminders.scheduled_for_deletion.copy().values():
            reminders.scheduled_for_deletion.pop(reminder.task_name, None)
            await self.delete_task(reminder.task_name)
        if user_reminders:
            for reminders_list in user_reminders.values():
                reminders_list.sort(key=lambda reminder: reminder.activity)
                await self.create_task(reminders_list)

    @tasks.loop(minutes=2.0)
    async def delete_old_reminders(self) -> None:
        """Task that deletes all old reminders"""
        try:
            old_reminders = await reminders.get_old_reminders()
        except:
            old_reminders = ()
        for reminder in old_reminders:
            try:
                await reminder.delete()
            except Exception as error:
                await errors.log_error(
                    f'Error deleting old reminder.\nFunction: delete_old_reminders\n'
                    f'Reminder: {reminder}\nError: {error}'
            )

    @tasks.loop(seconds=60)
    async def consolidate_tracking_log(self) -> None:
        """Task that consolidates tracking log entries older than 28 days into summaries"""
        start_time = utils.utcnow().replace(microsecond=0)
        if start_time.hour == 0 and start_time.minute == 0:
            log_entry_count = 0
            try:
                old_log_entries = await tracking.get_old_log_entries(28)
            except exceptions.NoDataFoundError:
                logs.logger.info('Didn\'t find any log entries to consolidate.')
                return
            entries = {}
            for log_entry in old_log_entries:
                date_time = log_entry.date_time.replace(hour=23, minute=59, second=59, microsecond=999999)
                key = (log_entry.user_id, log_entry.guild_id, log_entry.command, date_time)
                amount = entries.get(key, 0)
                entries[key] = amount + 1
                log_entry_count += 1
            for key, amount in entries.items():
                user_id, guild_id, command, date_time = key
                summary_log_entry = await tracking.insert_log_summary(user_id, guild_id, command, date_time, amount)
                date_time_min = date_time.replace(hour=0, minute=0, second=0, microsecond=0)
                date_time_max = date_time.replace(hour=23, minute=59, second=59, microsecond=999999)
                await tracking.delete_log_entries(user_id, guild_id, command, date_time_min, date_time_max)
                await asyncio.sleep(0.01)
            cur = settings.DATABASE.cursor()
            date_time = utils.utcnow() - timedelta(days=366)
            date_time = date_time.replace(hour=0, minute=0, second=0)
            sql = 'DELETE FROM tracking_log WHERE date_time<?'
            try:
                cur.execute(sql, (date_time,))
                cur.execute('VACUUM')
            except sqlite3.Error as error:
                logs.logger.error(f'Error while consolidating: {error}')
                raise
            end_time = utils.utcnow().replace(microsecond=0)
            time_passed = end_time - start_time
            logs.logger.info(f'Consolidated {log_entry_count:,} log entries in {format_timespan(time_passed)}.')

    @tasks.loop(minutes=2)
    async def delete_old_messages_from_cache(self) -> None:
        """Task that deletes messages from the message cache that are older than 2 minutes"""
        deleted_messages_count = await messages.delete_old_messages(timedelta(minutes=2))
        if settings.DEBUG_MODE:
            logs.logger.debug(f'Deleted {deleted_messages_count} messages from message cache.')

# Initialization
def setup(bot):
    bot.add_cog(TasksCog(bot))