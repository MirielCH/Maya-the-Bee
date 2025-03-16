# components.py
"""Contains global interaction components"""

import asyncio
import re
from typing import Dict, List, Literal, Optional

import discord

from database import cooldowns, reminders, users
from resources import emojis, modals, strings, views


# --- Miscellaneous ---
class CustomButton(discord.ui.Button):
    """Simple Button. Writes its custom id to the view value, stops the view and does an invisible response."""
    def __init__(self, style: discord.ButtonStyle, custom_id: str, label: Optional[str],
                 emoji: Optional[discord.PartialEmoji] = None):
        super().__init__(style=style, custom_id=custom_id, label=label, emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        self.view.value = self.custom_id
        self.view.stop()
        try:
            await interaction.response.send_message()
        except Exception:
            pass


# --- Reminder list ---
class DeleteCustomRemindersButton(discord.ui.Button):
    """Button to activate the select to delete custom reminders"""
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.grey, custom_id='active_select', label='Delete custom reminders',
                         emoji=None, row=2)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.remove_item(self)
        self.view.add_item(DeleteCustomReminderSelect(self.view, self.view.custom_reminders))
        embed = await self.view.embed_function(self.view.bot, self.view.user, self.view.user_settings,
                                               self.view.user_reminders, self.view.show_timestamps)
        await interaction.response.edit_message(embed=embed, view=self.view)


class DeleteCustomReminderSelect(discord.ui.Select):
    """Select to delete custom reminders"""
    def __init__(self, view: discord.ui.View, custom_reminders: List[reminders.Reminder], row: Optional[int] = 2):
        self.custom_reminders = custom_reminders

        options = []
        for reminder in custom_reminders:
            label = f'{reminder.custom_id} - {reminder.message[:92]}'
            options.append(discord.SelectOption(label=label, value=str(reminder.custom_id), emoji=None))
        super().__init__(placeholder='Delete custom reminders', min_values=1, max_values=1, options=options,
                         row=row, custom_id=f'delete_reminders')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        for reminder in self.custom_reminders.copy():
            if reminder.custom_id == int(select_value):
                await reminder.delete()
                self.custom_reminders.remove(reminder)
                for user_reminder in self.view.user_reminders:
                    if user_reminder.custom_id == reminder.custom_id:
                        self.view.user_reminders.remove(user_reminder)
                        break
        embed = await self.view.embed_function(self.view.bot, self.view.user, self.view.user_settings,
                                               self.view.user_reminders, self.view.show_timestamps)
        self.view.remove_item(self)
        if self.custom_reminders:
            self.view.add_item(DeleteCustomReminderSelect(self.view, self.view.custom_reminders))
        await interaction.response.edit_message(embed=embed, view=self.view)


class ToggleTimestampsButton(discord.ui.Button):
    """Button to toggle reminder list between timestamps and timestrings"""
    def __init__(self, label: str):
        super().__init__(style=discord.ButtonStyle.grey, custom_id='toggle_timestamps', label=label,
                         emoji=None, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.show_timestamps = not self.view.show_timestamps
        if self.view.show_timestamps:
            self.label = 'Show time left'
        else:
            self.label = 'Show end time'
        embed = await self.view.embed_function(self.view.bot, self.view.user, self.view.user_settings,
                                               self.view.user_reminders, self.view.show_timestamps)
        await interaction.response.edit_message(embed=embed, view=self.view)


# --- Settings: General ---
class SwitchSettingsSelect(discord.ui.Select):
    """Select to switch between settings embeds"""
    def __init__(self, view: discord.ui.View, commands_settings: Dict[str, callable], row: Optional[int] = None):
        self.commands_settings = commands_settings
        options = []
        for label in commands_settings.keys():
            options.append(discord.SelectOption(label=label, value=label, emoji=None))
        super().__init__(placeholder='➜ Switch to other settings', min_values=1, max_values=1, options=options, row=row,
                         custom_id='switch_settings')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        await interaction.response.edit_message()
        await self.commands_settings[select_value](self.view.bot, self.view.ctx, switch_view = self.view)


# --- Settings: Reminder messages ---
class ReminderMessageSelect(discord.ui.Select):
    """Select to select reminder messages by activity"""
    def __init__(self, view: discord.ui.View, activities: List[str], placeholder: str, custom_id: str,
                 row: Optional[int] = None):
        options = []
        options.append(discord.SelectOption(label='All', value='all', emoji=None))
        for activity in activities:
            options.append(discord.SelectOption(label=activity.replace('-',' ').capitalize(), value=activity, emoji=None))
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, row=row,
                         custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        self.view.activity = select_value
        all_custom_ids = []
        for child in self.view.children:
            all_custom_ids.append(child.custom_id)
        if select_value == 'all':
            if 'set_message' in all_custom_ids or 'reset_message' in all_custom_ids:
                for child in self.view.children.copy():
                    if child.custom_id in ('set_message', 'reset_message'):
                        self.view.remove_item(child)
            if 'reset_all' not in all_custom_ids:
                self.view.add_item(SetReminderMessageButton(style=discord.ButtonStyle.red, custom_id='reset_all',
                                                            label='Reset all messages', row=1))
        else:
            if 'reset_all' in all_custom_ids:
                for child in self.view.children.copy():
                    if child.custom_id == 'reset_all':
                        self.view.remove_item(child)
            if 'set_message' not in all_custom_ids:
                self.view.add_item(SetReminderMessageButton(style=discord.ButtonStyle.blurple, custom_id='set_message',
                                                            label='Change', row=1))
            if 'reset_message' not in all_custom_ids:
                self.view.add_item(SetReminderMessageButton(style=discord.ButtonStyle.red, custom_id='reset_message',
                                                            label='Reset', row=1))
        embeds = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings, select_value)
        await interaction.response.edit_message(embeds=embeds, view=self.view)


class SetReminderMessageButton(discord.ui.Button):
    """Button to edit reminder messages"""
    def __init__(self, style: discord.ButtonStyle, custom_id: str, label: str, disabled: Optional[bool] = False,
                 emoji: Optional[discord.PartialEmoji] = None, row: Optional[int] = 1):
        super().__init__(style=style, custom_id=custom_id, label=label, emoji=emoji,
                         disabled=disabled, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        def check(m: discord.Message) -> bool:
            return m.author == interaction.user and m.channel == interaction.channel

        if self.custom_id == 'reset_all':
            confirm_view = views.ConfirmCancelView(self.view.ctx, styles=[discord.ButtonStyle.red, discord.ButtonStyle.grey])
            confirm_interaction = await interaction.response.send_message(
                f'**{interaction.user.global_name}**, this will reset **all** messages to the default one. '
                f'Are you sure?',
                view=confirm_view,
                ephemeral=True
            )
            confirm_view.interaction_message = confirm_interaction
            await confirm_view.wait()
            if confirm_view.value == 'confirm':
                kwargs = {}
                for activity in strings.ACTIVITIES:
                    activity_column = strings.ACTIVITIES_COLUMNS[activity]
                    kwargs[f'{activity_column}_message'] = strings.DEFAULT_MESSAGES[activity]
                await self.view.user_settings.update(**kwargs)
                await interaction.edit_original_response(
                    content=(
                        f'Changed all messages back to their default message.\n\n'
                        f'Note that running reminders do not update automatically.'
                    ),
                    view=None
                )
                embeds = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings,
                                                        self.view.activity)
                await interaction.message.edit(embeds=embeds, view=self.view)
                return
            else:
                await confirm_interaction.edit_original_response(content='Aborted', view=None)
                return
        elif self.custom_id == 'set_message':
            await interaction.response.send_message(
                f'**{interaction.user.global_name}**, please send the new reminder message to this channel (or `abort` to abort):',
            )
            try:
                answer = await self.view.bot.wait_for('message', check=check, timeout=60)
            except asyncio.TimeoutError:
                await interaction.edit_original_response(content=f'**{interaction.user.global_name}**, you didn\'t answer in time.')
                return
            if answer.mentions:
                for user in answer.mentions:
                    if user != answer.author:
                        await interaction.delete_original_response(delay=5)
                        followup_message = await interaction.followup.send(
                            content='Aborted. Please don\'t ping other people in your reminders.',
                        )
                        await followup_message.delete(delay=5)
                        return
            new_message = answer.content
            if new_message.lower() in ('abort','cancel','stop'):
                await interaction.delete_original_response(delay=3)
                followup_message = await interaction.followup.send('Aborted.')
                await followup_message.delete(delay=3)
                return
            if len(new_message) > 1024:
                await interaction.delete_original_response(delay=5)
                followup_message = await interaction.followup.send(
                    'This is a command to set a new message, not to write a novel :thinking:',
                )
                await followup_message.delete(delay=5)
                return
            for placeholder in re.finditer(r'\{(.+?)\}', new_message):
                placeholder_str = placeholder.group(1)
                if placeholder_str not in strings.DEFAULT_MESSAGES[self.view.activity]:
                    allowed_placeholders = ''
                    for placeholder in re.finditer(r'\{(.+?)\}', strings.DEFAULT_MESSAGES[self.view.activity]):
                        allowed_placeholders = (
                            f'{allowed_placeholders}\n'
                            f'{emojis.BP} {{{placeholder.group(1)}}}'
                        )
                    if allowed_placeholders == '':
                        allowed_placeholders = f'There are no placeholders available for this message.'
                    else:
                        allowed_placeholders = (
                            f'Available placeholders for this message:\n'
                            f'{allowed_placeholders.strip()}'
                        )
                    await interaction.delete_original_response(delay=3)
                    followup_message = await interaction.followup.send(
                        f'Invalid placeholder found.\n\n'
                        f'{allowed_placeholders}',
                        ephemeral=True
                    )
                    await followup_message.delete(delay=3)
                    return
            await interaction.delete_original_response(delay=3)
            followup_message = await interaction.followup.send(
                f'Message updated!\n\n'
                f'Note that running reminders do not update automatically.'
            )
            await followup_message.delete(delay=3)
        elif self.custom_id == 'reset_message':
            new_message = strings.DEFAULT_MESSAGES[self.view.activity]
        kwargs = {}
        activity_column = strings.ACTIVITIES_COLUMNS[self.view.activity]
        kwargs[f'{activity_column}_message'] = new_message
        await self.view.user_settings.update(**kwargs)
        embeds = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings, self.view.activity)
        if interaction.response.is_done():
            await interaction.message.edit(embeds=embeds, view=self.view)
        else:
            await interaction.response.edit_message(embeds=embeds, view=self.view)


# --- Settings: Server ---
class ManageServerSettingsSelect(discord.ui.Select):
    """Select to change server settings"""
    def __init__(self, view: discord.ui.View, row: Optional[int] = None):
        options = []
        options.append(discord.SelectOption(label='Change prefix',
                                            value='set_prefix', emoji=None))
        super().__init__(placeholder='Change settings', min_values=1, max_values=1, options=options, row=row,
                         custom_id='manage_server_settings')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        if select_value == 'set_prefix':
            modal = modals.SetPrefixModal(self.view)
            await interaction.response.send_modal(modal)
            return
        for child in self.view.children.copy():
            if isinstance(child, ManageServerSettingsSelect):
                self.view.remove_item(child)
                self.view.add_item(ManageServerSettingsSelect(self.view))
                break
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.guild_settings)
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self.view)
        else:
            await interaction.response.edit_message(embed=embed, view=self.view)


# --- Settings: User ---
class ManageUserSettingsSelect(discord.ui.Select):
    """Select to change user settings"""
    def __init__(self, view: discord.ui.View, row: Optional[int] = None):
        options = []
        reactions_emoji = emojis.ENABLED if view.user_settings.reactions_enabled else emojis.DISABLED
        dnd_emoji = emojis.ENABLED if view.user_settings.dnd_mode_enabled else emojis.DISABLED
        slash_emoji = emojis.ENABLED if view.user_settings.reminders_slash_enabled else emojis.DISABLED
        tracking_emoji = emojis.ENABLED if view.user_settings.tracking_enabled else emojis.DISABLED
        options.append(discord.SelectOption(label=f'Reactions', emoji=reactions_emoji,
                                            value='toggle_reactions'))
        options.append(discord.SelectOption(label=f'DND mode', emoji=dnd_emoji,
                                            value='toggle_dnd'))
        options.append(discord.SelectOption(label=f'Slash commands in reminders', emoji=slash_emoji,
                                            value='toggle_slash'))
        options.append(discord.SelectOption(label=f'Command tracking', emoji=tracking_emoji,
                                            value='toggle_tracking'))
        options.append(discord.SelectOption(label=f'Change last rebirth time',
                                            value='set_last_rebirth', emoji=None))
        super().__init__(placeholder='Change settings', min_values=1, max_values=1, options=options, row=row,
                         custom_id='manage_user_settings')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        if select_value == 'toggle_reactions':
            await self.view.user_settings.update(reactions_enabled=not self.view.user_settings.reactions_enabled)
        elif select_value == 'toggle_dnd':
            await self.view.user_settings.update(dnd_mode_enabled=not self.view.user_settings.dnd_mode_enabled)
        elif select_value == 'toggle_slash':
            await self.view.user_settings.update(reminders_slash_enabled=not self.view.user_settings.reminders_slash_enabled)
        elif select_value == 'toggle_tracking':
            await self.view.user_settings.update(tracking_enabled=not self.view.user_settings.tracking_enabled)
        elif select_value == 'set_last_rebirth':
            modal = modals.SetLastRebirthModal(self.view)
            await interaction.response.send_modal(modal)
            return
        for child in self.view.children.copy():
            if isinstance(child, ManageUserSettingsSelect):
                self.view.remove_item(child)
                self.view.add_item(ManageUserSettingsSelect(self.view))
                break
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings)
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self.view)
        else:
            await interaction.response.edit_message(embed=embed, view=self.view)


class SetDonorTierSelect(discord.ui.Select):
    """Select to set a donor tier"""
    def __init__(self, view: discord.ui.View, placeholder: str, donor_type: Optional[str] = 'user',
                 disabled: Optional[bool] = False, row: Optional[int] = None):
        self.donor_type = donor_type
        options = []
        for index, donor_tier in enumerate(list(strings.DONOR_TIERS_EMOJIS.keys())):
            options.append(discord.SelectOption(label=donor_tier, value=str(index),
                                                emoji=strings.DONOR_TIERS_EMOJIS[donor_tier]))
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, disabled=disabled,
                         row=row, custom_id=f'set_{donor_type}_donor_tier')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        await self.view.user_settings.update(donor_tier=int(select_value))
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings)
        await interaction.response.edit_message(embed=embed, view=self.view)


class ToggleUserSettingsSelect(discord.ui.Select):
    """Toggle select that shows and toggles the status of user settings (except alerts)."""
    def __init__(self, view: discord.ui.View, toggled_settings: Dict[str, str], placeholder: str,
                 custom_id: Optional[str] = 'toggle_user_settings', row: Optional[int] = None):
        self.toggled_settings = toggled_settings
        options = []
        options.append(discord.SelectOption(label='Enable all', value='enable_all', emoji=None))
        options.append(discord.SelectOption(label='Disable all', value='disable_all', emoji=None))
        for label, setting in toggled_settings.items():
            setting_enabled = getattr(view.user_settings, setting)
            if isinstance(setting_enabled, users.UserReminder):
                setting_enabled = getattr(setting_enabled, 'enabled')
            emoji = emojis.ENABLED if setting_enabled else emojis.DISABLED
            options.append(discord.SelectOption(label=label, value=setting, emoji=emoji))
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, row=row,
                         custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        kwargs = {}
        if select_value in ('enable_all','disable_all'):
            enabled = True if select_value == 'enable_all' else False
            for setting in self.toggled_settings.values():
                if not setting.endswith('_enabled'):
                    setting = f'{setting}_enabled'
                kwargs[setting] = enabled
        else:
            setting_value = getattr(self.view.user_settings, select_value)
            if isinstance(setting_value, users.UserReminder):
                setting_value = getattr(setting_value, 'enabled')
            if not select_value.endswith('_enabled'):
                select_value = f'{select_value}_enabled'
            kwargs[select_value] = not setting_value
        await self.view.user_settings.update(**kwargs)
        for child in self.view.children.copy():
            if child.custom_id == self.custom_id:
                self.view.remove_item(child)
                self.view.add_item(ToggleUserSettingsSelect(self.view, self.toggled_settings,
                                                            self.placeholder, self.custom_id))
                break
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings)
        await interaction.response.edit_message(embed=embed, view=self.view)


# --- Tracking ---
class ToggleTrackingButton(discord.ui.Button):
    """Button to toggle the auto-ready feature"""
    def __init__(self, style: Optional[discord.ButtonStyle], custom_id: str, label: str,
                 disabled: bool = False, emoji: Optional[discord.PartialEmoji] = None):
        super().__init__(style=style, custom_id=custom_id, label=label, emoji=emoji,
                         disabled=disabled, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        enabled = True if self.custom_id == 'track' else False
        await self.view.user_settings.update(tracking_enabled=enabled)
        self.view.value = self.custom_id
        await self.view.user_settings.refresh()
        if self.view.user_settings.tracking_enabled:
            self.style = discord.ButtonStyle.grey
            self.label = 'Stop tracking me!'
            self.custom_id = 'untrack'
        else:
            self.style = discord.ButtonStyle.green
            self.label = 'Track me!'
            self.custom_id = 'track'
        if not interaction.response.is_done():
            await interaction.response.edit_message(view=self.view)
        else:
            await self.view.message.edit(view=self.view)


# --- Dev ---
class CopyEventReductionsButton(discord.ui.Button):
    """Button to toggle the auto-ready feature"""
    def __init__(self, style: Optional[discord.ButtonStyle], custom_id: str, label: str,
                 disabled: bool = False, emoji: Optional[discord.PartialEmoji] = None):
        super().__init__(style=style, custom_id=custom_id, label=label, emoji=emoji,
                         disabled=disabled)

    async def callback(self, interaction: discord.Interaction) -> None:
        for cooldown in self.view.all_cooldowns:
            if self.custom_id == 'copy_slash_text':
                await cooldown.update(event_reduction_mention=cooldown.event_reduction_slash)
            else:
                await cooldown.update(event_reduction_slash=cooldown.event_reduction_mention)
        embed = await self.view.embed_function(self.view.all_cooldowns)
        if not interaction.response.is_done():
            await interaction.response.edit_message(embed=embed, view=self.view)
        else:
            await self.view.message.edit(embed=embed, view=self.view)


class ManageEventReductionsSelect(discord.ui.Select):
    """Select to manage cooldowns"""
    def __init__(self, view: discord.ui.View, all_cooldowns: List[cooldowns.Cooldown],
                 cd_type: Literal['slash', 'text'], row: Optional[int] = None):
        self.all_cooldowns = all_cooldowns
        self.cd_type = cd_type
        options = []
        options.append(discord.SelectOption(label=f'All',
                                            value='all'))
        for cooldown in all_cooldowns:
            options.append(discord.SelectOption(label=cooldown.activity.capitalize(),
                                                value=cooldown.activity))
            cooldown.update()
        placeholders = {
            'slash': 'Change slash event reductions',
            'text': 'Change text event reductions',
        }
        super().__init__(placeholder=placeholders[cd_type], min_values=1, max_values=1, options=options, row=row,
                         custom_id=f'manage_{cd_type}')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        modal = modals.SetEventReductionModal(self.view, select_value, self.cd_type)
        await interaction.response.send_modal(modal)


class SetProgressBarColorSelect(discord.ui.Select):
    """Select to change the prune XP progress bar color"""
    def __init__(self, view: discord.ui.View, setting: str, placeholder: str, row: Optional[int] = None):
        options = []
        self.setting = setting
        for color in strings.PROGRESS_BAR_COLORS:
            options.append(discord.SelectOption(label=color, value=color.lower(),
                                                emoji=getattr(emojis, f'PROGRESS_100_{color.upper()}', None)))
        options.append(discord.SelectOption(label='Make it random!', value='random'))
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, row=row,
                         custom_id=placeholder)

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        await self.view.user_settings.update(**{self.setting: select_value})
        for child in self.view.children.copy():
            if isinstance(child, SetProgressBarColorSelect):
                if child.custom_id != self.custom_id: continue
                self.view.remove_item(child)
                self.view.add_item(SetProgressBarColorSelect(self.view, self.setting, self.placeholder))
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings)
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self.view)
        else:
            await interaction.response.edit_message(embed=embed, view=self.view)


class SetAlertSettingsSelect(discord.ui.Select):
    """Select to change the alert settings"""
    def __init__(self, view: discord.ui.View, row: Optional[int] = None):
        options = []
        alert_captcha_mode = 'ping' if view.user_settings.alert_captcha_dm else 'DM'
        alert_nugget_mode = 'ping' if view.user_settings.alert_nugget_dm else 'DM'
        alert_rebirth_mode = 'ping' if view.user_settings.alert_rebirth_dm else 'DM'
        options.append(discord.SelectOption(label=f'Send captcha alerts as {alert_captcha_mode}', value='alert_captcha_dm'))
        options.append(discord.SelectOption(label=f'Send nugget alerts as {alert_nugget_mode}', value='alert_nugget_dm'))
        options.append(discord.SelectOption(label=f'Send rebirth alerts as {alert_rebirth_mode}', value='alert_rebirth_dm'))
        
        super().__init__(placeholder='Change alert settings', min_values=1, max_values=1, options=options, row=row,
                         custom_id='set_nugget_settings')

    async def callback(self, interaction: discord.Interaction):
        kwargs = {}
        select_value = self.values[0]
        current_setting = getattr(self.view.user_settings, select_value)
        kwargs[select_value] = not current_setting
        await self.view.user_settings.update(**kwargs)
        for child in self.view.children.copy():
            if isinstance(child, SetAlertSettingsSelect):
                self.view.remove_item(child)
                self.view.add_item(SetAlertSettingsSelect(self.view))
                break
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings)
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self.view)
        else:
            await interaction.response.edit_message(embed=embed, view=self.view)
            

class SetAlertNuggetThresholdSelect(discord.ui.Select):
    """Select to change the nugget alert threshold"""
    def __init__(self, view: discord.ui.View, row: Optional[int] = None):
        options = []
        for name, emoji in strings.NUGGETS.items():
            options.append(discord.SelectOption(label=name, value=name, emoji=emoji))
        super().__init__(placeholder='Change nugget alert threshold', min_values=1, max_values=1, options=options, row=row,
                         custom_id='set_nugget_alert_threshold')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        await self.view.user_settings.update(alert_nugget_threshold=select_value)
        for child in self.view.children.copy():
            if isinstance(child, SetAlertNuggetThresholdSelect):
                self.view.remove_item(child)
                self.view.add_item(SetAlertNuggetThresholdSelect(self.view))
                break
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings)
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self.view)
        else:
            await interaction.response.edit_message(embed=embed, view=self.view)


# --- Miscellaneous ---
class TopicSelect(discord.ui.Select):
    """Topic Select"""
    def __init__(self, topics: dict, active_topic: str, placeholder: str, row: Optional[int] = None):
        self.topics = topics
        options = []
        for topic in topics.keys():
            label = topic
            emoji = '🔹' if topic == active_topic else None
            options.append(discord.SelectOption(label=label, value=label, emoji=emoji))
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, row=row,
                         custom_id='select_topic')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        self.view.active_topic = select_value
        for child in self.view.children:
            if child.custom_id == 'select_topic':
                options = []
                for topic in self.topics.keys():
                    label = topic
                    emoji = '🔹' if topic == self.view.active_topic else None
                    options.append(discord.SelectOption(label=label, value=label, emoji=emoji))
                child.options = options
                break
        embed = await self.view.topics[select_value]()
        await interaction.response.edit_message(embed=embed, view=self.view)