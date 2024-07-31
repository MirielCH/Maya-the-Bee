# settings.py
"""Contains global settings"""

import os
import sqlite3
import sys

from dotenv import load_dotenv


ENV_VARIABLE_MISSING = (
    'Required setting {var} in the .env file is missing. Please check your default.env file and update your .env file '
    'accordingly.'
)


# Files and directories
BOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BOT_DIR, 'database/maya_db.db')
if os.path.isfile(DB_FILE):
    DATABASE = sqlite3.connect(DB_FILE, isolation_level=None, detect_types=sqlite3.PARSE_DECLTYPES)
else:
    print(f'Database {DB_FILE} does not exist. Please follow the setup instructions in the README first.')
    sys.exit()
DATABASE.row_factory = sqlite3.Row
LOG_FILE = os.path.join(BOT_DIR, 'logs/discord.log')
IMG_LOGO = os.path.join(BOT_DIR, 'images/maya.png')
VERSION_FILE = os.path.join(BOT_DIR, 'VERSION')
IMG_DIR = os.path.join(BOT_DIR, 'images/')



# Load .env variables
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print(ENV_VARIABLE_MISSING.format(var='DISCORD_TOKEN'))
    sys.exit()

OWNER_ID = os.getenv('OWNER_ID')
if not OWNER_ID:
    print(ENV_VARIABLE_MISSING.format(var='OWNER_ID'))
    sys.exit()
try:
    OWNER_ID = int(OWNER_ID)
except:
    print(f'Owner ID "{OWNER_ID}" in the .env variable OWNER_ID is not a number.')
    sys.exit()

DEBUG_MODE = True if os.getenv('DEBUG_MODE') == 'ON' else False

DEV_IDS = os.getenv('DEV_IDS')
if not DEV_IDS:
    DEV_IDS = []
else:
    DEV_IDS = DEV_IDS.split(',')
    try:
        DEV_IDS = [int(dev_id.strip()) for dev_id in DEV_IDS]
    except:
        print('At least one id in the .env variable DEV_IDS is not a number.')
        sys.exit()
DEV_IDS += [OWNER_ID,]

DEV_GUILDS = os.getenv('DEV_GUILDS')
if not DEV_GUILDS:
    print(ENV_VARIABLE_MISSING.format(var='DEV_GUILDS'))
    sys.exit()
else:
    try:
        DEV_GUILDS = [int(guild_id.strip()) for guild_id in DEV_GUILDS.split(',')]
    except Exception as error:
        print(
            f'{error}\n'
            f'Make sure the .env variable DEV_GUILDS has the right format.'
        )
        sys.exit()


# Read bot version
_version_file = open(VERSION_FILE, 'r')
VERSION = _version_file.readline().rstrip('\n')
_version_file.close()


DONOR_TIERS_MULTIPLIERS = {
    0: 1,
    1: 0.9,
    2: 0.83,
    3: 0.75,
    4: 0.75,
    5: 0.7,
}


GAME_ID = 944160835255816232
TESTY_ID = 1050765002950332456 # Miriel's test bot to test triggers


DEFAULT_PREFIX = 'maya '
EMBED_COLOR = 0xFFBB01
ABORT_TIMEOUT = 60
INTERACTION_TIMEOUT = 300