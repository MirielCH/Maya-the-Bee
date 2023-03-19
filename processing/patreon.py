# patreon.py

from typing import Dict, Optional

import discord

from cache import messages
from database import users
from resources import exceptions, regex, strings


async def process_message(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                          user_settings: Optional[users.User]) -> bool:
    """Processes the message for all /use related actions.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    return_values = []
    return_values.append(await update_donor_tier_on_patreon(message, embed_data, user, user_settings))
    return any(return_values)


async def update_donor_tier_on_patreon(message: discord.Message, embed_data: Dict, user: Optional[discord.User],
                                       user_settings: Optional[users.User]) -> bool:
    """Update donor tier when opening the patreon message.

    Returns
    -------
    - True if a logo reaction should be added to the message
    - False otherwise
    """
    add_reaction = False
    search_strings = [
        'patreon and donations', #English
    ]
    if any(search_string in embed_data['title'].lower() for search_string in search_strings):
        if user is None:
            if embed_data['embed_user'] is not None:
                user = embed_data['embed_user']
                user_settings = embed_data['embed_user_settings']
            else:
                user_command_message = (
                    await messages.find_message(message.channel.id, regex.COMMAND_PATREON,
                                                user_name=embed_data['author']['name'])
                )
                user = user_command_message.author
        if user_settings is None:
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return add_reaction
        if not user_settings.bot_enabled: return add_reaction
        donor_tier = 0
        donor_tier_name = 'Non-donator'
        for index, name in enumerate(list(strings.DONOR_TIERS_EMOJIS.keys())):
            if name.lower() in embed_data['field0']['name'].lower():
                donor_tier = index
                donor_tier_name = name
                break
        if user_settings.donor_tier != donor_tier:
            await user_settings.update(donor_tier=donor_tier)
            await message.reply(
                f'Bzzt! I changed your donor tier setting to '
                f'{strings.DONOR_TIERS_EMOJIS[donor_tier_name]} `{donor_tier_name}`!'
            )
    return add_reaction