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
    for field in bot_message.embeds[0].fields:
        inventory = f'{inventory}{field.value}\n'
    inventory_data['apple'] = await functions.get_inventory_item(inventory, 'apple')
    inventory_data['chestnut_leaf'] = await functions.get_inventory_item(inventory, 'chestnutleaf')
    inventory_data['copper_nugget'] = await functions.get_inventory_item(inventory, 'coppernugget')
    inventory_data['energy_drink'] = await functions.get_inventory_item(inventory, 'energydrink')
    inventory_data['epic_potion'] = await functions.get_inventory_item(inventory, 'epicpotion')
    inventory_data['golden_nugget'] = await functions.get_inventory_item(inventory, 'goldennugget')
    inventory_data['golden_sapling'] = await functions.get_inventory_item(inventory, 'golden_sapling')
    inventory_data['honey'] = await functions.get_inventory_item(inventory, 'honey')
    inventory_data['honey_pot'] = await functions.get_inventory_item(inventory, 'honeypot')
    inventory_data['insecticide'] = await functions.get_inventory_item(inventory, 'insecticide')
    inventory_data['leaf'] = await functions.get_inventory_item(inventory, 'leaf')
    inventory_data['silver_nugget'] = await functions.get_inventory_item(inventory, 'silvernugget')
    inventory_data['sweet_apple'] = await functions.get_inventory_item(inventory, 'sweet_apple')
    inventory_data['water_bottle'] = await functions.get_inventory_item(inventory, 'waterbottle')
    inventory_data['wooden_nugget'] = await functions.get_inventory_item(inventory, 'woodennugget')
    embed = await embed_rebirth_guide(ctx_or_message, inventory_data, user, miri_mode, user_settings)
    if isinstance(ctx_or_message, discord.ApplicationContext):
        await ctx_or_message.respond(embed=embed)
    else:
        await ctx_or_message.reply(embed=embed)


# --- Embeds ---
async def embed_rebirth_guide(ctx_or_message: Union[discord.ApplicationContext, discord.Message],
                              inventory_data: Dict, user: discord.User, miri_mode: bool, user_settings: users.User) -> discord.Embed:
    """Rebirth guide embed"""
    copper_nuggets = inventory_data['copper_nugget'] + (inventory_data['silver_nugget'] * 8)
    wooden_nuggets = inventory_data['wooden_nugget']
    copper_nuggets_crafted = 0
    copper_nuggets_dismantled = 0
    insecticides_crafted = 0
    while True:
        if copper_nuggets >= 1 and wooden_nuggets >= 5:
            insecticides_crafted += 1
            copper_nuggets -= 1
            wooden_nuggets -= 5
        elif copper_nuggets < 1 and wooden_nuggets >= 20:
            copper_nuggets += 1
            wooden_nuggets -= 15
            copper_nuggets_crafted += 1
        elif copper_nuggets > 1 and wooden_nuggets < 5:
            copper_nuggets -= 1
            wooden_nuggets += 12
            copper_nuggets_dismantled += 1
        else:
            if wooden_nuggets >= 15: copper_nuggets_dismantled -= 1
            break
    apples = inventory_data['apple']
    honey = inventory_data['honey']
    honey_pots = inventory_data['honey_pot']
    sweet_apples_crafted = min((honey + (honey_pots * 10)) // 30, apples // 10)
    apples = apples - (sweet_apples_crafted * 10)
    honey_pots_crafted = sweet_apples_crafted * 2 - honey_pots
    if honey_pots_crafted < 0: honey_pots_crafted = 0
    honey = honey - (honey_pots_crafted * 10)
    leaves = inventory_data['leaf']
    epic_potions_crafted = min(inventory_data['golden_sapling'], honey // 10, leaves)
    honey = honey - (epic_potions_crafted * 10)
    leaves = leaves - epic_potions_crafted
    water_bottles_crafted = min(leaves // 40, honey // 3)
    if water_bottles_crafted > 0:
        honey = honey - honey % water_bottles_crafted
    resources = (
        f'{emojis.READY} {strings.SLASH_COMMANDS["claim"]}\n'
        f'{emojis.READY} {strings.SLASH_COMMANDS["hive claim honey"]}\n'
        f'{emojis.ENERGY} {strings.SLASH_COMMANDS["raid"]} to empty your energy\n'
        f'{emojis.READY} {strings.SLASH_COMMANDS["hive claim energy"]} if ready\n'
        f'{emojis.ENERGY} {strings.SLASH_COMMANDS["raid"]} to empty your energy\n'
        f'{emojis.ENERGY_DRINK} {strings.SLASH_COMMANDS["use"]} as many energy drinks as you can if you have any\n'
        f'{emojis.ENERGY} {strings.SLASH_COMMANDS["raid"]} to empty your energy\n'
        f'{emojis.CHEST_WOODEN} If you have chests ready, do **not** open them until after rebirth\n'
    )

    craft_dismantle = ''
    if inventory_data['silver_nugget'] > 0 and not miri_mode:
        craft_dismantle = (
            f'{emojis.NUGGET_SILVER} {strings.SLASH_COMMANDS["dismantle"]} `all` silver nuggets'
        )
    if copper_nuggets_dismantled > 0 and not miri_mode:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.NUGGET_COPPER} {strings.SLASH_COMMANDS["dismantle"]} `{copper_nuggets_dismantled:,}` copper nuggets'
        )
    if copper_nuggets_crafted > 0 and not miri_mode:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.NUGGET_COPPER} {strings.SLASH_COMMANDS["craft"]} `{copper_nuggets_crafted:,}` copper nuggets'
        )
        
    if insecticides_crafted > 0 and not miri_mode:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.INSECTICIDE} {strings.SLASH_COMMANDS["craft"]} `all` insecticides'
        )
    if honey_pots_crafted > 0:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.HONEY_POT} {strings.SLASH_COMMANDS["craft"]} `{honey_pots_crafted:,}` honey pots'
        )
    if sweet_apples_crafted > 0:
        if apples < 10 or (sweet_apples_crafted == (honey_pots + honey_pots_crafted) // 2):
            sweet_apples_amount = 'all'
        else:
            sweet_apples_amount = f'{sweet_apples_crafted:,}'
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.SWEET_APPLE} {strings.SLASH_COMMANDS["craft"]} `{sweet_apples_amount}` sweet apples'
        )
    if epic_potions_crafted > 0:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.EPIC_POTION} {strings.SLASH_COMMANDS["craft"]} `all` epic potions'
        )
    if water_bottles_crafted > 0:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.WATER_BOTTLE} {strings.SLASH_COMMANDS["craft"]} `all` water bottles'
        )
    if honey >= 10 and not miri_mode:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.HONEY_POT} {strings.SLASH_COMMANDS["craft"]} `all` honey pots'
        )
    if craft_dismantle == '':
        craft_dismantle = f'{emojis.ENABLED} All done!'
        
    use = ''
    if inventory_data['epic_potion'] > 0 or epic_potions_crafted > 0:
        epic_potions = inventory_data['epic_potion'] + epic_potions_crafted
        use = (
            f'{use}\n'
            f'{emojis.EPIC_POTION} {strings.SLASH_COMMANDS["use"]} `{epic_potions:,}` epic potions\n'
            f'{emojis.DETAIL} _Only sell them if you are in dire need of money._'
        )
    if inventory_data['insecticide'] > 0 or insecticides_crafted > 0:
        insecticides = inventory_data['insecticide'] + insecticides_crafted
        use = (
            f'{use}\n'
            f'{emojis.INSECTICIDE} {strings.SLASH_COMMANDS["use"]} insecticides if you need to (you have `{insecticides:,}`)'        
        )
    if inventory_data['sweet_apple'] > 0 or sweet_apples_crafted > 0:
        sweet_apples = inventory_data['sweet_apple'] + sweet_apples_crafted
        use = (
            f'{use}\n'
            f'{emojis.SWEET_APPLE} {strings.SLASH_COMMANDS["use"]} sweet apples if you need to (you have `{sweet_apples:,}`)'
        )
    if inventory_data['chestnut_leaf'] > 0:
        use = (
            f'{use}\n'
            f'{emojis.LEAF_CHESTNUT} {strings.SLASH_COMMANDS["use"]} chestnut leaves if you need to (you have `{inventory_data["chestnut_leaf"]:,}`)'
        )
    if use == '':
        use = f'{emojis.ENABLED} All done!'
    
    sell = ''
    if inventory_data['golden_nugget'] > 0 and not miri_mode:
        sell = (
            f'{emojis.NUGGET_GOLDEN} {strings.SLASH_COMMANDS["sell"]} `all` golden nuggets'
        )
    if copper_nuggets > 0 and not miri_mode:
        sell = (
            f'{sell}\n'
            f'{emojis.NUGGET_COPPER} {strings.SLASH_COMMANDS["sell"]} `all` copper nuggets'
        )
    if (inventory_data['insecticide'] > 0 or insecticides_crafted > 0) and not miri_mode:
        sell = (
            f'{sell}\n'
            f'{emojis.INSECTICIDE} {strings.SLASH_COMMANDS["sell"]} `all` insecticides'
        )
    if (inventory_data['epic_potion'] > 0 or epic_potions_crafted > 0) and not miri_mode:
        sell = (
            f'{sell}\n'
            f'{emojis.EPIC_POTION} {strings.SLASH_COMMANDS["sell"]} `all` epic potions'
        )
    if inventory_data['sweet_apple'] > 0 or sweet_apples_crafted > 0:
        sell = (
            f'{sell}\n'
            f'{emojis.SWEET_APPLE} {strings.SLASH_COMMANDS["sell"]} `all` sweet apples'
        )
    if inventory_data['chestnut_leaf'] > 0:
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
    if inventory_data['honey_pot'] > 0 or honey_pots_crafted > 0 and not miri_mode:
        sell = (
            f'{sell}\n'
            f'{emojis.HONEY_POT} {strings.SLASH_COMMANDS["sell"]} `all` honey pots'
        )
    if leaves > 0 and not miri_mode:
        sell = (
            f'{sell}\n'
            f'{emojis.LEAF} {strings.SLASH_COMMANDS["sell"]} `all` leaves'
        )
    if honey > 0:
        sell = (
            f'{sell}\n'
            f'{emojis.HONEY} {strings.SLASH_COMMANDS["sell"]} `all` honey'
        )
    if apples > 0 and not miri_mode:
        sell = (
            f'{sell}\n'
            f'{emojis.APPLE} {strings.SLASH_COMMANDS["sell"]} `all` apples'
        )
    if sell == '':
        sell = f'{emojis.ENABLED} All done!'
        
    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{user.global_name}\'s rebirth guide',
    )
    if not miri_mode: embed.add_field(name='1. Resources', value=resources, inline=False)
    embed.add_field(name='2. Craft & Dismantle', value=craft_dismantle.strip(), inline=False)
    embed.add_field(name='3. Use', value=use.strip(), inline=False)
    embed.add_field(name='4. Sell', value=sell.strip(), inline=False)
    if user_settings.rebirth <= 10:
        level_target = 5 + user_settings.rebirth
    else:
        level_target = 15 + ((user_settings.rebirth - 10) // 2)
    footer = f'Rebirth {user_settings.rebirth} • Level {user_settings.level:,}/{level_target:,}'
    if user_settings.level >= level_target:
        footer = f'{footer} • Ready for rebirth'
    embed.set_footer(text = footer)
    if isinstance(ctx_or_message, discord.ApplicationContext):
        embed.description = '_Tip: You can open this guide faster using `tree i rb`!_'
    return embed