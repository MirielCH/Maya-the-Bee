# bunnies.py
"""Provides access to the table "bunnies" in the database"""

from dataclasses import dataclass
import sqlite3
from typing import Tuple

from database import errors
from resources import exceptions, settings, strings


# Containers
@dataclass()
class Bunny():
    """Object that represents a record from the table "bunnies"."""
    epicness: int
    fertility: str
    name: str
    user_id: int
    record_exists: bool = True

    async def delete(self) -> None:
        """Deletes the bunny record from the database. Also calls refresh().

        Raises
        ------
        RecordExistsError if there was no error but the record was not deleted.
        Also logs all errors to the database.
        """
        await _delete_bunny(self)
        await self.refresh()
        if self.record_exists:
            error_message = f'Bunny record got deleted but record still exists.\n{self}'
            await errors.log_error(error_message)
            raise exceptions.RecordExistsError(error_message)

    async def refresh(self) -> None:
        """Refreshes bunny data from the database.
        If the record doesn't exist anymore, "record_exists" will be set to False.
        All other values will stay on their old values before deletion (!).
        """
        try:
            new_settings = await get_bunny(self.user_id, self.name)
        except exceptions.NoDataFoundError as error:
            self.record_exists = False
            return
        self.epicness = new_settings.epicness
        self.fertility = new_settings.fertility
        self.name = new_settings.name
        self.user_id = new_settings.user_id

    async def update(self, **kwargs) -> None:
        """Updates the bunny record in the database. Also calls refresh().

        Arguments
        ---------
        kwargs (column=value):
            epicness: int
            fertility: int
            name: str
            user_id: int
        """
        await _update_bunny(self, **kwargs)
        await self.refresh()


# Miscellaneous functions
async def _dict_to_bunny(record: dict) -> Bunny:
    """Creates a Bunny object from a database record

    Arguments
    ---------
    record: Database record from table "bunnies" as a dict.

    Returns
    -------
    Bunny object.

    Raises
    ------
    LookupError if something goes wrong reading the dict. Also logs this error to the database.
    """
    function_name = '_dict_to_bunny'
    try:
        bunny = Bunny(
            epicness = record['epicness'],
            fertility = record['fertility'],
            name = record['name'],
            user_id = record['user_id'],
            record_exists = True,
        )
    except Exception as error:
        await errors.log_error(
            strings.INTERNAL_ERROR_DICT_TO_OBJECT.format(function=function_name, record=record)
        )
        raise LookupError(error)

    return bunny


# Read Data
async def get_bunny(user_id: int, name: str) -> Bunny:
    """Gets all settings for a bunny from a user id and a bunny name.

    Arguments
    ---------
    user_id: int
    name: str

    Returns
    -------
    Bunny object

    Raises
    ------
    sqlite3.Error if something happened within the database.
    exceptions.NoDataFoundError if no bunny was found.
    LookupError if something goes wrong reading the dict.
    Also logs all errors to the database.
    """
    table = 'bunnies'
    function_name = 'get_bunny'
    sql = f'SELECT * FROM {table} WHERE user_id=? AND name=?'
    try:
        cur = settings.DATABASE.cursor()
        cur.execute(sql, (user_id, name))
        record = cur.fetchone()
    except sqlite3.Error as error:
        await errors.log_error(
            strings.INTERNAL_ERROR_SQLITE3.format(error=error, table=table, function=function_name, sql=sql)
        )
        raise
    if not record:
        raise exceptions.NoDataFoundError(
            f'No bunny data found in database for user "{user_id}" and name "{name}".'
        )
    bunny = await _dict_to_bunny(dict(record))

    return bunny


async def get_bunnies_by_user_id(user_id: int) -> Tuple[Bunny]:
    """Gets all bunnies for a specific user. The bunnies are ordered by their epicness (ASC) and then by their fertility (ASC).

    Arguments
    ---------
    user_id: int - The ID of the user for whom to retrieve bunnies.

    Returns
    -------
    Tuple[Bunny]

    Raises
    ------
    sqlite3.Error if something happened within the database.
    exceptions.NoDataFoundError if no bunny was found.
    LookupError if something goes wrong reading the dict.
    Also logs all errors to the database.
    """
    table = 'bunnies'
    function_name = 'get_bunnies_by_user_id'
    sql = f'SELECT * FROM {table} WHERE user_id=? ORDER BY epicness ASC, fertility ASC'
    try:
        cur = settings.DATABASE.cursor()
        cur.execute(sql, (user_id,))
        records = cur.fetchall()
    except sqlite3.Error as error:
        await errors.log_error(
            strings.INTERNAL_ERROR_SQLITE3.format(error=error, table=table, function=function_name, sql=sql)
        )
        raise

    if not records:
        error_message = 'No bunnies found in database.'
        if user_id is not None: error_message = f'{error_message} User: {user_id}'
        raise exceptions.NoDataFoundError(error_message)
    bunnies = []
    for record in records:
        bunny = await _dict_to_bunny(dict(record))
        bunnies.append(bunny)

    return tuple(bunnies)


# Write Data
async def _delete_bunny(bunny: Bunny) -> None:
    """Deletes bunny record. Use Bunny.delete() to trigger this function.

    Raises
    ------
    sqlite3.Error if something happened within the database.
    NoArgumentsError if no kwargs are passed (need to pass at least one)
    Also logs all errors to the database.
    """
    function_name = '_delete_bunny'
    table = 'bunnies'
    sql = f'DELETE FROM {table} WHERE user_id=? AND name=?'
    try:
        cur = settings.DATABASE.cursor()
        cur.execute(sql, (bunny.user_id, bunny.name,))
    except sqlite3.Error as error:
        await errors.log_error(
            strings.INTERNAL_ERROR_SQLITE3.format(error=error, table=table, function=function_name, sql=sql)
        )
        raise


async def _update_bunny(bunny: Bunny, **kwargs) -> None:
    """Updates a bunny record. Use Bunny.update() to trigger this function.

    Arguments
    ---------
    bunny: Bunny
    kwargs (column=value):
        epicness: int
        fertility: int
        name: str
        user_id: int

    Raises
    ------
    sqlite3.Error if something happened within the database.
    NoArgumentsError if no kwargs are passed (need to pass at least one)
    Also logs all errors to the database.
    """
    table = 'bunnies'
    function_name = '_update_bunny'
    if not kwargs:
        await errors.log_error(
            strings.INTERNAL_ERROR_NO_ARGUMENTS.format(table=table, function=function_name)
        )
        raise exceptions.NoArgumentsError('You need to specify at least one keyword argument.')
    try:
        cur = settings.DATABASE.cursor()
        sql = f'UPDATE {table} SET'
        for kwarg in kwargs:
            sql = f'{sql} {kwarg} = :{kwarg},'
        sql = sql.strip(",")
        kwargs['user_id_old'] = bunny.user_id
        kwargs['name_old'] = bunny.name
        sql = f'{sql} WHERE user_id = :user_id_old AND name = :name_old'
        cur.execute(sql, kwargs)
    except sqlite3.Error as error:
        await errors.log_error(
            strings.INTERNAL_ERROR_SQLITE3.format(error=error, table=table, function=function_name, sql=sql)
        )
        raise


async def insert_bunny(user_id: int, name: str, epicness: int, fertility: int) -> Bunny:
    """Inserts a bunny record.
    This function first checks if a bunny exists. If yes, the existing bunny will be updated instead and
    no new record is inserted.

    Arguments
    ---------
    user_id: int
    name: str
    epicness: int
    fertility: int

    Returns
    -------
    Bunny object with the newly created bunny.

    Raises
    ------
    sqlite3.Error if something happened within the database.
    Also logs all errors to the database.
    """
    function_name = 'insert_bunny'
    table = 'bunnies'    
    cur = settings.DATABASE.cursor()
    try:
        bunny = await get_bunny(user_id, name)
    except exceptions.NoDataFoundError:
        bunny = None
    if bunny is not None:
        await bunny.update(epicness=epicness, fertility=fertility)
    else:
        sql = (
            f'INSERT INTO {table} (user_id, name, fertility, epicness) VALUES (?, ?, ?, ?)'
        )
        try:
            cur.execute(sql, (user_id, name, fertility, epicness))
        except sqlite3.Error as error:
            await errors.log_error(
                strings.INTERNAL_ERROR_SQLITE3.format(error=error, table=table, function=function_name, sql=sql)
            )
            raise
        bunny = await get_bunny(user_id, name)

    return bunny