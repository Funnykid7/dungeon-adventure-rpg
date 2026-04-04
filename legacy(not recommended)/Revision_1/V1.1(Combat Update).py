import random
import time
import json
import os

SAVE_FILE = "dungeon_save.json"

def slow(text, d=0.02):
    for c in text:
        print(c, end="", flush=True)
        time.sleep(d)
    print()

def divider():
    print("\n" + "=" * 50)

# ---------------- CLASSES ----------------

classes = {
    "warrior": {
        "desc": "Frontline fighter. Strong and durable.",
        "hp": 130,
        "attack": (12, 18),
        "passive": "Takes 20% less damage."
    },
    "mage": {
        "desc": "Master of arcane arts. High damage, fragile.",
        "hp": 85,
        "attack": (16, 26),
        "passive": "Upper attacks deal bonus damage."
    },
    "rogue": {
        "desc": "Agile assassin. Unpredictable strikes.",
        "hp": 105,
        "attack": (10, 22),
        "passive": "Higher chance to dodge attacks."
    }
}

weapons = {
    "Dagger": {"bonus": 3, "price": 30},
    "Sword": {"bonus": 6, "price": 60},
    "Axe": {"bonus": 8, "price": 90},
    "Magic Staff": {"bonus": 10, "price": 120}
}

# ---------------- PLAYER SETUP ----------------

def choose_class():
    divider()
    slow("Choose your class:\n")
    for c, v in classes.items():
        slow(f"🧙 {c.upper()}")
        slow(f"  ➤ {v['desc']}")
        slow(f"  ➤ Passive: {v['passive']}\n")

    cls = ""
    while cls not in classes:
        cls = input("Choose (warrior/mage/rogue): ").lower()
    return cls

def new_player():
    name = input("Hero name: ")
    cls = choose_class()
    return {
        "name": name,
        "class": cls,
        "hp": classes[cls]["hp"],
        "max_hp": classes[cls]["hp"],
        "gold": 50,
        "potions": 2,
        "weapon": "Dagger",
        "rooms": 0
    }

# ---------------- ENEMIES ----------------

enemies = [
    {"name": "Goblin", "hp": 40, "attack": (6, 12)},
    {"name": "Skeleton", "hp": 50, "attack": (8, 14)},
    {"name": "Orc", "hp": 70, "attack": (10, 18)}
]

boss = {"name": "DUNGEON LORD", "hp": 160, "attack": (15, 30)}

positions = ["upper", "middle", "lower"]

# ---------------- COMBAT ----------------

def fight(player, enemy):
    slow(f"⚔️ {enemy['name']} appears!")

    while enemy["hp"] > 0 and player["hp"] > 0:
        divider()
        slow(f"{player['name']} HP: {player['hp']} | {enemy['name']} HP: {enemy['hp']}")

        atk_pos = input("Attack position (upper/middle/lower): ").lower()
        if atk_pos not in positions:
            slow("❌ Invalid attack position!")
            continue

        enemy_pos = random.choice(positions)

        base = random.randint(*classes[player["class"]]["attack"])
        bonus = weapons[player["weapon"]]["bonus"]
        dmg = base + bonus

        # Class passives
        if player["class"] == "mage" and atk_pos == "upper":
            dmg = int(dmg * 1.3)

        if atk_pos == enemy_pos:
            dmg = int(dmg * 1.5)
            slow("🎯 Perfect hit!")
        else:
            dmg = int(dmg * 0.7)
            slow(f"⚠️ Enemy guarded {enemy_pos}!")

        enemy["hp"] -= dmg
        slow(f"🗡️ You dealt {dmg} damage.")

        if enemy["hp"] <= 0:
            break

        # Enemy attack
        enemy_dmg = random.randint(*enemy["attack"])

        if player["class"] == "warrior":
            enemy_dmg = int(enemy_dmg * 0.8)

        if player["class"] == "rogue" and random.random() < 0.25:
            slow("💨 You dodged the attack!")
            continue

        player["hp"] -= enemy_dmg
        slow(f"💥 Enemy hits you for {enemy_dmg} damage!")

    if player["hp"] > 0:
        gold = random.randint(25, 60)
        player["gold"] += gold
        slow(f"🏆 Victory! You gained {gold} gold.")

# ---------------- ROOMS ----------------

def trap_room(player):
    slow("🕳️ A hidden trap activates!")
    if random.random() < 0.5:
        slow("😮 You dodged it!")
    else:
        dmg = random.randint(10, 25)
        player["hp"] -= dmg
        slow(f"💥 Trap hits you for {dmg} damage!")

def shrine_room(player):
    slow("🧙 You find an ancient shrine...")
    heal = random.randint(15, 30)
    player["hp"] = min(player["max_hp"], player["hp"] + heal)
    slow(f"✨ Shrine heals you for {heal} HP.")

def lore_room():
    lore = [
        "The dungeon was once a sacred temple.",
        "Many heroes entered, few returned.",
        "The Dungeon Lord feeds on fear."
    ]
    slow(f"📜 Lore: {random.choice(lore)}")

# ---------------- MERCHANT ----------------

def merchant(player):
    slow("🏪 A merchant greets you...")
    while True:
        divider()
        slow(f"Gold: {player['gold']}")
        slow("1. Buy potion (25g)")
        slow("2. Buy weapon")
        slow("3. Leave")

        c = input("Choose: ")
        if c == "1" and player["gold"] >= 25:
            player["gold"] -= 25
            player["potions"] += 1
            slow("🧪 Potion bought.")
        elif c == "2":
            for i, w in enumerate(weapons, 1):
                slow(f"{i}. {w} (+{weapons[w]['bonus']}) - {weapons[w]['price']}g")
            w = input("Choose number: ")
            if w.isdigit():
                w = int(w) - 1
                if 0 <= w < len(weapons):
                    weapon = list(weapons.keys())[w]
                    if player["gold"] >= weapons[weapon]["price"]:
                        player["gold"] -= weapons[weapon]["price"]
                        player["weapon"] = weapon
                        slow(f"⚔️ Equipped {weapon}")
        else:
            return

# ---------------- GAME LOOP ----------------

divider()
slow("🏰 DUNGEON ADVENTURE RPG")

player = new_player()

while player["hp"] > 0:
    player["rooms"] += 1
    divider()
    slow(f"🚪 Room {player['rooms']}")

    if player["rooms"] % 5 == 0:
        slow("👹 BOSS ROOM!")
        fight(player, boss.copy())
        continue

    event = random.choice([
        "enemy", "trap", "shrine", "lore",
        "merchant", "empty"
    ])

    if event == "enemy":
        fight(player, random.choice(enemies).copy())
    elif event == "trap":
        trap_room(player)
    elif event == "shrine":
        shrine_room(player)
    elif event == "lore":
        lore_room()
    elif event == "merchant":
        merchant(player)
    else:
        slow("😐 The room is empty.")

    slow(f"❤️ {player['hp']} | ⚔️ {player['weapon']} | 💰 {player['gold']}")

    if input("Continue? (y/n): ").lower() != "y":
        break

divider()
if player["hp"] <= 0:
    slow("☠️ You died in the dungeon...")
else:
    slow("🏆 You escaped the dungeon!")

slow(f"Rooms cleared: {player['rooms']}")
slow("✨ Thanks for playing!")
