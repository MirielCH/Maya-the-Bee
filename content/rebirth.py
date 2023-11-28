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
    user: discord.User,
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
            content = strings.MSG_WAIT_FOR_INPUT.format(user=user.display_name,
                                                        command=strings.SLASH_COMMANDS["inventory"])
            bot_message = await functions.wait_for_bot_or_abort(ctx_or_message, bot_message_task, content)
        except asyncio.TimeoutError:
            await ctx_or_message.respond(
                strings.MSG_BOT_MESSAGE_NOT_FOUND.format(user=user.display_name, information='inventory'),
                ephemeral=True
            )
            return
        if bot_message is None: return
    inventory = ''
    for field in bot_message.embeds[0].fields:
        inventory = f'{inventory}{field.value}\n'
    inventory_data['wooden_nugget'] = await functions.get_inventory_item(inventory, 'woodennugget')
    inventory_data['copper_nugget'] = await functions.get_inventory_item(inventory, 'coppernugget')
    inventory_data['silver_nugget'] = await functions.get_inventory_item(inventory, 'silvernugget')
    inventory_data['golden_nugget'] = await functions.get_inventory_item(inventory, 'goldennugget')
    inventory_data['apple'] = await functions.get_inventory_item(inventory, 'apple')
    inventory_data['honey'] = await functions.get_inventory_item(inventory, 'honey')
    inventory_data['honey_pot'] = await functions.get_inventory_item(inventory, 'honeypot')
    embed = await embed_rebirth_guide(ctx_or_message, inventory_data, user, user_settings)
    if isinstance(ctx_or_message, discord.ApplicationContext):
        await ctx_or_message.respond(embed=embed)
    else:
        await ctx_or_message.reply(embed=embed)


# --- Embeds ---
async def embed_rebirth_guide(ctx_or_message: Union[discord.ApplicationContext, discord.Message],
                              inventory_data: Dict, user: discord.User, user_settings: users.User) -> discord.Embed:
    """Rebirth guide embed"""
    copper_nuggets = inventory_data['copper_nugget'] + (inventory_data['silver_nugget'] * 8)
    wooden_nuggets = inventory_data['wooden_nugget']
    copper_nuggets_crafted = 0
    copper_nuggets_dismantled = 0
    insecticides = 0
    while True:
        if copper_nuggets >= 1 and wooden_nuggets >= 5:
            insecticides += 1
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
    sweet_apples_craftable = min((honey + (honey_pots * 10)) // 30, apples // 10)
    honey_pots_crafted = sweet_apples_craftable * 2 - honey_pots
    resources = (
        f'{emojis.READY} Use {strings.SLASH_COMMANDS["claim"]}\n'
        f'{emojis.READY} Use {strings.SLASH_COMMANDS["hive claim honey"]}\n'
        f'{emojis.ENERGY} Empty your energy\n'
        f'{emojis.READY} Use {strings.SLASH_COMMANDS["hive claim energy"]} if ready\n'
        f'{emojis.ENERGY} Empty your energy\n'
        f'{emojis.ENERGY_DRINK} Use as many energy drinks as you can if you have any\n'
        f'{emojis.ENERGY} Empty your energy\n'
        f'{emojis.CHEST_WOODEN} If you have chests ready, do **not** open them until after rebirth\n'
    )

    craft_dismantle = ''
    if inventory_data['silver_nugget'] > 0:
        craft_dismantle = (
            f'{emojis.NUGGET_SILVER} Dismantle `all` silver nuggets'
        )
    if copper_nuggets_dismantled > 0:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.NUGGET_COPPER} Dismantle `{copper_nuggets_dismantled:,}` copper nuggets'
        )
    if copper_nuggets_crafted > 0:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.NUGGET_COPPER} Craft `{copper_nuggets_crafted:,}` copper nuggets'
        )
        
    if insecticides > 0:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.INSECTICIDE} Craft `all` insecticides'
        )
    if honey_pots_crafted > 0:
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.HONEY_POT} Craft `{honey_pots_crafted:,}` honey pots'
        )
    if sweet_apples_craftable > 0:
        if sweet_apples_craftable == apples // 10:
            sweet_apples_amount = 'all'
        else:
            sweet_apples_amount = f'{sweet_apples_craftable:,}'
        craft_dismantle = (
            f'{craft_dismantle}\n'
            f'{emojis.SWEET_APPLE} Craft `{sweet_apples_amount}` sweet apples'
        )
    craft_dismantle = (
        f'{craft_dismantle}\n'
        f'{emojis.EPIC_POTION} Craft `all` epic potions\n'
        f'{emojis.WATER_BOTTLE} Craft `all` water bottles\n'
        f'{emojis.HONEY_POT} Craft `all` honey pots'
    )

    use = (
        f'{emojis.INSECTICIDE} Use as many insecticides as you want\n'
        f'{emojis.EPIC_POTION} Use as many epic potions as you want\n'
        f'{emojis.SWEET_APPLE} Use as many sweet apples as you want\n'
        f'{emojis.LEAF_CHESTNUT} Use as many chestnut leaves as you **can**\n'
    )

    sell = ''
    if inventory_data['golden_nugget'] > 0:
        sell = (
            f'{emojis.NUGGET_GOLDEN} Sell `all` golden nuggets'
        )
    if copper_nuggets > 0:
        sell = (
            f'{sell}\n'
            f'{emojis.NUGGET_COPPER} Sell `all` copper nuggets'
        )
    sell = (
        f'{sell}\n'
        f'{emojis.INSECTICIDE} Sell `all` insecticides\n'
        f'{emojis.EPIC_POTION} Sell `all` epic potions\n'
        f'{emojis.SWEET_APPLE} Sell `all` sweet apples\n'
        f'{emojis.LEAF_CHESTNUT} Sell `all` chestnut leaves\n'
        f'{emojis.ENERGY_DRINK} Sell `all` energy drinks\n'
        f'{emojis.WATER_BOTTLE} Sell `all` water bottles\n'
        f'{emojis.HONEY_POT} Sell `all` honey pots\n'
        f'{emojis.APPLE} Sell `all` apples\n'
        f'{emojis.LEAF} Sell `all` leaves\n'
        f'{emojis.HONEY} Sell `all` honey\n'
    )

    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{user.display_name}\'s rebirth guide',
    )
    embed.add_field(name='1. Resources', value=resources, inline=False)
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