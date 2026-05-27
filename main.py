import random
import pygame
import os
import sys

from src.constants import *
from src.constants import (CLASS_UPGRADES, FLOOR_CURSES, FLOOR_BLESSINGS, EQUIPMENT,
                           FLOOR_DECORATION_COLORS, ROOM_LABELS)
from src.entities import classes, weapons, FLOOR_ENEMY_NAMES, ENEMY_HINTS, ENEMY_STATS
from src.data_manager import save_game, load_game
from src.utils import sound, load_img
from src.ui import (show_msg, draw_minimap, draw_hp_bar, draw_modifier_pills,
                    draw_text_slow_static, flash_sprite, tint_sprite,
                    start_screen, intro_gui, merchant_gui, pause_menu,
                    game_over_screen, victory_screen, upgrade_screen,
                    show_stats_screen, modifier_select_screen, floor_transition_screen)
from src.hud import draw_hud, HUD_HEIGHT
from src.map_manager import generate_floor, get_room
from src.game_logic import use_potion, use_strength_potion, use_defense_potion, divine_intervention, gain_xp
from src.combat import fight
from src.rooms import (assign_quests, check_quests, chest_room, puzzle_room,
                       event_room, do_miniboss)
from src.player_defaults import ensure_player_keys, FightCtx
from src.overworld_features import (
    EmberSystem, draw_torch_glow, TORCH_POSITIONS,
    generate_hazards, update_hazards, draw_hazards, check_hazard_damage,
    generate_objects, draw_toasts,
    load_companion_sprites, update_companion, draw_companion,
    draw_room_label,
)

# ================= GLOBAL STATE =================
visited_rooms = {}
entered_rooms = set()    # rooms the player has physically walked into
current_room = (0, 0)
player_world_x = ROOM_W // 2
player_world_y = ROOM_H // 2
entry_dir = None
door_cooldown = 0
trap_rigged_doors = {}   # maps room coord tuple → rigged exit direction
room_hazards  = {}       # maps room coord → list of hazard dicts
room_objects  = {}       # maps room coord → list of interactive object dicts

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

def play_shrine_music():
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
    pygame.mixer.music.load(SHRINE_MUSIC)
    pygame.mixer.music.play(-1)

def play_boss_music():
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
    pygame.mixer.music.load(BOSS_MUSIC)
    pygame.mixer.music.play(-1)

def stop_music():
    pygame.mixer.music.stop()

_FLOOR_BG_NAMES = {1: "room", 2: "catacombs", 3: "crypts", 4: "void"}

def load_floor_bg(floor_num, fallback_surf):
    """Try to load floor-specific background, fall back to the default surface."""
    theme = _FLOOR_BG_NAMES.get(floor_num, "room")
    path = f"assets/overworld/{theme}_room.png"
    try:
        return pygame.transform.scale(
            pygame.image.load(path).convert(), (ROOM_W, ROOM_H))
    except Exception:
        return fallback_surf

def _do_save(player):
    global current_room, visited_rooms, player_world_x, player_world_y
    player["_current_room"] = current_room
    player["_visited_rooms"] = {str(k): v for k, v in visited_rooms.items()}
    player["_player_world_x"] = player_world_x
    player["_player_world_y"] = player_world_y
    save_game(player, SAVE_FILE)
    for _k in ("_current_room", "_visited_rooms", "_player_world_x", "_player_world_y"):
        player.pop(_k, None)

# ================= GAME SYSTEMS =================

def next_floor(player, screen, font, small_font, clock, upgrade_fn=None):
    global player_world_x, player_world_y, current_room
    from src.ui import fade_screen
    fade_screen(screen, clock, 'out', speed=8)
    player["floors_cleared"] = player.get("floors_cleared", 0) + 1
    player["floor"] += 1
    player["rooms"] = 0
    player["floor_gold_earned"] = 0
    current_room = (0, 0)
    generate_floor(player["floor"], visited_rooms)
    entered_rooms.clear()
    entered_rooms.add((0, 0))
    trap_rigged_doors.clear()
    room_hazards.clear()
    room_objects.clear()
    player_world_x = ROOM_W // 2
    player_world_y = ROOM_H // 2

    # Strip previous floor modifier effects
    player.pop("active_curse", None)
    player.pop("active_blessing", None)
    for k in [k for k in list(player) if k.startswith("_curse_") or k.startswith("_blessing_")]:
        player.pop(k)

    # Floor 2+: modifier selection
    if player["floor"] >= 2:
        curse_choices = random.sample(FLOOR_CURSES, min(2, len(FLOOR_CURSES)))
        blessing_choices = random.sample(FLOOR_BLESSINGS, min(2, len(FLOOR_BLESSINGS)))
        modifier_select_screen(screen, player, font, small_font, clock, curse_choices, blessing_choices)

    # Assign quests for this floor
    assign_quests(player)

    # Floor transition recap screen
    theme_name = FLOOR_THEMES.get(player["floor"], {}).get("name", f"Floor {player['floor']}")
    floor_transition_screen(screen, player, font, small_font, clock, theme_name)

    fade_screen(screen, clock, 'in', speed=8)
    player["_current_room"] = current_room
    player["_visited_rooms"] = {str(k): v for k, v in visited_rooms.items()}
    player["_player_world_x"] = player_world_x
    player["_player_world_y"] = player_world_y
    save_game(player, SAVE_FILE)
    for key in ("_current_room", "_visited_rooms", "_player_world_x", "_player_world_y"):
        player.pop(key, None)

def _init_room_data(room_pos, v_rooms, floor_num=1):
    """Lazily populate hazards and objects for a room on first visit."""
    room_type = v_rooms.get(room_pos, "enemy")
    if room_pos not in room_hazards:
        room_hazards[room_pos] = generate_hazards(room_type, floor_num)
    if room_pos not in room_objects:
        room_objects[room_pos] = generate_objects(room_type)


def overworld(player, screen, font, small_font, clock, player_sprites, room_bg, trap_bg, shrine_bg,
              npc_frames, companion_sprites, ember_system, torch_surf=None):
    global player_world_x, player_world_y, current_room, door_cooldown, entry_dir
    door_cooldown = DOOR_COOLDOWN_TIME
    entered_rooms.add(current_room)
    player_speed = 5
    player_dir = "down"
    player_frame = 0
    player_anim_timer = 0

    NPC_X = ROOM_W // 2 + 60
    NPC_Y = ROOM_H // 2 - 30

    # Build NPC list for this room visit
    room_data_init = visited_rooms.get(current_room)
    active_npcs = []
    if room_data_init in ("shrine", "cleared_shrine"):
        active_npcs = [{
            "x": NPC_X, "y": NPC_Y,
            "frame": 4, "name": "Shrine Keeper",
            "dialogue": SHRINE_NPC_DIALOGUE,
            "talked_to": room_data_init == "cleared_shrine",
        }]
        play_shrine_music()

    room_label_timer = 0
    room_label_text = ""
    active_toasts = []

    # Lazy-init hazards and objects for the starting room on overworld entry
    _init_room_data(current_room, visited_rooms, player["floor"])

    running = True
    while running:
        clock.tick(60)

        room_data = visited_rooms.get(current_room)

        # Lazily assign rigged door for unvisited trap rooms
        if room_data == "trap" and current_room not in trap_rigged_doors:
            nx, ny = current_room
            valid_dirs = [d for d, (dx, dy) in [("up",(0,-1)),("down",(0,1)),("left",(-1,0)),("right",(1,0))]
                          if 0 <= nx+dx < MAP_SIZE and 0 <= ny+dy < MAP_SIZE]
            if valid_dirs:
                trap_rigged_doors[current_room] = random.choice(valid_dirs)

        # Background
        if room_data in ("cleared_trap", "trap"):
            curr_bg = trap_bg
        elif room_data in ("cleared_shrine", "shrine"):
            curr_bg = shrine_bg
        else:
            curr_bg = room_bg

        screen.blit(curr_bg, (0, 0))
        if door_cooldown > 0: door_cooldown -= 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    use_potion(player, show_msg, screen, font, small_font, clock)
                if event.key == pygame.K_5:
                    use_strength_potion(player, show_msg, screen, font, small_font, clock)
                if event.key == pygame.K_6:
                    use_defense_potion(player, show_msg, screen, font, small_font, clock)
                if event.key == pygame.K_HOME:
                    player["_current_room"] = current_room
                    player["_visited_rooms"] = {str(k): v for k, v in visited_rooms.items()}
                    player["_player_world_x"] = player_world_x
                    player["_player_world_y"] = player_world_y
                    save_game(player, SAVE_FILE)
                    for _k in ("_current_room", "_visited_rooms", "_player_world_x", "_player_world_y"):
                        player.pop(_k, None)
                    show_msg(screen, "Game Saved Successfully!", font, small_font, clock)
                if event.key == pygame.K_TAB:
                    show_stats_screen(screen, player, font, small_font, clock)
                if event.key == pygame.K_ESCAPE:
                    result = pause_menu(screen, player, font, small_font, clock,
                                        save_fn=lambda: _do_save(player))
                    if result == "quit":
                        pygame.quit(); sys.exit()
                if event.key == pygame.K_RETURN:
                    player_cx = player_world_x + 32
                    player_cy = player_world_y + 32
                    for npc in active_npcs:
                        npc_cx = npc["x"] + 32
                        npc_cy = npc["y"] + 48
                        if ((player_cx - npc_cx)**2 + (player_cy - npc_cy)**2)**0.5 < 80:
                            for line in npc["dialogue"]:
                                show_msg(screen, line, font, small_font, clock)
                            if npc["name"] == "Shrine Keeper" and not npc["talked_to"]:
                                heal = random.randint(30, 45)
                                player["hp"] = min(player["max_hp"], player["hp"] + heal)
                                visited_rooms[current_room] = "cleared_shrine"
                                show_msg(screen, f"The shrine blesses you for +{heal} HP!", font, small_font, clock)
                            npc["talked_to"] = True
                            break

        keys = pygame.key.get_pressed()
        player_moving = False
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            player_world_y = max(HUD_HEIGHT + 5, player_world_y - player_speed)
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
                    target_type = visited_rooms.get((nx, ny), "enemy")
                    if target_type == "locked" and player.get("keys", 0) == 0:
                        door_cooldown = DOOR_COOLDOWN_TIME
                        active_toasts.append({
                            "text": "Locked — find a key first.",
                            "color": (200, 160, 60),
                            "x": SCREEN_W // 2 - 120,
                            "y": SCREEN_H // 2 - 30,
                            "w": 240,
                            "born_ms": pygame.time.get_ticks(),
                            "duration": 1800,
                        })
                        break
                    door_cooldown = DOOR_COOLDOWN_TIME
                    entry_dir = direction

                    # Trap: rigged door check
                    if room_data == "trap":
                        if trap_rigged_doors.get(current_room) == direction:
                            dmg = random.randint(15, 30)
                            player["hp"] -= dmg
                            visited_rooms[current_room] = "cleared_trap"
                            show_msg(screen, f"💥 The door was rigged! You take {dmg} damage!", font, small_font, clock)
                        else:
                            visited_rooms[current_room] = "cleared_trap"

                    # Shrine: restore explore music on exit
                    if room_data in ("shrine", "cleared_shrine"):
                        play_explore_music()

                    current_room = (nx, ny)
                    entered_rooms.add(current_room)
                    # Pre-init next room's hazards/objects + set room label
                    _init_room_data(current_room, visited_rooms, player["floor"])
                    next_room_type = visited_rooms.get(current_room, "enemy")
                    room_label_timer = pygame.time.get_ticks()
                    room_label_text = ROOM_LABELS.get(next_room_type, "")
                    running = False
                    break

        # NPC rendering
        player_cx = player_world_x + 32
        player_cy = player_world_y + 32

        # Decorations (after background, before sprites)
        theme_colors = FLOOR_DECORATION_COLORS.get(player["floor"], FLOOR_DECORATION_COLORS[1])
        draw_torch_glow(screen, player["floor"], torch_surf)
        for tx, ty in TORCH_POSITIONS:
            ember_system.spawn(tx, ty - 10, theme_colors["ember"])
        ember_system.update()
        ember_system.draw(screen)

        # Hazards
        h_list = room_hazards.get(current_room, [])
        update_hazards(h_list)
        draw_hazards(screen, h_list)
        player["_world_x"] = player_world_x
        player["_world_y"] = player_world_y
        check_hazard_damage(player, h_list, pygame.time.get_ticks())

        draw_toasts(screen, active_toasts, small_font, pygame.time.get_ticks())

        for npc in active_npcs:
            screen.blit(npc_frames[npc["frame"]], (npc["x"], npc["y"]))

        # "ENTER to talk" proximity hint
        for npc in active_npcs:
            npc_cx = npc["x"] + 32
            npc_cy = npc["y"] + 48
            if ((player_cx - npc_cx)**2 + (player_cy - npc_cy)**2)**0.5 < 80:
                hint = small_font.render("ENTER to talk", True, (255, 220, 100))
                screen.blit(hint, (npc["x"], npc["y"] - 20))
                break

        # Companion
        companion = player.get("companion")
        if companion:
            update_companion(companion, player_world_x, player_world_y)
            draw_companion(screen, companion, companion_sprites)

        screen.blit(sprite, (player_world_x, player_world_y))
        draw_hud(screen, player, small_font)
        draw_minimap(screen, visited_rooms, current_room, small_font, player["floor"], player, entered_rooms)
        draw_modifier_pills(screen, player, small_font)

        # Room label overlay
        if room_label_timer > 0:
            if not draw_room_label(screen, room_label_text, room_label_timer, font):
                room_label_timer = 0

        pygame.display.flip()

    from src.ui import draw_corridor_transition
    draw_corridor_transition(screen, clock, entry_dir, player["floor"])
    return get_room(current_room, visited_rooms)

# ================= SAFE STARTING ROOM =================

def safe_room(player, screen, font, small_font, clock, start_bg, npc_frames, player_sprites):
    import copy
    global player_world_x, player_world_y, door_cooldown
    player_world_x, player_world_y = ROOM_W // 2, ROOM_H - 150
    door_cooldown = DOOR_COOLDOWN_TIME

    npcs = copy.deepcopy(START_ROOM_NPCS)
    for npc in npcs:
        npc["talked_to"] = False

    player_speed = 5
    player_dir = "up"
    player_frame = 0
    player_anim_timer = 0

    running = True
    while running:
        clock.tick(60)
        screen.blit(start_bg, (0, 0))
        if door_cooldown > 0:
            door_cooldown -= 1

        player_cx = player_world_x + 32
        player_cy = player_world_y + 32

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    for npc in npcs:
                        npc_cx = npc["x"] + 32
                        npc_cy = npc["y"] + 48
                        if ((player_cx - npc_cx)**2 + (player_cy - npc_cy)**2)**0.5 < 80:
                            for line in npc["dialogue"]:
                                show_msg(screen, line, font, small_font, clock)
                            npc["talked_to"] = True
                            break

        keys = pygame.key.get_pressed()
        player_moving = False
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            player_world_y = max(HUD_HEIGHT + 5, player_world_y - player_speed)
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

        if door_cooldown == 0 and player_rect.colliderect(door_zones["up"]):
            running = False

        for npc in npcs:
            screen.blit(npc_frames[npc["frame"]], (npc["x"], npc["y"]))

        for npc in npcs:
            npc_cx = npc["x"] + 32
            npc_cy = npc["y"] + 48
            if ((player_cx - npc_cx)**2 + (player_cy - npc_cy)**2)**0.5 < 80:
                hint = small_font.render("ENTER to talk", True, (255, 220, 100))
                screen.blit(hint, (npc["x"], npc["y"] - 20))
                break

        screen.blit(sprite, (player_world_x, player_world_y))
        draw_hud(screen, player, small_font)
        pygame.display.flip()

    from src.ui import fade_screen
    fade_screen(screen, clock, 'out', speed=10)

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
    shrine_bg = pygame.transform.scale(pygame.image.load("assets/overworld/Shrine_room.png").convert(), (ROOM_W, ROOM_H))
    trap_bg = pygame.transform.scale(pygame.image.load("assets/overworld/Trap_room.png").convert(), (ROOM_W, ROOM_H))
    
    try:
        torch_surf = pygame.transform.scale(
            pygame.image.load("assets/overworld/torch.png").convert_alpha(), (32, 64))
        torch_surf.set_colorkey((255, 255, 255))
    except Exception:
        torch_surf = None

    battle_bg = pygame.transform.scale(pygame.image.load("assets/battle/background.png").convert(), (SCREEN_W, 400))
    merchant_bg = pygame.transform.scale(pygame.image.load("assets/overworld/merchant.png").convert(), (SCREEN_W, SCREEN_H))
    player_img = pygame.transform.scale(pygame.image.load("assets/battle/player.png").convert_alpha(), (256, 256))
    enemy_img = pygame.transform.scale(pygame.image.load("assets/battle/enemy.png").convert_alpha(), (164, 172))
    dungeon_lord_img = pygame.transform.scale(pygame.image.load("assets/battle/Dungeon_Lord.png").convert_alpha(), (256, 256))

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

    male_sprite = pygame.image.load("assets/overworld/npc/npc_male.png").convert_alpha()
    female_sprite = pygame.image.load("assets/overworld/npc/npc_female.png").convert_alpha()

    # Scale sprites proportionally (57×65 → 64×73, 66×70 → 64×68)
    male_sprite = pygame.transform.scale(male_sprite, (64, int(65 * 64 / 57)))
    female_sprite = pygame.transform.scale(female_sprite, (64, int(70 * 64 / 66)))

    # npc_frames list: [Guard, Survivor, Merchant's Friend, Scholar, Dungeon Scholar, Shrine Keeper]
    npc_frames = [male_sprite, female_sprite, male_sprite, female_sprite, female_sprite, female_sprite]

    companion_sprites = load_companion_sprites()
    ember_system = EmberSystem()

    def _gain_xp_with_upgrade(player, xp, show_msg_func, scr, fn, sfn, clk):
        gain_xp(player, xp, show_msg_func, scr, fn, sfn, clk,
                on_levelup=lambda: upgrade_screen(scr, player, fn, sfn, clk))

    fctx = FightCtx(
        battle_bg=battle_bg,
        player_img=player_img,
        enemy_img=enemy_img,
        dungeon_lord_img=dungeon_lord_img,
        divine_fn=divine_intervention,
        gain_xp_fn=_gain_xp_with_upgrade,
        use_potion_fn=use_potion,
        use_str_fn=use_strength_potion,
        use_def_fn=use_defense_potion,
        play_battle_fn=play_battle_music,
        play_explore_fn=play_explore_music,
    )

    # NG+ state
    ng_plus_mult = 1.0
    ng_plus_carry = None  # pre-built player dict for NG+ restart

    while True:  # outer NG+ loop — restarts on New Game+
        global current_room, visited_rooms, player_world_x, player_world_y

        if ng_plus_carry is not None:
            player = ng_plus_carry
            ng_plus_carry = None
            visited_rooms.clear()
            entered_rooms.clear()
            entered_rooms.add((0, 0))
            current_room = (0, 0)
            player_world_x = ROOM_W // 2
            player_world_y = ROOM_H // 2
            generate_floor(player["floor"], visited_rooms)
            trap_rigged_doors.clear()
            room_hazards.clear()
            room_objects.clear()
            is_new_game = True
        else:
            # Start Game
            res = start_screen(screen, big_font, font, small_font, SAVE_FILE, load_game, intro_gui, show_msg, clock)
            is_new_game = not hasattr(res, 'data')
            if not is_new_game:  # Loaded
                player = res.data
                current_room = res.current_room
                visited_rooms.update(res.visited_rooms)
                player_world_x = res.px
                player_world_y = res.py
                room_hazards.clear()
                room_objects.clear()
            else:  # New Game
                player = res
                generate_floor(player["floor"], visited_rooms)
                room_hazards.clear()
                room_objects.clear()

        play_explore_music()
        entered_rooms.clear()
        entered_rooms.add((0, 0))
        room_bg = load_floor_bg(player["floor"], room_bg)

        if is_new_game:
            try:
                start_bg = pygame.transform.scale(
                    pygame.image.load("assets/overworld/start_room.png").convert(), (ROOM_W, ROOM_H))
            except Exception:
                start_bg = room_bg
            if ng_plus_mult > 1.0:
                show_msg(screen, f"⚡ NEW GAME+ — Enemies are {int(ng_plus_mult*100-100)}% stronger! Your upgrades remain.", font, small_font, clock)
            else:
                show_msg(screen, "\"Welcome to the dungeon entrance. Talk to the others before you descend.\"", font, small_font, clock)
            safe_room(player, screen, font, small_font, clock, start_bg, npc_frames, player_sprites)
            show_msg(screen, "You step through the door into the dungeon...", font, small_font, clock)
            assign_quests(player)

        while player["hp"] > 0:
            room_type = overworld(player, screen, font, small_font, clock, player_sprites,
                                  room_bg, trap_bg, shrine_bg, npc_frames,
                                  companion_sprites, ember_system, torch_surf)

            # Spawning logic
            global entry_dir
            if entry_dir == "up": player_world_x, player_world_y = ROOM_W // 2, ROOM_H - 160
            elif entry_dir == "down": player_world_x, player_world_y = ROOM_W // 2, 120
            elif entry_dir == "left": player_world_x, player_world_y = ROOM_W - 160, ROOM_H // 2
            elif entry_dir == "right": player_world_x, player_world_y = 120, ROOM_H // 2
            entry_dir = None

            _CLEARED = ("cleared", "cleared_chest", "cleared_shrine", "cleared_merchant",
                        "cleared_trap", "cleared_puzzle", "cleared_locked", "cleared_event")

            # Blessing: heal on room entry
            heal_on_entry = player.get("_blessing_room_heal", 0)
            if heal_on_entry > 0 and room_type not in _CLEARED:
                player["hp"] = min(player["max_hp"], player["hp"] + heal_on_entry)

            # Companion healer bonus
            companion = player.get("companion")
            if companion and companion.get("role") == "healer" and room_type not in _CLEARED:
                player["hp"] = min(player["max_hp"], player["hp"] + 10)

            # Room entry flavor text (fires once per uncleared room)
            if room_type in ROOM_FLAVOR:
                show_msg(screen, random.choice(ROOM_FLAVOR[room_type]), font, small_font, clock)

            # Trap room: warn player on first entry
            if room_type == "trap":
                show_msg(screen, "You sense danger... one of these doors is rigged. Choose wisely.", font, small_font, clock)

            # 25% chance: ambient lore fragment surfaces in player's mind
            if room_type not in _CLEARED and random.random() < 0.25:
                show_msg(screen, f"A memory surfaces in your mind... {random.choice(LORE_FRAGMENTS)}", font, small_font, clock)

            # Quest: explore tracking
            check_quests(player, "explore", screen, font, small_font, clock,
                         upgrade_fn=lambda: upgrade_screen(screen, player, font, small_font, clock))

            if room_type == "boss":
                show_msg(screen, "The darkness parts... a presence stirs at the heart of the dungeon.", font, small_font, clock)
                show_msg(screen, "\"Another fool seeking glory in MY domain?\"", font, small_font, clock)
                show_msg(screen, "\"You have wandered far, little hero. This is where your journey ends.\"", font, small_font, clock)
                show_msg(screen, "👑 THE DUNGEON LORD AWAKENS!", font, small_font, clock)
                dl_hp = int((400 + player["level"] * 50) * ng_plus_mult)
                fctx.run(screen, player, {"name": "Dungeon Lord", "hp": dl_hp, "max_hp": dl_hp},
                         font, small_font, clock, show_msg, draw_hp_bar, flash_sprite, tint_sprite,
                         img_override=dungeon_lord_img,
                         play_music_override=play_boss_music)
                if player["hp"] > 0:
                    player["floors_cleared"] = player.get("floors_cleared", 0) + 1
                    vresult = victory_screen(screen, player, big_font, font, small_font, clock)
                    if vresult == "ng+":
                        ng_plus_mult = 1.5
                        base_cls = classes[player["class"]]
                        ng_player = ensure_player_keys({
                            "name": player["name"], "class": player["class"],
                            "hp": base_cls["hp"], "max_hp": base_cls["hp"],
                            "level": 1, "xp": 0, "gold": 100,
                            "potions": 1,
                            "weapon": "Dagger", "floor": 1, "rooms": 0,
                            "revived": False,
                            "upgrades": list(player.get("upgrades", [])),
                        })
                        all_upgs = list(UPGRADE_POOL) + CLASS_UPGRADES.get(ng_player["class"], [])
                        for upg_name in ng_player["upgrades"]:
                            upg = next((u for u in all_upgs if u["name"] == upg_name), None)
                            if upg:
                                upg["apply"](ng_player)
                        ng_player["_ng_plus"] = True
                        ng_plus_carry = ng_player
                break
            elif room_type == "exit":
                next_floor(player, screen, font, small_font, clock,
                           upgrade_fn=lambda: upgrade_screen(screen, player, font, small_font, clock))
                room_bg = load_floor_bg(player["floor"], room_bg)
                continue
            elif room_type == "enemy":
                enemy_name = random.choice(FLOOR_ENEMY_NAMES.get(player["floor"], ["Dungeon Fiend"]))
                hint = ENEMY_HINTS.get(enemy_name, "An unknown creature lurks here...")
                show_msg(screen, f"{enemy_name} — {hint}", font, small_font, clock)
                stats = ENEMY_STATS.get(enemy_name, {})
                base_hp = int((80 + player["floor"] * 25) * ng_plus_mult)
                e_hp = int(base_hp * stats.get("hp_mult", 1.0))
                hp_before = player["hp"]
                potions_before = player["potions"] + player.get("strength_potions", 0) + player.get("defense_potions", 0)
                result = fctx.run(screen, player, {
                    "name": enemy_name,
                    "hp": e_hp, "max_hp": e_hp,
                    "atk_range": stats.get("atk_range", (12, 22)),
                    "atk_weights": stats.get("atk_weights", [1, 1, 1]),
                    "def_weights": stats.get("def_weights", [1, 1, 1]),
                    "status_chance": stats.get("status_chance", {}),
                }, font, small_font, clock, show_msg, draw_hp_bar, flash_sprite, tint_sprite)
                if result:
                    visited_rooms[current_room] = "cleared"
                    room_hazards.pop(current_room, None)
                    check_quests(player, "kill", screen, font, small_font, clock,
                                 upgrade_fn=lambda: upgrade_screen(screen, player, font, small_font, clock))
                    if player["hp"] == hp_before:
                        check_quests(player, "no_damage", screen, font, small_font, clock,
                                     upgrade_fn=lambda: upgrade_screen(screen, player, font, small_font, clock))
                    potions_after = player["potions"] + player.get("strength_potions", 0) + player.get("defense_potions", 0)
                    if potions_after >= potions_before:
                        check_quests(player, "no_potion", screen, font, small_font, clock,
                                     upgrade_fn=lambda: upgrade_screen(screen, player, font, small_font, clock))
                    check_quests(player, "gold", screen, font, small_font, clock)
            elif room_type == "merchant":
                show_msg(screen, random.choice(MERCHANT_GREETINGS), font, small_font, clock)
                merchant_gui(screen, player, merchant_bg, font, small_font, show_msg, clock)
                visited_rooms[current_room] = "cleared_merchant"
                check_quests(player, "noncombat", screen, font, small_font, clock,
                             upgrade_fn=lambda: upgrade_screen(screen, player, font, small_font, clock))
            elif room_type == "chest":
                chest_room(player, visited_rooms, current_room, screen, font, small_font, clock,
                           upgrade_fn=lambda: upgrade_screen(screen, player, font, small_font, clock))
            elif room_type == "miniboss":
                _flash = pygame.Surface((SCREEN_W, SCREEN_H))
                _flash.fill((100, 0, 180))
                _snap = screen.copy()
                for _a in range(0, 130, 26):
                    screen.blit(_snap, (0, 0))
                    _flash.set_alpha(_a)
                    screen.blit(_flash, (0, 0))
                    pygame.display.flip()
                    clock.tick(60)
                mb_won = do_miniboss(player, visited_rooms, current_room, screen, font, small_font, clock,
                                     ng_plus_mult, fctx)
                if mb_won:
                    check_quests(player, "kill", screen, font, small_font, clock,
                                 upgrade_fn=lambda: upgrade_screen(screen, player, font, small_font, clock))
            elif room_type == "puzzle":
                puzzle_room(player, visited_rooms, current_room, screen, font, small_font, clock,
                            gain_xp_fn=_gain_xp_with_upgrade)
            elif room_type == "elite":
                enemy_name = random.choice(FLOOR_ENEMY_NAMES.get(player["floor"], ["Dungeon Fiend"]))
                hint = ENEMY_HINTS.get(enemy_name, "An unknown creature lurks here...")
                _flash = pygame.Surface((SCREEN_W, SCREEN_H))
                _flash.fill((180, 0, 0))
                _snap = screen.copy()
                for _a in range(0, 130, 26):
                    screen.blit(_snap, (0, 0))
                    _flash.set_alpha(_a)
                    screen.blit(_flash, (0, 0))
                    pygame.display.flip()
                    clock.tick(60)
                show_msg(screen, "An elite creature stirs in the shadows...", font, small_font, clock)
                show_msg(screen, f"ELITE: {enemy_name} — {hint}", font, small_font, clock)
                stats = ENEMY_STATS.get(enemy_name, {})
                base_hp = int((80 + player["floor"] * 25) * ng_plus_mult * 1.5)
                e_hp = int(base_hp * stats.get("hp_mult", 1.0))
                result = fctx.run(screen, player, {
                    "name": f"Elite {enemy_name}",
                    "hp": e_hp, "max_hp": e_hp,
                    "atk_range": stats.get("atk_range", (12, 22)),
                    "atk_weights": stats.get("atk_weights", [1, 1, 1]),
                    "def_weights": stats.get("def_weights", [1, 1, 1]),
                    "status_chance": stats.get("status_chance", {}),
                    "elite": True, "enrage_threshold": 0.6,
                }, font, small_font, clock, show_msg, draw_hp_bar, flash_sprite, tint_sprite)
                if result:
                    bonus_xp = 25 + player["floor"] * 10
                    bonus_gold = int((random.randint(30, 50) + player["floor"] * 8) * player.get("_blessing_gold_mult", 1.0))
                    player["gold"] += bonus_gold
                    player["floor_gold_earned"] = player.get("floor_gold_earned", 0) + bonus_gold
                    show_msg(screen, f"⚡ Elite defeated! Bonus: +{bonus_xp} XP +{bonus_gold}g", font, small_font, clock)
                    _gain_xp_with_upgrade(player, bonus_xp, show_msg, screen, font, small_font, clock)
                    visited_rooms[current_room] = "cleared"
                    room_hazards.pop(current_room, None)
                    check_quests(player, "kill", screen, font, small_font, clock,
                                 upgrade_fn=lambda: upgrade_screen(screen, player, font, small_font, clock))
            elif room_type == "locked":
                if player.get("keys", 0) > 0:
                    player["keys"] -= 1
                    show_msg(screen, "🗝️ You use a key to unlock the chamber... an upgrade awaits!", font, small_font, clock)
                    upgrade_screen(screen, player, font, small_font, clock)
                    visited_rooms[current_room] = "cleared_locked"
                else:
                    show_msg(screen, "🔒 This room is locked. Find a key in chests or defeat a Guardian.", font, small_font, clock)
            elif room_type == "event":
                event_room(player, visited_rooms, current_room, screen, font, small_font, clock,
                           fctx=fctx)

        if ng_plus_carry is not None:
            continue  # NG+ restart — go back to outer while True top
        stop_music()
        if player["hp"] <= 0:
            # Companion flees on death
            if player.get("companion"):
                player["companion"] = None
                player.pop("_companion_atk_bonus", None)
                player.pop("_companion_discount", None)
            game_over_screen(screen, player, big_font, font, small_font, clock)
        break  # normal exit from outer NG+ loop

    pygame.quit()

if __name__ == "__main__":
    main()
