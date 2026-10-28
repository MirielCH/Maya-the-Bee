# inventory.py
"""Contains inventory commands"""

import asyncio
from typing import Dict, Optional, Union

import discord

from database import users
from resources import emojis, functions, settings, strings


# --- Commands ---
async def command_inventory_calculator(
    ctx_or_message: Union[discord.ApplicationContext, discord.Message],
    user: discord.User,
    bot: Optional[discord.Bot] = None
) -> None:
    """Inventory calculator command"""
    user_settings: users.User = await users.get_user(user.id)
    inventory_data = {}
    if isinstance(ctx_or_message, discord.Message):
        bot_message = ctx_or_message
    else:
        bot_message_task = asyncio.ensure_future(functions.wait_for_inventory_message(bot, ctx_or_message))
        try:
            content = strings.MSG_WAIT_FOR_INPUT.format(user=user.global_name,
                                                        command=strings.SLASH_COMMANDS["inventory"])
            bot_message = await functions.wait_for_bot_or_abort(ctx_or_message, bot_message_task, content)
        except asyncio.TimeoutError:
            await ctx_or_message.respond(
                strings.MSG_BOT_MESSAGE_NOT_FOUND.format(user=user.global_name, information='inventory'),
                ephemeral=True
            )
            return
        if bot_message is None: return
    inventory = ''
    if bot_message.embeds:
        for field in bot_message.embeds[0].fields:
            inventory = f'{inventory}{field.value}\n'
    if bot_message.components:
        text_displays = await functions.parse_text_displays(bot_message)
        for text_display in text_displays:
            inventory = f'{inventory}{text_display}\n'
    inventory_data['apple'] = await functions.get_inventory_item(inventory, 'apple_2')
    inventory_data['chestnut_leaf'] = await functions.get_inventory_item(inventory, 'chestnut_leaf_2')
    inventory_data['copper_nugget'] = await functions.get_inventory_item(inventory, 'copper_nugget_2')
    inventory_data['energy_drink'] = await functions.get_inventory_item(inventory, 'edrink_2')
    inventory_data['epic_potion'] = await functions.get_inventory_item(inventory, 'epic_potion_2')
    inventory_data['golden_nugget'] = await functions.get_inventory_item(inventory, 'golden_nugget_2')
    inventory_data['golden_sapling'] = await functions.get_inventory_item(inventory, 'golden_sapling_2')
    inventory_data['honey'] = await functions.get_inventory_item(inventory, 'honey_3')
    inventory_data['leaf'] = await functions.get_inventory_item(inventory, 'leaf_2')
    inventory_data['silver_nugget'] = await functions.get_inventory_item(inventory, 'silver_nugget_2')
    inventory_data['water_bottle'] = await functions.get_inventory_item(inventory, 'water_bottle_2')
    inventory_data['wood'] = await functions.get_inventory_item(inventory, 'wood_3')
    embed = await embed_inventory_calculator(ctx_or_message, inventory_data, user, user_settings)
    if isinstance(ctx_or_message, discord.ApplicationContext):
        await ctx_or_message.respond(embed=embed)
    else:
        await ctx_or_message.reply(embed=embed)


# --- Embeds ---
async def embed_inventory_calculator(ctx_or_message: Union[discord.ApplicationContext, discord.Message],
                                     inventory_data: Dict, user: discord.User, user_settings: users.User) -> discord.Embed:
    """Inventory calculator embed"""

    # Nuggets
    wooden_nuggets = (
        inventory_data['wood']
        + inventory_data['copper_nugget'] * 12
        + inventory_data['silver_nugget'] * 12 * 8
        + inventory_data['golden_nugget'] * 12 * 8 * 4
    )
    copper_nuggets = (
        inventory_data['wood'] // 15
        + inventory_data['copper_nugget']
        + inventory_data['silver_nugget'] * 8
        + inventory_data['golden_nugget'] * 8 * 4
    )
    silver_nuggets = (
        inventory_data['wood'] // 15 // 10
        + inventory_data['copper_nugget'] // 10
        + inventory_data['silver_nugget']
        + inventory_data['golden_nugget'] * 4
    )
    golden_nuggets = (
        inventory_data['wood'] // 15 // 10 // 5
        + inventory_data['copper_nugget'] // 10 // 5
        + inventory_data['silver_nugget'] // 5
        + inventory_data['golden_nugget']
    )

    # Water bottles
    water_bottles = inventory_data['water_bottle'] + min(inventory_data['leaf'] // 40, inventory_data['honey'] // 3)

    # Epic potions
    epic_potions = inventory_data['epic_potion'] + min(inventory_data['golden_sapling'], inventory_data['honey'] // 10, inventory_data['leaf'])

    nuggets = (
        f'{emojis.WOOD} `{wooden_nuggets:,}` wooden nuggets\n'
        f'{emojis.NUGGET_COPPER} `{copper_nuggets:,}` copper nuggets\n'
        f'{emojis.NUGGET_SILVER} `{silver_nuggets:,}` silver nuggets\n'
        f'{emojis.NUGGET_GOLDEN} `{golden_nuggets:,}` golden nuggets\n'
    )
    consumables = (
        f'{emojis.WATER_BOTTLE} `{water_bottles:,}` water bottles\n'
        f'{emojis.EPIC_POTION} `{epic_potions:,}` epic potions\n'
    )
        
    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{user.global_name}\'s inventory calculator',
        description = (
            f'_Each amount assumes you use your whole inventory **on that item only**. You can\'t craft all of these '
            f'items with the same materials._\n'
            f'_Diamond nuggets are not included in the calculation._'
        )
    )
    embed.add_field(name='Nuggets', value=nuggets, inline=False)
    embed.add_field(name='Consumables', value=consumables, inline=False)
    
    return embed