# cooldowns.py
"""Provides access to the table "errors" in the database"""

import sqlite3
import traceback
from typing import Optional, Union

import discord
from discord import utils
from discord.ext import commands

from resources import exceptions, logs, settings, strings


async def log_error(error: Union[Exception, str], ctx: Optional[Union[commands.Context, discord.Message]] = None) -> None:
    """Logs an error to the database and the logfile

    Arguments
    ---------
    error: Exception or a simple string.
    ctx: If context or message is available, the function will log the user input, the message timestamp,
    the message jump_url and the user settings. If not, current time is used, settings and input are logged as "N/A".

    Raises
    ------
    sqlite3.Error when something goes wrong in the database. Also logs this error to the log file.
    """
    table = 'errors'
    function_name = 'log_error'
    sql = f'INSERT INTO {table} (date_time, error, user_settings, jump_url) VALUES (?, ?, ?, ?)'
    if hasattr(error, 'message'):
        error_message = f'Error: {error.message}'
    else:
        error_message = str(error)
    try:
        module = error.__class__.__module__
        if module is None or module == str.__class__.__module__:
            error_message = f'{error_message.strip()}\n- Module: {error.__class__.__name__}'
        if hasattr(error, '__traceback__'):
            traceback_str = "".join(traceback.format_tb(error.__traceback__))
        else:
            traceback_str = 'N/A'
        if isinstance(error, Exception):
            error_message = (
                f'{error_message}\n'
                f'- Traceback:\n'
                f'{traceback_str}'
            )
        error_message = (
            f'{error_message}\n'
            f'- Exception type: {module}.{error.__class__.__name__}'
        )
    except Exception as error:
        error_message = f'{error_message}\n\nGot the following error while trying to get type and traceback:\n{error}'
    message = None
    if isinstance(ctx, commands.Context):
        message = ctx.message
    elif isinstance(ctx, discord.Message):
        message = ctx
    if message is not None:
        user_settings = 'N/A'
        date_time = message.edited_at if message.edited_at else message.created_at
        jump_url = message.jump_url
        if not message.author.bot:
            try:
                from database import users
                user: users.User = await users.get_user(message.author.id)
                user_settings = str(user)
            except exceptions.FirstTimeUserError:
                pass
    else:
        date_time = utils.utcnow()
        jump_url = 'N/A'
        user_settings = 'N/A'
    try:
        cur = settings.DATABASE.cursor()
        cur.execute(sql, (date_time, error_message, user_settings, jump_url))
        logs.logger.error(f'\n{error_message}\n>> Jump URL: {jump_url}')
    except sqlite3.Error as error:
        if ctx is not None:
            logs.logger.error(
                strings.INTERNAL_ERROR_SQLITE3.format(error=error, table=table, function=function_name, sql=sql),
                ctx
            )
        else:
            logs.logger.error(
                strings.INTERNAL_ERROR_SQLITE3.format(error=error, table=table, function=function_name, sql=sql)
            )
        raise