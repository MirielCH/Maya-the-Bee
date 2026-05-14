# list_ready.py
"""Contains ready list command"""

from typing import Optional, Union

import discord
from discord import utils
from discord.ext import commands

from database import reminders, users
from resources import emojis, functions, exceptions, settings, strings


# -- Commands ---
async def command_ready(
    bot: discord.Bot,
    ctx: Union[commands.Context, discord.ApplicationContext, discord.Message],
    user: Optional[discord.User] = None
) -> None:
    """Lists all activities off cooldown"""
    user = user if user is not None else ctx.author
    try:
        user_settings: users.User = await users.get_user(user.id)
    except exceptions.FirstTimeUserError:
        if user == ctx.author:
            raise
        else:
            await functions.reply_or_respond(ctx, 'This user is not registered with me.', True)
        return
    
    embed = await embed_ready_list(user, user_settings)
    if embed is None:
        embed = discord.Embed(
           color = settings.EMBED_COLOR,
            title = f'{user.global_name}\'s ready list'
        )
        embed.description = f'{emojis.ENABLED} All done!'
        embed.set_footer(text = 'Use "/settings ready-list" to change the content of this list.')
    if isinstance(ctx, discord.ApplicationContext):
        interaction_message = await ctx.respond(embed=embed)
    else:
        interaction_message = await ctx.reply(embed=embed)


# -- Embeds ---
async def embed_ready_list(user: discord.User, user_settings: users.User) -> discord.Embed | None:
    """Embed with ready activities"""
    current_time = utils.utcnow().replace(microsecond=0)
    commands_ready = list(strings.ACTIVITIES_READY_COMMANDS)
    reminders_chests = []
    quests_ready = list(strings.ACTIVITIES_QUEST)
    reminders_larvae = []
    pruner_ready = list(strings.ACTIVITIES_TOOL)

    try:
        active_reminders = list(await reminders.get_active_reminders(user.id))
    except:
        active_reminders = []

    for reminder in active_reminders:
        if reminder.end_time < current_time: continue
        if reminder.activity in commands_ready:
            commands_ready.remove(reminder.activity)
        elif reminder.activity.startswith('chest'):
            reminders_chests.append(reminder)
        elif reminder.activity.startswith('larva'):
            reminders_larvae.append(reminder)
        elif reminder.activity in quests_ready:
            quests_ready.remove(reminder.activity)
        elif reminder.activity in pruner_ready:
            pruner_ready.remove(reminder.activity)

    ready_list = ''

    if commands_ready:
        for activity in commands_ready:
            show_command = getattr(user_settings, strings.ACTIVITIES_READY_COMMANDS_SETTINGS[activity])
            if not show_command: continue
            if activity in strings.ACTIVITIES_SLASH_COMMANDS:
                slash_command = strings.SLASH_COMMANDS[strings.ACTIVITIES_SLASH_COMMANDS[activity]]
            else:
                slash_command = strings.SLASH_COMMANDS[activity]
            ready_list = f'{ready_list}\n- {slash_command}'

    if len(pruner_ready) >= 2 and user_settings.ready_show_pruner:
        if any([strings.PRUNER_TYPES[user_settings.pruner_type] < 5, user_settings.pruner_level < 10, user_settings.pruner_tier < 10]):
            if user_settings.pruner_level < 10:
                ready_list = f'{ready_list}\n- {strings.SLASH_COMMANDS["tool"]} upgrade'
            else:
                ready_list = f'{ready_list}\n- {strings.SLASH_COMMANDS["laboratory"]} research'
                
    if len(reminders_chests) < 3 and user_settings.ready_show_chests:
        if user_settings.chests_slots_ready > 0:
            ready_list = f'{ready_list}\n- {user_settings.chests_slots_ready} {strings.SLASH_COMMANDS['chests']} ready to open'
        if user_settings.chests_slots_empty > 0 and user_settings.chests_in_queue > 0:
            ready_list = f'{ready_list}\n- {min(user_settings.chests_slots_empty, user_settings.chests_in_queue)} {strings.SLASH_COMMANDS['chests']} ready to start'

    if quests_ready and user_settings.ready_show_quests:
        quest_types = ''
        for quest in quests_ready:
            quest_types = f'{quest_types}, {quest.replace("quest-", "").replace("-", " ").title()}'
        ready_list = f'{ready_list}\n- {len(quests_ready)} {strings.SLASH_COMMANDS["quests"]} ready to start: {quest_types.strip(", ")}'
        
    if len(reminders_larvae) < user_settings.incubator_slots_total and user_settings.ready_show_incubator:
        if any([user_settings.incubator_slots_ready > 0, user_settings.incubator_slots_hungry > 0, user_settings.incubator_slots_empty > 0]):
            if user_settings.incubator_slots_ready > 0:
                ready_list = f'{ready_list}\n- {strings.SLASH_COMMANDS["incubator show"]}: {user_settings.incubator_slots_ready} larva(e) ready to claim'
            if user_settings.incubator_slots_hungry > 0:
                ready_list = f'{ready_list}\n- {strings.SLASH_COMMANDS["incubator show"]}: {user_settings.incubator_slots_hungry} larva(e) hungry'
            if user_settings.incubator_slots_empty > 0:
                ready_list = f'{ready_list}\n- {strings.SLASH_COMMANDS["incubator show"]}: {user_settings.incubator_slots_empty} slots empty'

    if user_settings.rebirth <= 10:
        level_target = 5 + user_settings.rebirth
    else:
        level_target = 15 + ((user_settings.rebirth - 10) // 2)
    if user_settings.level >= level_target and user_settings.ready_show_rebirth:
        ready_list = f'{ready_list}\n- Ready to {strings.SLASH_COMMANDS["rebirth"]} (Level {user_settings.level} / {level_target})'

    if not ready_list and user_settings.ready_show_when_empty:
        ready_list = f'{emojis.ENABLED} All done!'

    embed = None

    if ready_list:
        embed = discord.Embed(
           color = settings.EMBED_COLOR,
            title = f'{user.global_name}\'s ready list'
        )
        embed.description = ready_list
        
    return embed