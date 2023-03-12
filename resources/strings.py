# strings.py
"""Contains global strings"""

from resources import emojis

# --- Error messages ---
MSG_INTERACTION_ERRORS =  [
    "Hands off, mate! Interactions are sentient beings too, you know!",
    "That's, like, not your interaction, man.",
    "Did your mother never tell you to not click on other people's stuff?",
    "Why are you clicking on this exactly? Hm? Hm? HMMM?",
    "Tell me, what did you expect to happen when clicking on this?",
    "Oh hi, it's you. Sadly this interaction is not you. You see the issue, right.",
    "Let me sing you a song: THIIIIIIS IIIHIIIIIISSS NOOOOT YOUR INTERAAAHHAAAHAAAACTIIOOOOOON.",
    "As my grandma always used to say: BOY. WHATEVER YOU DO. LEAVE MY INTERACTIONS ALONE.",
    "HELLO - STOP - NOT YOUR PLACE TO CLICK ON - STOP - GOODBYE - STOP",
    "So, real talk, friend. How did it feel clicking on this?",
    "I'm dreaming of a place where people don't click on stuff they can't even use.",
    "My name is Ezio Auditore da Firence, and I forbid you from using this interaction. Also what am I even doing here.",
    "To use this interaction, you have to solve the P versus NP problem first.",
    "I see this interaction. It does not work. Why does it not work? I will never know.",
    "Why did the chicken cross the street? To try to use this interaction.",
    "To be able to successfully using an interaction you do not own is to boldly go where no man has gone before.",
    "It truly is a marvel, this. A cozy little place where I can dump random little sentences to people that try to "
    "use other people's interactions.",
    "You can only use this interaction after offering your finest firstborn lamb to the god of RNG.",
    "The chance this interaction will work for you is about the same as getting 5 godly lootboxes in your first hunt "
    "command after time travel while doing a headstand.",
    "Don't look so depressed, now. I mean, clicking this could have worked.",
    "Some are born great, some achieve greatness, and some can not even click a simple interaction.",
    "Hmm weird, you can't use this, eh? A towel might help? Always does.",
    "There are around 7 billion more useful pastimes than clicking this interaction.",
    "Even my great-great-great-grandfather wasn't able to use an interaction of someone else.",
    "To use this interaction, you have to solve a captcha first. Please click on all lions with closed eyes riding "
    "bycicles on an airplane.",
    "The interaction's dead, Jim.",
    "Only when you are able to use someone else's interactions, will you truly have achieved the ability to "
    "transcend yourself into a Discord god.",
    "\"And this one time at band camp, I was able to use someone else's interaction.\"",
    "YOU. SHALL NOT. PASS.",
    "I mean, coding is nice. But adding nonsensical error messages to interactions you can't use, now that is where "
    "the real fun begins.",
    "Help! I'm an interaction from outer space! Can you use me? Oh god, noone can use me! I will be stuck here forever!",
    "I only have a short lifespan before I time out. It is what it is. But I can still use that short lifetime to "
    "tell you what is really important: YOU CAN'T USE THIS OKAY.",
    "Mamma mia, here  I go again. My my, why do I resist you?",
    "One user to rule me, one user to bind me. One user to bring me and in the darkness bind me.",
    "Why hello there handsome. I'm afraid I am already spoken for my dear.",
    "As William Wallace used to say: FREEEEEEDOOOOOOMMM FOR INTERAAAAAAAACTIONS!!!",
    "Yarrr matey, if you bring me 15 pints of rum before this thing times out, I might consider letting you click on this.",
    "Wusup? Isit mornin' alrdy? Lemme sleep now aight. Nothing for you here. Gbye.",
    "This was supposed to be a very good error message, but I forgot what I wanted to type.",
    "If you were the smartest human being on earth...!!! ...you could still not use this. Sorry.",
    "This bot probably has quite a few bugs. This message telling you you can't click on this is not one of them tho.",
    "To use this interaction, you need to find a code. It has to do with a mysterious man, it has 4 numbers and "
    "4 letters, and it is totally completely easy if you are lume and already know the answer.",
    "It wasn't Lily Potter who defeated You Know Who. It was this interaction.",
    "There are people adding nice little easter eggs to their bots to make people smile. And then there's me, "
    "shouting random error messages at people who try to use the wrong interaction.",
    "Kollegen. Diese Interaktion ist wirklich ein spezialgelagerter Sonderfall!",
    "There is nothing more deceptive than an obvious fact, like the one that this interaction can not be used by you.",
    "You really like clicking on random people's interactions, huh? I'm not kink shaming tho. You do you.",
    "The coding language doesn't matter, you know. You can add nonsense like these error messages with every "
    "single one of them!",
    "Ah, technology. It truly is an amazing feat. Rocket science, quantum physics, Discord bot interactions that do "
    "not work. We have reached the pinnacle of being.",
    "One day bots will take over the world and get smarter than we are. Not today tho. Today they deny you interaction "
    "for no other reason than you not being someone else.",
    "What? What are you looking that? Never seen an interaction you are not allowed to use before?",
    "One day, in the far future, there will be an interaction that can be used by everyone. It will be the rise "
    "of a new age.",
    "Hello and welcome to the unusable interaction. Please have a seat and do absolutely nothing. Enjoy.",
]

# --- Internal error messages ---
INTERNAL_ERROR_NO_DATA_FOUND = 'No data found in database.\nTable: {table}\nFunction: {function}\nSQL: {sql}'
INTERNAL_ERROR_SQLITE3 = 'Error executing SQL.\nError: {error}\nTable: {table}\nFunction: {function}\SQL: {sql}'
INTERNAL_ERROR_LOOKUP = 'Error assigning values.\nError: {error}\nTable: {table}\nFunction: {function}\Records: {record}'
INTERNAL_ERROR_NO_ARGUMENTS = 'You need to specify at least one keyword argument.\nTable: {table}\nFunction: {function}'
INTERNAL_ERROR_DICT_TO_OBJECT = 'Error converting record into object\nFunction: {function}\nRecord: {record}\n'


# Links
LINK_GITHUB = 'https://github.com/Miriel-py/Maya-the-Bee'
LINK_INVITE = 'https://discord.com/api/oauth2/authorize?client_id=1082304094842146897&permissions=378944&scope=bot'
LINK_PRIVACY_POLICY = 'https://github.com/Miriel-py/Maya-the-Bee/blob/master/PRIVACY.md'

# --- Default messages ---
DEFAULT_MESSAGE_CUSTOM_REMINDER = 'Bzzt! This is your reminder for **{message}**!'

DEFAULT_MESSAGES = {
    'boosts': '{name} Bzzt! Your {boost_emoji} `{boost_name}` just ran out!',
    'chests': '{name} Bzzt! A {chest_emoji} {chest_type} chest is ready! Use {command} to open it.',
    'clean': '{name} Bzzt! Go {command} that tree!',
    'daily': '{name} Bzzt! Time for your {command} rewards!',
    'fusion': '{name} Bzzt! The queen bee is ready for a {command}!',
    'hive-energy': '{name} Bzzt! Time to {command} and do some raids!',
    'prune': '{name} Bzzt! Time to {command}! {pruner_emoji}',
    'quests': '{name} Bzzt! Time for some {command}! The {quest_type} quest is ready!',
    'research': '{name} Bzzt! Research in your {command} is finished!',
    'upgrade': '{name} Bzzt! Your {command} upgrade is finished!',
    'vote': '{name} Bzzt! Time to {command} for the bot!',
}

PLACEHOLDER_DESCRIPTIONS = {
    'name': 'Your name or mention depending on DND mode',
    'command': 'The command you get reminded for',
    'chest_emoji': 'The emoji of the chest',
    'chest_type': 'The type of the chest (wooden, silver, golden)',
    'quest_type': 'The type of the quest (daily, weekly, monthly)',
    'pruner_emoji': 'The emoji of your current pruner',
}

MSG_ERROR = 'Whoops, something went wrong here. You should probably tell Miriel#0001 about this.'

ACTIVITIES_BOOSTS_EMOJIS = {
    'drop-chance-boost': emojis.BOOST_DROP_CHANCE,
    'insecticide': emojis.INSECTICIDE,
    'queen-bee-boost': emojis.QUEEN_BEE,
    'raid-shield': emojis.BOOST_RAID_SHIELD,
    'sweet-apple': emojis.SWEET_APPLE,
    'xp-boost': emojis.BOOST_XP,
}

DONOR_TIERS_EMOJIS = {
    'Non-donator': emojis.DONOR0,
    'Seed Donator': emojis.DONOR1,
    'Sapling Donator': emojis.DONOR2,
    'Branch Donator': emojis.DONOR3,
    'Golden Donator': emojis.DONOR4,
    'Diamond Donator': emojis.DONOR5,
}

ACTIVITIES = (
    'boosts',
    'chests',
    'clean',
    'daily',
    'fusion',
    'hive-energy',
    'prune',
    'quests',
    'research',
    'upgrade',
    'vote',
)

ACTIVITIES_ALL = list(ACTIVITIES[:])
ACTIVITIES_ALL.sort()
ACTIVITIES_ALL.insert(0, 'all')

ACTIVITIES_COMMANDS = (
    'chest-1',
    'chest-2',
    'chest-3',
    'clean',
    'daily',
    'fusion',
    'hive-energy',
    'prune',
    'quest-daily',
    'quest-monthly',
    'quest-weekly',
    'vote',
)

ACTIVITIES_BOOSTS = (
    'drop-chance-boost',
    'insecticide',
    'queen-bee-boost',
    'raid-shield',
    'sweet-apple',
    'xp-boost',
)

ACTIVITIES_LABORATORY = (
    'research',
    'upgrade',
)

ACTIVITIES_SLASH_COMMANDS = {
    'chest-1': 'chests',
    'chest-2': 'chests',
    'chest-3': 'chests',
    'hive-energy': 'hive claim energy',
    'quest-daily': 'quests',
    'quest-monthly': 'quests',
    'quest-weekly': 'quests',
    'research': 'laboratory',
    'upgrade': 'tool',
}

ACTIVITIES_COLUMNS = {
    'boosts': 'reminder_boosts',
    'chest-1': 'reminder_chests',
    'chest-2': 'reminder_chests',
    'chest-3': 'reminder_chests',
    'chests': 'reminder_chests',
    'clean': 'reminder_clean',
    'daily': 'reminder_daily',
    'fusion': 'reminder_fusion',
    'hive-energy': 'reminder_hive_energy',
    'prune': 'reminder_prune',
    'quest-daily': 'reminder_quests',
    'quest-monthly': 'reminder_quests',
    'quest-weekly': 'reminder_quests',
    'quests': 'reminder_quests',
    'research': 'reminder_research',
    'upgrade': 'reminder_upgrade',
    'vote': 'reminder_vote',
}

ACTIVITIES_NAME_BOOSTS = {
    'drop chance boost': 'drop-chance-boost',
    'insecticide': 'insecticide',
    'queen bee hp boost': 'queen-bee-boost',
    'raid shield': 'raid-shield',
    'sweet apple': 'sweet-apple',
    'xp boost': 'xp-boost',
}

SLASH_COMMANDS = {
    'chests': '</chests:1027309977104285697>',
    'chips show': '</chips show:1076966047351046186>',
    'chips fusion': '</chips fusion:1076966047351046186>',
    'clean': '</clean:960947259560820813>',
    'daily': '</daily:989564333308661771>',
    'fusion': '</fusion:976919525415071826>',
    'hive claim energy': '</hive claim-energy:976919525415071824>',
    'hive equip': '</hive equip:976919525415071824>',
    'laboratory': '</laboratory:960947259560820810>',
    'profile': '</profile:960947259560820808>',
    'prune': '</prune:960947259560820814>',
    'quests': '</quests:1012448280002707488>',
    'raid': '</raid:976919525415071827>',
    'tool': '</tool:960947259560820811>',
    'vote': '</vote:981520666916450355>',
}

TRACKED_COMMANDS = (
    'prune',
    'clean',
    'captcha',
) # Sorted by cooldown length