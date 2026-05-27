import pygame

# Screen Dimensions
SCREEN_W, SCREEN_H = 960, 540
ROOM_W, ROOM_H = 960, 540

# Game Settings
SAVE_FILE = "dungeon_save.json"
MAP_SIZE = 5
MAX_FLOORS = 4
FLASH_DURATION = 10
DOOR_COOLDOWN_TIME = 20
TILE_SIZE = 48
DOOR_SIZE = 48
DOOR_PADDING = 8

# Audio Paths
BATTLE_MUSIC = "assets/audio/battle_music.mp3"
EXPLORE_MUSIC = "assets/audio/game_world.mp3"
SHRINE_MUSIC  = "assets/audio/shrine_room.mp3"
BOSS_MUSIC    = "assets/audio/boss_music.mp3"

START_ROOM_NPCS = [
    {"x": 180, "y": 370, "frame": 0, "name": "Guard", "dialogue": [
        "\"Welcome, adventurer. Beyond that door lies the dungeon.\"",
        "\"Many have entered. Few have returned. Prepare yourself.\"",
    ]},
    {"x": 740, "y": 360, "frame": 1, "name": "Survivor", "dialogue": [
        "\"I made it out... barely. The traps nearly got me.\"",
        "\"One of the doors in every trap room is rigged. Choose wisely.\"",
    ]},
    {"x": 480, "y": 230, "frame": 2, "name": "Merchant's Friend", "dialogue": [
        "\"My friend sells wares inside. Find him when you can.\"",
        "\"Better weapons make all the difference down there.\"",
    ]},
    {"x": 130, "y": 210, "frame": 3, "name": "Scholar", "dialogue": [
        "\"Seeking knowledge about the dungeon, are you?\"",
        "\"Floor 1: Standard Dungeon - a taste of what lies below.\"",
        "\"Floor 2: The Catacombs - mostly lesser creatures, some merchants.\"",
        "\"Floor 3: The Crypts - stronger foes, rarer loot. Many have perished here.\"",
        "\"Floor 4: The Void - where nightmares dwell. Few return from this depth.\"",
        "\"The Dungeon Lord awaits at the deepest chamber. Legend says it was imprisoned there ages ago.\"",
    ]},
    {"x": 790, "y": 210, "frame": 3, "name": "Dungeon Scholar", "dialogue": [
        "\"Before you descend, heed this: the dungeon rewards the patient.\"",
        "\"Shrines restore the wounded. Merchants arm the wise. Seek them out.\"",
        "\"Elite chambers and guardians guard the richest spoils — and the deadliest blows.\"",
        "\"Keys open sealed vaults. Wander far enough and you'll find what you need.\"",
        "\"Press TAB to study your quests and progress. Knowledge is its own kind of armor.\"",
    ]},
]

SHRINE_NPC_DIALOGUE = [
    "\"Thank the gods... you found me here.\"",
    "\"This shrine keeps me safe. Take its blessing.\"",
    "\"You navigate these cursed halls with the grace of a true adventurer.\"",
]

UPGRADE_POOL = [
    {"name": "Fortify",       "desc": "+25 Max HP",              "apply": lambda p: p.update({"max_hp": p["max_hp"]+25, "hp": min(p["hp"]+25, p["max_hp"]+25)})},
    {"name": "Keen Edge",     "desc": "+3 flat attack bonus",     "apply": lambda p: p.update({"_atk_bonus": p.get("_atk_bonus",0)+3})},
    {"name": "Fleet Foot",    "desc": "+10% dodge (all classes)", "apply": lambda p: p.update({"_dodge_bonus": p.get("_dodge_bonus",0)+0.10})},
    {"name": "Iron Will",     "desc": "+10% damage reduction",    "apply": lambda p: p.update({"_dmg_reduce": p.get("_dmg_reduce",0)+0.10})},
    {"name": "Treasure Nose", "desc": "+15 gold per combat win",  "apply": lambda p: p.update({"_gold_bonus": p.get("_gold_bonus",0)+15})},
]

CLASS_UPGRADES = {
    "warrior": [{"name": "Iron Fortress",  "desc": "Perfect blocks deal 5 reflected damage",       "apply": lambda p: p.update({"_reflect_dmg": p.get("_reflect_dmg",0)+5})}],
    "mage":    [{"name": "Arcane Surge",   "desc": "Every 3rd Upper attack auto-crits",             "apply": lambda p: p.update({"_arcane_surge": True})}],
    "rogue":   [{"name": "Shadow Step",    "desc": "First attack each fight is a guaranteed hit",   "apply": lambda p: p.update({"_shadow_step": True})}],
    "paladin": [{"name": "Sacred Ground",  "desc": "Paladin heal range becomes 10-25 HP",           "apply": lambda p: p.update({"_sacred_ground": True})}],
    "ranger":  [{"name": "Eagle Eye",      "desc": "Critical hit chance increases to 40%",          "apply": lambda p: p.update({"_eagle_eye": True})}],
    "monk":    [{"name": "Momentum",       "desc": "3 consecutive same-position attacks deal x1.8", "apply": lambda p: p.update({"_momentum": True})}],
}

SYNERGIES = [
    ("Keen Edge",  "Iron Fortress",  lambda p: p.update({"_reflect_dmg": p.get("_reflect_dmg",0)+5}),  "Synergy: Keen Edge + Iron Fortress — Reflected damage +5!"),
    ("Fleet Foot", "Shadow Step",    lambda p: p.update({"_dodge_bonus": p.get("_dodge_bonus",0)+0.10}), "Synergy: Fleet Foot + Shadow Step — Dodge +10%!"),
    ("Fortify",    "Sacred Ground",  lambda p: p.update({"_sacred_heal_bonus": True}),                   "Synergy: Fortify + Sacred Ground — Paladin heals 15-30 HP!"),
]

FLOOR_CURSES = [
    {"name": "Blood Pact",    "desc": "Lose 10 HP at the start of every fight",          "apply": lambda p: p.update({"_curse_combat_start_dmg": 10}),   "remove": lambda p: p.pop("_curse_combat_start_dmg", None)},
    {"name": "Weakened",      "desc": "Deal 20% less attack damage this floor",           "apply": lambda p: p.update({"_curse_atk_mult": 0.80}),          "remove": lambda p: p.pop("_curse_atk_mult", None)},
    {"name": "Fragile",       "desc": "Lose 15 Max HP for this floor (min 1)",            "apply": lambda p: p.update({"max_hp": max(1, p["max_hp"]-15), "hp": min(p["hp"], max(1, p["max_hp"]-15))}), "remove": lambda p: p.update({"max_hp": p["max_hp"]+15})},
    {"name": "Cursed Hands",  "desc": "Potions heal 20 HP less this floor",               "apply": lambda p: p.update({"_curse_potion_reduce": 20}),       "remove": lambda p: p.pop("_curse_potion_reduce", None)},
]

FLOOR_BLESSINGS = [
    {"name": "Blessed Ground",  "desc": "Heal 15 HP on every room entry this floor",       "apply": lambda p: p.update({"_blessing_room_heal": 15}),       "remove": lambda p: p.pop("_blessing_room_heal", None)},
    {"name": "Battle Frenzy",   "desc": "Deal 15% more attack damage this floor",          "apply": lambda p: p.update({"_blessing_atk_mult": 1.15}),      "remove": lambda p: p.pop("_blessing_atk_mult", None)},
    {"name": "Guardian Spirit", "desc": "First dodge per combat is always guaranteed",     "apply": lambda p: p.update({"_blessing_free_dodge": True}),    "remove": lambda p: p.pop("_blessing_free_dodge", None)},
    {"name": "Golden Touch",    "desc": "Earn 25% more gold from all sources this floor",  "apply": lambda p: p.update({"_blessing_gold_mult": 1.25}),     "remove": lambda p: p.pop("_blessing_gold_mult", None)},
]

QUEST_POOL = [
    {"id": "slayer",     "desc": "Slayer: Kill {goal} enemies this floor",          "type": "kill",         "goal_mult": lambda f: f*2+1, "reward_gold": 50,  "reward_upgrade": False},
    {"id": "explorer",   "desc": "Explorer: Visit {goal} different rooms",          "type": "explore",      "goal_mult": lambda f: 6,    "reward_gold": 40,  "reward_upgrade": False},
    {"id": "untouched",  "desc": "Untouched: Win a fight without taking damage",    "type": "no_damage",    "goal_mult": lambda f: 1,    "reward_gold": 60,  "reward_upgrade": True},
    {"id": "potion_free","desc": "Iron Will: Win 2 fights without using potions",   "type": "no_potion",    "goal_mult": lambda f: 2,    "reward_gold": 60,  "reward_upgrade": False},
    {"id": "hoarder",    "desc": "Hoarder: Earn {goal} gold this floor",            "type": "gold",         "goal_mult": lambda f: 80,   "reward_gold": 0,   "reward_upgrade": True},
    {"id": "pacifist",   "desc": "Pacifist: Clear {goal} non-combat rooms",         "type": "noncombat",    "goal_mult": lambda f: 3,    "reward_gold": 40,  "reward_upgrade": False},
]

EQUIPMENT = {
    "armor": [
        {"name": "Leather Armor", "price": 50,  "desc": "+5% dmg reduction",  "apply": lambda p: p.update({"_dmg_reduce": p.get("_dmg_reduce",0)+0.05})},
        {"name": "Chain Mail",    "price": 150, "desc": "+12% dmg reduction", "apply": lambda p: p.update({"_dmg_reduce": p.get("_dmg_reduce",0)+0.12})},
        {"name": "Plate Armor",   "price": 300, "desc": "+20% dmg reduction", "apply": lambda p: p.update({"_dmg_reduce": p.get("_dmg_reduce",0)+0.20})},
    ],
    "ring": [
        {"name": "Ring of Power",     "price": 80,  "desc": "+7 flat attack",    "apply": lambda p: p.update({"_atk_bonus": p.get("_atk_bonus",0)+7})},
        {"name": "Ring of Swiftness", "price": 60,  "desc": "+8% dodge",         "apply": lambda p: p.update({"_dodge_bonus": p.get("_dodge_bonus",0)+0.08})},
        {"name": "Ring of Vampirism", "price": 120, "desc": "15% lifesteal",     "apply": lambda p: p.update({"_lifesteal": 0.15})},
    ],
    "trinket": [
        {"name": "Lucky Charm", "price": 50,  "desc": "30% resist statuses",  "apply": lambda p: p.update({"_status_resist": 0.30})},
        {"name": "Dungeon Map", "price": 75,  "desc": "Reveals all room types","apply": lambda p: p.update({"_map_reveal": True})},
        {"name": "War Banner",  "price": 100, "desc": "+10% XP from kills",    "apply": lambda p: p.update({"_xp_bonus": 0.10})},
    ],
}

ROOM_FLAVOR = {
    "enemy":    ["The air reeks of blood...", "You hear growling in the shadows.", "Something lurks nearby."],
    "trap":     ["The floorboards creak underfoot.", "This room feels... wrong.", "Something is off here."],
    "shrine":   ["A warm glow fills the chamber.", "Peace washes over you.", "The air feels sacred."],
    "merchant": ["The smell of coin and tallow.", "A familiar face in the dark.", "Someone has set up shop."],
    "chest":    ["Something glitters in the corner.", "Fortune favors the bold.", "An untouched chest!"],
    "miniboss": ["The ground trembles.", "An overwhelming presence fills the room.", "This foe is unlike the others."],
    "boss":     ["The darkness thickens.", "Every torch goes cold.", "Something ancient awakens."],
    "puzzle":   ["Strange runes glow on the walls...", "A test of memory awaits.", "The dungeon poses a riddle."],
    "elite":    ["A powerful presence lurks here.", "This one is no ordinary foe.", "Something hunts you back."],
    "locked":   ["A heavy door bars the way.", "The lock glints in torchlight.", "Forbidden chambers lie ahead."],
    "event":    ["Something unusual stirs here...", "Fate takes an unexpected turn.", "This room holds a surprise."],
}

MERCHANT_GREETINGS = [
    "\"Ah, a customer! Business is slow in these cursed halls.\"",
    "\"You look terrible. Buy something, you'll feel better.\"",
    "\"Rare goods, fair prices. The dungeon provides.\"",
    "\"I followed adventurers down here for profit. No regrets.\"",
]

CLASS_PASSIVES = {
    "warrior": "Takes 20% reduced incoming damage.",
    "mage":    "Upper attacks deal +30% damage.",
    "rogue":   "25% chance to dodge enemy hits.",
    "paladin": "40% chance to heal 6-15 HP on hit. Divine Intervention once per run.",
    "ranger":  "25% critical hit chance (x1.6 damage).",
    "monk":    "x1.4 damage when repeating the same attack position.",
}

FLOOR_THEMES = {
    1: {"name": "Standard Dungeon", "enemy_w": 0.25, "merchant_w": 0.20},
    2: {"name": "The Catacombs",    "enemy_w": 0.35, "merchant_w": 0.15},
    3: {"name": "The Crypts",       "enemy_w": 0.45, "merchant_w": 0.10},
    4: {"name": "The Void",         "enemy_w": 0.55, "merchant_w": 0.05},
}

FLOOR_DECORATION_COLORS = {
    1: {"ember": (200, 180, 140), "glow": (220, 200, 160)},  # Standard: neutral tan
    2: {"ember": (255, 120, 40),  "glow": (255, 180, 80)},   # Catacombs: warm orange
    3: {"ember": (80,  80,  255), "glow": (120, 120, 255)},  # Crypts: cold blue
    4: {"ember": (180, 0,   255), "glow": (220, 80,  255)},  # Void: purple
}

ROOM_LABELS = {
    "enemy":    "ENEMY LAIR",
    "chest":    "TREASURE CHAMBER",
    "shrine":   "SHRINE OF THE FALLEN",
    "merchant": "WANDERING MERCHANT",
    "trap":     "TRAPPED CORRIDOR",
    "puzzle":   "PUZZLE VAULT",
    "elite":    "ELITE SENTINEL",
    "miniboss": "GUARDIAN LAIR",
    "event":    "STRANGE ENCOUNTER",
    "locked":   "SEALED VAULT",
    "boss":     "THRONE OF DARKNESS",
}

LORE_FRAGMENTS = [
    "A faded inscription reads: 'He who descends three floors never returns the same.'",
    "A bloodied journal entry — Day 12: 'The shadows breathe here. I can hear them.'",
    "Carved into stone: 'Beware the third floor. The Void remembers your name.'",
    "A tattered note: 'The merchant knows more than he sells. Ask him about the Lord.'",
    "Ancient runes translate to: 'Gold is the dungeon's currency. Fear is its language.'",
    "A child's drawing scratched into the wall: a stick figure fleeing a many-eyed shadow.",
    "Faded text: 'The Guardian was once a hero. The dungeon claimed them. As it will you.'",
    "An alchemist's scrawl: 'Floor 2 water is toxic. Do not drink. I drank. Do not drink.'",
    "Etched deeply: 'Three doors. One truth. The dungeon tests patience, not strength.'",
    "A poem fragment: 'When torches dim and echoes fade, the Dungeon Lord has found its prey.'",
]

COMPANION_ROLES = ["healer", "scout", "combat", "merchant"]
COMPANION_ROLE_DESCS = {
    "healer":   "+10 HP each new uncleared room",
    "scout":    "Reveals nearby minimap rooms",
    "combat":   "+8 flat damage in fights",
    "merchant": "15% discount at all shops",
}

# Door Zones
door_zones = {
    "up": pygame.Rect(432, 85, 96, 48),
    "down": pygame.Rect(432, 456, 96, 48),
    "left": pygame.Rect(36, 216, 48, 96),
    "right": pygame.Rect(876, 216, 48, 96),
}
