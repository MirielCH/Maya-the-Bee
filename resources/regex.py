# regex.py

import re


# --- User data extraction ---
USER_ID_FROM_ICON_URL = re.compile(r"avatars\/(.+?)\/")
USERNAME_FROM_EMBED_AUTHOR = re.compile(r"^(.+?)'s")
NAME_FROM_MESSAGE = re.compile(r"\s\*\*(.+?)\*\*\s")
NAME_FROM_MESSAGE_START = re.compile(r"^\*\*(.+?)\*\*\s")


# --- User command detection ---
COMMAND_BEES = re.compile(r"\bbees?\b")
COMMAND_BONUSES = re.compile(r"(?:\bboosts\b|\bbonuses\b)")
COMMAND_CHESTS = re.compile(r"\bchests?\b")
COMMAND_CHIPS = re.compile(r"\bchips?\b")
COMMAND_CHIPS_FUSION = re.compile(r"\bchips?\b\s+\bfusion\b")
COMMAND_CLEAN = re.compile(r"\bclean\b")
COMMAND_COOLDOWNS = re.compile(r"(?:\bcd\b|\bcooldowns?\b)")
COMMAND_DAILY = re.compile(r"\bdaily\b")
COMMAND_FUSION = re.compile(r"\bfusion\b")
COMMAND_HIVE = re.compile(r"\bhive\b")
COMMAND_INVENTORY = re.compile(r"(?:\binventory\b|\binv\b|\bi\b)")
COMMAND_LABORATORY = re.compile(r"(?:\blab\b|\blaboratory\b)")
COMMAND_LEAGUE = re.compile(r"\bleague\b")
COMMAND_PATREON = re.compile(r"(?:\bpatreon\b|\bdonate\b)")
COMMAND_PROFILE_STATS = re.compile(r"(?:\bp\b|\bprofile\b|\bstats\b|\bstatistics\b|\bproduction\b)")
COMMAND_PRUNE = re.compile(r"\bprune\b")
COMMAND_QUESTS = re.compile(r"\bquests?\b")
COMMAND_RAID = re.compile(r"\braid\b")
COMMAND_REBIRTH = re.compile(r"\brebirth\b")
COMMAND_REBIRTH_GUIDE = re.compile(r"(?:\binventory\b|\binv\b|\bi\b)\s+(?:\brebirth\b|\brb\b|\bguide\b)")
COMMAND_SHOP = re.compile(r"\bshop\b")
COMMAND_TOOL = re.compile(r"\btool\b")
COMMAND_USE_ENERGY_DRINK = re.compile(r"\buse\b\s+\benergy\b\s+\bdrink\b")
COMMAND_USE_INSECTICIDE = re.compile(r"\buse\b\s+\binsecticide\b")
COMMAND_USE_SWEET_APPLE = re.compile(r"\buse\b\s+\bsweet\b\s+\bapple\b")
COMMAND_VOTE = re.compile(r"\bvote\b")