# rebirth.py
"""Contains rebirth commands"""

import asyncio
from typing import Dict, Optional, Union

import discord

from database import users
from resources import emojis, functions, settings, strings


# --- Commands ---
async def command_rebirth_guide(
    ctx_or_message: Union[discord.ApplicationContext, discord.Message],
    user: discord.User, miri_mode: bool,
    bot: Optional[discord.Bot] = None
) -> None:
    """Rebirth guide command"""
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
    embed = await embed_rebirth_guide(ctx_or_message, inventory_data, user, miri_mode, user_settings)
    if isinstance(ctx_or_message, discord.ApplicationContext):
        await ctx_or_message.respond(embed=embed)
    else:
        await ctx_or_message.reply(embed=embed)


# --- Embeds ---
async def embed_rebirth_guide(ctx_or_message: Union[discord.ApplicationContext, discord.Message],
                              inventory_data: Dict, user: discord.User, miri_mode: bool, user_settings: users.User) -> discord.Embed:
    """Rebirth guide embed"""
    wooden_nuggets = inventory_data['wood'] % 15
    copper_nuggets_crafted = inventory_data['wood'] // 15
    copper_nuggets = inventory_data['copper_nugget'] + copper_nuggets_crafted
    silver_nuggets_crafted = copper_nuggets // 10
    copper_nuggets = copper_nuggets % 10
    silver_nuggets = inventory_data['silver_nugget'] + silver_nuggets_crafted
    golden_nuggets_crafted = silver_nuggets // 5
    silver_nuggets = silver_nuggets % 5
    golden_nuggets = inventory_data['golden_nugget'] + golden_nuggets_crafted
    honey = inventory_data['honey']
    leaves = inventory_data['leaf']
    epic_potions_crafted = min(inventory_data['golden_sapling'], honey // 10, leaves)
    honey = honey - (epic_potions_crafted * 10)
    leaves = leaves - epic_potions_crafted
    water_bottles_crafted = min(leaves // 40, honey // 3)
    if water_bottles_crafted > 0:
        honey = honey - honey % water_bottles_crafted
    upgrade_chips = (
        f'{emojis.CHIPS} Use {strings.SLASH_COMMANDS["chips show"]} to upgrade your chips.\n'
        f'{emojis.DETAIL2} _Craft and/or dismantle nuggets as you see fit._\n'
        f'{emojis.DETAIL} _**Reopen this rebirth guide after you\'re done.**_\n'
    )
    resources = (
        f'{emojis.READY} {strings.SLASH_COMMANDS["claim"]}\n'
        f'{emojis.READY} {strings.SLASH_COMMANDS["hive claim honey"]}\n'
        f'{emojis.ENERGY} {strings.SLASH_COMMANDS["raid"]} to empty your energy\n'
        f'{emojis.READY} {strings.SLASH_COMMANDS["hive claim energy"]} if ready\n'
        f'{emojis.ENERGY} {strings.SLASH_COMMANDS["raid"]} to empty your energy\n'
        f'{emojis.ENERGY_DRINK} {strings.SLASH_COMMANDS["use"]} your energy drink if you can\n'
        f'{emojis.ENERGY} {strings.SLASH_COMMANDS["raid"]} to empty your energy\n'
        f'{emojis.CHEST_WOODEN} If you have chests ready, do **not** open them until after rebirth\n'
    )

    craft_dismantle = ''
    if copper_nuggets_crafted > 0 and not miri_mode:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.NUGGET_COPPER} {strings.SLASH_COMMANDS["craft"]} `all` copper nuggets'
        )
    if silver_nuggets_crafted > 0 and not miri_mode:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.NUGGET_SILVER} {strings.SLASH_COMMANDS["craft"]} `all` silver nuggets'
        )
    if golden_nuggets_crafted > 0 and not miri_mode:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.NUGGET_GOLDEN} {strings.SLASH_COMMANDS["craft"]} `all` golden nuggets'
        )
    if epic_potions_crafted > 0 and not miri_mode:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.EPIC_POTION} {strings.SLASH_COMMANDS["craft"]} `all` epic potions'
        )
    if water_bottles_crafted > 0:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.WATER_BOTTLE} {strings.SLASH_COMMANDS["craft"]} `all` water bottles'
        )
    if craft_dismantle == '':
        craft_dismantle = f'{emojis.ENABLED} All done!'
        
    use = ''
    if (inventory_data['epic_potion'] > 0 or epic_potions_crafted > 0) and not miri_mode:
        epic_potions = inventory_data['epic_potion'] + epic_potions_crafted
        use = (
            f'{use}\n'  
            f'{emojis.EPIC_POTION} {strings.SLASH_COMMANDS["use"]} `all` epic potions (you have `{epic_potions:,}`)\n'
            f'{emojis.DETAIL} _Only sell them if you are in dire need of money._'
        )
    if inventory_data['chestnut_leaf'] > 0:
        use = (
            f'{use}\n'
            f'{emojis.LEAF_CHESTNUT} {strings.SLASH_COMMANDS["use"]} chestnut leaves if you need to (you have `{inventory_data["chestnut_leaf"]:,}`)'
        )
    if use == '':
        use = f'{emojis.ENABLED} All done!'
    
    sell = ''
    if wooden_nuggets > 0 and not miri_mode:
        sell = (
            f'{sell}\n'
            f'{emojis.WOOD} {strings.SLASH_COMMANDS["sell"]} `all` wooden nuggets'
        )
    if copper_nuggets > 0 and not miri_mode:
        sell = (
            f'{sell}\n'
            f'{emojis.NUGGET_COPPER} {strings.SLASH_COMMANDS["sell"]} `all` copper nuggets'
        )
    if silver_nuggets > 0 and not miri_mode:
        sell = (
            f'{sell}\n'
            f'{emojis.NUGGET_SILVER} {strings.SLASH_COMMANDS["sell"]} `all` silver nuggets'
        )
    if golden_nuggets > 0 and not miri_mode:
        sell = (
            f'{sell}\n'
            f'{emojis.NUGGET_GOLDEN} {strings.SLASH_COMMANDS["sell"]} `all` golden nuggets'
        )
    if (inventory_data['epic_potion'] > 0 or epic_potions_crafted > 0) and not miri_mode:
        sell = (
            f'{sell}\n'
            f'{emojis.EPIC_POTION} {strings.SLASH_COMMANDS["sell"]} `all` epic potions'
        )
    if inventory_data['chestnut_leaf'] > 0 and not miri_mode:
        sell = (
            f'{sell}\n'
            f'{emojis.LEAF_CHESTNUT} {strings.SLASH_COMMANDS["sell"]} `all` chestnut leaves'
        )
    if inventory_data['energy_drink'] > 0 and not miri_mode:
        sell = (
            f'{sell}\n'
            f'{emojis.ENERGY_DRINK} {strings.SLASH_COMMANDS["sell"]} `all` energy drinks'
        )
    if inventory_data['water_bottle'] > 0 or water_bottles_crafted > 0:
        sell = (
            f'{sell}\n'
            f'{emojis.WATER_BOTTLE} {strings.SLASH_COMMANDS["sell"]} `all` water bottles'
        )
    if leaves > 0:
        sell = (
            f'{sell}\n'
            f'{emojis.LEAF} {strings.SLASH_COMMANDS["sell"]} `all` leaves'
        )
    if honey > 0:
        sell = (
            f'{sell}\n'
            f'{emojis.HONEY} {strings.SLASH_COMMANDS["sell"]} `all` honey'
        )
    if inventory_data['apple'] > 0:
        sell = (
            f'{sell}\n'
            f'{emojis.APPLE} {strings.SLASH_COMMANDS["sell"]} `all` apples'
        )
    sell = (
        f'{sell}\n'
        f'_If you have any sweet apples or insecticide left, sell them all!_\n'
    )
    if sell == '':
        sell = f'{emojis.ENABLED} All done!'
        
    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{user.global_name}\'s rebirth guide',
    )
    if not miri_mode: embed.add_field(name='1. Upgrade chips', value=upgrade_chips, inline=False)
    if not miri_mode: embed.add_field(name='2. Resources', value=resources, inline=False)
    embed.add_field(name='3. Craft & Dismantle', value=craft_dismantle.strip(), inline=False)
    embed.add_field(name='4. Use', value=use.strip(), inline=False)
    embed.add_field(name='5. Sell', value=sell.strip(), inline=False)
    if user_settings.rebirth <= 10:
        level_target = 5 + user_settings.rebirth
    else:
        level_target = 15 + ((user_settings.rebirth - 10) // 2)
    footer = f'Rebirth {user_settings.rebirth} • Level {user_settings.level:,}/{level_target:,}'
    if user_settings.level >= level_target:
        footer = f'{footer} • Ready for rebirth'
    embed.set_footer(text = footer)
    return embed