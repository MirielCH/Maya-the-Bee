# modals.py

import re
from typing import Literal

import discord
from discord import utils
from discord.ui import InputText, Modal


# --- Settings: Server ---
class SetPrefixModal(Modal):
    def __init__(self, view: discord.ui.View) -> None:
        super().__init__(title='Change prefix')
        self.view = view
        self.add_item(
            InputText(
                label='New prefix:',
                placeholder="Enter prefix ...",
            )
        )

    async def callback(self, interaction: discord.Interaction):
        new_prefix = self.children[0].value
        await self.view.guild_settings.update(prefix=new_prefix)
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.guild_settings)
        await interaction.response.edit_message(embed=embed, view=self.view)


# --- Settings: User ---
class SetLastRebirthModal(Modal):
    def __init__(self, view: discord.ui.View) -> None:
        super().__init__(title='Change last rebirth time')
        self.view = view
        self.add_item(
            InputText(
                label='Message ID or link of your last rebirth:',
                placeholder="Enter message ID or link ..."
            )
        )

    async def callback(self, interaction: discord.Interaction):
        msg_error = (
            f'No valid message ID or URL found.\n\n'
            f'Use the ID or link of the message that announced your rebirth\n'
            f'If you don\'t have access to that message, choose another message that is as close '
            f'to your last rebirth as possible.\n'
            f'Note that it does not matter if I can actually read the message, I only need the ID or link.'
        )
        message_id_link = self.children[0].value.lower()
        if 'discord.com/channels' in message_id_link:
            message_id_match = re.search(r"\/[0-9]+\/[0-9]+\/(.+?)$", message_id_link)
            if message_id_match:
                message_id = message_id_match.group(1)
            else:
                await interaction.response.edit_message(view=self.view)
                await interaction.followup.send(msg_error, ephemeral=True)
                return
        else:
            message_id = message_id_link
        try:
            rebirth_time = utils.snowflake_time(int(message_id)).replace(microsecond=0)
        except:
            await interaction.response.edit_message(view=self.view)
            await interaction.followup.send(msg_error, ephemeral=True)
            return
        await self.view.user_settings.update(last_rebirth=rebirth_time.isoformat(sep=' '))
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings)
        await interaction.response.edit_message(embed=embed, view=self.view)


# -- Dev ---
class SetEventReductionModal(Modal):
    def __init__(self, view: discord.ui.View, activity: str, cd_type: Literal['slash', 'text']) -> None:
        titles = {
            'slash': 'Change slash event reduction',
            'text': 'Change text event reduction',
        }
        labels = {
            'slash': 'Event reduction in percent:',
            'text': 'Event reduction in percent:',
        }
        placeholders = {
            'slash': 'Enter event reduction...',
            'text': 'Enter event reduction...',
        }
        super().__init__(title=titles[cd_type])
        self.view = view
        self.activity = activity
        self.cd_type = cd_type
        self.add_item(
            InputText(
                label=labels[cd_type],
                placeholder=placeholders[cd_type],
            )
        )

    async def callback(self, interaction: discord.Interaction):
        new_value = self.children[0].value
        try:
            new_value = float(new_value)
        except ValueError:
            await interaction.response.edit_message(view=self.view)
            await interaction.followup.send('That is not a valid number.', ephemeral=True)
            return
        if not 0 <= new_value <= 100:
            await interaction.response.edit_message(view=self.view)
            await interaction.followup.send('The reduction needs to be between 0 and 100 percent.', ephemeral=True)
            return
        if self.activity == 'all':
            for cooldown in self.view.all_cooldowns:
                if self.cd_type == 'slash':
                    await cooldown.update(event_reduction_slash=new_value)
                else:
                    await cooldown.update(event_reduction_mention=new_value)
        else:
            for cooldown in self.view.all_cooldowns:
                if cooldown.activity == self.activity:
                    if self.cd_type == 'slash':
                        await cooldown.update(event_reduction_slash=new_value)
                    else:
                        await cooldown.update(event_reduction_mention=new_value)
        embed = await self.view.embed_function(self.view.all_cooldowns)
        await interaction.response.edit_message(embed=embed, view=self.view)