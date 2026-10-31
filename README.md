# Maya the Bee

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Python: 3.12](https://img.shields.io/badge/Python-3.12-brightgreen.svg)](https://www.python.org/) [![Database: SQLite](https://img.shields.io/badge/Database-SQLite-blue.svg)](https://www.sqlite.org/index.html)

Reminder / Helper for the Discord game bot "Elder Arborium" (formerly known as "Tree Tycoon").  

## Invite

• If you want to not bother with any of the following and just invite Maya, click [here](https://discord.com/api/oauth2/authorize?client_id=1082304094842146897&permissions=378944&scope=bot)  

## Setup to run your own instance

• Install python 3.12 or higher.  
• Install the third party libraries mentioned in `requirements.txt`.  
• Create a Discord application with a bot user, activate the required intents and generate a bot token.  
• Rename `default.env` to `.env` and set all required variables mentioned in the file.  
• Rename `database/default_db.db` to `database/DATABASE.db`.  
• Upload all emojis in `images/emojis` to a private server Maya can see.  
• Change all emojis in `resources/emojis.py` to the ones you uploaded.  
• Run `bot.py`.  
• Invite Maya to your server(s). Note the required permissions below.  

## Updating your bot instance

• Replace all `.py` files.  
• Upload emojis and change their ID in `resources/emojis.py` if there are new ones.  
• Restart the bot.  
• If the bot requires database changes, it will not start. In that case, I recommend turning off the bot and manually update your database. You can check the default database to see what changed.  

## Required intents

• guilds  
• members  
• message_content  
• messages  

## Required permissions

• Send Messages  
• Embed Links  
• Add Reactions  
• Use External Emoji  
• Read Message History  

## Commands

Maya uses slash commands.  
Use `/help` for an overview.  

## Dev commands

These commands are only available if you host yourself and provide bot admin level functionality.  
They are restricted as follows:  
• They can only be used by users set in DEV_IDS.  
• They are not registered globally and only show up in the servers set in DEV_GUILDS.  
• They are not listed in `/help`.  

The following commands are available:  

### `/dev consolidate`

Manually triggers the tracking consolidation. This runs daily at 00:00 UTC, so you probably won't need this.  

### `/dev event-reductions`

Manages global event reductions. If there ever will be reduced cooldowns in an event, this is the command to use.  

### `/dev post-message`

Allows you to send a custom message via Maya to a channel.  

### `/dev reload`

Allows reloading of cogs and modules on the fly.  
Note that you should always restart the bot when there is a breaking change, no matter what.  

It's not possible to reload the following files:  
• Cogs with slash command definitions. Due to Discord restrictions, you need to restart the whole thing if you change slash commands.  
• The file `bot.py` as this is the main file that is running.  
• The file `tasks.py`. I had mixed results with this, just restart instead.  

To reload files in subfolders, use `folder.file` (e.g. `resources.settings`). Cogs don't need that, the filename is enough (e.g. `prune`).  

### `/dev dump-error-log`

Exports the contents of the table `error_log` as a CSV file.  

### `/dev create-hash`

Creates a hash of a value using the secret key in your .env file.  

### `/dev server-list`

Lists all servers Maya is in by name.  

### `/dev shutdown`

Shuts down the bot. Note that if the bot is registered as a systemctl or systemd service, it will automatically restart.  
