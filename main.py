import random
import pygame
import os
import sys

# Import custom modules
from src.constants import *
from src.entities import classes, weapons
from src.data_manager import save_game, load_game
from src.utils import sound, load_img
from src.ui import (draw_hud, show_msg, draw_minimap, draw_hp_bar, 
                    draw_text_slow_static, flash_sprite, tint_sprite,
                    start_screen, intro_gui, merchant_gui)
from src.map_manager import generate_floor, get_room
from src.game_logic import use_potion, use_strength_potion, use_defense_potion, divine_intervention, gain_xp
from src.combat import fight

# ================= GLOBAL STATE =================
visited_rooms = {}
current_room = (0, 0)
player_world_x = ROOM_W // 2
player_world_y = ROOM_H // 2
entry_dir = None
door_cooldown = 0

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

# ================= GAME SYSTEMS =================

def trap(player, screen, font, small_font, clock):
    show_msg(screen, "🕳️ A hidden trap activates!", font, small_font, clock)
    if random.random() < 0.5:
        show_msg(screen, "💨 You managed to dodge it!", font, small_font, clock)
    else:
        dmg = random.randint(15, 30)
        player["hp"] -= dmg
        sound("hit")
        show_msg(screen, f"💥 Trap hits you for {dmg} damage!", font, small_font, clock)
    visited_rooms[current_room] = "cleared"

def shrine(player, screen, font, small_font, clock):
    heal = random.randint(30, 45)
    player["hp"] = min(player["max_hp"], player["hp"] + heal)
    sound("heal")
    show_msg(screen, f"✨ The ancient shrine heals you for {heal} HP!", font, small_font, clock)
    visited_rooms[current_room] = "cleared"

def next_floor(player, screen, font, small_font, clock):
    global player_world_x, player_world_y, current_room
    show_msg(screen, f"⬇️ Descending to floor {player['floor'] + 1}...", font, small_font, clock)
    player["floor"] += 1
    player["rooms"] = 0
    current_room = (0, 0)
    generate_floor(player["floor"], visited_rooms)
    player_world_x = ROOM_W // 2
    player_world_y = ROOM_H // 2

def overworld(player, screen, font, small_font, clock, player_sprites, room_bg):
    global player_world_x, player_world_y, current_room, door_cooldown, entry_dir
    door_cooldown = DOOR_COOLDOWN_TIME
    player_speed = 4
    player_dir = "down"
    player_frame = 0
    player_anim_timer = 0

    running = True
    while running:
        clock.tick(60)
        screen.blit(room_bg, (0, 0))
        if door_cooldown > 0: door_cooldown -= 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    use_potion(player, show_msg, screen, font, small_font, clock)
                if event.key == pygame.K_s or event.key == pygame.K_HOME:
                    player["_current_room"] = current_room
                    player["_visited_rooms"] = {str(k): v for k, v in visited_rooms.items()}
                    player["_player_world_x"] = player_world_x
                    player["_player_world_y"] = player_world_y
                    save_game(player, SAVE_FILE)
                    show_msg(screen, "💾 Game Saved Successfully!", font, small_font, clock)

        keys = pygame.key.get_pressed()
        player_moving = False
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            player_world_y = max(40, player_world_y - player_speed)
            player_dir = "up"
            player_moving = True
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            player_world_y = min(ROOM_H - 80, player_world_y + player_speed)
            player_dir = "down"
            player_moving = True
        elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
            player_world_x = max(40, player_world_x - player_speed)
            player_dir = "left"
            player_moving = True
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            player_world_x = min(ROOM_W - 80, player_world_x + player_speed)
            player_dir = "right"
            player_moving = True

        if player_moving:
            player_anim_timer += 1
            if player_anim_timer >= 12:
                player_frame = (player_frame + 1) % 2
                player_anim_timer = 0
        else:
            player_frame = 0

        sprite = player_sprites[player_dir]["walk"][player_frame] if player_moving else player_sprites[player_dir]["idle"]
        player_rect = pygame.Rect(player_world_x + 16, player_world_y + 16, 32, 32)

        for direction, door in door_zones.items():
            if door_cooldown == 0 and player_rect.colliderect(door):
                nx, ny = current_room
                if direction == "up": ny -= 1
                elif direction == "down": ny += 1
                elif direction == "left": nx -= 1
                elif direction == "right": nx += 1
                
                if 0 <= nx < MAP_SIZE and 0 <= ny < MAP_SIZE:
                    door_cooldown = DOOR_COOLDOWN_TIME
                    entry_dir = direction
                    current_room = (nx, ny)
                    running = False
                    break

        screen.blit(sprite, (player_world_x, player_world_y))
        draw_hud(screen, player, small_font)
        draw_minimap(screen, visited_rooms, current_room, small_font)
        pygame.display.flip()

    return get_room(current_room, visited_rooms)

# ================= MAIN LOOP =================

def main():
    pygame.init()
    pygame.mixer.init()
    
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Dungeon Adventure")
    clock = pygame.time.Clock()

    # Load Fonts
    BASE_DIR = os.getcwd()
    FONT_PATH = os.path.join(BASE_DIR, "assets", "fonts", "dungeon.ttf")
    font = pygame.font.Font(FONT_PATH, 32)
    big_font = pygame.font.Font(FONT_PATH, 48)
    small_font = pygame.font.Font(FONT_PATH, 18)

    # Load Assets
    room_bg = pygame.transform.scale(pygame.image.load("assets/overworld/room.png").convert(), (ROOM_W, ROOM_H))
    battle_bg = pygame.transform.scale(pygame.image.load("assets/battle/background.png").convert(), (SCREEN_W, 400))
    merchant_bg = pygame.transform.scale(pygame.image.load("assets/overworld/merchant.png").convert(), (SCREEN_W, SCREEN_H))
    player_img = pygame.transform.scale(pygame.image.load("assets/battle/player.png").convert_alpha(), (256, 256))
    enemy_img = pygame.transform.scale(pygame.image.load("assets/battle/enemy.png").convert_alpha(), (164, 172))

    player_sprites = {
        "up": {
            "idle": load_img("assets/overworld/player/Player Idle Forward.png"),
            "walk": [load_img("assets/overworld/player/Player Walk Forward 1.png"), load_img("assets/overworld/player/Player Walk Forward 2.png")]
        },
        "down": {
            "idle": load_img("assets/overworld/player/Player Idle Backward.png"),
            "walk": [load_img("assets/overworld/player/Player Walk Backward 1.png"), load_img("assets/overworld/player/Player Walk Backward 2.png")]
        },
        "right": {
            "idle": load_img("assets/overworld/player/Player Idle Right.png"),
            "walk": [load_img("assets/overworld/player/Player Walk Right 1.png"), load_img("assets/overworld/player/Player Walk Right 2.png")]
        }
    }
    player_sprites["left"] = {
        "idle": pygame.transform.flip(player_sprites["right"]["idle"], True, False),
        "walk": [pygame.transform.flip(player_sprites["right"]["walk"][0], True, False), pygame.transform.flip(player_sprites["right"]["walk"][1], True, False)]
    }

    # Start Game
    res = start_screen(screen, big_font, font, small_font, SAVE_FILE, load_game, intro_gui, show_msg, clock)
    
    if hasattr(res, 'data'): # Loaded
        player = res.data
        global current_room, visited_rooms, player_world_x, player_world_y
        current_room = res.current_room
        visited_rooms.update(res.visited_rooms)
        player_world_x = res.px
        player_world_y = res.py
    else: # New Game
        player = res
        generate_floor(player["floor"], visited_rooms)

    play_explore_music()

    while player["hp"] > 0:
        room_type = overworld(player, screen, font, small_font, clock, player_sprites, room_bg)

        # Spawning logic
        global entry_dir
        if entry_dir == "up": player_world_x, player_world_y = ROOM_W // 2, ROOM_H - 160
        elif entry_dir == "down": player_world_x, player_world_y = ROOM_W // 2, 120
        elif entry_dir == "left": player_world_x, player_world_y = ROOM_W - 160, ROOM_H // 2
        elif entry_dir == "right": player_world_x, player_world_y = 120, ROOM_H // 2
        entry_dir = None

        if room_type == "boss":
            show_msg(screen, "👑 THE DUNGEON LORD AWAKENS!", font, small_font, clock)
            fight(screen, player, {"name": "Dungeon Lord", "hp": 350+player["level"]*40, "max_hp": 350+player["level"]*40},
                  battle_bg, player_img, enemy_img, font, small_font, clock, show_msg, draw_hp_bar, None, flash_sprite, tint_sprite,
                  divine_intervention, gain_xp, use_potion, use_strength_potion, use_defense_potion, 
                  play_battle_music, play_explore_music)
            if player["hp"] > 0: show_msg(screen, "🏆 YOU HAVE CONQUERED THE DUNGEON!", font, small_font, clock)
            break
        elif room_type == "exit":
            next_floor(player, screen, font, small_font, clock)
            continue
        elif room_type == "enemy":
            fight(screen, player, {"name": "Dungeon Fiend", "hp": 80+player["floor"]*25, "max_hp": 80+player["floor"]*25},
                  battle_bg, player_img, enemy_img, font, small_font, clock, show_msg, draw_hp_bar, None, flash_sprite, tint_sprite,
                  divine_intervention, gain_xp, use_potion, use_strength_potion, use_defense_potion, 
                  play_battle_music, play_explore_music)
            if player["hp"] > 0: visited_rooms[current_room] = "cleared"
        elif room_type == "merchant": merchant_gui(screen, player, merchant_bg, font, small_font, show_msg, clock)
        elif room_type == "trap": trap(player, screen, font, small_font, clock)
        elif room_type == "shrine": shrine(player, screen, font, small_font, clock)

    if player["hp"] <= 0: show_msg(screen, "☠️ You have perished in the dungeon...", font, small_font, clock)
    show_msg(screen, "✨ Thanks for playing Dungeon Adventure!", font, small_font, clock)
    stop_music()
    pygame.quit()

if __name__ == "__main__":
    main()
