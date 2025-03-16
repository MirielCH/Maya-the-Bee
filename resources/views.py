# views.py
"""Contains global interaction views"""

import random
from typing import Dict, List, Optional, Union

import discord
from discord.ext import commands

from database import cooldowns, guilds, reminders, users
from resources import components, functions, settings, strings


# --- Miscellaneous ---
class AbortView(discord.ui.View):
    """View with an abort button.

    Also needs the interaction of the response with the view, so do AbortView.interaction = await ctx.respond('foo').

    Returns
    -------
    'abort' while button is active.
    'timeout' on timeout.
    None if nothing happened yet.
    """
    def __init__(self, ctx: discord.ApplicationContext, interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.value = None
        self.interaction = interaction
        self.user = ctx.author

    @discord.ui.button(custom_id="abort", style=discord.ButtonStyle.grey, label='Abort')
    async def button_abort(self, button: discord.ui.Button, interaction: discord.Interaction):
        """Abort button"""
        self.value = button.custom_id
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        self.value = 'timeout'
        self.stop()


class ConfirmCancelView(discord.ui.View):
    """View with confirm and cancel button.

    Args: ctx, styles: Optional[List[discord.ButtonStyle]], labels: Optional[list[str]]

    Also needs the message with the view, so do view.message = await ctx.interaction.original_message().
    Without this message, buttons will not be disabled when the interaction times out.

    Returns 'confirm', 'cancel' or None (if timeout/error)
    """
    def __init__(self, ctx: Union[commands.Context, discord.ApplicationContext],
                 styles: Optional[List[discord.ButtonStyle]] = [discord.ButtonStyle.grey, discord.ButtonStyle.grey],
                 labels: Optional[List[str]] = ['Yes','No'],
                 interaction_message: Optional[Union[discord.Message, discord.Interaction]] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.value = None
        self.user = ctx.author
        self.interaction_message = interaction_message
        self.add_item(components.CustomButton(style=styles[0], custom_id='confirm', label=labels[0]))
        self.add_item(components.CustomButton(style=styles[1], custom_id='cancel', label=labels[1]))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            return False
        return True

    async def on_timeout(self):
        self.stop()


class OneButtonView(discord.ui.View):
    """View with one button that returns the custom id of that button.

    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Returns
    -------
    None while active
    custom id of the button when pressed
    'timeout' on timeout.
    """
    def __init__(self, ctx: Union[commands.Context, discord.ApplicationContext], style: discord.ButtonStyle,
                 custom_id: str, label: str, emoji: Optional[discord.PartialEmoji] = None,
                 interaction_message: Optional[Union[discord.Message, discord.Interaction]] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.value = None
        self.interaction_message = interaction_message
        self.ctx = ctx
        self.user = ctx.author
        self.add_item(components.CustomButton(style=style, custom_id=custom_id, label=label, emoji=emoji))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(random.choice(strings.MSG_INTERACTION_ERRORS), ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        self.disable_all_items()
        if isinstance(self.ctx, discord.ApplicationContext):
            await functions.edit_interaction(self.interaction_message, view=self)
        else:
            await self.interaction_message.edit(view=self)
        self.stop()


# --- Reminder management ---
class RemindersListView(discord.ui.View):
    """View with a select that deletes custom reminders.

    Also needs the message of the response with the view, so do view.interaction = await ctx.respond('foo').

    Returns
    -------
    None
    """
    def __init__(self, bot: discord.Bot, ctx: Union[commands.Context, discord.ApplicationContext], user: discord.User,
                 user_settings: users.User,
                 user_reminders: List[reminders.Reminder], custom_reminders: List[reminders.Reminder],
                 embed_function: callable, show_timestamps: Optional[bool] = False,
                 interaction_message: Optional[Union[discord.Message, discord.Interaction]] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.value = None
        self.bot = bot
        self.ctx = ctx
        self.user_reminders = user_reminders
        self.custom_reminders = custom_reminders
        self.embed_function = embed_function
        self.interaction_message = interaction_message
        self.user = user
        self.user_settings = user_settings
        self.show_timestamps = show_timestamps
        self.add_item(components.ToggleTimestampsButton('Show end time'))
        if custom_reminders:
            self.add_item(components.DeleteCustomRemindersButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(random.choice(strings.MSG_INTERACTION_ERRORS), ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        self.disable_all_items()
        if isinstance(self.ctx, discord.ApplicationContext):
            await functions.edit_interaction(self.interaction_message, view=self)
        else:
            await self.interaction_message.edit(view=self)
        self.stop()


# --- Settings ---
class SettingsAlertsView(discord.ui.View):
    """View with a all components to manage alert settings.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    bot: Bot.
    user_settings: User object with the settings of the user.
    embed_function: Function that returns the settings embed. The view expects the following arguments:
    - bot: Bot
    - user_settings: User object with the settings of the user
    commands_settings: Dict[str, callable] with the names and embeds of all settings pages to switch to

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, user_settings: users.User,
                 embed_function: callable, commands_settings: Dict, interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.bot = bot
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.user_settings = user_settings
        self.embed_function = embed_function
        toggled_settings = {
            'Captcha alert': 'alert_captcha_enabled',
            'Nugget alert': 'alert_nugget_enabled',
            'Rebirth alert': 'alert_rebirth_enabled',
        }
        self.add_item(components.ToggleUserSettingsSelect(self, toggled_settings, 'Toggle alerts'))
        self.add_item(components.SetAlertSettingsSelect(self))
        self.add_item(components.SetAlertNuggetThresholdSelect(self))
        self.add_item(components.SwitchSettingsSelect(self, commands_settings))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(random.choice(strings.MSG_INTERACTION_ERRORS), ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()

        
class SettingsHelpersView(discord.ui.View):
    """View with a all components to manage helper settings.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    bot: Bot.
    user_settings: User object with the settings of the user.
    embed_function: Function that returns the settings embed. The view expects the following arguments:
    - bot: Bot
    - user_settings: User object with the settings of the user
    commands_settings: Dict[str, callable] with the names and embeds of all settings pages to switch to

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, user_settings: users.User,
                 embed_function: callable, commands_settings: Dict, interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.bot = bot
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.user_settings = user_settings
        self.embed_function = embed_function
        toggled_settings = {
            'Context commands': 'helper_context_enabled',
            'Fusion level summary': 'helper_fusion_enabled',
            'Level XP popup': 'helper_prune_enabled',
            'Rebirth summary': 'helper_rebirth_enabled',
            'Trophy progress popup': 'helper_trophies_enabled',
        }
        self.add_item(components.ToggleUserSettingsSelect(self, toggled_settings, 'Toggle helpers'))
        self.add_item(
            components.SetProgressBarColorSelect(self, 'helper_prune_progress_bar_color',
                                                      'Change XP progress bar color')
        )
        self.add_item(
            components.SetProgressBarColorSelect(self, 'helper_trophies_trophy_progress_bar_color',
                                                      'Change trophy progress bar color')
        )
        self.add_item(
            components.SetProgressBarColorSelect(self, 'helper_trophies_diamond_progress_bar_color',
                                                      'Change diamond trophy progress bar color')
        )
        self.add_item(components.SwitchSettingsSelect(self, commands_settings))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(random.choice(strings.MSG_INTERACTION_ERRORS), ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()


class SettingsMessagesView(discord.ui.View):
    """View with a all components to change message reminders.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    bot: Bot.
    user_settings: User object with the settings of the user.
    embed_function: Function that returns a list of embeds to see specific messages. The view expects the following arguments:
    - bot: Bot
    - user_settings: User object with the settings of the user
    - activity: str, If this is None, the view doesn't show the buttons to change a message
    commands_settings: Dict[str, callable] with the names and embeds of all settings pages to switch to

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, user_settings: users.User,
                 embed_function: callable, commands_settings: Dict, activity: Optional[str] = 'all',
                 interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.bot = bot
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.user_settings = user_settings
        self.embed_function = embed_function
        self.activity = activity
        self.commands_settings = commands_settings
        if activity == 'all':
            self.add_item(components.SetReminderMessageButton(style=discord.ButtonStyle.red, custom_id='reset_all',
                                                              label='Reset all messages'))
        else:
            self.add_item(components.SetReminderMessageButton(style=discord.ButtonStyle.blurple, custom_id='set_message',
                                                              label='Change'))
            self.add_item(components.SetReminderMessageButton(style=discord.ButtonStyle.red, custom_id='reset_message',
                                                              label='Reset'))
        placeholder = 'Choose activity (1)' if len (strings.ACTIVITIES) > 24 else 'Choose activity'
        self.add_item(components.ReminderMessageSelect(self, strings.ACTIVITIES[:24], placeholder,
                                                       'select_message_activity_1', row=2))
        if len(strings.ACTIVITIES) > 24:
            self.add_item(components.ReminderMessageSelect(self, strings.ACTIVITIES[24:], 'Choose activity (2)',
                                                           'select_message_activity_2', row=3))
        self.add_item(components.SwitchSettingsSelect(self, commands_settings, row=4))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(random.choice(strings.MSG_INTERACTION_ERRORS), ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()


class SettingsRemindersView(discord.ui.View):
    """View with a all components to manage reminder settings.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    bot: Bot.
    user_settings: User object with the settings of the user.
    embed_function: Function that returns the settings embed. The view expects the following arguments:
    - bot: Bot
    - user_settings: User object with the settings of the user
    commands_settings: Dict[str, callable] with the names and embeds of all settings pages to switch to

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, user_settings: users.User,
                 embed_function: callable, commands_settings: Dict, interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.bot = bot
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.user_settings = user_settings
        self.embed_function = embed_function
        self.commands_settings = commands_settings
        toggled_settings_commands = {
            'Boosts': 'reminder_boosts',
            'Chests': 'reminder_chests',
            'Clean': 'reminder_clean',
            'Daily': 'reminder_daily',
            'Fusion': 'reminder_fusion',
            'Hive energy': 'reminder_hive_energy',
            'Prune': 'reminder_prune',
            'Quests': 'reminder_quests',
            'Research': 'reminder_research',
            'Upgrade': 'reminder_upgrade',
            'Vote': 'reminder_vote',
        }

        self.add_item(components.ToggleUserSettingsSelect(self, toggled_settings_commands, 'Toggle reminders',
                                                          'toggle_command_reminders'))
        self.add_item(components.SwitchSettingsSelect(self, commands_settings))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(random.choice(strings.MSG_INTERACTION_ERRORS), ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()


class SettingsServerView(discord.ui.View):
    """View with a all components to manage server settings.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    bot: Bot.
    guild_settings: Guild object with the settings of the guild/server.
    embed_function: Function that returns the settings embed. The view expects the following arguments:
    - bot: Bot
    - ctx: context
    - guild_settings: ClanGuild object with the settings of the guild/server

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, guild_settings: guilds.Guild,
                 embed_function: callable, interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.bot = bot
        self.value = None
        self.embed_function = embed_function
        self.interaction = interaction
        self.user = ctx.author
        self.guild_settings = guild_settings
        self.add_item(components.ManageServerSettingsSelect(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(random.choice(strings.MSG_INTERACTION_ERRORS), ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()


class SettingsUserView(discord.ui.View):
    """View with a all components to manage user settings.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    bot: Bot.
    user_settings: User object with the settings of the user.
    embed_function: Function that returns the settings embed. The view expects the following arguments:
    - bot: Bot
    - user_settings: User object with the settings of the user

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, user_settings: users.User,
                 embed_function: callable, commands_settings: Dict, interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.bot = bot
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.user_settings = user_settings
        self.embed_function = embed_function
        self.commands_settings = commands_settings
        self.add_item(components.SetDonorTierSelect(self, 'Change your donor tier', 'user'))
        self.add_item(components.ManageUserSettingsSelect(self))
        self.add_item(components.SwitchSettingsSelect(self, commands_settings))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(random.choice(strings.MSG_INTERACTION_ERRORS), ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()


# --- Tracking ---
class StatsView(discord.ui.View):
    """View with a button to toggle command tracking.

    Also needs the message of the response with the view, so do AbortView.message = await message.reply('foo').

    Returns
    -------
    'track' if tracking was enabled
    'untrack' if tracking was disabled
    'timeout' on timeout.
    None if nothing happened yet.
    """
    def __init__(self, ctx: Union[commands.Context, discord.ApplicationContext], user: discord.User,
                 user_settings: users.User,
                 interaction_message: Optional[Union[discord.Message, discord.Interaction]] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.value = None
        self.ctx = ctx
        self.interaction_message = interaction_message
        self.user = ctx.author
        self.user_settings = user_settings
        if not user_settings.tracking_enabled:
            style = discord.ButtonStyle.green
            custom_id = 'track'
            label = 'Track me!'
        else:
            style = discord.ButtonStyle.grey
            custom_id = 'untrack'
            label = 'Stop tracking me!'
        self.add_item(components.ToggleTrackingButton(style=style, custom_id=custom_id, label=label))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(random.choice(strings.MSG_INTERACTION_ERRORS), ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        self.disable_all_items()
        if isinstance(self.ctx, discord.ApplicationContext):
            await functions.edit_interaction(self.interaction_message, view=self)
        else:
            await self.interaction_message.edit(view=self)
        self.stop()



# --- Dev ---
class DevEventReductionsView(discord.ui.View):
    """View with a all components to manage cooldown settings.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    bot: Bot.
    user_settings: User object with the settings of the user.
    embed_function: Function that returns the settings embed. The view expects the following arguments:
    - bot: Bot
    - user_settings: User object with the settings of the user

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, all_cooldowns: List[cooldowns.Cooldown],
                 embed_function: callable, interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.bot = bot
        self.ctx = ctx
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.all_cooldowns = all_cooldowns
        self.embed_function = embed_function
        self.add_item(components.ManageEventReductionsSelect(self, all_cooldowns, 'slash'))
        self.add_item(components.ManageEventReductionsSelect(self, all_cooldowns, 'text'))
        self.add_item(components.CopyEventReductionsButton(discord.ButtonStyle.grey, 'copy_slash_text',
                                                           'Copy slash > text'))
        self.add_item(components.CopyEventReductionsButton(discord.ButtonStyle.grey, 'copy_text_slash',
                                                           'Copy text > slash'))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(random.choice(strings.MSG_INTERACTION_ERRORS), ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()