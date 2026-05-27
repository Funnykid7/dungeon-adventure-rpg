classes = {
    "warrior": {
        "desc": "Tank fighter. Takes reduced damage.",
        "hp": 150,
        "attack": (12, 18)
    },
    "mage": {
        "desc": "Glass cannon. Upper attacks deal more damage.",
        "hp": 95,
        "attack": (16, 26)
    },
    "rogue": {
        "desc": "Agile assassin. High dodge chance.",
        "hp": 115,
        "attack": (10, 22)
    },
    "paladin": {
        "desc": "Holy warrior. Chance to heal every turn.",
        "hp": 160,
        "attack": (11, 17)
    },
    "ranger": {
        "desc": "Precision striker. Critical hits possible.",
        "hp": 120,
        "attack": (13, 21)
    },
    "monk": {
        "desc": "Martial artist. Strong combo attacks.",
        "hp": 110,
        "attack": (14, 20)
    }
}

weapons = {
    "Dagger": {"bonus": 3, "price": 30},
    "Sword": {"bonus": 6, "price": 60},
    "Axe": {"bonus": 9, "price": 90},
    "Magic Staff": {"bonus": 12, "price": 120},
    "Royal Claymore": {"bonus": 18, "price": 250},
    "Spear of the Sheik": {"bonus": 26, "price": 400}
}

FLOOR_ENEMY_NAMES = {
    1: ["Goblin", "Skeleton", "Giant Rat", "Cursed Shade", "Tomb Creeper"],
    2: ["Troll", "Wraith", "Stone Golem", "Bone Archer", "Cave Lurker"],
    3: ["Demon", "Lich", "Shadow Fiend", "Void Stalker", "Death Knight"],
}

ENEMY_STATS = {
    # Floor 1 — status_chance: {status: probability per hit}
    "Goblin":       {"hp_mult": 0.70, "atk_range": (10, 18), "atk_weights": [3, 1, 1], "def_weights": [3, 1, 1]},
    "Skeleton":     {"hp_mult": 0.85, "atk_range": (11, 19), "atk_weights": [1, 3, 1], "def_weights": [1, 3, 1]},
    "Giant Rat":    {"hp_mult": 0.75, "atk_range": (10, 20), "atk_weights": [1, 1, 3], "def_weights": [1, 1, 1]},
    "Cursed Shade": {"hp_mult": 0.90, "atk_range": (13, 22), "atk_weights": [2, 1, 1], "def_weights": [1, 1, 2]},
    "Tomb Creeper": {"hp_mult": 1.10, "atk_range": (9,  16), "atk_weights": [1, 1, 1], "def_weights": [1, 1, 1],
                     "status_chance": {"poison": 0.35}},
    # Floor 2
    "Troll":        {"hp_mult": 1.10, "atk_range": (16, 28), "atk_weights": [1, 2, 1], "def_weights": [1, 2, 1]},
    "Wraith":       {"hp_mult": 0.90, "atk_range": (12, 22), "atk_weights": [1, 1, 1], "def_weights": [1, 1, 1],
                     "status_chance": {"poison": 0.25}},
    "Stone Golem":  {"hp_mult": 1.60, "atk_range": (10, 18), "atk_weights": [1, 2, 1], "def_weights": [1, 2, 1],
                     "status_chance": {"stun": 0.20}},
    "Bone Archer":  {"hp_mult": 0.90, "atk_range": (13, 22), "atk_weights": [1, 1, 3], "def_weights": [1, 1, 2]},
    "Cave Lurker":  {"hp_mult": 0.85, "atk_range": (14, 24), "atk_weights": [2, 1, 1], "def_weights": [2, 1, 1]},
    # Floor 3
    "Demon":        {"hp_mult": 1.10, "atk_range": (18, 30), "atk_weights": [3, 1, 1], "def_weights": [2, 1, 1],
                     "status_chance": {"bleed": 0.30}},
    "Lich":         {"hp_mult": 1.00, "atk_range": (15, 25), "atk_weights": [1, 1, 1], "def_weights": [1, 1, 1]},
    "Shadow Fiend": {"hp_mult": 0.85, "atk_range": (17, 27), "atk_weights": [1, 1, 1], "def_weights": [1, 1, 1],
                     "status_chance": {"poison": 0.20}},
    "Void Stalker": {"hp_mult": 1.00, "atk_range": (20, 35), "atk_weights": [1, 1, 1], "def_weights": [1, 1, 1],
                     "status_chance": {"bleed": 0.40}},
    "Death Knight": {"hp_mult": 1.20, "atk_range": (18, 32), "atk_weights": [1, 2, 2], "def_weights": [1, 2, 2],
                     "status_chance": {"stun": 0.25}},
}

ENEMY_HINTS = {
    "Goblin":       "Quick but frail. Upper attacks catch it off guard.",
    "Skeleton":     "Weak to Middle. Rattles but doesn't dodge.",
    "Giant Rat":    "Erratic. Expect Lower lunges.",
    "Cursed Shade": "Hard to read. Watch for Upper sweeps.",
    "Tomb Creeper": "Slow. Punish with any position.",
    "Troll":        "Heavy hitter. Keep your DEF potion ready.",
    "Wraith":       "Unpredictable. Perfect blocks are harder.",
    "Stone Golem":  "High HP. Outlasting it is key.",
    "Bone Archer":  "Favours Lower attacks. Stay mobile.",
    "Cave Lurker":  "Stealth strikes — it lunges fast.",
    "Demon":        "Upper attacks deal extra pain. Block hard.",
    "Lich":         "Uses all positions equally. Trust your gut.",
    "Shadow Fiend": "Evasive. Combo attacks work well (Monk).",
    "Void Stalker": "High damage. Pop a Strength Potion early.",
    "Death Knight": "Hits like the Dungeon Lord. Survive the first wave.",
}
