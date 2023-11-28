# users.py
"""Provides access to the table "users" in the database"""

from dataclasses import dataclass
from datetime import datetime
import sqlite3
from typing import NamedTuple, Tuple

from database import errors
from resources import exceptions, settings, strings


# Containers
class UserReminder(NamedTuple):
    """Object that summarizes all user settings for a specific alert"""
    enabled: bool
    message: str

@dataclass()
class User():
    """Object that represents a record from table "user"."""
    bot_enabled: bool
    dnd_mode_enabled: bool
    donor_tier: int
    helper_context_enabled: bool
    helper_prune_enabled: bool
    helper_prune_progress_bar_color: str
    last_rebirth: datetime
    league_beta: bool
    level: int
    pruner_type: str
    reactions_enabled: bool
    rebirth: int
    reminder_boosts: UserReminder
    reminder_chests: UserReminder
    reminder_clean: UserReminder
    reminder_daily: UserReminder
    reminder_fusion: UserReminder
    reminder_hive_energy: UserReminder
    reminder_prune: UserReminder
    reminder_quests: UserReminder
    reminder_research: UserReminder
    reminder_upgrade: UserReminder
    reminder_vote: UserReminder
    reminders_slash_enabled: bool
    research_time: int
    streak_vote: int
    tracking_enabled: bool
    user_id: int
    xp: int
    xp_gain_average: float
    xp_prune_count: int
    xp_target: int

    async def refresh(self) -> None:
        """Refreshes user data from the database."""
        new_settings: User = await get_user(self.user_id)
        self.bot_enabled = new_settings.bot_enabled
        self.dnd_mode_enabled = new_settings.dnd_mode_enabled
        self.donor_tier = new_settings.donor_tier
        self.helper_context_enabled = new_settings.helper_context_enabled
        self.helper_prune_enabled = new_settings.helper_prune_enabled
        self.last_rebirth = new_settings.last_rebirth
        self.league_beta = new_settings.league_beta
        self.level = new_settings.level
        self.helper_prune_progress_bar_color = new_settings.helper_prune_progress_bar_color
        self.pruner_type = new_settings.pruner_type
        self.reactions_enabled = new_settings.reactions_enabled
        self.rebirth = new_settings.rebirth
        self.reminder_boosts = new_settings.reminder_boosts
        self.reminder_chests = new_settings.reminder_chests
        self.reminder_clean = new_settings.reminder_clean
        self.reminder_daily = new_settings.reminder_daily
        self.reminder_fusion = new_settings.reminder_fusion
        self.reminder_hive_energy = new_settings.reminder_hive_energy
        self.reminder_prune = new_settings.reminder_prune
        self.reminder_quests = new_settings.reminder_quests
        self.reminder_research = new_settings.reminder_research
        self.reminder_upgrade = new_settings.reminder_upgrade
        self.reminder_vote = new_settings.reminder_vote
        self.reminders_slash_enabled = new_settings.reminders_slash_enabled
        self.research_time = new_settings.research_time
        self.streak_vote = new_settings.streak_vote
        self.tracking_enabled = new_settings.tracking_enabled
        self.xp = new_settings.xp
        self.xp_gain_average = new_settings.xp_gain_average
        self.xp_prune_count = new_settings.xp_prune_count
        self.xp_target = new_settings.xp_target

    async def update(self, **kwargs) -> None:
        """Updates the user record in the database. Also calls refresh().
        If user_donor_tier is updated and a partner is set, the partner's partner_donor_tier is updated as well.

        Arguments
        ---------
        kwargs (column=value):
            bot_enabled: bool
            dnd_mode_enabled: bool
            donor_tier: int
            helper_context_enabled: bool
            helper_prune_enabled: bool
            last_rebirth: datetime UTC aware
            league_beta: bool
            level: int
            helper_prune_progress_bar_color: str
            pruner_type: str
            reactions_enabled: bool
            rebirth: int
            reminder_boosts_enabled: bool
            reminder_boosts_message: str
            reminder_chests_enabled: bool
            reminder_chests_message: str
            reminder_clean_enabled: bool
            reminder_clean_message: str
            reminder_daily_enabled: bool
            reminder_daily_message: str
            reminder_fusion_enabled: bool
            reminder_fusion_message: str
            reminder_hive_energy_enabled: bool
            reminder_hive_energy_message: str
            reminder_prune_enabled: bool
            reminder_prune_message: str
            reminder_quests_enabled: bool
            reminder_quests_message: str
            reminder_research_enabled: bool
            reminder_research_message: str
            reminder_upgrade_enabled: bool
            reminder_upgrade_message: str
            reminder_vote_enabled: bool
            reminder_vote_message: str
            reminders_slash_enabled: bool
            research_time: int
            streak_vote: int
            tracking_enabled: bool
            xp: int
            xp_gain_average: float
            xp_prune_count: int
            xp_target: int
        """
        await _update_user(self, **kwargs)
        await self.refresh()


# Miscellaneous functions
async def _dict_to_user(record: dict) -> User:
    """Creates a User object from a database record

    Arguments
    ---------
    record: Database record from table "user" as a dict.

    Returns
    -------
    User object.

    Raises
    ------
    LookupError if something goes wrong reading the dict. Also logs this error to the database.
    """
    function_name = '_dict_to_user'
    try:
        user = User(
            bot_enabled = bool(record['bot_enabled']),
            dnd_mode_enabled = bool(record['dnd_mode_enabled']),
            donor_tier = record['donor_tier'],
            last_rebirth = datetime.fromisoformat(record['last_rebirth']),
            league_beta = bool(record['league_beta']),
            helper_context_enabled = bool(record['helper_context_enabled']),
            helper_prune_enabled = bool(record['helper_prune_enabled']),
            helper_prune_progress_bar_color = record['helper_prune_progress_bar_color'],
            level = record['level'],
            pruner_type = '' if record['pruner_type'] is None else record['pruner_type'],
            reactions_enabled = bool(record['reactions_enabled']),
            rebirth = record['rebirth'],
            reminder_boosts = UserReminder(enabled=bool(record['reminder_boosts_enabled']),
                                           message=record['reminder_boosts_message']),
            reminder_chests = UserReminder(enabled=bool(record['reminder_chests_enabled']),
                                           message=record['reminder_chests_message']),
            reminder_clean = UserReminder(enabled=bool(record['reminder_clean_enabled']),
                                          message=record['reminder_clean_message']),
            reminder_daily = UserReminder(enabled=bool(record['reminder_daily_enabled']),
                                          message=record['reminder_daily_message']),
            reminder_fusion = UserReminder(enabled=bool(record['reminder_fusion_enabled']),
                                           message=record['reminder_fusion_message']),
            reminder_hive_energy = UserReminder(enabled=bool(record['reminder_hive_energy_enabled']),
                                                message=record['reminder_hive_energy_message']),
            reminder_prune = UserReminder(enabled=bool(record['reminder_prune_enabled']),
                                          message=record['reminder_prune_message']),
            reminder_quests = UserReminder(enabled=bool(record['reminder_quests_enabled']),
                                           message=record['reminder_quests_message']),
            reminder_research = UserReminder(enabled=bool(record['reminder_research_enabled']),
                                             message=record['reminder_research_message']),
            reminder_upgrade = UserReminder(enabled=bool(record['reminder_upgrade_enabled']),
                                            message=record['reminder_upgrade_message']),
            reminder_vote = UserReminder(enabled=bool(record['reminder_vote_enabled']),
                                         message=record['reminder_vote_message']),
            reminders_slash_enabled = bool(record['reminders_slash_enabled']),
            research_time = record['research_time'],
            streak_vote = record['streak_vote'],
            tracking_enabled = bool(record['tracking_enabled']),
            xp = record['xp'],
            xp_gain_average = float(record['xp_gain_average']),
            xp_prune_count = record['xp_prune_count'],
            xp_target = record['xp_target'],
            user_id = record['user_id'],
        )
    except Exception as error:
        await errors.log_error(
            strings.INTERNAL_ERROR_DICT_TO_OBJECT.format(function=function_name, record=record)
        )
        raise LookupError(error)

    return user


# Get data
async def get_user(user_id: int) -> User:
    """Gets all user settings.

    Returns
    -------
    User object

    Raises
    ------
    sqlite3.Error if something happened within the database.
    exceptions.FirstTimeUserError if no user was found.
    LookupError if something goes wrong reading the dict.
    Also logs all errors to the database.
    """
    table = 'users'
    function_name = 'get_user'
    sql = f'SELECT * FROM {table} WHERE user_id=?'
    try:
        cur = settings.DATABASE.cursor()
        cur.execute(sql, (user_id,))
        record = cur.fetchone()
    except sqlite3.Error as error:
        await errors.log_error(
            strings.INTERNAL_ERROR_SQLITE3.format(error=error, table=table, function=function_name, sql=sql)
        )
        raise
    if not record:
        raise exceptions.FirstTimeUserError(f'No user data found in database for user "{user_id}".')
    user = await _dict_to_user(dict(record))

    return user


async def get_all_users() -> Tuple[User]:
    """Gets all user settings of all users.

    Returns
    -------
    Tuple with User objects

    Raises
    ------
    sqlite3.Error if something happened within the database.
    exceptions.NoDataFoundError if no guild was found.
    LookupError if something goes wrong reading the dict.
    Also logs all errors to the database.
    """
    table = 'users'
    function_name = 'get_all_users'
    sql = f'SELECT * FROM {table}'
    try:
        cur = settings.DATABASE.cursor()
        cur.execute(sql)
        records = cur.fetchall()
    except sqlite3.Error as error:
        await errors.log_error(
            strings.INTERNAL_ERROR_SQLITE3.format(error=error, table=table, function=function_name, sql=sql)
        )
        raise
    if not records:
        raise exceptions.FirstTimeUserError(f'No user data found in database (how likely is that).')
    users = []
    for record in records:
        user = await _dict_to_user(dict(record))
        users.append(user)

    return tuple(users)


async def get_user_count() -> int:
    """Gets the amount of users in the table "users".

    Returns
    -------
    Amound of users: int

    Raises
    ------
    sqlite3.Error if something happened within the database. Also logs this error to the log file.
    """
    table = 'users'
    function_name = 'get_user_count'
    sql = f'SELECT COUNT(user_id) FROM {table}'
    try:
        cur = settings.DATABASE.cursor()
        cur.execute(sql)
        record = cur.fetchone()
    except sqlite3.Error as error:
        await errors.log_error(
            strings.INTERNAL_ERROR_SQLITE3.format(error=error, table=table, function=function_name, sql=sql)
        )
        raise
    (user_count,) = record

    return user_count


# Write Data
async def _update_user(user: User, **kwargs) -> None:
    """Updates user record. Use User.update() to trigger this function.
    If user_donor_tier is updated and a partner is set, the partner's partner_donor_tier is updated as well.

    Arguments
    ---------
    user_id: int
    kwargs (column=value):
        bot_enabled: bool
        dnd_mode_enabled: bool
        donor_tier: int
        helper_context_enabled: bool
        helper_prune_enabled: bool
        last_rebirth: datetime UTC aware
        league_beta: bool
        level: int
        helper_prune_progress_bar_color: str
        pruner_type: str
        reactions_enabled: bool
        rebirth: int
        reminder_boosts_enabled: bool
        reminder_boosts_message: str
        reminder_chests_enabled: bool
        reminder_chests_message: str
        reminder_clean_enabled: bool
        reminder_clean_message: str
        reminder_daily_enabled: bool
        reminder_daily_message: str
        reminder_fusion_enabled: bool
        reminder_fusion_message: str
        reminder_hive_energy_enabled: bool
        reminder_hive_energy_message: str
        reminder_prune_enabled: bool
        reminder_prune_message: str
        reminder_quests_enabled: bool
        reminder_quests_message: str
        reminder_research_enabled: bool
        reminder_research_message: str
        reminder_upgrade_enabled: bool
        reminder_upgrade_message: str
        reminder_vote_enabled: bool
        reminder_vote_message: str
        reminders_slash_enabled: bool
        research_time: int
        streak_vote: int
        tracking_enabled: bool
        xp: int
        xp_gain_average: float
        xp_prune_count: int
        xp_target: int

    Raises
    ------
    sqlite3.Error if something happened within the database.
    NoArgumentsError if no kwargs are passed (need to pass at least one)
    Also logs all errors to the database.
    """
    table = 'users'
    function_name = '_update_user'
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
        kwargs['user_id'] = user.user_id
        sql = f'{sql} WHERE user_id = :user_id'
        cur.execute(sql, kwargs)
        if 'user_donor_tier' in kwargs and user.partner_id is not None:
            partner = await get_user(user.partner_id)
            await partner.update(partner_donor_tier=kwargs['user_donor_tier'])
    except sqlite3.Error as error:
        await errors.log_error(
            strings.INTERNAL_ERROR_SQLITE3.format(error=error, table=table, function=function_name, sql=sql)
        )
        raise


async def insert_user(user_id: int) -> User:
    """Inserts a record in the table "users".

    Returns
    -------
    User object with the newly created user.

    Raises
    ------
    sqlite3.Error if something happened within the database.
    Also logs all errors to the database.
    """
    function_name = 'insert_user'
    table = 'users'
    columns = ''
    values = [user_id,]
    for activity, default_message in strings.DEFAULT_MESSAGES.items():
        columns = f'{columns},{strings.ACTIVITIES_COLUMNS[activity]}_message'
        values.append(default_message)
    sql = f'INSERT INTO {table} (user_id{columns}) VALUES ('
    for value in values:
        sql = f'{sql}?,'
    sql = f'{sql.strip(",")})'
    try:
        cur = settings.DATABASE.cursor()
        cur.execute(sql, values)
    except sqlite3.Error as error:
        await errors.log_error(
            strings.INTERNAL_ERROR_SQLITE3.format(error=error, table=table, function=function_name, sql=sql)
        )
        raise
    user = await get_user(user_id)

    return user