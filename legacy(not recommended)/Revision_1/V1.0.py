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
    print("\n" + "=" * 45)

# ---------------- PLAYER SETUP ----------------

classes = {
    "warrior": {"hp": 120, "attack": (12, 20)},
    "mage": {"hp": 80, "attack": (15, 25)},
    "rogue": {"hp": 100, "attack": (10, 30)}
}

weapons = {
    "Dagger": {"bonus": 3, "price": 30},
    "Sword": {"bonus": 6, "price": 60},
    "Axe": {"bonus": 8, "price": 90},
    "Magic Staff": {"bonus": 10, "price": 120}
}

def new_player():
    name = input("Hero name: ")
    cls = ""
    while cls not in classes:
        cls = input("Choose class (warrior/mage/rogue): ").lower()

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

# ---------------- SAVE / LOAD ----------------

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

# ---------------- ENEMIES ----------------

enemies = [
    {"name": "Goblin", "hp": 35, "attack": (6, 12)},
    {"name": "Skeleton", "hp": 45, "attack": (8, 14)},
    {"name": "Orc", "hp": 65, "attack": (10, 18)}
]

boss = {"name": "DUNGEON LORD", "hp": 150, "attack": (15, 30)}

# ---------------- MERCHANT ----------------

def merchant(player):
    slow("🏪 A mysterious merchant appears...")
    while True:
        divider()
        slow(f"💰 Gold: {player['gold']}")
        slow("1️⃣ Buy potion (25 gold)")
        slow("2️⃣ Buy weapon")
        slow("3️⃣ Leave shop")

        choice = input("Choose: ")

        if choice == "1":
            if player["gold"] >= 25:
                player["gold"] -= 25
                player["potions"] += 1
                slow("🧪 Potion purchased!")
            else:
                slow("❌ Not enough gold.")

        elif choice == "2":
            for i, w in enumerate(weapons, 1):
                slow(f"{i}. {w} (+{weapons[w]['bonus']} dmg) - {weapons[w]['price']}g")

            w_choice = input("Choose weapon or press Enter to cancel: ")
            if w_choice.isdigit():
                w_choice = int(w_choice) - 1
                if 0 <= w_choice < len(weapons):
                    weapon = list(weapons.keys())[w_choice]
                    price = weapons[weapon]["price"]
                    if player["gold"] >= price:
                        player["gold"] -= price
                        player["weapon"] = weapon
                        slow(f"⚔️ You equipped {weapon}!")
                    else:
                        slow("❌ Not enough gold.")

        elif choice == "3":
            slow("🧙 Merchant disappears into the shadows...")
            return

# ---------------- COMBAT ----------------

def fight(player, enemy):
    slow(f"⚔️ {enemy['name']} appears!")
    defending = False

    while enemy["hp"] > 0 and player["hp"] > 0:
        print(f"\n{player['name']} HP: {player['hp']} | {enemy['name']} HP: {enemy['hp']}")
        choice = input("(A)ttack (P)otion (D)efend (R)un: ").lower()

        if choice == "a":
            base = random.randint(*classes[player["class"]]["attack"])
            bonus = weapons[player["weapon"]]["bonus"]
            dmg = base + bonus
            enemy["hp"] -= dmg
            slow(f"🗡️ You deal {dmg} damage!")

        elif choice == "p":
            if player["potions"] > 0:
                heal = random.randint(20, 35)
                player["hp"] = min(player["max_hp"], player["hp"] + heal)
                player["potions"] -= 1
                slow(f"🧪 Healed {heal} HP.")
            else:
                slow("❌ No potions!")

        elif choice == "d":
            defending = True
            slow("🛡️ You defend!")

        elif choice == "r":
            if random.random() < 0.4:
                slow("🏃 Escaped!")
                return
            else:
                slow("❌ Escape failed!")

        if enemy["hp"] > 0:
            dmg = random.randint(*enemy["attack"])
            if defending:
                dmg //= 2
                defending = False
            player["hp"] -= dmg
            slow(f"💥 You take {dmg} damage!")

    if player["hp"] > 0:
        gold = random.randint(20, 50)
        player["gold"] += gold
        slow(f"🏆 Victory! Gained {gold} gold.")

# ---------------- GAME LOOP ----------------

divider()
slow("🏰 DUNGEON ADVENTURE RPG")

player = None
if input("Load game? (y/n): ").lower() == "y":
    player = load_game()

if not player:
    player = new_player()

while player["hp"] > 0:
    player["rooms"] += 1
    divider()
    slow(f"🚪 Room {player['rooms']}")

    if player["rooms"] % 5 == 0:
        slow("👹 BOSS FIGHT!")
        fight(player, boss.copy())
        continue

    event = random.choice(["enemy", "treasure", "potion", "merchant", "empty"])

    if event == "enemy":
        fight(player, random.choice(enemies).copy())

    elif event == "treasure":
        gold = random.randint(30, 80)
        player["gold"] += gold
        slow(f"💰 Found {gold} gold!")

    elif event == "potion":
        player["potions"] += 1
        slow("🧪 Found a potion!")

    elif event == "merchant":
        merchant(player)

    else:
        slow("😐 Empty room...")

    slow(f"❤️ {player['hp']} | ⚔️ {player['weapon']} | 💰 {player['gold']} | 🧪 {player['potions']}")

    cmd = input("Continue? (y/n/save): ").lower()
    if cmd == "save":
        save_game(player)
        break
    elif cmd != "y":
        break

divider()
if player["hp"] <= 0:
    slow("☠️ You died in the dungeon...")
else:
    slow("🏆 You escaped the dungeon!")

slow(f"Rooms cleared: {player['rooms']}")
slow("✨ Thanks for playing!")
n