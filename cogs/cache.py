# cache.py
"""Collects messages containing rpg and mention commands for the local cache"""

import discord
from discord.ext import commands

from cache import messages
from resources import settings


class CacheCog(commands.Cog):
    """Cog that contains the cache commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.bot: return
        if message.embeds or message.content is None: return
        correct_mention = False
        bot_prefixes = [
            'tree ',
            't ',
            'testy ',
        ]
        if any(message.content.lower().startswith(bot_prefix) for bot_prefix in bot_prefixes):
            await messages.store_message(message)
            return
        if message.mentions:
            for mentioned_user in message.mentions:
                if mentioned_user.id in (settings.TREE_ID, settings.TREE_BETA_ID):
                    correct_mention = True
                    break
            if correct_mention:
                await messages.store_message(message)

# Initialization
def setup(bot):
    bot.add_cog(CacheCog(bot))