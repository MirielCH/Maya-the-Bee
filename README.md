[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Python: 3.8](https://img.shields.io/badge/Python-3.8+-brightgreen.svg)](https://www.python.org/) [![Database: SQLite](https://img.shields.io/badge/Database-SQLite-blue.svg)](https://www.sqlite.org/index.html)
# Maya the Bee

Reminder for the Discord bot Tree.

# Invite
• If you want to not bother with any of the following and just invite Maya, click [here](https://discord.com/api/oauth2/authorize?client_id=1082304094842146897&permissions=378944&scope=bot)

# Setup to run your own instance
• Install python 3.8, 3.9 or 3.10. Note that python 3.11+ is untested. It might run, or it might not.
• Install the third party libraries mentioned in `requirements.txt`.
• Create a Discord application with a bot user, activate the required intents and generate a bot token.
• Rename `default.env` to `.env` and set all required variables mentioned in the file.
• Rename `database/default_db.db` to `database/DATABASE.db`.
• Upload all emojis in `images/emojis` to a private server Maya can see.
• Change all emojis in `resources/emojis.py` to the ones you uploaded.
• Run `bot.py`.
• Invite Maya to your server(s). Note the required permissions below.

# Updating your bot instance
• Replace all `.py` files.
• Upload emojis and change their ID in `resources/emojis.py` if there are new ones.
• Restart the bot.
• If the bot requires database changes, it will not start and tell you so. In that case, turn off the bot, **BACKUP YOUR DATABASE** and run `database/update_database.py`.

# Required intents
• guilds
• members
• message_content
• messages

# Required permissions
• Send Messages
• Embed Links
• Add Reactions
• Use External Emoji
• Read Message History

# Commands
Maya uses slash commands but also supports some legacy commands.
Default prefix for legacy commands is `maya ` and is changeable in `/settings server`.
Use `/help` for an overview.