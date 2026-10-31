# dev.py
"""Internal dev commands"""

import csv
import importlib
import os
import re
import sys
from typing import List

import discord
from discord.commands import SlashCommandGroup, Option
from discord.ext import commands

from database import cooldowns, users
from resources import emojis, exceptions, functions, logs, settings, views


EVENT_REDUCTION_TYPES = [
    'Text commands',
    'Slash commands',
]

MSG_NOT_DEV = 'You are not allowed to use this command.'

class DevCog(commands.Cog):
    """Cog class containing internal dev commands"""
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    dev = SlashCommandGroup(
        "dev",
        "Development commands",
        guild_ids=settings.DEV_GUILDS,
        default_member_permissions=discord.Permissions(administrator=True)
    )

    # Commands
    @dev.command()
    async def reload(
        self,
        ctx: discord.ApplicationContext,
        modules: Option(str, 'Cogs or modules to reload'),
    ) -> None:
        """Reloads cogs or modules"""
        if ctx.author.id not in settings.DEV_IDS:
            await ctx.respond(MSG_NOT_DEV, ephemeral=True)
            return
        modules = modules.split(' ')
        actions = []
        for module in modules:
            name_found = False
            cog_name = f'cogs.{module}' if not 'cogs.' in module else module
            try:
                cog_status = self.bot.reload_extension(cog_name)
            except:
                cog_status = 'Error'
            if cog_status is None:
                actions.append(f'+ Extension \'{cog_name}\' reloaded.')
                name_found = True
            if not name_found:
                for module_name in sys.modules.copy():
                    if module == module_name:
                        module = sys.modules.get(module_name)
                        if module is not None:
                            importlib.reload(module)
                            actions.append(f'+ Module \'{module_name}\' reloaded.')
                            name_found = True
            if not name_found:
                actions.append(f'- No loaded cog or module with the name \'{module}\' found.')

        message = ''
        for action in actions:
            message = f'{message}\n{action}'
        await ctx.respond(f'```diff\n{message}\n```')

    @dev.command(name='event-reductions')
    async def dev_event_reductions(self, ctx: discord.ApplicationContext) -> None:
        """Change event reductions"""
        if ctx.author.id not in settings.DEV_IDS:
            await ctx.respond(MSG_NOT_DEV, ephemeral=True)
            return
        all_cooldowns = list(await cooldowns.get_all_cooldowns())
        view = views.DevEventReductionsView(ctx, self.bot, all_cooldowns, embed_dev_event_reductions)
        embed = await embed_dev_event_reductions(all_cooldowns)
        interaction = await ctx.respond(embed=embed, view=view)
        view.interaction = interaction

    @dev.command(name='post-message')
    async def post_message(
        self,
        ctx: discord.ApplicationContext,
        message_id: Option(str, 'Message ID of the message IN THIS CHANNEL with the content'),
        channel_id: Option(str, 'Channel ID of the channel where the message is sent to'),
        embed_title: Option(str, 'Title of the embed', max_length=256),
    ) -> None:
        """Sends the content of a message to a channel in an embed"""
        if ctx.author.id not in settings.DEV_IDS:
            await ctx.respond(MSG_NOT_DEV, ephemeral=True)
            return
        await self.bot.wait_until_ready()
        try:
            message_id = int(message_id)
        except ValueError:
            await ctx.respond('The message ID is not a valid number.', ephemeral=True)
            return
        try:
            channel_id = int(channel_id)
        except ValueError:
            await ctx.respond('The channel ID is not a valid number.', ephemeral=True)
            return
        try:
            message = await ctx.channel.fetch_message(message_id)
        except:
            await ctx.respond(
                f'No message with that message ID found.\n'
                f'Note that the message needs to be in **this** channel!',
                ephemeral=True
            )
            return
        try:
            channel = await self.bot.fetch_channel(channel_id)
        except:
            await ctx.respond('No channel with that channel ID found.', ephemeral=True)
            return
        embed = discord.Embed(
            title = embed_title,
            description = message.content
        )
        view = views.ConfirmCancelView(ctx, styles=[discord.ButtonStyle.blurple, discord.ButtonStyle.grey])
        interaction = await ctx.respond(
            f'I will send the following embed to the channel `{channel.name}`. Proceed?',
            view=view,
            embed=embed
        )
        view.interaction_message = interaction
        await view.wait()
        if view.value is None:
            await ctx.followup.send(f'**{ctx.author.global_name}**, you didn\'t answer in time.')
        elif view.value == 'confirm':
            await channel.send(embed=embed)
            await functions.edit_interaction(interaction, view=None)
            await ctx.followup.send('Message sent.')
        else:
            await functions.edit_interaction(interaction, view=None)
            await ctx.followup.send('Sending aborted.')

    @dev.command()
    async def shutdown(self, ctx: discord.ApplicationContext):
        """Shuts down the bot"""
        if ctx.author.id not in settings.DEV_IDS:
            await ctx.respond(MSG_NOT_DEV, ephemeral=True)
            return
        view = views.ConfirmCancelView(ctx, styles=[discord.ButtonStyle.red, discord.ButtonStyle.grey])
        interaction = await ctx.respond(f'**{ctx.author.global_name}**, are you **SURE**?', view=view)
        view.interaction_message = interaction
        await view.wait()
        if view.value is None:
            await functions.edit_interaction(interaction, content=f'**{ctx.author.global_name}**, you didn\'t answer in time.',
                                             view=None)
        elif view.value == 'confirm':
            await functions.edit_interaction(interaction, content='Shutting down.', view=None)
            await self.bot.close()
        else:
            await functions.edit_interaction(interaction, content='Shutdown aborted.', view=None)

    @dev.command()
    async def cache(self, ctx: discord.ApplicationContext):
        """Shows cache size"""
        if ctx.author.id not in settings.DEV_IDS:
            await ctx.respond(MSG_NOT_DEV, ephemeral=True)
            return
        from cache import messages
        cache_size = sys.getsizeof(messages._MESSAGE_CACHE)
        channel_count = len(messages._MESSAGE_CACHE)
        message_count = 0
        for channel_messages in messages._MESSAGE_CACHE.values():
            message_count += len(channel_messages)
            cache_size += sys.getsizeof(channel_messages)
            for message in channel_messages:
                cache_size += sys.getsizeof(message)
        await ctx.respond(
            f'Cache size: {cache_size / 1024:,.2f} KB\n'
            f'Channel count: {channel_count:,}\n'
            f'Message count: {message_count:,}\n'
        )

    @dev.command(name='server-list')
    async def server_list(self, ctx: discord.ApplicationContext):
        """Lists the servers the bot is in by name"""
        if ctx.author.id not in settings.DEV_IDS:
            await ctx.respond(MSG_NOT_DEV, ephemeral=True)
            return
        description = ''
        guilds = sorted(self.bot.guilds, key=lambda guild: guild.name)
        for guild in guilds:
            if len(description) > 4000:
                description = f'{description}\n{emojis.BP} ... and more'
                break
            else:
                description = f'{description}\n{emojis.BP} {guild.name}'

        embed = discord.Embed(
            color = settings.EMBED_COLOR,
            title = 'Server list',
            description = description.strip(),
        )
        await ctx.respond(embed=embed)

    @dev.command()
    async def consolidate(self, ctx: discord.ApplicationContext):
        """Miriel test command. Consolidates tracking records older than 28 days manually"""
        if ctx.author.id not in settings.DEV_IDS:
            await ctx.respond(MSG_NOT_DEV, ephemeral=True)
            return
        await ctx.defer()
        from datetime import datetime
        import asyncio
        from humanfriendly import format_timespan
        from database import tracking
        start_time = datetime.utcnow().replace(microsecond=0)
        log_entry_count = 0
        try:
            old_log_entries = await tracking.get_old_log_entries(28)
        except exceptions.NoDataFoundError:
            await ctx.respond('Nothing to do.')
            return
        entries = {}
        for log_entry in old_log_entries:
            date_time = log_entry.date_time.replace(hour=23, minute=59, second=59, microsecond=999999)
            key = (log_entry.user_id, log_entry.command_or_drop, date_time)
            amount = entries.get(key, 0)
            entries[key] = amount + 1
            log_entry_count += 1
        for key, amount in entries.items():
            user_id, command, date_time = key
            summary_log_entry = await tracking.insert_log_summary(user_id, command, date_time, amount)
            date_time_min = date_time.replace(hour=0, minute=0, second=0, microsecond=0)
            date_time_max = date_time.replace(hour=23, minute=59, second=59, microsecond=999999)
            await tracking.delete_log_entries(user_id, command, date_time_min, date_time_max)
            await asyncio.sleep(0.01)
        cur = settings.NAVI_DB.cursor()
        cur.execute('VACUUM')
        end_time = datetime.utcnow().replace(microsecond=0)
        time_passed = end_time - start_time
        logs.logger.info(f'Consolidated {log_entry_count:,} log entries in {format_timespan(time_passed)} manually.')
        await ctx.respond(f'Consolidated {log_entry_count:,} log entries in {format_timespan(time_passed)}.')

    @dev.command(name='create-hash')
    async def dev_create_hash(
        self,
        ctx: discord.ApplicationContext,
        value: Option(str, 'Value to create a hash for'),
    ) -> None:
        """Creates a hash of the given value"""
        if ctx.author.id not in settings.DEV_IDS:
            await ctx.respond(MSG_NOT_DEV, ephemeral=True)
            return

        await ctx.respond(
            f'Hash of `{value}`:\n```{functions.create_hash(value)}```'
        )

    @dev.command(name='migrate-database')
    async def dev_migrate_users(
        self,
        ctx: discord.ApplicationContext,
    ) -> None:
        """Migrates the users table to a new one with encrypted user ids"""

        if ctx.author.id not in settings.DEV_IDS:
            await ctx.respond(MSG_NOT_DEV, ephemeral=True)
            return

        def quotes(name: str) -> str:
            return '"' + name.replace('"', '""') + '"'
        
        await ctx.defer()

        settings.DATABASE.create_function("uid_hash", 1, lambda value: functions.create_hash(value))
        settings.DATABASE.create_function("uid_token", 1, lambda value: functions.encrypt(value))
        db_create_users_sql = settings.DATABASE.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'").fetchone()[0]
        db_create_reminders_sql = settings.DATABASE.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='reminders'").fetchone()[0]
        db_create_bunnies_sql = settings.DATABASE.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='bunnies'").fetchone()[0]
        db_create_tracking_log_sql = settings.DATABASE.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='tracking_log'").fetchone()[0]
        db_create_errors_sql = settings.DATABASE.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='errors'").fetchone()[0]
        db_extras_users = [
            record[0] for record in settings.DATABASE.execute(
                "SELECT sql FROM sqlite_master WHERE tbl_name='users' "
                "AND type IN ('index','trigger') AND sql IS NOT NULL"
            )
        ]
        db_extras_reminders = [
            record[0] for record in settings.DATABASE.execute(
                "SELECT sql FROM sqlite_master WHERE tbl_name='reminders' "
                "AND type IN ('index','trigger') AND sql IS NOT NULL"
            )
        ]
        db_extras_bunnies = [
            record[0] for record in settings.DATABASE.execute(
                "SELECT sql FROM sqlite_master WHERE tbl_name='bunnies' "
                "AND type IN ('index','trigger') AND sql IS NOT NULL"
            )
        ]
        db_extras_tracking_log = [
            record[0] for record in settings.DATABASE.execute(
                "SELECT sql FROM sqlite_master WHERE tbl_name='tracking_log' "
                "AND type IN ('index','trigger') AND sql IS NOT NULL"
            )
        ]
        db_extras_errors = [
            record[0] for record in settings.DATABASE.execute(
                "SELECT sql FROM sqlite_master WHERE tbl_name='errors' "
                "AND type IN ('index','trigger') AND sql IS NOT NULL"
            )
        ]
        db_columns_users = [record[1] for record in settings.DATABASE.execute("PRAGMA table_info(users)")]

        try:
            settings.DATABASE.execute("BEGIN")

            # Migrate table "users"
            new_sql_users = re.sub(r'^CREATE TABLE\s+\S+', 'CREATE TABLE users_new', db_create_users_sql, flags=re.IGNORECASE)
            new_sql_users, number_of_replacements = re.subn(r'\buser_id\b.+?\b,', 'user_id_hash TEXT UNIQUE PRIMARY KEY NOT NULL, user_id_token BLOB NOT NULL,',
                                                            new_sql_users, flags=re.IGNORECASE)
            if number_of_replacements != 1:
                raise Exception("Column user_id not found in table 'users', check db_create_users_sql")
            settings.DATABASE.execute(new_sql_users)

            insert_columns = ", ".join(column for column in db_columns_users).replace('user_id,', 'user_id_hash, user_id_token,')
            select_columns = ", ".join(column for column in db_columns_users).replace('user_id,', 'uid_hash(user_id), uid_token(user_id),')
            settings.DATABASE.execute(f"INSERT INTO users_new ({insert_columns}) SELECT {select_columns} FROM users")

            user_count_old = settings.DATABASE.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            user_count_new = settings.DATABASE.execute("SELECT COUNT(*) FROM users_new").fetchone()[0]
            if user_count_old != user_count_new:
                raise Exception(f"Row count mismatch: Found {user_count_old} old users, but only migrated {user_count_new} users.")

            settings.DATABASE.execute("DROP TABLE users")
            settings.DATABASE.execute("ALTER TABLE users_new RENAME TO users")

            for sql in db_extras_users:
                settings.DATABASE.execute(sql.replace('user_id', 'user_id_hash'))


            # Migrate table "reminders"
            new_sql_reminders = re.sub(r'^CREATE TABLE\s+\S+', 'CREATE TABLE reminders_new', db_create_reminders_sql, flags=re.IGNORECASE)
            new_sql_reminders, number_of_replacements = re.subn(r'\buser_id\b\s+INTEGER\b', 'user_id_hash TEXT',
                                                            new_sql_reminders, flags=re.IGNORECASE)
            if number_of_replacements != 1:
                raise Exception("Column user_id not found in table 'reminders', check db_create_reminders_sql")
            new_sql_reminders, number_of_replacements = re.subn(r'\buser_id\b,', 'user_id_hash,',
                                                            new_sql_reminders, flags=re.IGNORECASE)
            if number_of_replacements != 1:
                raise Exception("Column user_id not found in table 'reminders', check db_create_reminders_sql")
            new_sql_reminders, number_of_replacements = re.subn(r'\bchannel_id\b\s+\bINTEGER\b', 'channel_id_token BLOB',
                                                            new_sql_reminders, flags=re.IGNORECASE)
            if number_of_replacements != 1:
                raise Exception("Column user_id not found in table 'reminders', check db_create_reminders_sql")
            settings.DATABASE.execute(new_sql_reminders)

            insert_columns = "user_id_hash, activity, channel_id_token, end_time, message, triggered, custom_id"
            select_columns = "uid_hash(user_id), activity, uid_token(channel_id), end_time, message, triggered, custom_id"
            settings.DATABASE.execute(f"INSERT INTO reminders_new ({insert_columns}) SELECT {select_columns} FROM reminders")

            reminders_count_old = settings.DATABASE.execute("SELECT COUNT(*) FROM reminders").fetchone()[0]
            reminders_count_new = settings.DATABASE.execute("SELECT COUNT(*) FROM reminders_new").fetchone()[0]
            if reminders_count_old != reminders_count_new:
                raise Exception(f"Row count mismatch: Found {reminders_count_old} old reminders, but only migrated {reminders_count_new} reminders.")

            settings.DATABASE.execute("DROP TABLE reminders")
            settings.DATABASE.execute("ALTER TABLE reminders_new RENAME TO reminders")

            for sql in db_extras_reminders:
                settings.DATABASE.execute(sql.replace('user_id', 'user_id_hash'))
                

            # Migrate table "bunnies"
            new_sql_bunnies = re.sub(r'^CREATE TABLE\s+\S+', 'CREATE TABLE bunnies_new', db_create_bunnies_sql, flags=re.IGNORECASE)
            new_sql_bunnies, number_of_replacements = re.subn(r'\buser_id\b\s+INTEGER\b', 'user_id_hash TEXT',
                                                            new_sql_bunnies, flags=re.IGNORECASE)
            if number_of_replacements != 1:
                raise Exception("Column user_id not found in table 'bunnies', check db_create_bunnies_sql")
            settings.DATABASE.execute(new_sql_bunnies)

            insert_columns = "user_id_hash, name, fertility, epicness"
            select_columns = "uid_hash(user_id), name, fertility, epicness"
            settings.DATABASE.execute(f"INSERT INTO bunnies_new ({insert_columns}) SELECT {select_columns} FROM bunnies")

            bunnies_count_old = settings.DATABASE.execute("SELECT COUNT(*) FROM bunnies").fetchone()[0]
            bunnies_count_new = settings.DATABASE.execute("SELECT COUNT(*) FROM bunnies_new").fetchone()[0]
            if bunnies_count_old != bunnies_count_new:
                raise Exception(f"Row count mismatch: Found {bunnies_count_old} old bunnies, but only migrated {bunnies_count_new} bunnies.")

            settings.DATABASE.execute("DROP TABLE bunnies")
            settings.DATABASE.execute("ALTER TABLE bunnies_new RENAME TO bunnies")

            for sql in db_extras_bunnies:
                settings.DATABASE.execute(sql.replace('user_id', 'user_id_hash'))
                
            
            # Migrate table "tracking_log"
            new_sql_tracking_log = re.sub(r'^CREATE TABLE\s+\S+', 'CREATE TABLE tracking_log_new', db_create_tracking_log_sql, flags=re.IGNORECASE)
            new_sql_tracking_log, number_of_replacements = re.subn(r'\buser_id\b\s+INTEGER\b', 'user_id_hash TEXT',
                                                            new_sql_tracking_log, flags=re.IGNORECASE)
            if number_of_replacements != 1:
                raise Exception("Column user_id not found in table 'tracking_log', check db_create_tracking_log_sql")
            new_sql_tracking_log, number_of_replacements = re.subn(r'\bguild_id\b.+?,', '',
                                                            new_sql_tracking_log, flags=re.IGNORECASE)
            if number_of_replacements != 1:
                raise Exception("Column guild_id not found in table 'tracking_log', check db_create_tracking_log_sql")
            settings.DATABASE.execute(new_sql_tracking_log)

            insert_columns = "user_id_hash, command_or_drop, amount, date_time, type"
            select_columns = "uid_hash(user_id), command_or_drop, amount, date_time, type"
            settings.DATABASE.execute(f"INSERT INTO tracking_log_new ({insert_columns}) SELECT {select_columns} FROM tracking_log")

            tracking_log_count_old = settings.DATABASE.execute("SELECT COUNT(*) FROM tracking_log").fetchone()[0]
            tracking_log_count_new = settings.DATABASE.execute("SELECT COUNT(*) FROM tracking_log_new").fetchone()[0]
            if tracking_log_count_old != tracking_log_count_new:
                raise Exception(f"Row count mismatch: Found {tracking_log_count_old} old tracking records, but only migrated {tracking_log_count_new} tracking records.")

            settings.DATABASE.execute("DROP TABLE tracking_log")
            settings.DATABASE.execute("ALTER TABLE tracking_log_new RENAME TO tracking_log")

            for sql in db_extras_tracking_log:
                settings.DATABASE.execute(sql.replace('user_id', 'user_id_hash'))
                
            # Migrate table "errors"
            new_sql_errors = re.sub(r'^CREATE TABLE\s+\S+', 'CREATE TABLE errors_new', db_create_errors_sql, flags=re.IGNORECASE)
            new_sql_errors, number_of_replacements = re.subn(r'\bjump_url\b\s+TEXT\b', 'jump_url_token BLOB',
                                                                    new_sql_errors, flags=re.IGNORECASE)
            if number_of_replacements != 1:
                raise Exception("Column jump_url not found in table 'errors', check db_create_errors_sql")
            new_sql_errors, number_of_replacements = re.subn(r'\buser_settings\b\s+TEXT\b,', '',
                                                                    new_sql_errors, flags=re.IGNORECASE)
            if number_of_replacements != 1:
                raise Exception("Column user_settings not found in table 'errors', check db_create_errors_sql")
            new_sql_errors, number_of_replacements = re.subn(r'\bmessage_content\b\s+TEXT\b,', '',
                                                                    new_sql_errors, flags=re.IGNORECASE)
            if number_of_replacements != 1:
                raise Exception("Column message_content not found in table 'errors', check db_create_errors_sql")
            settings.DATABASE.execute(new_sql_errors)

            insert_columns = "date_time, error, jump_url_token"
            select_columns = "date_time, error, uid_token(jump_url)"
            settings.DATABASE.execute(f"INSERT INTO errors_new ({insert_columns}) SELECT {select_columns} FROM errors")

            errors_count_old = settings.DATABASE.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
            errors_count_new = settings.DATABASE.execute("SELECT COUNT(*) FROM errors_new").fetchone()[0]
            if errors_count_old != errors_count_new:
                raise Exception(f"Row count mismatch: Found {errors_count_old} old error records, but only migrated {errors_count_new} error records.")

            settings.DATABASE.execute("DROP TABLE errors")
            settings.DATABASE.execute("ALTER TABLE errors_new RENAME TO errors")

            for sql in db_extras_errors:
                settings.DATABASE.execute(sql)


            # Commit
            settings.DATABASE.execute("COMMIT")
            settings.DATABASE.execute("VACUUM")
            answer = f'Done.'
        except Exception as error:
            settings.DATABASE.execute("ROLLBACK")
            answer = f'Migration failed:\n```{str(error)}```'

        await ctx.respond(answer)

    @dev.command(name='user-settings')
    @commands.bot_has_permissions(send_messages=True, attach_files=True)
    async def dev_user_settings(self, ctx: discord.ApplicationContext, user_id: str) -> None:
        """Lists user settings of a given user"""
        if ctx.author.id not in settings.DEV_IDS:
            await ctx.respond(MSG_NOT_DEV, ephemeral=True)
            return

        try:
            user_id_int: int = int(user_id)
        except:
            await ctx.respond('Invalid user ID.')
            return

        try:
            user_settings: users.User = await users.get_user(user_id_int)
        except exceptions.FirstTimeUserError:
            await ctx.respond(f'This user is not registered with Maya.')
            return

        line: str
        file_content: str = ''
        text_file_path: str = 'dev_user_settings.py'
        for line in str(user_settings).split(')'):
            file_content = f'{file_content.strip()}\n{line.strip(', \n')})'
        text_file = open(text_file_path, 'w')
        text_file.write(file_content.strip(') '))
        text_file.close()
        
        await ctx.respond(content=f'**User settings for `{user_id}`**', file=discord.File(text_file_path))

        os.remove(text_file_path)
        
    @dev.command(name='dump-error-log')
    @commands.bot_has_permissions(send_messages=True, attach_files=True)
    async def dev_user_settings(
        self,
        ctx: discord.ApplicationContext,
        amount: Option(int, 'Amount of records, newest first', default=0),
    ) -> None:
        """Dumps the error log as a CSV file"""
        if ctx.author.id not in settings.DEV_IDS:
            await ctx.respond(MSG_NOT_DEV, ephemeral=True)
            return

        await ctx.defer()
        try:
            if amount > 0:
                sql = f'SELECT * FROM (SELECT * FROM errors ORDER BY date_time DESC LIMIT {amount}) AS newest ORDER BY date_time ASC' 
            else:
                sql = 'SELECT * FROM errors ORDER BY date_time ASC'
            cur = settings.DATABASE.cursor()
            cur.execute(sql)
            records = cur.fetchall()
            
        except Exception as error:
            await ctx.respond(content=f'Error retrieving data:\n```{error}```')

        all_records_as_dict = []
        for record in records:
            record_as_dict = dict(record)
            if record_as_dict['jump_url_token'] is not None:
                record_as_dict['jump_url'] = functions.decrypt(record_as_dict['jump_url_token'])
            else:
                record_as_dict['jump_url'] = 'N/A'
            del record_as_dict['jump_url_token']
            all_records_as_dict.append(record_as_dict)

        csv_file_path = 'error_log.csv'

        with open("error_log.csv", "w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(all_records_as_dict[0].keys()), delimiter=";", quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(all_records_as_dict)

        await ctx.respond(content=f'Error log as CSV:', file=discord.File(csv_file_path))
        os.remove(csv_file_path)


def setup(bot):
    bot.add_cog(DevCog(bot))


# --- Embeds ---
async def embed_dev_event_reductions(all_cooldowns: List[cooldowns.Cooldown]) -> discord.Embed:
    """Event reductions embed"""
    reductions_slash = reductions_text = ''
    for cooldown in all_cooldowns:
        if cooldown.event_reduction_slash > 0:
            event_reduction_slash = f'**`{cooldown.event_reduction_slash}`**%'
        else:
            event_reduction_slash = f'`{cooldown.event_reduction_slash}`%'
        reductions_slash = f'{reductions_slash}\n{emojis.BP} {cooldown.activity}: {event_reduction_slash}'
        if cooldown.event_reduction_mention > 0:
            event_reduction_text = f'**`{cooldown.event_reduction_mention}`**%'
        else:
            event_reduction_text = f'`{cooldown.event_reduction_mention}`%'
        reductions_text = f'{reductions_text}\n{emojis.BP} {cooldown.activity}: {event_reduction_text}'
    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = 'Event reduction settings',
    )
    embed.add_field(name='Slash commands', value=reductions_slash, inline=False)
    embed.add_field(name='Text & mention commands', value=reductions_text, inline=False)
    return embed