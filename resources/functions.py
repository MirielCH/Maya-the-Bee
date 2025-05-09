# functions.py

import asyncio
from datetime import timedelta
from math import ceil, floor
import random
import re
from typing import Any, Coroutine, List, Optional, Union

import discord
from discord.ext import commands
from discord import utils
from humanfriendly import format_timespan

from database import cooldowns, errors, reminders, users
from resources import emojis, exceptions, functions, regex, settings, strings, views


# --- Get discord data ---
async def get_interaction(message: discord.Message) -> discord.Interaction:
    """Returns the interaction object if the message was triggered by a slash command. Returns None if no user was found."""
    if message.reference is not None:
        if message.reference.cached_message is not None:
            message = message.reference.cached_message
        else:
            message = await message.channel.fetch_message(message.reference.message_id)
    return message.interaction


async def get_interaction_user(message: discord.Message) -> discord.User:
    """Returns the user object if the message was triggered by a slash command. Returns None if no user was found."""
    interaction = await get_interaction(message)
    return interaction.user if interaction is not None else None


async def get_discord_user(bot: discord.Bot, user_id: int) -> discord.User:
    """Checks the user cache for a user and makes an additional API call if not found. Returns None if user not found."""
    await bot.wait_until_ready()
    user = bot.get_user(user_id)
    if user is None:
        try:
            user = await bot.fetch_user(user_id)
        except discord.NotFound:
            pass
    return user


async def get_discord_channel(bot: discord.Bot, channel_id: int) -> discord.User:
    """Checks the channel cache for a channel and makes an additional API call if not found. Returns None if channel not found."""
    if channel_id is None: return None
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            pass
        except discord.Forbidden:
            raise
    return channel


# --- Reactions
async def add_logo_reaction(message: discord.Message) -> None:
    """Adds a Maya reaction if not already added"""
    reaction_exists = False
    for reaction in message.reactions:
        if reaction.emoji == emojis.LOGO:
            reaction_exists = True
            break
    if not reaction_exists: await message.add_reaction(emojis.LOGO)
        

async def add_reminder_reaction(message: discord.Message, reminder: reminders.Reminder,  user_settings: users.User) -> None:
    """Adds a Maya reaction if the reminder was created, otherwise add a warning and send the error if debug mode is on"""
    if reminder.record_exists and user_settings.reactions_enabled:
        await add_logo_reaction(message)
    elif not reminder.record_exists:
        if settings.DEBUG_MODE or message.guild.id in settings.DEV_GUILDS:
            await message.add_reaction(emojis.WARNING)
            await message.channel.send(strings.MSG_ERROR)


async def add_warning_reaction(message: discord.Message) -> None:
    """Adds a warning reaction if debug mode is on or the guild is a dev guild"""
    if settings.DEBUG_MODE or message.guild.id in settings.DEV_GUILDS:
        await message.add_reaction(emojis.WARNING)


# --- Regex ---
async def get_match_from_patterns(patterns: List[str], string: str) -> re.Match:
    """Searches a string for a regex patterns out of a list of patterns and returns the first match.
    Returns None if no match is found.
    """
    for pattern in patterns:
        match = re.search(pattern, string, re.IGNORECASE)
        if match: break
    return match


# --- Time calculations ---
async def get_guild_member_by_name(guild: discord.Guild, user_name: str) -> List[discord.Member]:
    """Returns all guild members found by the given name"""
    members = []
    for member in guild.members:
        if await encode_text(member.name) == await encode_text(user_name) and not member.bot:
            try:
                await users.get_user(member.id)
            except exceptions.FirstTimeUserError:
                continue
            members.append(member)
    return members


async def calculate_time_left_from_cooldown(message: discord.Message, user_settings: users.User, activity: str) -> timedelta:
    """Returns the time left for a reminder based on a cooldown."""
    slash_command = True if message.interaction is not None else False
    cooldown: cooldowns.Cooldown = await cooldowns.get_cooldown(activity)
    message_time = message.edited_at if message.edited_at else message.created_at
    bot_answer_time = message_time.replace(microsecond=0)
    current_time = utils.utcnow().replace(microsecond=0)
    time_elapsed = current_time - bot_answer_time
    actual_cooldown = cooldown.actual_cooldown_slash() if slash_command else cooldown.actual_cooldown_mention()
    if cooldown.donor_affected:
        time_left_seconds = (actual_cooldown
                             * settings.DONOR_TIERS_MULTIPLIERS[user_settings.donor_tier]
                             - time_elapsed.total_seconds())
    else:
        time_left_seconds = actual_cooldown - time_elapsed.total_seconds()
    return timedelta(seconds=time_left_seconds)


async def calculate_time_left_from_timestring(message: discord.Message, timestring: str) -> timedelta:
    """Returns the time left for a reminder based on a timestring."""
    time_left = await parse_timestring_to_timedelta(timestring.lower())
    message_time = message.edited_at if message.edited_at else message.created_at
    bot_answer_time = message_time.replace(microsecond=0)
    current_time = utils.utcnow().replace(microsecond=0)
    time_elapsed = current_time - bot_answer_time
    return time_left - time_elapsed


async def check_timestring(string: str) -> str:
    """Checks if a string is a valid timestring. Returns itself it valid.

    Raises
    ------
    ErrorInvalidTime if timestring is not a valid timestring.
    """
    last_time_code = None
    last_char_was_number = False
    timestring = ''
    current_number = ''
    pos = 0
    while not pos == len(string):
        slice = string[pos:pos+1]
        pos = pos+1
        allowedcharacters_numbers = set('1234567890')
        allowedcharacters_timecode = set('wdhms')
        if set(slice).issubset(allowedcharacters_numbers):
            timestring = f'{timestring}{slice}'
            current_number = f'{current_number}{slice}'
            last_char_was_number = True
        elif set(slice).issubset(allowedcharacters_timecode) and last_char_was_number:
            if slice == 'w':
                if last_time_code is None:
                    timestring = f'{timestring}w'
                    try:
                        current_number_numeric = int(current_number)
                    except:
                        raise exceptions.InvalidTimestringError('Invalid timestring.')
                    last_time_code = 'weeks'
                    last_char_was_number = False
                    current_number = ''
                else:
                    raise exceptions.InvalidTimestringError('Invalid timestring.')
            elif slice == 'd':
                if last_time_code in ('weeks',None):
                    timestring = f'{timestring}d'
                    try:
                        current_number_numeric = int(current_number)
                    except:
                        raise exceptions.InvalidTimestringError('Invalid timestring.')
                    last_time_code = 'days'
                    last_char_was_number = False
                    current_number = ''
                else:
                    raise exceptions.InvalidTimestringError('Invalid timestring.')
            elif slice == 'h':
                if last_time_code in ('weeks','days',None):
                    timestring = f'{timestring}h'
                    try:
                        current_number_numeric = int(current_number)
                    except:
                        raise exceptions.InvalidTimestringError('Invalid timestring.')
                    last_time_code = 'hours'
                    last_char_was_number = False
                    current_number = ''
                else:
                    raise exceptions.InvalidTimestringError('Invalid timestring.')
            elif slice == 'm':
                if last_time_code in ('weeks','days','hours',None):
                    timestring = f'{timestring}m'
                    try:
                        current_number_numeric = int(current_number)
                    except:
                        raise exceptions.InvalidTimestringError('Invalid timestring.')
                    last_time_code = 'minutes'
                    last_char_was_number = False
                    current_number = ''
                else:
                    raise exceptions.InvalidTimestringError('Invalid timestring.')
            elif slice == 's':
                if last_time_code in ('weeks','days','hours','minutes',None):
                    timestring = f'{timestring}s'
                    try:
                        current_number_numeric = int(current_number)
                    except:
                        raise exceptions.InvalidTimestringError('Invalid timestring.')
                    last_time_code = 'seconds'
                    last_char_was_number = False
                    current_number = ''
                else:
                    raise exceptions.InvalidTimestringError('Invalid timestring.')
            else:
                raise exceptions.InvalidTimestringError('Invalid timestring.')
        else:
            raise exceptions.InvalidTimestringError('Invalid timestring.')
    if last_char_was_number:
        raise exceptions.InvalidTimestringError('Invalid timestring.')

    return timestring


async def parse_timestring_to_timedelta(timestring: str) -> timedelta:
    """Parses a time string and returns the time as timedelta."""
    time_left_seconds = 0

    if '-' in timestring: return timedelta(days=-1)
    if 'ms' in timestring: return timedelta(seconds=1)
    if 'y' in timestring:
        years_start = 0
        years_end = timestring.find('y')
        years = timestring[years_start:years_end]
        timestring = timestring[years_end+1:].strip()
        try:
            time_left_seconds = time_left_seconds + (int(years) * 52 * 604800)
        except:
            await errors.log_error(
                f'Error parsing timestring \'{timestring}\', couldn\'t convert \'{years}\' to an integer'
            )
    if 'w' in timestring:
        weeks_start = 0
        weeks_end = timestring.find('w')
        weeks = timestring[weeks_start:weeks_end]
        timestring = timestring[weeks_end+1:].strip()
        try:
            time_left_seconds = time_left_seconds + (int(weeks) * 604800)
        except:
            await errors.log_error(
                f'Error parsing timestring \'{timestring}\', couldn\'t convert \'{weeks}\' to an integer'
            )
    if 'd' in timestring:
        days_start = 0
        days_end = timestring.find('d')
        days = timestring[days_start:days_end]
        timestring = timestring[days_end+1:].strip()
        try:
            time_left_seconds = time_left_seconds + (int(days) * 86400)
        except:
            await errors.log_error(
                f'Error parsing timestring \'{timestring}\', couldn\'t convert \'{days}\' to an integer'
            )
    if 'h' in timestring:
        hours_start = 0
        hours_end = timestring.find('h')
        hours = timestring[hours_start:hours_end]
        timestring = timestring[hours_end+1:].strip()
        try:
            time_left_seconds = time_left_seconds + (int(hours) * 3600)
        except:
            await errors.log_error(
                f'Error parsing timestring \'{timestring}\', couldn\'t convert \'{hours}\' to an integer'
            )
    if 'm' in timestring:
        minutes_start = 0
        minutes_end = timestring.find('m')
        minutes = timestring[minutes_start:minutes_end]
        timestring = timestring[minutes_end+1:].strip()
        try:
            time_left_seconds = time_left_seconds + (int(minutes) * 60)
        except:
            await errors.log_error(
                f'Error parsing timestring \'{timestring}\', couldn\'t convert \'{minutes}\' to an integer'
            )
    if 's' in timestring:
        seconds_start = 0
        seconds_end = timestring.find('s')
        seconds = timestring[seconds_start:seconds_end]
        decimal_point_location = seconds.find('.')
        if decimal_point_location > -1:
            seconds = seconds[:decimal_point_location]
        timestring = timestring[seconds_end+1:].strip()
        try:
            time_left_seconds = time_left_seconds + int(seconds)
        except:
            await errors.log_error(
                f'Error parsing timestring \'{timestring}\', couldn\'t convert \'{seconds}\' to an integer'
            )

    if time_left_seconds > 999_999_999:
        raise OverflowError('Timestring out of valid range. Stop hacking.')

    return timedelta(seconds=time_left_seconds)


async def parse_timedelta_to_timestring(time_left: timedelta) -> str:
    """Creates a time string from a timedelta."""
    years = time_left.total_seconds() // 31_536_000
    years = int(years)
    weeks = (time_left.total_seconds() % 31_536_000) // 604_800
    weeks = int(weeks)
    days = (time_left.total_seconds() % 604_800) // 86_400
    days = int(days)
    hours = (time_left.total_seconds() % 86_400) // 3_600
    hours = int(hours)
    minutes = (time_left.total_seconds() % 3_600) // 60
    minutes = int(minutes)
    seconds = time_left.total_seconds() % 60
    seconds = int(seconds)

    timestring = ''
    if not years == 0:
        timestring = f'{timestring}{years}y '
    if not weeks == 0:
        timestring = f'{timestring}{weeks}w '
    if not days == 0:
        timestring = f'{timestring}{days}d '
    if not hours == 0:
        timestring = f'{timestring}{hours}h '
    timestring = f'{timestring}{minutes}m {seconds}s'

    return timestring


# --- Message processing ---
async def encode_text(text: str) -> str:
    """Encodes all unicode characters in a text in a way that is consistent on both Windows and Linux"""
    text = (
        text
        .encode('unicode-escape',errors='ignore')
        .decode('ASCII')
        .replace('\\','')
        .strip('*')
    )

    return text


def encode_text_non_async(text: str) -> str:
    """Encodes all unicode characters in a text in a way that is consistent on both Windows and Linux (non async)"""
    text = (
        text
        .encode('unicode-escape',errors='ignore')
        .decode('ASCII')
        .replace('\\','')
        .strip('*')
    )

    return text


async def encode_message(bot_message: discord.Message) -> str:
    """Encodes a message to a version that converts all potentionally problematic unicode characters (async)"""
    if not bot_message.embeds:
        message = await encode_text(bot_message.content)
    else:
        embed: discord.Embed = bot_message.embeds[0]
        message_author = message_description = message_fields = message_title = ''
        if embed.author: message_author = await encode_text(str(embed.author))
        if embed.description: message_description = await encode_text(str(embed.description))
        if embed.title: message_title = str(embed.title)
        if embed.fields: message_fields = str(embed.fields)
        message = f'{message_author}{message_description}{message_fields}{message_title}'

    return message


def encode_message_non_async(bot_message: discord.Message) -> str:
    """Encodes a message to a version that converts all potentionally problematic unicode characters (non async)"""
    if not bot_message.embeds:
        message = encode_text_non_async(bot_message.content)
    else:
        embed: discord.Embed = bot_message.embeds[0]
        message_author = message_description = message_fields = message_title = ''
        if embed.author: message_author = encode_text_non_async(str(embed.author))
        if embed.description: message_description = encode_text_non_async(str(embed.description))
        if embed.title: message_title = str(embed.title)
        if embed.fields: message_fields = str(embed.fields)
        message = f'{message_author}{message_description}{message_fields}{message_title}'

    return message


async def encode_message_with_fields(bot_message: discord.Message) -> str:
    """Encodes a message to a version that converts all potentionally problematic unicode characters
    (async, fields encoded)"""
    if not bot_message.embeds:
        message = await encode_text(bot_message.content)
    else:
        embed: discord.Embed = bot_message.embeds[0]
        message_author = message_description = message_fields = message_title = ''
        if embed.author: message_author = await encode_text(str(embed.author))
        if embed.description: message_description = await encode_text(str(embed.description))
        if embed.title: message_title = str(embed.title)
        if embed.fields: message_fields = await encode_text(str(embed.fields))
        message = f'{message_author}{message_description}{message_fields}{message_title}'

    return message


def encode_message_with_fields_non_async(bot_message: discord.Message) -> str:
    """Encodes a message to a version that converts all potentionally problematic unicode characters
    (non async, fields encoded)"""
    if not bot_message.embeds:
        message = encode_text_non_async(bot_message.content)
    else:
        embed: discord.Embed = bot_message.embeds[0]
        message_author = message_description = message_fields = message_title = ''
        if embed.author: message_author = encode_text_non_async(str(embed.author))
        if embed.description: message_description = encode_text_non_async(str(embed.description))
        if embed.title: message_title = str(embed.title)
        if embed.fields: message_fields = encode_text_non_async(str(embed.fields))
        message = f'{message_author}{message_description}{message_fields}{message_title}'

    return message


# Miscellaneous
async def calculate_percentage(item_amount: int, total_amount: int) -> float:
        try:
            percentage = round(item_amount / total_amount * 100, 2)
        except ZeroDivisionError:
            percentage = 0
        return percentage

async def call_ready_command(bot: commands.Bot, message: discord.Message, user: discord.User) -> None:
    """Calls the ready command as a reply to the current message"""
    command = bot.get_application_command(name='ready')
    if command is not None: await command.callback(command.cog, message, user=user)


async def get_game_command(user_settings: users.User, command_name: str) -> str:
    """Gets a game command. Slash or text, depending on user setting."""
    if user_settings.reminders_slash_enabled:
        return strings.SLASH_COMMANDS.get(command_name, None)
    else:
        return command_name


async def get_maya_slash_command(bot: discord.Bot, command_name: str) -> str:
    """Gets a slash command from Maya. If found, returns the slash mention. If not found, just returns /command.
    Note that slash mentions only work with GLOBAL commands."""
    main_command, *sub_commands = command_name.lower().split(' ')
    for command in bot.application_commands:
        if command.name == main_command:
            return f'</{command_name}:{command.id}>'
    return f'`/{command_name}`'


def await_coroutine(coro):
    """Function to call a coroutine outside of an async function"""
    while True:
        try:
            coro.send(None)
        except StopIteration as error:
            return error.value


async def edit_interaction(interaction: Union[discord.Interaction, discord.WebhookMessage], **kwargs) -> None:
    """Edits a reponse. The response can either be an interaction OR a WebhookMessage"""
    content = kwargs.get('content', utils.MISSING)
    embed = kwargs.get('embed', utils.MISSING)
    embeds = kwargs.get('embeds', utils.MISSING)
    view = kwargs.get('view', utils.MISSING)
    file = kwargs.get('file', utils.MISSING)
    if isinstance(interaction, discord.WebhookMessage):
        await interaction.edit(content=content, embed=embed, embeds=embeds, view=view)
    else:
        await interaction.edit_original_response(content=content, file=file, embed=embed, embeds=embeds, view=view)


async def bool_to_text(boolean: bool) -> str:
        return f'{emojis.ENABLED}`Enabled`' if boolean else f'{emojis.DISABLED}`Disabled`'


async def reply_or_respond(ctx: Union[discord.ApplicationContext, commands.Context], answer: str,
                           ephemeral: Optional[bool] = False) -> Union[discord.Message, discord.Integration]:
    """Sends a reply or reponse, depending on the context type"""
    if isinstance(ctx, commands.Context):
        return await ctx.reply(answer)
    else:
        return await ctx.respond(answer, ephemeral=ephemeral)


async def get_inventory_item(inventory: str, emoji_name: str) -> int:
    """Extracts the amount of a material from an inventory
    Because the material is only listed with its emoji, the exact and full emoji name needs to be given."""
    material_match = re.search(fr'`\s*([\d,.kmb]+?)`\*\* <:{emoji_name}:\d+>', inventory, re.IGNORECASE)
    if not material_match: return 0
    amount_patterns = [
        r'([\d\.,]+[kmb]?)',
        r'(\d+)',
    ]
    amount_match = await functions.get_match_from_patterns(amount_patterns, material_match.group(1))
    amount = amount_match.group(1)
    if amount.lower().endswith('k'):
        return int(round(float(amount.lower().rstrip('k')) * 1_000))
    elif amount.lower().endswith('m'):
        return int(round(float(amount.lower().rstrip('m')) * 1_000_000))
    elif amount.lower().endswith('b'):
        return int(round(float(amount.lower().rstrip('b')) * 1_000_000_000 ))
    else:
        amount = amount.replace(',','').replace('.','')
        if amount.isnumeric():
            return int(amount)
        else:
            raise ValueError(f'Inventory amount "{amount}" can\'t be parsed.')        


async def get_result_from_tasks(ctx: discord.ApplicationContext, tasks: List[asyncio.Task]) -> Any:
    """Returns the first result from several running asyncio tasks."""
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except asyncio.CancelledError:
        return
    for task in pending:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    try:
        result = list(done)[0].result()
    except asyncio.CancelledError:
        pass
    except asyncio.TimeoutError as error:
        raise
    except Exception as error:
        await errors.log_error(error, ctx)
        raise
    return result


# Wait for input
async def wait_for_bot_or_abort(ctx: discord.ApplicationContext, bot_message_task: Coroutine,
                                content: str) -> Union[discord.Message, None]:
    """Sends a message with an abort button that tells the user to input a command.
    This function then waits for both view input and bot_message_task.
    If the bot message task finishes first, the bot message is returned, otherwise return value is None.

    The abort button is removed after this function finishes.
    Make sure that the view timeout is longer than the bot message task timeout to get proper errors.

    Arguments
    ---------
    ctx: Context.
    bot_message_task: The task with the coroutine that waits for the EPIC RPG message.
    content: The content of the message that tells the user what to enter.

    Returns
    -------
    Bot message if message task finished first.
    None if the interaction was aborted or the view timed out first.

    Raises
    ------
    asyncio.TimeoutError if the bot message task timed out before the view timed out.
    This error is also logged to the database.
    """
    view = views.AbortView(ctx)
    interaction = await ctx.respond(content, view=view)
    view.interaction = interaction
    view_task = asyncio.ensure_future(view.wait())
    done, pending = await asyncio.wait([bot_message_task, view_task], return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    if view.value in ('abort','timeout'):
        try:
            await edit_interaction(interaction, content=strings.MSG_ABORTED, view=None)
        except discord.errors.NotFound:
            pass
    elif view.value is None:
        view.stop()
        asyncio.ensure_future(edit_interaction(interaction, view=None))
    bot_message = None
    if bot_message_task.done():
        try:
            bot_message = bot_message_task.result()
        except asyncio.CancelledError:
            pass
        except asyncio.TimeoutError as error:
            raise
        except Exception as error:
            await errors.log_error(error, ctx)
            raise

    return bot_message


async def wait_for_inventory_message(bot: commands.Bot, ctx: discord.ApplicationContext) -> discord.Message:
    """Waits for and returns the message with the inventory embed from Tree"""
    def game_check(message_before: discord.Message, message_after: Optional[discord.Message] = None):
        correct_message = False
        message = message_after if message_after is not None else message_before
        if message.embeds:
            embed = message.embeds[0]
            if embed.author:
                embed_author = encode_text_non_async(str(embed.author.name))
                icon_url = embed.author.icon_url
                try:
                    user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, icon_url)
                    if user_id_match:
                        user_id = int(user_id_match.group(1))
                        search_strings = [
                            f'\'s inventory', #All languages
                        ]
                        if (any(search_string in embed_author for search_string in search_strings)
                            and user_id == ctx.author.id):
                            correct_message = True
                    else:
                        ctx_author = encode_text_non_async(ctx.author.name)
                        search_strings = [
                            f'{ctx_author}\'s inventory', ##All languages
                        ]
                        if any(search_string in embed_author for search_string in search_strings):
                            correct_message = True
                except:
                    pass

        return ((message.author.id in (settings.GAME_ID, settings.TESTY_ID)) and (message.channel == ctx.channel)
                and correct_message)

    message_task = asyncio.ensure_future(bot.wait_for('message', check=game_check,
                                                      timeout = settings.ABORT_TIMEOUT))
    message_edit_task = asyncio.ensure_future(bot.wait_for('message_edit', check=game_check,
                                                           timeout = settings.ABORT_TIMEOUT))
    result = await get_result_from_tasks(ctx, [message_task, message_edit_task])
    return result[1] if isinstance(result, tuple) else result


async def design_trophy_summary(user_settings: users.User) -> discord.Embed:
    """Design and returns a tropy summary embed"""

    embed = discord.Embed()
    
    trophy_amount_next_league = last_league_amount = 0
    next_league = next_league_emoji = ''
    
    if user_settings.trophies >= 86_000 and user_settings.league_beta:
        league_name = 'Beta'
        league_emoji = emojis.LEAGUE_BETA
    else:
        for trophy_amount, league_data in strings.LEAGUES.items():
            if user_settings.trophies >= trophy_amount:
                league_name, league_emoji = league_data
            else:
                next_league, next_league_emoji = league_data
                league_index = list(strings.LEAGUES.keys()).index(trophy_amount)
                if league_index > 0:
                    last_league_amount = list(strings.LEAGUES.keys())[league_index - 1]
                else:
                    last_league_amount = 0
                if next_league == 'Beta' and user_settings.beta_pass_available == 0 and user_settings.diamond_rings < 1_350:
                    break
                trophy_amount_next_league = trophy_amount
                break
    
    embed.title = f'{league_emoji} League {league_name} • {emojis.TROPHY} {user_settings.trophies:,}'
    embed_description = ''

    if trophy_amount_next_league > 0:
        trophies_left = trophy_amount_next_league - user_settings.trophies
        trophies_percentage = (trophy_amount_next_league - last_league_amount - trophies_left) / (trophy_amount_next_league - last_league_amount) * 100
        trophies_progress_bar = await get_progress_bar(trophies_percentage, 
                                                       user_settings.helper_trophies_trophy_progress_bar_color)
        embed_description = (
            f'{trophies_progress_bar}\n'
            f'**{trophy_amount_next_league - user_settings.trophies:,}** {emojis.TROPHY} until League {next_league}'
        )
        if user_settings.trophies_gain_average > 0:
            raids_until_next_league = ceil(trophies_left / round(user_settings.trophies_gain_average))
            embed_description = (
                f'{embed_description}\n'
                f'➜ **{raids_until_next_league:,}** raids at **{round(user_settings.trophies_gain_average):,}** {emojis.TROPHY} average'
            )
    else:
        trophies_progress_bar = await get_progress_bar(100, 
                                                       user_settings.helper_trophies_trophy_progress_bar_color)
        embed_description = (
            f'{trophies_progress_bar}\n'
            f'Seasonal max league reached.'
        )

    if user_settings.trophies > 74_000:
        embed.title = f'{embed.title} • {emojis.DIAMOND_TROPHY} {user_settings.diamond_trophies:,}'
        diamond_trophies_left = user_settings.diamond_rings_cap - user_settings.diamond_rings - user_settings.diamond_trophies
        diamond_trophies_percentage = (user_settings.diamond_trophies + user_settings.diamond_rings) / user_settings.diamond_rings_cap * 100
        diamond_trophies_progress_bar = await get_progress_bar(diamond_trophies_percentage,
                                                               user_settings.helper_trophies_diamond_progress_bar_color)
        if diamond_trophies_left <= 0:
            left_until_cap_str = 'Diamond ring cap reached.'
        else:
            left_until_cap_str = f'**{diamond_trophies_left:,}** {emojis.DIAMOND_TROPHY} until ring cap'
        embed_description = (
            f'{embed_description}\n\n'
            f'{diamond_trophies_progress_bar}\n'
            f'{left_until_cap_str} (**{user_settings.diamond_rings:,}** {emojis.DIAMOND_RING} in inventory)'
        )
        if user_settings.diamond_trophies_gain_average > 0 and diamond_trophies_left > 0:
            raids_until_ring_cap = ceil(diamond_trophies_left / round(user_settings.diamond_trophies_gain_average))
            embed_description = (
                f'{embed_description}\n'
                f'➜ **{raids_until_ring_cap:,}** raids at **{round(user_settings.diamond_trophies_gain_average):,}** '
                f'{emojis.DIAMOND_TROPHY} average'
            )
        rings_to_keep = 1_350 if not user_settings.league_beta and user_settings.beta_pass_available == 0 else 0
        if diamond_trophies_left <= 0 and user_settings.diamond_rings > (rings_to_keep + 450):
            embed_description = (
                f'{embed_description}\n'
                f'➜ You can spend diamond rings in the seasonal {strings.SLASH_COMMANDS["shop"]} to make space!'
            )
            if rings_to_keep > 1:
                embed_description = (
                    f'{embed_description}\n'
                    f'➜ ⚠️ Make sure you keep at least **{rings_to_keep:,}** to be able to reach League Beta!'
                )    
        if user_settings.trophies >= 86_000 and not user_settings.league_beta and user_settings.diamond_rings >= 1_350:
            embed_description = (
                f'{embed_description}\n\n'
                f'⚠️ **Beta pass not active!** Go buy one in {strings.SLASH_COMMANDS["shop"]}!'
            )

    if embed_description:
        embed.description = embed_description.strip()    

    current_time = utils.utcnow().replace(microsecond=0)
    reset_day = 28 if 14 <= current_time.day < 28 else 14
    reset_month = current_time.month + 1 if reset_day == 14 and current_time.day >= 28 else current_time.month
    if reset_month > 12:
        reset_month = 1
        reset_year = current_time.year + 1
    else:
        reset_year = current_time.year
    reset_date = utils.utcnow().replace(year=reset_year, month=reset_month, day=reset_day, hour=0, minute=0, microsecond=0)
    embed.set_footer(text=f'Next reset in {format_timespan(reset_date - current_time)}')
            
    return embed


async def get_progress_bar(percentage: float, color: str) -> str:
    """Returns a progress bar"""
    if color == 'random':
        color = random.choice(strings.PROGRESS_BAR_COLORS)
    if percentage > 100: percentage = 100
    progress = 6 / 100 * percentage
    progress_emojis_full = floor(progress)
    progress_emojis_empty = 6 - progress_emojis_full - 1
    if progress_emojis_empty < 0: progress_emojis_empty = 0
    progress_25_emoji = getattr(emojis,f'PROGRESS_25_{color.upper()}', emojis.PROGRESS_25_GREEN)
    progress_50_emoji = getattr(emojis, f'PROGRESS_50_{color.upper()}', emojis.PROGRESS_50_GREEN)
    progress_75_emoji = getattr(emojis, f'PROGRESS_75_{color.upper()}', emojis.PROGRESS_75_GREEN)
    progress_100_emoji = getattr(emojis, f'PROGRESS_100_{color.upper()}', emojis.PROGRESS_100_GREEN)
    progress_emoji_fractional = ''
    if progress_emojis_full < 6:
        progress_fractional = progress % 1
        if 0 <= progress_fractional < 0.25:
            progress_emoji_fractional = emojis.PROGRESS_0
        elif 0.25 <= progress_fractional < 0.5:
            progress_emoji_fractional = progress_25_emoji
        elif 0.5 <= progress_fractional < 0.75:
            progress_emoji_fractional = progress_50_emoji
        elif 0.75 <= progress_fractional < 1:
            progress_emoji_fractional = progress_75_emoji
        else:
            progress_emoji_fractional = progress_100_emoji
    progress_bar = ''
    for x in range(progress_emojis_full):
        progress_bar = f'{progress_bar}{progress_100_emoji}'
    progress_bar = f'{progress_bar}{progress_emoji_fractional}'
    for x in range(progress_emojis_empty):
        progress_bar = f'{progress_bar}{emojis.PROGRESS_0}'

    return progress_bar