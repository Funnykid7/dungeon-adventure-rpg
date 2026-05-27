import random
import pygame
import time
import json
import os
pygame.mixer.init()
BATTLE_MUSIC = "battle_music.mp3"
EXPLORE_MUSIC = "game_world.mp3"

SAVE_FILE = "dungeon_save.json"
MAP_SIZE = 5
MAX_FLOORS = 3

# ================= UTILITIES =================

def slow(text, d=0.02):
    for c in text:
        print(c, end="", flush=True)
        time.sleep(d)
    print()

def divider():
    print("\n" + "=" * 60)

def sound(kind):
    sounds = {
        "attack": "\a",
        "hit": "\a\a",
        "block": "\a",
        "heal": "\a\a",
        "level": "\a\a\a",
        "boss": "\a\a\a\a",
        "death": "\a\a\a\a\a"
    }
    print(sounds.get(kind, ""), end="", flush=True)
    
def play_explore_music():
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
    pygame.mixer.music.load(EXPLORE_MUSIC)
    pygame.mixer.music.play(-1)

def play_battle_music():
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
    pygame.mixer.music.load(BATTLE_MUSIC)
    pygame.mixer.music.play(-1)

def stop_music():
    pygame.mixer.music.stop()



# ================= MAP SYSTEM =================

def create_map():
    return [["?" for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]

def draw_map(dmap, px, py, floor):
    divider()
    slow(f"🗺️ FLOOR {floor}")
    for y in range(MAP_SIZE):
        row = ""
        for x in range(MAP_SIZE):
            row += "@ " if (x == px and y == py) else dmap[y][x] + " "
        print(row)
    divider()

def move_player(px, py):
    move = input("Move (W/A/S/D): ").lower()
    if move == "w" and py > 0: py -= 1
    elif move == "s" and py < MAP_SIZE - 1: py += 1
    elif move == "a" and px > 0: px -= 1
    elif move == "d" and px < MAP_SIZE - 1: px += 1
    else: slow("🚧 Wall blocks your path.")
    return px, py

# ================= CLASSES =================

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
        "desc": "Holy warrior. Heals slightly every turn.",
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

positions = ["upper", "middle", "lower"]

weapons = {
    "Dagger": {"bonus": 3, "price": 30},
    "Sword": {"bonus": 6, "price": 60},
    "Axe": {"bonus": 9, "price": 90},
    "Magic Staff": {"bonus": 12, "price": 120},
    "Royal Claymore": {"bonus": 18, "price": 250},
    "Spear of the Sheik": {"bonus": 26, "price": 400}
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

    return {
        "name": name,
        "class": cls,
        "hp": classes[cls]["hp"],
        "max_hp": classes[cls]["hp"],
        "level": 1,
        "xp": 0,
        "gold": 50,

        # Potions
        "potions": 2,
        "strength_potions": 0,
        "defense_potions": 0,

        # Potion effects
        "strength_turns": 0,
        "defense_turns": 0,

        "weapon": "Dagger",
        "floor": 1,
        "rooms": 0,
        "revived": False,
        "map": create_map(),
        "x": MAP_SIZE // 2,
        "y": MAP_SIZE // 2,
        "last_attack": None
    }


# ================= POTIONS =================

def use_potion(player):
    if player["potions"] <= 0:
        slow("❌ No potions left.")
        return
    heal = 40
    player["potions"] -= 1
    player["hp"] = min(player["max_hp"], player["hp"] + heal)
    sound("heal")
    slow(f"🧪 Healed {heal} HP.")
    
def use_strength_potion(player):
    if player["strength_potions"] <= 0:
        slow("❌ No strength potions.")
        return
    player["strength_potions"] -= 1
    player["strength_turns"] = 5
    slow("💪 Strength increased for 5 turns!")

def use_defense_potion(player):
    if player["defense_potions"] <= 0:
        slow("❌ No defense potions.")
        return
    player["defense_potions"] -= 1
    player["defense_turns"] = 5
    slow("🛡️ Defense increased for 5 turns!")

# ================= DIVINE INTERVENTION =================

def divine_intervention(player):
    if player["revived"]:
        return False
    if random.random() <= 0.3:
        divider()
        sound("level")
        slow("✨ THE GODS INTERVENE ✨")
        player["hp"] = player["max_hp"]
        player["revived"] = True
        return True
    return False

# ================= LEVELING =================

def gain_xp(player, amount):
    player["xp"] += amount
    if player["xp"] >= player["level"] * 60:
        player["xp"] = 0
        player["level"] += 1
        player["max_hp"] += 10
        player["hp"] = player["max_hp"]
        sound("level")
        slow(f"📈 Level up! Now level {player['level']}")

# ================= COMBAT =================

def fight(player, enemy):
    slow(f"⚔️ {enemy['name']} appears!")
    play_battle_music()

    while enemy["hp"] > 0 and player["hp"] > 0:
        potion_used = False

        divider()
        slow(f"{player['name']} HP {player['hp']} | {enemy['name']} HP {enemy['hp']}")
        atk = input("upper/middle/lower | potion | str | def: ").lower()

        # ---- PLAYER ACTION ----
        if atk == "potion":
            use_potion(player)
            potion_used = True
        elif atk == "str":
            use_strength_potion(player)
            potion_used = True
        elif atk == "def":
            use_defense_potion(player)
            potion_used = True
        elif atk not in positions:
            continue

        # ---- PLAYER ATTACK (ONLY IF NOT POTION) ----
        if not potion_used:
            dmg = random.randint(*classes[player["class"]]["attack"])
            dmg += weapons[player["weapon"]]["bonus"] + player["level"] * 2

            if player["strength_turns"] > 0:
                dmg = int(dmg * 1.5)

            if player["class"] == "mage" and atk == "upper":
                dmg = int(dmg * 1.3)

            if player["class"] == "ranger" and random.random() < 0.25:
                dmg = int(dmg * 1.6)
                slow("🎯 Critical hit!")

            if player["class"] == "monk" and atk == player["last_attack"]:
                dmg = int(dmg * 1.4)
                slow("🥋 Combo!")

            enemy["hp"] -= dmg
            slow(f"You deal {dmg} damage.")

            if enemy["hp"] <= 0:
                break

        # ---- ENEMY TURN ----
        enemy_dmg = random.randint(10, 18) + player["floor"] * 2

        if potion_used:
            enemy_dmg = int(enemy_dmg * 0.6)  # reduced damage

        if player["defense_turns"] > 0:
            enemy_dmg = int(enemy_dmg * 0.5)

        if player["class"] == "warrior":
            enemy_dmg = int(enemy_dmg * 0.8)

        if player["class"] == "rogue" and random.random() < 0.25:
            slow("💨 Dodged!")
        else:
            player["hp"] -= enemy_dmg
            slow(f"Enemy hits {enemy_dmg}")

        # ---- PASSIVES & TURN CLEANUP ----
        if player["class"] == "paladin":
            heal = 4
            player["hp"] = min(player["max_hp"], player["hp"] + heal)
            slow("✨ Holy light heals you")

        if player["hp"] <= 0 and divine_intervention(player):
            continue

        player["strength_turns"] = max(0, player["strength_turns"] - 1)
        player["defense_turns"] = max(0, player["defense_turns"] - 1)

        if not potion_used:
            player["last_attack"] = atk

    # ---- POST COMBAT ----
    if player["hp"] > 0:
        gain_xp(player, 40 + player["floor"] * 10)
        gold = random.randint(40, 80)
        player["gold"] += gold
        slow(f"🏆 Victory! +{gold} gold")

    pygame.mixer.music.fadeout(1000)
    time.sleep(1)
    play_explore_music()


# ================= ROOMS =================

def merchant(player):
    slow("🏪 Merchant appears.")
    while True:
        slow(f"Gold: {player['gold']}")
        slow("1. Healing Potion (25g)")
        slow("2. Strength Potion (200g)")
        slow("3. Defense Potion (200g)")
        slow("4. Weapons")
        slow("5. Leave")
        c = input("> ")

        if c == "1" and player["gold"] >= 25:
            player["gold"] -= 25
            player["potions"] += 1
        elif c == "2" and player["gold"] >= 200:
            player["gold"] -= 200
            player["strength_potions"] += 1
        elif c == "3" and player["gold"] >= 200:
            player["gold"] -= 200
            player["defense_potions"] += 1
        elif c == "4":
            for i, w in enumerate(weapons, 1):
                slow(f"{i}. {w} | Damage +{weapons[w]['bonus']} | {weapons[w]['price']}g")
            pick = input("> ")
            if pick.isdigit():
                w = list(weapons.keys())[int(pick) - 1]
                if player["gold"] >= weapons[w]["price"]:
                    player["gold"] -= weapons[w]["price"]
                    player["weapon"] = w
        else:
            return

def trap(player):
    slow("🕳️ Trap!")
    if random.random() < 0.5:
        slow("You escape.")
    else:
        dmg = random.randint(15, 30)
        player["hp"] -= dmg
        sound("hit")

def shrine(player):
    heal = random.randint(30, 45)
    player["hp"] = min(player["max_hp"], player["hp"] + heal)
    sound("heal")
    slow(f"🧙 Shrine heals {heal}")

# ================= FLOOR TRANSITION =================

def next_floor(player):
    divider()
    slow(f"⬇️ Descending to floor {player['floor'] + 1}...")
    player["floor"] += 1
    player["map"] = create_map()
    player["x"] = MAP_SIZE // 2
    player["y"] = MAP_SIZE // 2
    player["rooms"] = 0

# ================= GAME LOOP =================

divider()
slow("🏰 DUNGEON ADVENTURE RPG")
slow("🌌 Version 2.3 — Music Update")

player = load_game() if input("Load game? (y/n): ").lower() == "y" else create_player()
play_explore_music()

while player["hp"] > 0:
    draw_map(player["map"], player["x"], player["y"], player["floor"])
    player["map"][player["y"]][player["x"]] = "."

    player["rooms"] += 1
    player["x"], player["y"] = move_player(player["x"], player["y"])

    if player["rooms"] >= 12:
        if player["floor"] < MAX_FLOORS:
            next_floor(player)
            continue
        else:
            sound("boss")
            slow("👑 THE DUNGEON LORD AWAKENS")
            fight(player, {"name": "Dungeon Lord", "hp": 350 + player["level"] * 40})
            break

    event = random.choice(["enemy", "trap", "shrine", "merchant"])
    if event == "enemy":
        fight(player, {"name": "Dungeon Fiend", "hp": 80 + player["floor"] * 25})
    elif event == "trap":
        trap(player)
    elif event == "shrine":
        shrine(player)
    elif event == "merchant":
        merchant(player)

    slow(f"❤️ {player['hp']} | 🧪 {player['potions']} | 💪 {player['strength_potions']} | 🛡️ {player['defense_potions']} | ⭐ {player['level']} | 💰 {player['gold']}")
    cmd = input("Continue? (y/n/save/potion): ").lower()
    if cmd == "potion":
        use_potion(player)
    elif cmd == "save":
        save_game(player)
        break
    elif cmd != "y":
        break

divider()
slow("✨ Thanks for playing Dungeon Adventure RPG!")
stop_music()
