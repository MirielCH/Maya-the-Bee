# skins.py
"""Contains the skins command"""

from typing import Optional

import discord

from resources import emojis, functions, settings, strings


SKINS_NAMES = {
    'skin_default': 'Default',
    'skin_dinosaur': 'Anna\'s Dinosaur Enclosure',
    'skin_copper': 'Copper',
    'skin_diamond': 'Diamond',
    'skin_easter': 'Easter Event',
    'skin_dragon': 'FAM\'s Purple Dragon',
    'skin_fashalin': 'Fort Fashalin',
    'skin_golden': 'Golden',
    'skin_halloween': 'Halloween Event',
    'skin_vector': 'Innovative Vector',
    'skin_patreon': 'Patreon Member',
    'skin_phoenix': 'Phoenix',
    'skin_shinobi': 'Shinobi Skirmishes',
    'skin_silver': 'Silver',
    'skin_xmas': 'XMAS Event',
}

SKINS_EMOJIS = {
    strings.SKIN_DEFAULT: emojis.SKIN_DEFAULT,
    strings.SKIN_DINOSAUR: emojis.SKIN_DINOSAUR,
    strings.SKIN_COPPER: emojis.SKIN_COPPER,
    strings.SKIN_DIAMOND: emojis.SKIN_DIAMOND,
    strings.SKIN_EASTER: emojis.SKIN_EASTER,
    strings.SKIN_DRAGON: emojis.SKIN_DRAGON,
    strings.SKIN_GOLDEN: emojis.SKIN_GOLDEN,
    strings.SKIN_HALLOWEEN: emojis.SKIN_HALLOWEEN,
    strings.SKIN_VECTOR: emojis.SKIN_VECTOR,
    strings.SKIN_PATREON: emojis.SKIN_PATREON,
    strings.SKIN_PHOENIX: emojis.SKIN_PHOENIX,
    strings.SKIN_FASHALIN: emojis.SKIN_FASHALIN,
    strings.SKIN_SHINOBI: emojis.SKIN_SHINOBI,
    strings.SKIN_SILVER: emojis.SKIN_SILVER,
    strings.SKIN_XMAS: emojis.SKIN_XMAS,
}


# --- Components ---
class SkinsSelect(discord.ui.Select):
    """Skins Select"""
    def __init__(self, placeholder: str, row: Optional[int] = None):
        options = []
        for skin, emoji in SKINS_EMOJIS.items():
            options.append(discord.SelectOption(label=SKINS_NAMES[skin], value=skin, emoji=emoji))
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, row=row,
                         custom_id='select_skin')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        self.view.active_skin = select_value
        embed, file = await embed_skins(self.view.active_skin)
        await interaction.response.edit_message(embed=embed, view=self.view, file=file)


# --- Views ---
class SkinsView(discord.ui.View):
    """View with a topic select and a skin preview select.
    Also needs the interaction of the response with the view, so do SkinsView.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    topics: Topics to select from - dict (description: function). The functions need to return an embed and have no
    arguments
    skins: Skins to select from - dict (name: description)
    active_topic: Currently chosen topic
    active_skin: Currently chosen skin

    Returns
    -------
    'timeout if timed out.
    None otherwise.
    """
    def __init__(self, ctx: discord.ApplicationContext, active_skin: str,
                 placeholder: str = 'Choose skin ...',
                 interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.active_skin = active_skin
        self.placeholder = placeholder
        self.add_item(SkinsSelect(self.placeholder))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        #if interaction.user.id != self.user.id:
            #await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            #return False
        return True

    async def on_timeout(self) -> None:
        self.value = 'timeout'
        self.stop()

# --- Commands ---
async def command_skins(bot: discord.AutoShardedBot, ctx: discord.ApplicationContext, active_skin: str) -> None:
    """Skins list command"""
    view = SkinsView(ctx, active_skin)
    embed, file = await embed_skins(active_skin)
    interaction = await ctx.respond(embed=embed, view=view, file=file)
    view.interaction = interaction
    await view.wait()
    try:
        await functions.edit_interaction(interaction, view=None)
    except discord.errors.NotFound:
        pass


# --- Embeds ----
async def embed_skins(active_skin: str = 'skin_default') -> tuple[discord.Embed, discord.File]:
    """Skins embed"""
    match active_skin:
        case strings.SKIN_DEFAULT:
            source = (
                f'The default skin is available to all players.'
            )
        case strings.SKIN_DINOSAUR | strings.SKIN_DRAGON | strings.SKIN_FASHALIN | strings.SKIN_VECTOR | strings.SKIN_SHINOBI:
            source = (
                f'Available in the **skinpack** {strings.SLASH_COMMANDS["shop"]} for '
                f'100 {emojis.GEM} + 10,000 {emojis.COIN}'
            )
        case strings.SKIN_COPPER:
            source = (
                f'Unlocked by researching a Tier I {emojis.PRUNER_COPPER} Copper Pruner.'
            )
        case strings.SKIN_SILVER:
            source = (
                f'Unlocked by researching a Tier I {emojis.PRUNER_SILVER} Silver Pruner.'
            )
        case strings.SKIN_GOLDEN:
            source = (
                f'Unlocked by researching a Tier I {emojis.PRUNER_GOLDEN} Golden Pruner.'
            )
        case strings.SKIN_DIAMOND:
            source = (
                f'Available in the **seasonal** {strings.SLASH_COMMANDS["shop"]} for '
                f'100 {emojis.GEM} + 10,000 {emojis.COIN} + 45,000 {emojis.DIAMOND_RING}'
            )
        case strings.SKIN_EASTER:
            source = (
                f'Available in the event shop during the easter event.\n'
            )
        case strings.SKIN_HALLOWEEN:
            source = (
                f'Available in the event shop during the halloween event.\n'
            )
        case strings.SKIN_XMAS:
            source = (
                f'Available in the event shop during the christmas event.\n'
            )
        case strings.SKIN_PHOENIX:
            source = (
                f'This skin is unique and was awarded to the first player reaching rebirth 100.\n'
            )
        case strings.SKIN_PATREON:
            source = (
                f'Unlocked by supporting the bot on {strings.SLASH_COMMANDS["patreon"]}.'
            )
        case _:
            source = (
                f'Unknown'
            )
            
    embed = discord.Embed(
        color = settings.EMBED_COLOR,
        title = f'{SKINS_NAMES[active_skin]} Skin',
        description=source,
    )
    embed.add_field(name='Preview', value=f'** **', inline=False)
    filename = f'{active_skin}.gif'
    file = discord.File(f'{settings.IMG_DIR}Skins/{active_skin}.gif', filename=filename)
    embed.set_image(url=f'attachment://{filename}')
    return (embed, file)