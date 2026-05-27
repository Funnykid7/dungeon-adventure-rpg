import random
import time

# ---------------- UTILS ----------------

def slow(text, d=0.02):
    for c in text:
        print(c, end="", flush=True)
        time.sleep(d)
    print()

def divider():
    print("\n" + "=" * 60)

# ---------------- CLASSES ----------------

classes = {
    "warrior": {
        "desc": "Frontline tank. Bleed attacks. Takes less damage.",
        "hp": 140,
        "attack": (12, 18),
        "passive": "20% damage reduction",
        "status": "bleed"
    },
    "mage": {
        "desc": "Glass cannon. Burn damage. Strong upper attacks.",
        "hp": 90,
        "attack": (16, 26),
        "passive": "Upper attacks +30%",
        "status": "burn"
    },
    "rogue": {
        "desc": "Agile assassin. Freeze enemies. Dodge chance.",
        "hp": 110,
        "attack": (10, 22),
        "passive": "25% dodge chance",
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

# ---------------- PLAYER ----------------

def create_player():
    divider()
    name = input("Hero name: ")
    divider()

    for c, v in classes.items():
        slow(f"{c.upper()}: {v['desc']}")
        slow(f"Passive: {v['passive']}\n")

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
        "potions": 2,
        "weapon": "Dagger",
        "rooms": 0,
        "attack_memory": {"upper": 0, "middle": 0, "lower": 0},
        "path": None
    }

# ---------------- LEVELING ----------------

def gain_xp(player, amount):
    player["xp"] += amount
    needed = player["level"] * 60
    if player["xp"] >= needed:
        player["xp"] -= needed
        player["level"] += 1
        player["max_hp"] += 10
        player["hp"] = player["max_hp"]
        slow(f"📈 LEVEL UP! Now level {player['level']}")

# ---------------- STATUS EFFECTS ----------------

def apply_status(enemy, status):
    enemy["status"] = status
    enemy["status_turns"] = 3

# ---------------- COMBAT ----------------

def fight(player, enemy):
    slow(f"⚔️ {enemy['name']} engages you!")
    enemy.setdefault("memory", {"upper": 0, "middle": 0, "lower": 0})

    while enemy["hp"] > 0 and player["hp"] > 0:
        divider()
        slow(f"{player['name']} HP: {player['hp']} | {enemy['name']} HP: {enemy['hp']}")

        atk = input("Attack (upper/middle/lower): ").lower()
        if atk not in positions:
            continue

        player["attack_memory"][atk] += 1
        enemy["memory"][atk] += 1

        predicted = max(enemy["memory"], key=enemy["memory"].get)
        enemy_guard = predicted if random.random() < 0.6 else random.choice(positions)

        base = random.randint(*classes[player["class"]]["attack"])
        dmg = base + weapons[player["weapon"]]["bonus"] + player["level"] * 2

        if player["class"] == "mage" and atk == "upper":
            dmg = int(dmg * 1.3)

        if atk == enemy_guard:
            dmg = int(dmg * 0.6)
            slow("🛡️ Enemy blocked!")
        else:
            dmg = int(dmg * 1.4)
            slow("🎯 Direct hit!")

        enemy["hp"] -= dmg
        slow(f"🗡️ You deal {dmg} damage.")

        if random.random() < 0.3:
            apply_status(enemy, classes[player["class"]]["status"])
            slow(f"🧪 {enemy['name']} is afflicted with {enemy['status']}")

        if enemy["hp"] <= 0:
            break

        enemy_dmg = random.randint(8, 16)
        if player["class"] == "warrior":
            enemy_dmg = int(enemy_dmg * 0.8)

        if player["class"] == "rogue" and random.random() < 0.25:
            slow("💨 You dodged!")
        else:
            player["hp"] -= enemy_dmg
            slow(f"💥 Enemy hits for {enemy_dmg}")

        if enemy.get("status"):
            enemy["status_turns"] -= 1
            if enemy["status"] == "bleed":
                enemy["hp"] -= 5
                slow("🩸 Bleed damage")
            elif enemy["status"] == "burn":
                enemy["hp"] -= 7
                slow("🔥 Burn damage")

            if enemy["status_turns"] <= 0:
                enemy.pop("status")

    if player["hp"] > 0:
        gold = random.randint(30, 60)
        player["gold"] += gold
        gain_xp(player, 40)
        slow(f"🏆 Victory! +{gold} gold")

# ---------------- ROOMS ----------------

def trap_room(player):
    slow("🕳️ A trap springs!")
    if random.random() < 0.5:
        slow("You dodged it!")
    else:
        dmg = random.randint(10, 25)
        player["hp"] -= dmg
        slow(f"Trap deals {dmg} damage")

def shrine_room(player):
    slow("🧙 Ancient shrine restores you")
    heal = random.randint(20, 35)
    player["hp"] = min(player["max_hp"], player["hp"] + heal)
    slow(f"Healed {heal} HP")

def lore_room():
    lore = [
        "The dungeon was once holy ground.",
        "The Dungeon Lord feeds on ambition.",
        "Every path has a price."
    ]
    slow(f"📜 {random.choice(lore)}")

def merchant(player):
    slow("🏪 Merchant appears")
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
            slow("Potion purchased")
        elif c == "2":
            for i, w in enumerate(weapons, 1):
                slow(f"{i}. {w} (+{weapons[w]['bonus']}) {weapons[w]['price']}g")
            w = input("Choose: ")
            if w.isdigit():
                w = int(w) - 1
                if 0 <= w < len(weapons):
                    wp = list(weapons.keys())[w]
                    if player["gold"] >= weapons[wp]["price"]:
                        player["gold"] -= weapons[wp]["price"]
                        player["weapon"] = wp
                        slow(f"Equipped {wp}")
        else:
            return

# ---------------- GAME LOOP ----------------

divider()
slow("🏰 DUNGEON ADVENTURE RPG – EVOLUTION UPDATE")

player = create_player()

while player["hp"] > 0:
    player["rooms"] += 1
    divider()
    slow(f"🚪 Room {player['rooms']}")

    if player["rooms"] == 6:
        slow("🔀 The dungeon splits...")
        player["path"] = input("Choose path (light/shadow): ").lower()

    if player["rooms"] % 5 == 0:
        boss = {"name": "Dungeon Lord's Guard", "hp": 120 + player["level"] * 20}
        fight(player, boss)
        continue

    event = random.choice(["enemy", "trap", "shrine", "lore", "merchant", "enemy"])
    if event == "enemy":
        fight(player, {"name": "Dungeon Fiend", "hp": 60 + player["level"] * 10})
    elif event == "trap":
        trap_room(player)
    elif event == "shrine":
        shrine_room(player)
    elif event == "lore":
        lore_room()
    elif event == "merchant":
        merchant(player)

    slow(f"❤️ {player['hp']} | ⭐ Lv {player['level']} | 💰 {player['gold']}")

    if input("Continue? (y/n): ").lower() != "y":
        break

divider()
slow("🏁 ENDING")

if player["path"] == "shadow" and player["level"] >= 5:
    slow("👑 Shadow Conqueror Ending")
elif player["path"] == "light":
    slow("✨ Savior of the Dungeon Ending")
else:
    slow("😐 Wanderer Ending")

slow("✨ Thanks for playing!")
