# settings.py
"""Contains settings commands"""

import re
from typing import List, Optional

import discord
from discord import utils

from database import guilds, reminders, users
from resources import emojis, exceptions, functions, settings, strings, views


# --- Commands ---
async def command_on(bot: discord.Bot, ctx: discord.ApplicationContext) -> None:
    """On command"""
    first_time_user = False
    try:
        user_settings: users.User = await users.get_user(ctx.author.id)
        if user_settings.bot_enabled:
            await ctx.respond(f'**{ctx.author.name}**, I\'m already turned on.', ephemeral=True)
            return
    except exceptions.FirstTimeUserError:
        user_settings = await users.insert_user(ctx.author.id)
        first_time_user = True
    if not user_settings.bot_enabled: await user_settings.update(bot_enabled=True)
    if not user_settings.bot_enabled:
        await ctx.respond(strings.MSG_ERROR, ephemeral=True)
        return
    if not first_time_user:
        answer = f'Bzzt! Welcome back **{ctx.author.name}**!'
        if user_settings.helper_prune_enabled:
            answer = (
                f'{answer}\n'
                f'Please use {strings.SLASH_COMMANDS["profile"]} to start XP tracking.'
            )
        await ctx.respond(answer)
    else:
        field_settings = (
            f'To set your **donor tier** and change other settings, click the button below or use '
            f'{await functions.get_maya_slash_command(bot, "settings user")}.\n'
            f'Please also use {strings.SLASH_COMMANDS["profile"]} to start XP tracking.'
        )
        field_tracking = (
            f'I track the amount of some Tree commands you use. Check '
            f'{await functions.get_maya_slash_command(bot, "stats")} to see what commands are tracked.\n'
            f'**__No personal data is processed or stored in any way!__**\n'
            f'You can opt-out of command tracking in {await functions.get_maya_slash_command(bot, "stats")} '
            f'or in your user settings.\n\n'
        )
        field_privacy = (
            f'To read more about what data is processed and why, feel free to check the privacy policy found in '
            f'{await functions.get_maya_slash_command(bot, "help")}.'
        )
        file_name = 'logo.png'
        img_logo = discord.File(settings.IMG_LOGO, filename=file_name)
        image_url = f'attachment://{file_name}'
        embed = discord.Embed(
            title = f'Bzzt {ctx.author.name}!',
            description = (
                f'I am here to remind you of Tree commands!\n'
                f'Have a look at {await functions.get_maya_slash_command(bot, "help")} for a list of my own commands.'
            ),
            color =  settings.EMBED_COLOR,
        )
        embed.add_field(name='Settings', value=field_settings, inline=False)
        embed.add_field(name='Command tracking', value=field_tracking, inline=False)
        embed.add_field(name='Privacy policy', value=field_privacy, inline=False)
        embed.set_thumbnail(url=image_url)
        view = views.OneButtonView(ctx, discord.ButtonStyle.blurple, 'pressed', '➜ Settings')
        interaction = await ctx.respond(embed=embed, file=img_logo, view=view)
        view.interaction_message = interaction
        await view.wait()
        if view.value == 'pressed':
            await functions.edit_interaction(interaction, view=None)
            await command_settings_user(bot, ctx)


async def command_off(bot: discord.Bot, ctx: discord.ApplicationContext) -> None:
    """Off command"""
    user: users.User = await users.get_user(ctx.author.id)
    if not user.bot_enabled:
        await ctx.respond(f'**{ctx.author.name}**, I\'m already turned off.', ephemeral=True)
        return
    answer = (
        f'**{ctx.author.name}**, turning me off will disable me completely. It will also delete all of your active '
        f'reminders.\n'
        f'Are you sure?'
    )
    view = views.ConfirmCancelView(ctx, styles=[discord.ButtonStyle.red, discord.ButtonStyle.grey])
    interaction = await ctx.respond(answer, view=view)
    view.interaction_message = interaction
    await view.wait()
    if view.value is None:
        await functions.edit_interaction(
            interaction, content=f'**{ctx.author.name}**, you left me flying.', view=None)
    elif view.value == 'confirm':
        await user.update(bot_enabled=False)
        try:
            active_reminders = await reminders.get_active_reminders(ctx.author.id)
            for reminder in active_reminders:
                await reminder.delete()
        except exceptions.NoDataFoundError:
            pass
        if not user.bot_enabled:
            answer = (
                f'**{ctx.author.name}**, I\'m now turned off.\n'
                f'All active reminders were deleted.\n'
                f'Bzzt! {emojis.LOGO}'
            )
            await functions.edit_interaction(interaction, content=answer, view=None)
        else:
            await ctx.followup.send(strings.MSG_ERROR)
            return
    else:
        await functions.edit_interaction(interaction, content='Aborted.', view=None)


async def command_settings_helpers(bot: discord.Bot, ctx: discord.ApplicationContext,
                                   switch_view: Optional[discord.ui.View] = None) -> None:
    """Helper settings command"""
    commands_settings = {
        'Helpers': command_settings_helpers,
        'Reminders': command_settings_reminders,
        'Reminder messages': command_settings_messages,
        'User': command_settings_user,
    }
    user_settings = interaction = None
    if switch_view is not None:
        user_settings = getattr(switch_view, 'user_settings', None)
        interaction = getattr(switch_view, 'interaction', None)
        switch_view.stop()
    if user_settings is None:
        user_settings: users.User = await users.get_user(ctx.author.id)
    view = views.SettingsHelpersView(ctx, bot, user_settings, embed_settings_helpers, commands_settings)
    embed = await embed_settings_helpers(bot, ctx, user_settings)
    if interaction is None:
        interaction = await ctx.respond(embed=embed, view=view)
    else:
        await functions.edit_interaction(interaction, embed=embed, view=view)
    view.interaction = interaction
    await view.wait()

    
async def command_settings_messages(bot: discord.Bot, ctx: discord.ApplicationContext,
                                    switch_view: Optional[discord.ui.View] = None) -> None:
    """Reminder message settings command"""
    commands_settings = {
        'Helpers': command_settings_helpers,
        'Reminders': command_settings_reminders,
        'Reminder messages': command_settings_messages,
        'User': command_settings_user,
    }
    user_settings = interaction = None
    if switch_view is not None:
        user_settings = getattr(switch_view, 'user_settings', None)
        interaction = getattr(switch_view, 'interaction', None)
        switch_view.stop()
    if user_settings is None:
        user_settings: users.User = await users.get_user(ctx.author.id)
    view = views.SettingsMessagesView(ctx, bot, user_settings, embed_settings_messages, commands_settings, 'all')
    embeds = await embed_settings_messages(bot, ctx, user_settings, 'all')
    if interaction is None:
        interaction = await ctx.respond(embeds=embeds, view=view)
    else:
        await functions.edit_interaction(interaction, embeds=embeds, view=view)
    view.interaction = interaction
    await view.wait()


async def command_settings_reminders(bot: discord.Bot, ctx: discord.ApplicationContext,
                                     switch_view: Optional[discord.ui.View] = None) -> None:
    """Reminder settings command"""
    commands_settings = {
        'Helpers': command_settings_helpers,
        'Reminders': command_settings_reminders,
        'Reminder messages': command_settings_messages,
        'User': command_settings_user,
    }
    user_settings = interaction = None
    if switch_view is not None:
        user_settings = getattr(switch_view, 'user_settings', None)
        interaction = getattr(switch_view, 'interaction', None)
        switch_view.stop()
    if user_settings is None:
        user_settings: users.User = await users.get_user(ctx.author.id)
    view = views.SettingsRemindersView(ctx, bot, user_settings, embed_settings_reminders, commands_settings)
    embed = await embed_settings_reminders(bot, ctx, user_settings)
    if interaction is None:
        interaction = await ctx.respond(embed=embed, view=view)
    else:
        await functions.edit_interaction(interaction, embed=embed, view=view)
    view.interaction = interaction
    await view.wait()


async def command_settings_server(bot: discord.Bot, ctx: discord.ApplicationContext) -> None:
    """Server settings command"""
    guild_settings: guilds.Guild = await guilds.get_guild(ctx.guild.id)
    view = views.SettingsServerView(ctx, bot, guild_settings, embed_settings_server)
    embed = await embed_settings_server(bot, ctx, guild_settings)
    interaction = await ctx.respond(embed=embed, view=view)
    view.interaction = interaction
    await view.wait()


async def command_settings_user(bot: discord.Bot, ctx: discord.ApplicationContext,
                                switch_view: Optional[discord.ui.View] = None) -> None:
    """User settings command"""
    commands_settings = {
        'Helpers': command_settings_helpers,
        'Reminders': command_settings_reminders,
        'Reminder messages': command_settings_messages,
        'User': command_settings_user,
    }
    user_settings = interaction = None
    if switch_view is not None:
        user_settings = getattr(switch_view, 'user_settings', None)
        interaction = getattr(switch_view, 'interaction', None)
        switch_view.stop()
    if user_settings is None:
        user_settings: users.User = await users.get_user(ctx.author.id)
    view = views.SettingsUserView(ctx, bot, user_settings, embed_settings_user, commands_settings)
    embed = await embed_settings_user(bot, ctx, user_settings)
    if interaction is None:
        interaction = await ctx.respond(embed=embed, view=view)
    else:
        await functions.edit_interaction(interaction, embed=embed, view=view)
    view.interaction = interaction
    await view.wait()


# --- Embeds ---
async def embed_settings_helpers(bot: discord.Bot, ctx: discord.ApplicationContext, user_settings: users.User) -> discord.Embed:
    """Helper settings embed"""
    helpers = (
        f'{emojis.BP} **Context Helper**: {await functions.bool_to_text(user_settings.helper_context_enabled)}\n'
        f'{emojis.DETAIL} _Shows some helpful slash commands depending on context._\n'
        f'{emojis.BP} **Prune Assistant**: {await functions.bool_to_text(user_settings.helper_prune_enabled)}\n'
        f'{emojis.DETAIL} _Shows XP to next level after using {strings.SLASH_COMMANDS["prune"]}._\n'
        f'{emojis.DETAIL} _**Use {strings.SLASH_COMMANDS["profile"]} to start tracking.**_\n'
    )
    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{ctx.author.name}\'s helper settings',
        description = '_Settings to toggle some helpful little features._'
    )
    embed.add_field(name='Helpers', value=helpers, inline=False)
    return embed


async def embed_settings_messages(bot: discord.Bot, ctx: discord.ApplicationContext,
                                  user_settings: users.User, activity: str) -> List[discord.Embed]:
    """Reminder message specific activity embed"""
    embed_no = 1
    embed_descriptions = {embed_no: ''}
    embeds = []
    if activity == 'all':
        description = ''
        for activity in strings.ACTIVITIES:
            title = f'{ctx.author.name}\'s reminder messages'
            activity_column = strings.ACTIVITIES_COLUMNS[activity]
            alert = getattr(user_settings, activity_column)
            alert_message = (
                f'{emojis.BP} **{activity.replace("-"," ").capitalize()}**\n'
                f'{emojis.DETAIL} {alert.message}'
            )
            activity = activity.replace('-',' ').capitalize()
            if len(embed_descriptions[embed_no]) + len(alert_message) > 4096:
                embed_no += 1
                embed_descriptions[embed_no] = ''
            embed_descriptions[embed_no] = f'{embed_descriptions[embed_no]}\n{alert_message}'
        for embed_no, description in embed_descriptions.items():
            embed = discord.Embed(
                color = settings.EMBED_COLOR,
                title = title if embed_no < 2 else None,
                description = description
            )
            embeds.append(embed)
    else:
        activity_column = strings.ACTIVITIES_COLUMNS[activity]
        alert = getattr(user_settings, activity_column)
        title = f'{activity.replace("-"," ").capitalize()} reminder message'
        embed = discord.Embed(
            color = settings.EMBED_COLOR,
            title = title if embed_no < 2 else None
        )
        allowed_placeholders = ''
        for placeholder_match in re.finditer('\{(.+?)\}', strings.DEFAULT_MESSAGES[activity]):
            placeholder = placeholder_match.group(1)
            placeholder_description = strings.PLACEHOLDER_DESCRIPTIONS.get(placeholder, '')
            allowed_placeholders = (
                f'{allowed_placeholders}\n'
                f'{emojis.BP} **{{{placeholder}}}**'
            )
            if placeholder_description != '':
                allowed_placeholders = f'{allowed_placeholders}\n{emojis.DETAIL}_{placeholder_description}_'
        if allowed_placeholders == '':
            allowed_placeholders = '_There are no placeholders available for this message._'
        embed.add_field(name='Current message', value=f'{emojis.BP} {alert.message}', inline=False)
        embed.add_field(name='Supported placeholders', value=allowed_placeholders.strip(), inline=False)
        embeds = [embed,]

    return embeds


async def embed_settings_reminders(bot: discord.Bot, ctx: discord.ApplicationContext,
                                   user_settings: users.User) -> discord.Embed:
    """Reminder settings embed"""
    command_reminders = (
        f'{emojis.BP} **Boosts**: {await functions.bool_to_text(user_settings.reminder_boosts.enabled)}\n'
        f'{emojis.BP} **Chests**: {await functions.bool_to_text(user_settings.reminder_chests.enabled)}\n'
        f'{emojis.BP} **Clean**: {await functions.bool_to_text(user_settings.reminder_clean.enabled)}\n'
        f'{emojis.BP} **Daily**: {await functions.bool_to_text(user_settings.reminder_daily.enabled)}\n'
        f'{emojis.BP} **Fusion**: {await functions.bool_to_text(user_settings.reminder_fusion.enabled)}\n'
        f'{emojis.BP} **Hive energy**: {await functions.bool_to_text(user_settings.reminder_hive_energy.enabled)}\n'
    )
    command_reminders2 = (
        f'{emojis.BP} **Prune**: {await functions.bool_to_text(user_settings.reminder_prune.enabled)}\n'
        f'{emojis.BP} **Quests**: {await functions.bool_to_text(user_settings.reminder_quests.enabled)}\n'
        f'{emojis.BP} **Research**: {await functions.bool_to_text(user_settings.reminder_research.enabled)}\n'
        f'{emojis.BP} **Upgrade**: {await functions.bool_to_text(user_settings.reminder_upgrade.enabled)}\n'
        f'{emojis.BP} **Vote**: {await functions.bool_to_text(user_settings.reminder_vote.enabled)}\n'
    )
    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{ctx.author.name}\'s reminder settings',
        description = (
            f'_Note that disabling a reminder also deletes the active reminder._'
        )
    )
    embed.add_field(name='Reminders (I)', value=command_reminders, inline=False)
    embed.add_field(name='Reminders (II)', value=command_reminders2, inline=False)
    return embed


async def embed_settings_server(bot: discord.Bot, ctx: discord.ApplicationContext,
                                guild_settings: guilds.Guild) -> discord.Embed:
    """Server settings embed"""
    server_settings = (
        f'{emojis.BP} **Prefix**: `{guild_settings.prefix}`\n'
    )
    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{ctx.guild.name} server settings',
    )
    embed.add_field(name='Settings', value=server_settings, inline=False)
    return embed


async def embed_settings_user(bot: discord.Bot, ctx: discord.ApplicationContext,
                              user_settings: users.User) -> discord.Embed:
    """User settings embed"""
    donor_tier = list(strings.DONOR_TIERS_EMOJIS.keys())[user_settings.donor_tier]
    donor_tier_emoji = strings.DONOR_TIERS_EMOJIS[donor_tier]
    donor_tier = f'{donor_tier_emoji} `{donor_tier}`'

    bot = (
        f'{emojis.BP} **Bot**: {await functions.bool_to_text(user_settings.bot_enabled)}\n'
        f'{emojis.DETAIL} _You can toggle this with {await functions.get_maya_slash_command(bot, "on")} '
        f'and {await functions.get_maya_slash_command(bot, "off")}._\n'
        f'{emojis.BP} **Donor tier**: {donor_tier}\n'
        f'{emojis.BP} **Reactions**: {await functions.bool_to_text(user_settings.reactions_enabled)}\n'
    )
    behaviour = (
        f'{emojis.BP} **DND mode**: {await functions.bool_to_text(user_settings.dnd_mode_enabled)}\n'
        f'{emojis.DETAIL} _If DND mode is enabled, Maya won\'t ping you._\n'
        f'{emojis.BP} **Slash commands in reminders**: {await functions.bool_to_text(user_settings.reminders_slash_enabled)}\n'
        f'{emojis.DETAIL} _If you can\'t see slash mentions properly, update your Discord app._\n'
    )
    tracking = (
        f'{emojis.BP} **Command tracking**: {await functions.bool_to_text(user_settings.tracking_enabled)}\n'
        f'{emojis.BP} **Last rebirth**: {utils.format_dt(user_settings.last_rebirth)}\n'
        f'{emojis.DETAIL} _This is used to calculate your command count since your last rebirth._\n'
    )
    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{ctx.author.name}\'s user settings',
    )
    embed.add_field(name='Main', value=bot, inline=False)
    embed.add_field(name='Reminder behaviour', value=behaviour, inline=False)
    embed.add_field(name='Tracking', value=tracking, inline=False)
    return embed