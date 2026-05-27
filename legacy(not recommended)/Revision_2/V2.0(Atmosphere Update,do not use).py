import random
import time
import json
import os

SAVE_FILE = "dungeon_save.json"
MAP_SIZE = 5

# ================= UTILITIES =================

def slow(text, d=0.02):
    for c in text:
        print(c, end="", flush=True)
        time.sleep(d)
    print()

def divider():
    print("\n" + "=" * 60)

def sound(type_):
    sounds = {
        "attack": "\a",
        "hit": "\a\a",
        "block": "\a",
        "level": "\a\a\a",
        "boss": "\a\a\a\a",
        "heal": "\a\a",
        "death": "\a\a\a\a\a"
    }
    print(sounds.get(type_, ""), end="", flush=True)

# ================= MAP SYSTEM =================

def create_map():
    return [["?" for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]

def draw_map(dungeon_map, px, py):
    divider()
    slow("🗺️ DUNGEON MAP")
    for y in range(MAP_SIZE):
        row = ""
        for x in range(MAP_SIZE):
            if x == px and y == py:
                row += "@ "
            elif dungeon_map[y][x] == "B":
                row += "B "
            else:
                row += dungeon_map[y][x] + " "
        print(row)
    divider()

def move_player(px, py):
    slow("Move (W/A/S/D):")
    move = input("> ").lower()

    if move == "w" and py > 0:
        py -= 1
    elif move == "s" and py < MAP_SIZE - 1:
        py += 1
    elif move == "a" and px > 0:
        px -= 1
    elif move == "d" and px < MAP_SIZE - 1:
        px += 1
    else:
        slow("🚧 A wall blocks your path.")
    return px, py

# ================= CLASSES =================

classes = {
    "warrior": {
        "desc": "Tank fighter. High HP. Takes reduced damage.",
        "hp": 140,
        "attack": (12, 18),
        "status": "bleed"
    },
    "mage": {
        "desc": "Glass cannon. Strong upper attacks. Burn damage.",
        "hp": 90,
        "attack": (16, 26),
        "status": "burn"
    },
    "rogue": {
        "desc": "Agile assassin. Dodge chance. Freeze enemies.",
        "hp": 110,
        "attack": (10, 22),
        "status": "freeze"
    }
}

positions = ["upper", "middle", "lower"]

weapons = {
    "Dagger": {"bonus": 3, "price": 30},
    "Sword": {"bonus": 6, "price": 60},
    "Axe": {"bonus": 8, "price": 90},
    "Magic Staff": {"bonus": 10, "price": 120}
}

# ================= SAVE / LOAD =================

def save_game(player):
    with open(SAVE_FILE, "w") as f:
        json.dump(player, f)
    slow("💾 Game saved.")

def load_game():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            slow("📂 Save loaded.")
            return json.load(f)
    return None

# ================= PLAYER =================

def create_player():
    divider()
    name = input("Hero name: ")
    divider()

    for c, v in classes.items():
        slow(f"{c.upper()}: {v['desc']}")

    cls = ""
    while cls not in classes:
        cls = input("Choose class: ").lower()

    player = {
        "name": name,
        "class": cls,
        "hp": classes[cls]["hp"],
        "max_hp": classes[cls]["hp"],
        "level": 1,
        "xp": 0,
        "gold": 50,
        "potions": 2,
        "weapon": "Dagger",
        "rooms": 0,
        "attack_memory": {"upper": 0, "middle": 0, "lower": 0},
        "path": None,
        "final_boss_defeated": False,
        "map": create_map(),
        "x": MAP_SIZE // 2,
        "y": MAP_SIZE // 2
    }
    return player

# ================= LEVELING =================

def gain_xp(player, amount):
    player["xp"] += amount
    if player["xp"] >= player["level"] * 60:
        player["xp"] = 0
        player["level"] += 1
        player["max_hp"] += 10
        player["hp"] = player["max_hp"]
        sound("level")
        slow(f"📈 LEVEL UP! You are now level {player['level']}")

# ================= COMBAT =================

def fight(player, enemy, final=False):
    slow(f"⚔️ {enemy['name']} attacks!")
    enemy["memory"] = {"upper": 0, "middle": 0, "lower": 0}

    while enemy["hp"] > 0 and player["hp"] > 0:
        divider()
        slow(f"{player['name']} HP: {player['hp']} | {enemy['name']} HP: {enemy['hp']}")

        atk = input("Attack (upper/middle/lower): ").lower()
        if atk not in positions:
            continue

        sound("attack")
        player["attack_memory"][atk] += 1
        enemy["memory"][atk] += 1

        guard = max(enemy["memory"], key=enemy["memory"].get)
        base = random.randint(*classes[player["class"]]["attack"])
        dmg = base + weapons[player["weapon"]]["bonus"] + player["level"] * 2

        if player["class"] == "mage" and atk == "upper":
            dmg = int(dmg * 1.3)

        if atk == guard:
            dmg = int(dmg * 0.6)
            sound("block")
            slow("🛡️ Blocked!")
        else:
            dmg = int(dmg * 1.4)
            slow("🎯 Direct hit!")

        enemy["hp"] -= dmg
        slow(f"You deal {dmg} damage.")

        if enemy["hp"] <= 0:
            break

        enemy_dmg = random.randint(10, 18 if not final else 24)

        if player["class"] == "warrior":
            enemy_dmg = int(enemy_dmg * 0.8)

        if player["class"] == "rogue" and random.random() < 0.25:
            slow("💨 You dodged!")
        else:
            sound("hit")
            player["hp"] -= enemy_dmg
            slow(f"Enemy hits for {enemy_dmg}")

    if player["hp"] > 0:
        gain_xp(player, 60 if final else 40)
        gold = random.randint(40, 100)
        player["gold"] += gold
        slow(f"🏆 Victory! +{gold} gold")

# ================= ROOMS =================

def trap_room(player):
    slow("🕳️ A trap triggers!")
    if random.random() < 0.5:
        slow("You escape unharmed.")
    else:
        dmg = random.randint(15, 30)
        player["hp"] -= dmg
        sound("hit")
        slow(f"Trap deals {dmg} damage!")

def shrine_room(player):
    slow("🧙 A healing shrine glows.")
    heal = random.randint(25, 40)
    player["hp"] = min(player["max_hp"], player["hp"] + heal)
    sound("heal")
    slow(f"Healed {heal} HP.")

def lore_room():
    lore = [
        "The dungeon watches all who enter.",
        "Only sacrifice grants power.",
        "The final door judges the soul."
    ]
    slow("📜 " + random.choice(lore))

def merchant(player):
    slow("🏪 A merchant appears.")
    while True:
        divider()
        slow(f"Gold: {player['gold']}")
        slow("1. Buy potion (25g)")
        slow("2. Buy weapon")
        slow("3. Leave")

        c = input("> ")
        if c == "1" and player["gold"] >= 25:
            player["gold"] -= 25
            player["potions"] += 1
            slow("Potion bought.")
        elif c == "2":
            for i, w in enumerate(weapons, 1):
                slow(f"{i}. {w} (+{weapons[w]['bonus']}) {weapons[w]['price']}g")
            w = input("> ")
            if w.isdigit():
                w = int(w) - 1
                wp = list(weapons.keys())[w]
                if player["gold"] >= weapons[wp]["price"]:
                    player["gold"] -= weapons[wp]["price"]
                    player["weapon"] = wp
                    slow(f"Equipped {wp}")
        else:
            return

# ================= GAME LOOP =================

divider()
slow("🏰 DUNGEON ADVENTURE RPG")
slow("🌌 Version 8 — Atmosphere Update")

player = None
if input("Load game? (y/n): ").lower() == "y":
    player = load_game()

if not player:
    player = create_player()

while player["hp"] > 0:
    draw_map(player["map"], player["x"], player["y"])
    player["map"][player["y"]][player["x"]] = "."

    player["rooms"] += 1
    slow(f"🚪 Room {player['rooms']}")

    if player["rooms"] == 6 and not player["path"]:
        player["path"] = input("Choose path (light/shadow): ").lower()

    if player["rooms"] == 15:
        player["map"][0][0] = "B"
        sound("boss")
        slow("👑 THE DUNGEON LORD EMERGES!")
        fight(player, {"name": "Dungeon Lord", "hp": 300 + player["level"] * 30}, final=True)
        player["final_boss_defeated"] = player["hp"] > 0
        save_game(player)
        break

    event = random.choice(["enemy", "trap", "shrine", "lore", "merchant"])
    if event == "enemy":
        fight(player, {"name": "Dungeon Fiend", "hp": 70 + player["level"] * 15})
    elif event == "trap":
        trap_room(player)
    elif event == "shrine":
        shrine_room(player)
    elif event == "lore":
        lore_room()
    elif event == "merchant":
        merchant(player)

    slow(f"❤️ HP: {player['hp']} | ⭐ Lv {player['level']} | 💰 {player['gold']}")
    cmd = input("Continue? (y/n/save): ").lower()
    if cmd == "save":
        save_game(player)
        break
    elif cmd != "y":
        break

# ================= ENDINGS =================

divider()
slow("🏁 FINAL ENDING")

if player["final_boss_defeated"]:
    if player["path"] == "shadow" and player["level"] >= 6:
        slow("👑 TRUE CONQUEROR ENDING")
    elif player["path"] == "light":
        slow("✨ TRUE SAVIOR ENDING")
    else:
        slow("⚔️ SURVIVOR ENDING")
else:
    sound("death")
    slow("😐 WANDERER ENDING")

slow("✨ Thanks for playing Dungeon Adventure RPG!")
nn