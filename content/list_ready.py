# list_ready.py
"""Contains ready list command"""

from typing import Optional, Union

import discord
from discord.ext import commands

from database import users
from resources import emojis, functions, exceptions, settings


# -- Commands ---
async def command_ready(
    bot: discord.Bot,
    ctx: Union[commands.Context, discord.ApplicationContext, discord.Message],
    user: Optional[discord.User] = None
) -> None:
    """Lists all activities off cooldown"""
    user = user if user is not None else ctx.author
    try:
        user_settings: users.User = await users.get_user(user.id)
    except exceptions.FirstTimeUserError:
        if user == ctx.author:
            raise
        else:
            await functions.reply_or_respond(ctx, 'This user is not registered with me.', True)
        return
    
    embed = await functions.design_embed_ready_list(user, user_settings)
    if embed is None:
        embed = discord.Embed(
           color = settings.EMBED_COLOR,
            title = f'{user.global_name}\'s ready list'
        )
        embed.description = f'{emojis.ENABLED} All done!'
        embed.set_footer(text = 'Use "/settings ready-list" to change the content of this list.')
    if isinstance(ctx, discord.ApplicationContext):
        interaction_message = await ctx.respond(embed=embed)
    else:
        interaction_message = await ctx.reply(embed=embed)