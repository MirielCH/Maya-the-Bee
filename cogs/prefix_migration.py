# prefix_migration.py
# Responds to the last set guild prefix and tells users that the prefix has been removed and to use other commands instead.

import itertools
import sqlite3

import discord
from discord.ext import bridge, commands

from resources import functions, settings

prefix_slash_commands: dict[str, str] = {
    'list': 'reminders list',
    'cd': 'reminders list',
    'ready': 'ready list',
    'rd': 'ready list',
    'reminder': 'reminders add',
    'rm': 'reminders add',
    'stats': 'stats',
    'st': 'stats',
}

class PrefixMigrationCog(commands.Cog):
    """Cog that contains the prefix migration commands"""
    def __init__(self, bot: bridge.AutoShardedBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.bot: return
        if not message.guild: return

        prefix: str
        try:
            cur=settings.DATABASE.cursor()
            cur.execute("SELECT prefix FROM guilds WHERE guild_id=?", (message.guild.id,))
            record = cur.fetchone()
            prefix = record['prefix'].replace('"','') if record else 'navi '
        except sqlite3.Error as error:
            return
        
        all_prefixes: map[str] = map(''.join, itertools.product(*((char.upper(), char.lower()) for char in prefix)))
        message_command: str = ''
        for prefix in list(all_prefixes):
            if message.content.startswith(prefix):
                message_command = message.content.lstrip(prefix).lower().lower()
                if message_command not in prefix_slash_commands:
                    message_command = message_command.split(' ')[0]
                if message_command not in prefix_slash_commands: return
                break

        if message_command:
            await message.reply(
                f'# Prefix commands have been removed!\n'
                f'➜ Please use {await functions.get_maya_slash_command(self.bot, prefix_slash_commands[message_command])} or `@Maya {message_command}` instead.\n'
                f'Use {await functions.get_maya_slash_command(self.bot, 'help')} to see all available commands.\n'
                f'## What? Why??\n'
                f'Discord requires it. Slash and mention commands were introduced around 5 years ago and are now enforced.\n'
                f'Prefix commands are no longer accepted.\n'
                f'## I demand my money back!\n'
                f'Please find and submit Permit A38 to apply for a refund.\n'
            )


# Initialization
def setup(bot: bridge.AutoShardedBot):
    bot.add_cog(PrefixMigrationCog(bot))