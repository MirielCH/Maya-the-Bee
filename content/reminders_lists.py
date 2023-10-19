# reminders_lists.py
"""Contains reminder list commands"""

from typing import List, Optional, Union

import discord
from discord import utils
from discord.ext import commands

from database import reminders, users
from resources import emojis, functions, exceptions, settings, strings, views


# -- Commands ---
async def command_list(
    bot: discord.Bot,
    ctx: Union[commands.Context, discord.ApplicationContext, discord.Message],
    user: Optional[discord.User] = None
) -> None:
    """Lists all active reminders"""
    user = user if user is not None else ctx.author
    try:
        user_settings: users.User = await users.get_user(user.id)
    except exceptions.FirstTimeUserError:
        if user == ctx.author:
            raise
        else:
            await functions.reply_or_respond(ctx, 'This user is not registered with me.', True)
        return
    try:
        custom_reminders = list(await reminders.get_active_reminders(user.id, 'custom'))
    except exceptions.NoDataFoundError:
        custom_reminders = []
    try:
        user_reminders = list(await reminders.get_active_reminders(user.id))
    except:
        user_reminders = []
    embed = await embed_reminders_list(bot, user, user_settings, user_reminders)
    view = views.RemindersListView(bot, ctx, user, user_settings, user_reminders, custom_reminders, embed_reminders_list)
    if isinstance(ctx, discord.ApplicationContext):
        interaction_message = await ctx.respond(embed=embed, view=view)
    else:
        interaction_message = await ctx.reply(embed=embed, view=view)
    view.interaction_message = interaction_message
    await view.wait()


# -- Embeds ---
async def embed_reminders_list(bot: discord.Bot, user: discord.User, user_settings: users.User,
                               user_reminders: List[reminders.Reminder],
                               show_timestamps: Optional[bool] = False) -> discord.Embed:
    """Embed with active reminders"""
    current_time = utils.utcnow().replace(microsecond=0)
    reminders_commands_list = []
    reminders_chests_list = []
    reminders_quests_list = []
    reminders_tool_list = []
    reminders_boosts_list = []
    reminders_custom_list = []
    for reminder in user_reminders:
        if reminder.activity == 'custom':
            reminders_custom_list.append(reminder)
        elif reminder.activity.startswith('chest'):
            reminders_chests_list.append(reminder)
        elif reminder.activity.startswith('quest'):
            reminders_quests_list.append(reminder)
        elif reminder.activity in strings.ACTIVITIES_TOOL:
            reminders_tool_list.append(reminder)
        elif reminder.activity in strings.ACTIVITIES_BOOSTS:
            reminders_boosts_list.append(reminder)
        else:
            reminders_commands_list.append(reminder)

    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{user.name}\'s active reminders'
    )
    if not user_reminders:
        embed.description = f'{emojis.BP} You have no active reminders'
    if reminders_commands_list:
        field_command_reminders = ''
        for reminder in reminders_commands_list:
            if show_timestamps:
                flag = 'T' if reminder.end_time.day == current_time.day else 'f'
                reminder_time = utils.format_dt(reminder.end_time, style=flag)
            else:
                time_left = reminder.end_time - current_time
                timestring = await functions.parse_timedelta_to_timestring(time_left)
                reminder_time = f'**`{timestring}`**'
            activity = reminder.activity.replace('-',' ').title()
            field_command_reminders = (
                f'{field_command_reminders}\n'
                f'{emojis.COOLDOWN} **{activity}** • {reminder_time}'
            )
        embed.add_field(name='Commands', value=field_command_reminders.strip(), inline=False)
    if reminders_quests_list:
        field_quests_reminders = ''
        for reminder in reminders_quests_list:
            if show_timestamps:
                flag = 'T' if reminder.end_time.day == current_time.day else 'f'
                reminder_time = utils.format_dt(reminder.end_time, style=flag)
            else:
                time_left = reminder.end_time - current_time
                timestring = await functions.parse_timedelta_to_timestring(time_left)
                reminder_time = f'**`{timestring}`**'
            if 'weekly' in reminder.message:
                activity = 'Weekly'
            elif 'monthly' in reminder.message:
                activity = 'Monthly'
            else:
                activity = 'Daily'
            field_quests_reminders = (
                f'{field_quests_reminders}\n'
                f'{emojis.COOLDOWN} **{activity}** • {reminder_time}'
            )
        embed.add_field(name='Quests', value=field_quests_reminders.strip(), inline=False)
    if reminders_chests_list:
        field_chests_reminders = ''
        for reminder in reminders_chests_list:
            if show_timestamps:
                flag = 'T' if reminder.end_time.day == current_time.day else 'f'
                reminder_time = utils.format_dt(reminder.end_time, style=flag)
            else:
                time_left = reminder.end_time - current_time
                timestring = await functions.parse_timedelta_to_timestring(time_left)
                reminder_time = f'**`{timestring}`**'
            if 'silver' in reminder.message:
                emoji = emojis.CHEST_SILVER
                activity = 'Silver'
            elif 'golden' in reminder.message:
                emoji = emojis.CHEST_GOLDEN
                activity = 'Golden'
            elif 'wooden' in reminder.message:
                emoji = emojis.CHEST_WOODEN
                activity = 'Wooden'
            elif 'pumpkin' in reminder.message:
                emoji = emojis.PUMPKIN
                activity = 'Pumpkin'
            else:
                emoji = emojis.CHEST_WOODEN
                activity = reminder.activity.capitalize()
            field_chests_reminders = (
                f'{field_chests_reminders}\n'
                f'{emoji} **{activity}** • {reminder_time}'
            )
        embed.add_field(name='Chests', value=field_chests_reminders.strip(), inline=False)
    if reminders_tool_list:
        field_tool_reminders = ''
        for reminder in reminders_tool_list:
            if show_timestamps:
                flag = 'T' if reminder.end_time.day == current_time.day else 'f'
                reminder_time = utils.format_dt(reminder.end_time, style=flag)
            else:
                time_left = reminder.end_time - current_time
                timestring = await functions.parse_timedelta_to_timestring(time_left)
                reminder_time = f'**`{timestring}`**'
            activity = reminder.activity.replace('-',' ').title()
            field_tool_reminders = (
                f'{field_tool_reminders}\n'
                f'{emojis.LABORATORY} **{activity}** • {reminder_time}'
            )
        if user_settings.pruner_type is not None:
            pruner_emoji = getattr(emojis, f'PRUNER_{user_settings.pruner_type.upper()}', '')
        else:
            pruner_emoji = ''
        embed.add_field(name=f'Tool {pruner_emoji}', value=field_tool_reminders.strip(), inline=False)
    if reminders_boosts_list:
        field_boosts_reminders = ''
        for reminder in reminders_boosts_list:
            if show_timestamps:
                flag = 'T' if reminder.end_time.day == current_time.day else 'f'
                reminder_time = utils.format_dt(reminder.end_time, style=flag)
            else:
                time_left = reminder.end_time - current_time
                timestring = await functions.parse_timedelta_to_timestring(time_left)
                reminder_time = f'**`{timestring}`**'
            activity = reminder.activity.replace('-',' ').title()
            if reminder.activity in strings.ACTIVITIES_BOOSTS_EMOJIS:
                emoji = strings.ACTIVITIES_BOOSTS_EMOJIS[reminder.activity]
            else:
                emoji = emojis.BP
            field_boosts_reminders = (
                f'{field_boosts_reminders}\n'
                f'{emoji} **{activity}** • {reminder_time}'
            )
        embed.add_field(name='Boosts', value=field_boosts_reminders.strip(), inline=False)
    if reminders_custom_list:
        field_custom_reminders = ''
        for reminder in reminders_custom_list:
            if show_timestamps:
                flag = 'T' if reminder.end_time.day == current_time.day else 'f'
                reminder_time = utils.format_dt(reminder.end_time, style=flag)
            else:
                time_left = reminder.end_time - current_time
                timestring = await functions.parse_timedelta_to_timestring(time_left)
                reminder_time = f'**`{timestring}`**'
            custom_id = f'0{reminder.custom_id}' if reminder.custom_id <= 9 else reminder.custom_id
            field_custom_reminders = (
                f'{field_custom_reminders}\n'
                f'{emojis.BP} **{custom_id}** • {reminder_time} • {reminder.message}'
            )
        embed.add_field(name='Custom', value=field_custom_reminders.strip(), inline=False)
    return embed