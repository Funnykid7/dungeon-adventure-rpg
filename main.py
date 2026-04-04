import random
import pygame
import time
import json
import os
import sys

# Import custom modules
from src.entities import classes, weapons
from src.data_manager import save_game, load_game, slow
from src.utils import divider, sound, load_img

# ================= COMBAT LOG =================
battle_messages = []
waiting_for_input = False

#================== MISC =======================
pygame.init()
pygame.mixer.init()
BATTLE_MUSIC = "assets/audio/battle_music.mp3"
EXPLORE_MUSIC = "assets/audio/game_world.mp3"

SAVE_FILE = "dungeon_save.json"
MAP_SIZE = 5
MAX_FLOORS = 3

player_flash_timer = 0
enemy_flash_timer = 0
FLASH_DURATION = 10
door_cooldown = 0
DOOR_COOLDOWN_TIME = 20  # frames (~0.3 sec)


# ================= OVERWORLD =================
TILE_SIZE = 48
ROOM_W, ROOM_H = 960, 540

player_world_x = ROOM_W // 2
player_world_y = ROOM_H // 2
player_speed = 4

current_room = (0, 0)
visited_rooms = {}
entry_dir = None
DOOR_SIZE = 48
DOOR_PADDING = 8

door_zones = {
    "up": pygame.Rect(432, 36, 96, 48),
    "down": pygame.Rect(432, 456, 96, 48),
    "left": pygame.Rect(36, 216, 48, 96),
    "right": pygame.Rect(876, 216, 48, 96),
}

# ================= UTILITIES =================

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

def draw_battle_ui(player_hp, enemy_hp):
    screen.blit(battle_bg, (0, 0))
    screen.blit(player_img, (200, 260))
    screen.blit(enemy_img, (600, 240))

    p_text = font.render(f"HP: {player_hp}", True, (255, 255, 255))
    e_text = font.render(f"HP: {enemy_hp}", True, (255, 80, 80))

    screen.blit(p_text, (200, 230))
    screen.blit(e_text, (600, 210))

def draw_hp_bar(screen, x, y, w, h, current, max_hp, color):
    ratio = max(0, current / max_hp)
    pygame.draw.rect(screen, (60, 60, 60), (x, y, w, h))
    pygame.draw.rect(screen, color, (x, y, int(w * ratio), h))
    pygame.draw.rect(screen, (0, 0, 0), (x, y, w, h), 2)

def draw_text_slow(text, x, y):
    words = text.split(" ")
    line = ""
    for word in words:
        test = line + word + " "
        surface = font.render(test, True, (255,255,255))
        if surface.get_width() > SCREEN_W - 48:
            screen.blit(font.render(line, True, (255,255,255)), (x, y))
            y += 32
            line = word + " "
        else:
            line = test
    screen.blit(font.render(line, True, (255,255,255)), (x, y))


def clear_dialogue_box():
    dialogue_rect = pygame.Rect(
        0,
        SCREEN_H - 140,
        SCREEN_W,
        140
    )
    pygame.draw.rect(screen, (20, 20, 20), dialogue_rect)
    pygame.draw.rect(screen, (180, 180, 180), dialogue_rect, 3)



def show_battle_messages():
    global waiting_for_input

    if not battle_messages:
        waiting_for_input = False
        return

    waiting_for_input = True
    text_surface = font.render(battle_messages[0], True, (255, 255, 255))
    screen.blit(text_surface, (24, SCREEN_H - 110))

def flash_sprite(sprite):
    flash = sprite.copy()
    flash.fill((255, 0, 0, 120), special_flags=pygame.BLEND_RGBA_ADD)
    return flash

def tint_sprite(sprite, color):
    tinted = sprite.copy()
    tinted.fill(color, special_flags=pygame.BLEND_RGB_ADD)
    return tinted


def overworld(player):
    global player_world_x, player_world_y, current_room
    global door_cooldown
    global entry_dir
    door_cooldown = DOOR_COOLDOWN_TIME


    running = True
    clock = pygame.time.Clock()

    while running:
        clock.tick(60)
        screen.blit(room_bg, (0, 0))
        if door_cooldown > 0:
            door_cooldown -= 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        global player_dir, player_frame, player_anim_timer, player_moving

        player_moving = False

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            player_world_y -= player_speed
            player_dir = "up"
            player_moving = True

        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            player_world_y += player_speed
            player_dir = "down"
            player_moving = True

        elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
            player_world_x -= player_speed
            player_dir = "left"
            player_moving = True

        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            player_world_x += player_speed
            player_dir = "right"
            player_moving = True


    # ===== ANIMATION =====
        if player_moving:
            player_anim_timer += 1
            if player_anim_timer >= 12:
                player_frame = (player_frame + 1) % 2
                player_anim_timer = 0
        else:
            player_frame = 0


        # ===== SELECT SPRITE FIRST =====
        if player_moving:
            sprite = player_sprites[player_dir]["walk"][player_frame]
        else:
            sprite = player_sprites[player_dir]["idle"]

        # ===== PLAYER COLLISION RECT =====
        player_rect = pygame.Rect(
            player_world_x + 16,
            player_world_y + 16,
            32,
            32
            )


       # ===== INVISIBLE DOOR TRIGGERS =====

        for direction, door in door_zones.items():
            if door_cooldown == 0 and player_rect.colliderect(door):

                door_cooldown = DOOR_COOLDOWN_TIME  # ✅ SET HERE ONLY
                entry_dir = direction

                if direction == "up":
                    current_room = (current_room[0], current_room[1] - 1)
                elif direction == "down":
                    current_room = (current_room[0], current_room[1] + 1)
                elif direction == "left":
                    current_room = (current_room[0] - 1, current_room[1])
                elif direction == "right":
                    current_room = (current_room[0] + 1, current_room[1])

                running = False
                break




        # ===== DRAW PLAYER =====
        screen.blit(sprite, (player_world_x, player_world_y))



        pygame.display.flip()

    return get_room(current_room, player["floor"])


def weapon_shop_gui(player):
    clock = pygame.time.Clock()
    running = True

    weapon_items = list(weapons.items())

    while running:
        clock.tick(60)
        screen.blit(merchant_bg, (0, 0))

        panel = pygame.Rect(60, 60, 900, 420)
        pygame.draw.rect(screen, (24, 24, 24), panel)
        pygame.draw.rect(screen, (200, 180, 120), panel, 4)

        title = font.render("WEAPON SHOP", True, (255, 220, 120))
        screen.blit(title, (400, 80))

        y = 140
        for i, (name, data) in enumerate(weapon_items):
            txt = f"{i+1}. {name}  (+{data['bonus']} ATK)  {data['price']}g"
            screen.blit(font.render(txt, True, (255, 255, 255)), (120, y))
            y += 40

        gold_txt = font.render(f"Gold: {player['gold']}", True, (255, 220, 120))
        screen.blit(gold_txt, (700, 100))

        screen.blit(
            small_font.render("ESC - Back", True, (200,200,200)),
            (120, 430)
        )

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    if idx < len(weapon_items):
                        name, data = weapon_items[idx]
                        if player["gold"] >= data["price"]:
                            player["gold"] -= data["price"]
                            player["weapon"] = name
                            player["atk_bonus"] = data["bonus"]


# ================= MAP SYSTEM =================

def create_map():
    return [["?" for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]

def move_player(px, py):
    move = input("Move (W/A/S/D): ").lower()
    if move == "w" and py > 0: py -= 1
    elif move == "s" and py < MAP_SIZE - 1: py += 1
    elif move == "a" and px > 0: px -= 1
    elif move == "d" and px < MAP_SIZE - 1: px += 1
    else: slow("🚧 Wall blocks your path.")
    return px, py


ROOM_TYPES = ["enemy", "merchant", "trap", "shrine", "empty"]
CLEARED_ROOM = "cleared"


def get_room(room_pos, floor):
    if room_pos not in visited_rooms:
        if random.random() < 0.15:
            visited_rooms[room_pos] = "merchant"
        elif random.random() < 0.3:
            visited_rooms[room_pos] = "trap"
        elif random.random() < 0.4:
            visited_rooms[room_pos] = "shrine"
        else:
            visited_rooms[room_pos] = "enemy"
    return visited_rooms[room_pos]

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
    global waiting_for_input
    global player_flash_timer, enemy_flash_timer
    waiting_for_input = False
    play_battle_music()
    battle_messages.clear()


    running = True
    action = None
    attack_pos = None

    while running and enemy["hp"] > 0 and player["hp"] > 0:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if waiting_for_input:
                    battle_messages.pop(0)
                    if not battle_messages:
                        waiting_for_input = False
                    continue


                #Only allow actions if no text is showing
                if event.key == pygame.K_1:
                    action = "attack"
                    attack_pos = "upper"
                    battle_messages.append("You used UPPER attack!")

                elif event.key == pygame.K_2:
                    action = "attack"
                    attack_pos = "middle"
                    battle_messages.append("You used MIDDLE attack!")

                elif event.key == pygame.K_3:
                    action = "attack"
                    attack_pos = "lower"
                    battle_messages.append("You used LOWER attack!")

                elif event.key == pygame.K_4 and player["potions"] > 0:
                    use_potion(player)
                    action = "potion"
                    battle_messages.append("You used a potion!")

                elif event.key == pygame.K_5 and player["strength_potions"] > 0:
                    use_strength_potion(player)
                    action = "potion"
                    battle_messages.append("💪 Strength boosted!")

                elif event.key == pygame.K_6 and player["defense_potions"] > 0:
                    use_defense_potion(player)
                    action = "potion"
                    battle_messages.append("🛡️ Defense boosted!")



                if not battle_messages:
                    waiting_for_input = False


        # ===== RESOLVE TURN =====
        if action is not None:
            battle_messages.clear()
            dmg = None

            if action == "attack":
                dmg = random.randint(*classes[player["class"]]["attack"])
                dmg += weapons[player["weapon"]]["bonus"] + player["level"] * 2

                if player["strength_turns"] > 0:
                    dmg = int(dmg * 1.5)

                if player["class"] == "mage" and attack_pos == "upper":
                    dmg = int(dmg * 1.3)

                if player["class"] == "ranger" and random.random() < 0.25:
                    dmg = int(dmg * 1.6)
                    battle_messages.append("🎯 CRITICAL HIT!")

                if player["class"] == "monk" and player["last_attack"] == attack_pos:
                    dmg = int(dmg * 1.4)
                    battle_messages.append("🥋 COMBO STRIKE!")

                enemy["hp"] -= dmg
                global enemy_flash_timer
                enemy_flash_timer = FLASH_DURATION


                msg = f"You dealt {dmg} damage!"
                battle_messages.append(msg)

                player["last_attack"] = attack_pos

                # ===== PALADIN PASSIVE HEAL =====
                if player["class"] == "Paladin" and player["hp"] > 0:
                    heal = max(1, player["max_hp"] // 12)
                    player["hp"] = min(player["max_hp"], player["hp"] + heal)

                    battle_messages.append(f"Paladin heals {heal} HP!")


            # ----- ENEMY TURN -----
            if enemy["hp"] > 0:
                enemy_dmg = random.randint(10, 18) + player["floor"] * 2

                if action == "potion":
                    enemy_dmg = int(enemy_dmg * 0.6)

                if player["defense_turns"] > 0:
                    enemy_dmg = int(enemy_dmg * 0.5)
                    battle_messages.append("🛡️ Damage reduced!")

                if player["class"] == "warrior":
                    enemy_dmg = int(enemy_dmg * 0.8)

                if player["class"] == "rogue" and random.random() < 0.25:
                    enemy_dmg = 0
                    battle_messages.append("💨 You dodged the attack!")

                player["hp"] -= enemy_dmg
                if enemy_dmg > 0:
                    msg = f"Enemy hit you for {enemy_dmg} damage!"
                    battle_messages.append(msg)

                if player["class"] == "paladin":
                    player["hp"] = min(player["max_hp"], player["hp"] + 4)

            player["strength_turns"] = max(0, player["strength_turns"] - 1)
            player["defense_turns"] = max(0, player["defense_turns"] - 1)

            action = None
            attack_pos = None

        # ===== DRAW =====
        screen.blit(battle_bg, (0, 0))
        # Player sprite
        if player_flash_timer > 0:
            screen.blit(flash_sprite(player_img), (120, 200))
            player_flash_timer -= 1
        else:
            screen.blit(player_img, (120, 200))

        # Enemy sprite
        if enemy_flash_timer > 0:
            screen.blit(tint_sprite(enemy_img, (180, 0, 0)), (600, 80))
            enemy_flash_timer -= 1
        else:
            screen.blit(enemy_img, (600, 80))




        # Player HP
        draw_hp_bar(screen, 180, 180, 120, 12,
                    player["hp"], player["max_hp"], (80, 200, 80))
        screen.blit(font.render(player["name"], True, (255,255,255)), (180, 150))
        #Enemy HP
        draw_hp_bar(screen, 620, 75, 120, 12,
                    enemy["hp"], enemy["max_hp"], (220, 80, 80))
        screen.blit(font.render(enemy["name"], True, (255,120,120)), (570, 40))



         # UI panel
        DIALOGUE_HEIGHT = 140
        dialogue_rect = pygame.Rect(
            0,
            SCREEN_H - DIALOGUE_HEIGHT,
            SCREEN_W,
            DIALOGUE_HEIGHT
)
        pygame.draw.rect(screen, (32, 32, 32), dialogue_rect)
        pygame.draw.rect(screen, (200, 200, 200), dialogue_rect, 4)

        show_battle_messages()
        # ==== COMMAND HELP ====
        command_text = "     1-Upper   2-Middle   3-Lower   4-Heal   5-Str   6-Def"
        cmd_surface = font.render(command_text, True, (255, 220, 120))
        screen.blit(cmd_surface, (24, SCREEN_H - 32))

        pygame.display.flip()

        if player["hp"] <= 0 and divine_intervention(player):
            continue

# ===== REWARDS =====
    xp_gain = 25 + player["floor"] * 10
    gold_gain = random.randint(15, 30) + player["floor"] * 5

    gain_xp(player, xp_gain)
    player["gold"] += gold_gain

    battle_messages.clear()
    battle_messages.append(f"⭐ Gained {xp_gain} XP!")
    battle_messages.append(f"💰 Found {gold_gain} gold!")
    visited_rooms[current_room] = CLEARED_ROOM

    waiting_for_input = True

    pygame.mixer.music.fadeout(500)
    play_explore_music()




# ================= ROOMS =================

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
slow("🌌 Version 3.0 — Revamp")


SCREEN_W, SCREEN_H = 960, 540
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Dungeon Battle")

clock = pygame.time.Clock()

# ================= OVERWORLD SPRITES =================

player_sprites = {
    "up": {
        "idle": load_img("assets/overworld/player/Player Idle Forward.png"),
        "walk": [
            load_img("assets/overworld/player/Player Walk Forward 1.png"),
            load_img("assets/overworld/player/Player Walk Forward 2.png")
        ]
    },
    "down": {
        "idle": load_img("assets/overworld/player/Player Idle Backward.png"),
        "walk": [
            load_img("assets/overworld/player/Player Walk Backward 1.png"),
            load_img("assets/overworld/player/Player Walk Backward 2.png")
        ]
    },
    "right": {
        "idle": load_img("assets/overworld/player/Player Idle Right.png"),
        "walk": [
            load_img("assets/overworld/player/Player Walk Right 1.png"),
            load_img("assets/overworld/player/Player Walk Right 2.png")
        ]
    }
}

# Auto-generate left
player_sprites["left"] = {
    "idle": pygame.transform.flip(player_sprites["right"]["idle"], True, False),
    "walk": [
        pygame.transform.flip(player_sprites["right"]["walk"][0], True, False),
        pygame.transform.flip(player_sprites["right"]["walk"][1], True, False)
    ]
}

player_dir = "down"
player_frame = 0
player_anim_timer = 0
player_moving = False

room_bg = pygame.image.load("assets/overworld/room.png").convert()
battle_bg = pygame.image.load("assets/battle/background.png").convert()
player_img = pygame.image.load("assets/battle/player.png").convert_alpha()
enemy_img = pygame.image.load("assets/battle/enemy.png").convert_alpha()
world_player = pygame.image.load("assets/battle/player.png").convert_alpha()

merchant_bg = pygame.image.load("assets/overworld/merchant.png").convert()

def load_frames(path):
    return [
        pygame.image.load(os.path.join(path, f)).convert_alpha()
        for f in sorted(os.listdir(path))
    ]

battle_bg = pygame.transform.scale(battle_bg, (SCREEN_W, 400))
player_img = pygame.transform.scale(player_img, (256, 256))
enemy_img = pygame.transform.scale(enemy_img, (164, 172))
room_bg = pygame.transform.scale(room_bg, (ROOM_W, ROOM_H))
merchant_bg = pygame.transform.scale(merchant_bg, (SCREEN_W, SCREEN_H))


BASE_DIR = os.getcwd()

FONT_PATH = os.path.join(BASE_DIR, "assets", "fonts", "dungeon.ttf")
font = pygame.font.Font(FONT_PATH, 32)
big_font = pygame.font.Font(FONT_PATH, 48)
small_font = pygame.font.Font(FONT_PATH, 18)


player = load_game(SAVE_FILE) if input("Load game? (y/n): ").lower() == "y" else create_player()
play_explore_music()

while player["hp"] > 0:
    room_type = overworld(player)

    # ===== APPLY SPAWN OFFSET =====
    if entry_dir == "up":
        player_world_x = ROOM_W // 2
        player_world_y = ROOM_H - 160

    elif entry_dir == "down":
        player_world_x = ROOM_W // 2
        player_world_y = 120

    elif entry_dir == "left":
        player_world_x = ROOM_W - 160
        player_world_y = ROOM_H // 2

    elif entry_dir == "right":
        player_world_x = 120
        player_world_y = ROOM_H // 2

    entry_dir = None


    if room_type == "enemy":
        enemy_hp = 80 + player["floor"] * 25
        fight(player, {
            "name": "Dungeon Fiend",
            "hp": enemy_hp,
            "max_hp": enemy_hp,
        })

    elif room_type == "cleared":
        pass  # Empty room, nothing happens


    elif room_type == "merchant":
        weapon_shop_gui(player)

    elif room_type == "trap":
        trap(player)

    elif room_type == "shrine":
        shrine(player)

    player["rooms"] += 1

    if player["rooms"] >= 12:
        if player["floor"] < MAX_FLOORS:
            next_floor(player)
        else:
            slow("👑 THE DUNGEON LORD AWAKENS")
            boss_hp = 350 + player["level"] * 40
            fight(player, {
                "name": "Dungeon Lord",
                "hp": boss_hp,
                "max_hp": boss_hp
            })
            break

    slow(
        f"❤️ {player['hp']} | 🧪 {player['potions']} | "
        f"💪 {player['strength_potions']} | "
        f"🛡️ {player['defense_potions']} | "
        f"⭐ {player['level']} | 💰 {player['gold']}"
    )

divider()
slow("✨ Thanks for playing Dungeon Adventure!")
stop_music()
