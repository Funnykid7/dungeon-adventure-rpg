import pygame
import sys
import random
import os
import json
from src.constants import (SCREEN_W, SCREEN_H, MAP_SIZE, ROOM_W, ROOM_H,
                            UPGRADE_POOL, CLASS_PASSIVES, CLASS_UPGRADES, SYNERGIES,
                            EQUIPMENT, FLOOR_CURSES, FLOOR_BLESSINGS)
from src.entities import classes, weapons
from src.player_defaults import ensure_player_keys

def fade_screen(screen, clock, fade_type='out', speed=5):
    """Smoothly fades the screen to/from black."""
    fade_surface = pygame.Surface((SCREEN_W, SCREEN_H))
    fade_surface.fill((0, 0, 0))
    
    if fade_type == 'out':
        for alpha in range(0, 256, speed):
            fade_surface.set_alpha(alpha)
            # We can't easily redraw the whole screen here without passing everything, 
            # so we just overlay black.
            screen.blit(fade_surface, (0, 0))
            pygame.display.flip()
            clock.tick(60)
    else:
        snapshot = screen.copy()
        for alpha in range(255, -1, -speed):
            screen.blit(snapshot, (0, 0))
            fade_surface.set_alpha(alpha)
            screen.blit(fade_surface, (0, 0))
            pygame.display.flip()
            clock.tick(60)

def _wrap_text(text, font, max_width):
    words = text.split(' ')
    lines, current = [], ''
    for word in words:
        test = (current + ' ' + word).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def show_msg(screen, text, font, small_font, clock):
    """Displays a message in a dialogue box with a scrolling effect."""
    visible_chars = 0
    scroll_speed = 0.5
    waiting = True

    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                if visible_chars < len(text):
                    visible_chars = len(text)
                else:
                    waiting = False

        # UI panel
        DIALOGUE_HEIGHT = 140
        dialogue_rect = pygame.Rect(0, SCREEN_H - DIALOGUE_HEIGHT, SCREEN_W, DIALOGUE_HEIGHT)
        pygame.draw.rect(screen, (28, 28, 28), dialogue_rect)
        pygame.draw.rect(screen, (200, 200, 200), dialogue_rect, 4)

        # Text
        if visible_chars < len(text):
            visible_chars += scroll_speed

        current_text = text[:int(visible_chars)]
        lines = _wrap_text(current_text, font, SCREEN_W - 60)
        for i, line in enumerate(lines[:3]):
            txt = font.render(line, True, (255, 255, 255))
            screen.blit(txt, (30, SCREEN_H - 125 + i * 40))

        # Prompt
        if visible_chars >= len(text):
            prompt = small_font.render("Press any key to continue...", True, (150, 150, 150))
            screen.blit(prompt, (SCREEN_W - 220, SCREEN_H - 20))

        pygame.display.flip()
        clock.tick(60)

MINIMAP_ICONS = {
    "merchant": "M", "cleared_merchant": "M",
    "exit":     "E",
    "boss":     "B",
    "shrine":   "S", "cleared_shrine":   "S",
    "trap":     "T", "cleared_trap":     "T",
    "chest":    "C", "cleared_chest":    "C",
    "miniboss": "!",
    "puzzle":   "?", "cleared_puzzle":   "?",
    "elite":    "E",
    "locked":   "L", "cleared_locked":   "L",
    "event":    "*", "cleared_event":    "*",
}
CLEARED_TYPES = {"cleared_merchant", "cleared_shrine", "cleared_trap", "cleared_chest",
                 "cleared_puzzle", "cleared_locked", "cleared_event"}

_MINIMAP_ROOM_COLORS = {
    "enemy":            (160, 60,  60),
    "cleared":          (55,  55,  55),
    "boss":             (200, 40,  40),
    "exit":             (60,  200, 120),
    "merchant":         (200, 160, 40),
    "cleared_merchant": (80,  65,  20),
    "shrine":           (80,  120, 200),
    "cleared_shrine":   (40,  60,  90),
    "trap":             (180, 80,  30),
    "cleared_trap":     (60,  35,  15),
    "chest":            (200, 180, 40),
    "cleared_chest":    (80,  70,  20),
    "miniboss":         (220, 100, 30),
    "puzzle":           (120, 60,  200),
    "cleared_puzzle":   (50,  30,  80),
    "elite":            (200, 60,  160),
    "locked":           (80,  80,  120),
    "cleared_locked":   (40,  40,  60),
    "event":            (60,  180, 200),
    "cleared_event":    (30,  70,  80),
}

def draw_minimap(screen, visited_rooms, current_room, small_font, floor_num=1, player=None, entered_rooms=None):
    """Color-coded 5x5 minimap. Only reveals rooms the player has entered."""
    CELL_SIZE = 32
    MAP_X = SCREEN_W - (CELL_SIZE * MAP_SIZE) - 18
    MAP_Y = SCREEN_H - (CELL_SIZE * MAP_SIZE) - 46
    map_reveal = player.get("_map_reveal", False) if player else False
    companion = player.get("companion") if player else None
    scout_reveal = companion and companion.get("role") == "scout"
    if entered_rooms is None:
        entered_rooms = set()

    bg_w = CELL_SIZE * MAP_SIZE + 20
    bg_h = CELL_SIZE * MAP_SIZE + 40
    bg_rect = pygame.Rect(MAP_X - 10, MAP_Y - 30, bg_w, bg_h)
    pygame.draw.rect(screen, (15, 12, 28), bg_rect, border_radius=6)
    pygame.draw.rect(screen, (180, 150, 60), bg_rect, 2, border_radius=6)

    title = small_font.render(f"FL{floor_num}", True, (200, 175, 80))
    screen.blit(title, (MAP_X - 4, MAP_Y - 26))

    pulse = abs((pygame.time.get_ticks() % 1000) - 500) / 500  # 0→1→0
    pulse_color = (int(200 + 55 * pulse), int(200 + 55 * pulse), 60)

    cx, cy = current_room
    for x in range(MAP_SIZE):
        for y in range(MAP_SIZE):
            rx = MAP_X + x * CELL_SIZE
            ry = MAP_Y + y * CELL_SIZE
            rect = pygame.Rect(rx, ry, CELL_SIZE - 2, CELL_SIZE - 2)
            room_data = visited_rooms.get((x, y))
            is_current = (x, y) == current_room

            in_scout_range = scout_reveal and abs(x - cx) <= 2 and abs(y - cy) <= 2
            revealed = (x, y) in entered_rooms or map_reveal or in_scout_range

            if is_current:
                pygame.draw.rect(screen, pulse_color, rect, border_radius=3)
                icon = MINIMAP_ICONS.get(room_data, "")
                if icon:
                    char = small_font.render(icon, True, (0, 0, 0))
                    screen.blit(char, (rx + (CELL_SIZE - 2 - char.get_width()) // 2,
                                       ry + (CELL_SIZE - 2 - char.get_height()) // 2))
            elif revealed and room_data is not None:
                color = _MINIMAP_ROOM_COLORS.get(room_data, (35, 35, 50))
                pygame.draw.rect(screen, color, rect, border_radius=3)
                icon = MINIMAP_ICONS.get(room_data, "")
                if icon:
                    char_color = (220, 220, 220) if room_data not in CLEARED_TYPES else (130, 130, 130)
                    char = small_font.render(icon, True, char_color)
                    screen.blit(char, (rx + (CELL_SIZE - 2 - char.get_width()) // 2,
                                       ry + (CELL_SIZE - 2 - char.get_height()) // 2))
            else:
                # Unexplored — dark cell, no type info
                pygame.draw.rect(screen, (25, 22, 35), rect, border_radius=3)
                pygame.draw.rect(screen, (60, 55, 80), rect, 1, border_radius=3)

def start_screen(screen, big_font, font, small_font, SAVE_FILE, load_game_func, intro_gui_func, show_msg_func, clock):
    """Initial screen to New Game or Load Game."""
    has_save = os.path.exists(SAVE_FILE)
    selected = 0 # 0 for New Game, 1 for Load Game
    save_meta = ""
    if has_save:
        try:
            with open(SAVE_FILE) as _f:
                _raw = json.load(_f)
            save_meta = f"Lv.{_raw.get('level',1)} · Floor {_raw.get('floor',1)} · {str(_raw.get('class','?')).capitalize()}"
        except Exception:
            save_meta = ""
    
    # We need to return multiple values if loading
    class LoadResult:
        def __init__(self, data, current_room=None, visited_rooms=None, px=None, py=None):
            self.data = data
            self.current_room = current_room
            self.visited_rooms = visited_rooms
            self.px = px
            self.py = py

    def do_load():
        data = load_game_func(SAVE_FILE)
        if data:
            # Restore globals from loaded data
            raw_rooms = data.get("_visited_rooms", {})
            v_rooms = {}
            for k, v in raw_rooms.items():
                try:
                    # Safely parse the tuple string "(x, y)"
                    key_tuple = tuple(map(int, k.strip("()").replace(" ", "").split(",")))
                    v_rooms[key_tuple] = v
                except: continue
            
            c_room = tuple(data.get("_current_room", (0, 0)))
            px = data.get("_player_world_x", ROOM_W // 2)
            py = data.get("_player_world_y", ROOM_H // 2)
            
            ensure_player_keys(data)
            
            show_msg_func(screen, "📂 Save Loaded Successfully!", font, small_font, clock)
            return LoadResult(data, c_room, v_rooms, px, py)
        else:
            show_msg_func(screen, "❌ Failed to load save!", font, small_font, clock)
            return None

    while True:
        clock.tick(60)
        screen.fill((15, 15, 15))
        
        title = big_font.render("DUNGEON ADVENTURE", True, (255, 215, 0))
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 100))
        
        # New Game
        color = (255, 255, 255) if selected == 0 else (100, 100, 100)
        new_txt = font.render("> NEW GAME <" if selected == 0 else "  NEW GAME  ", True, color)
        screen.blit(new_txt, (SCREEN_W // 2 - new_txt.get_width() // 2, 250))
        
        # Load Game
        if has_save:
            color = (255, 255, 255) if selected == 1 else (100, 100, 100)
            load_txt = font.render("> LOAD GAME <" if selected == 1 else "  LOAD GAME  ", True, color)
        else:
            color = (60, 60, 60)
            load_txt = font.render("  LOAD GAME (No Save)  ", True, color)

        screen.blit(load_txt, (SCREEN_W // 2 - load_txt.get_width() // 2, 310))
        if save_meta:
            meta_txt = small_font.render(save_meta, True, (160, 160, 120))
            screen.blit(meta_txt, (SCREEN_W // 2 - meta_txt.get_width() // 2, 345))
        
        instr = small_font.render("Arrows to Select | ENTER to Confirm", True, (150, 150, 150))
        screen.blit(instr, (SCREEN_W // 2 - instr.get_width() // 2, 450))
            
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP or event.key == pygame.K_DOWN:
                    if has_save:
                        selected = 1 - selected
                if event.key == pygame.K_RETURN:
                    if selected == 0:
                        return intro_gui_func(screen, big_font, font, small_font, clock)
                    elif selected == 1 and has_save:
                        res = do_load()
                        if res: return res
                # Shortcuts
                if event.key == pygame.K_1:
                    return intro_gui_func(screen, big_font, font, small_font, clock)
                if event.key == pygame.K_2 and has_save:
                    res = do_load()
                    if res: return res

def intro_gui(screen, big_font, font, small_font, clock):
    """GUI for name entry and class selection."""
    name = ""
    input_active = True
    
    class_list = list(classes.keys())
    
    while input_active:
        clock.tick(60)
        screen.fill((20, 20, 20))
        
        title = big_font.render("DUNGEON ADVENTURE", True, (255, 215, 0))
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 50))
        
        prompt = font.render("Enter Hero Name:", True, (200, 200, 200))
        screen.blit(prompt, (SCREEN_W // 2 - prompt.get_width() // 2, 150))
        
        pygame.draw.rect(screen, (50, 50, 50), (SCREEN_W // 2 - 200, 200, 400, 50))
        pygame.draw.rect(screen, (200, 200, 200), (SCREEN_W // 2 - 200, 200, 400, 50), 2)
        
        name_surface = font.render(name + ("|" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""), True, (255, 255, 255))
        screen.blit(name_surface, (SCREEN_W // 2 - name_surface.get_width() // 2, 205))
        
        instr = small_font.render("Press ENTER to confirm", True, (150, 150, 150))
        screen.blit(instr, (SCREEN_W // 2 - instr.get_width() // 2, 260))
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if name.strip():
                        input_active = False
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif event.key == pygame.K_SPACE:
                    if len(name) < 15:
                        name += " "
                else:
                    if len(name) < 15 and event.unicode.isalnum():
                        name += event.unicode

    # Class Selection
    input_active = True
    idx = 0
    
    while input_active:
        clock.tick(60)
        screen.fill((20, 20, 20))
        
        current_cls = class_list[idx]
        cls_data = classes[current_cls]
        
        # Header
        header = font.render(f"Choose Class for {name}", True, (255, 215, 0))
        screen.blit(header, (SCREEN_W // 2 - header.get_width() // 2, 50))
        
        # Selection
        cls_txt = big_font.render(current_cls.upper(), True, (255, 255, 255))
        screen.blit(cls_txt, (SCREEN_W // 2 - cls_txt.get_width() // 2, 150))
        
        # Description
        desc_y = 250
        draw_text_slow_static(screen, cls_data['desc'], SCREEN_W // 2 - 250, desc_y, 500, small_font)
        
        stats_txt = small_font.render(f"Base HP: {cls_data['hp']} | Attack: {cls_data['attack'][0]}-{cls_data['attack'][1]}", True, (100, 255, 100))
        screen.blit(stats_txt, (SCREEN_W // 2 - stats_txt.get_width() // 2, 350))
        
        # Navigation
        nav = small_font.render("< Left / Right > to browse | ENTER to select", True, (200, 200, 200))
        screen.blit(nav, (SCREEN_W // 2 - nav.get_width() // 2, 450))
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    idx = (idx + 1) % len(class_list)
                elif event.key == pygame.K_LEFT:
                    idx = (idx - 1) % len(class_list)
                elif event.key == pygame.K_RETURN:
                    selected_class = current_cls
                    input_active = False

    return {
        "name": name,
        "class": selected_class,
        "hp": classes[selected_class]["hp"],
        "max_hp": classes[selected_class]["hp"],
        "level": 1,
        "xp": 0,
        "gold": 50,
        "potions": 2,
        "strength_potions": 0,
        "defense_potions": 0,
        "strength_turns": 0,
        "defense_turns": 0,
        "weapon": "Dagger",
        "floor": 1,
        "rooms": 0,
        "revived": False,
        "map": None,
        "last_attack": None,
        "enemies_killed": 0,
        "gold_earned": 0,
        "floors_cleared": 0,
        "keys": 0,
        "equipment": {"armor": None, "ring": None, "trinket": None},
        "quests": [],
        "floor_gold_earned": 0,
    }

def merchant_gui(screen, player, merchant_bg, font, small_font, show_msg_func, clock):
    clock = clock
    running = True
    menu_mode = "weapons"  # "weapons" | "potions" | "equipment"

    discount = player.get("_companion_discount", 0.0)

    def discounted(price):
        return max(1, int(price * (1 - discount)))

    weapon_items = [(n, d) for n, d in weapons.items() if n != "Dagger"]
    potion_items = [
        {"name": "Healing Potion", "price": discounted(25), "key": "potions", "desc": "Restores 40 HP"},
        {"name": "Strength Potion", "price": discounted(100), "key": "strength_potions", "desc": "1.5x Dmg (5 turns)"},
        {"name": "Defense Potion", "price": discounted(100), "key": "defense_potions", "desc": "0.5x Dmg Recv (5 turns)"}
    ]
    # Flatten equipment into a display list with slot info
    equip_list = []
    for slot, items in EQUIPMENT.items():
        for item in items:
            equip_list.append({"slot": slot, **item})

    while running:
        clock.tick(60)
        screen.blit(merchant_bg, (0, 0))

        panel = pygame.Rect(60, 60, 900, 420)
        pygame.draw.rect(screen, (24, 24, 24), panel)
        pygame.draw.rect(screen, (200, 180, 120), panel, 4)

        mode_labels = {"weapons": "WEAPON SHOP", "potions": "POTION SHOP", "equipment": "EQUIPMENT SHOP"}
        title = font.render(mode_labels[menu_mode], True, (255, 220, 120))
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 80))

        gold_txt = font.render(f"Gold: {player['gold']}", True, (255, 220, 120))
        screen.blit(gold_txt, (700, 100))

        y = 140
        if menu_mode == "weapons":
            current_bonus = weapons[player["weapon"]]["bonus"]
            for i, (name, data) in enumerate(weapon_items):
                is_downgrade = data["bonus"] < current_bonus
                is_owned = name == player["weapon"]
                wpn_price = discounted(data['price'])
                if is_owned:
                    color, status = (100, 255, 100), "(Equipped)"
                elif is_downgrade:
                    color, status = (255, 100, 100), "(Downgrade)"
                elif player['gold'] >= wpn_price:
                    color, status = (255, 255, 255), f"- {wpn_price}g"
                else:
                    color, status = (100, 100, 100), f"- {wpn_price}g"
                txt = f"{i+1}. {name} (+{data['bonus']} ATK) {status}"
                screen.blit(font.render(txt, True, color), (120, y))
                y += 40
        elif menu_mode == "potions":
            for i, item in enumerate(potion_items):
                color = (255, 255, 255) if player['gold'] >= item['price'] else (100, 100, 100)
                txt = f"{i+1}. {item['name']} - {item['price']}g ({item['desc']})"
                screen.blit(font.render(txt, True, color), (120, y))
                y += 40
        else:  # equipment
            eq_owned = player.get("equipment", {})
            for i, item in enumerate(equip_list):
                owned_name = eq_owned.get(item["slot"])
                is_owned = owned_name == item["name"]
                eq_price = discounted(item["price"])
                if is_owned:
                    color, status = (100, 255, 100), "(OWNED)"
                elif player["gold"] >= eq_price:
                    color, status = (255, 255, 255), f"- {eq_price}g"
                else:
                    color, status = (100, 100, 100), f"- {eq_price}g"
                txt = f"{i+1}. [{item['slot'].upper()}] {item['name']} — {item['desc']}  {status}"
                screen.blit(font.render(txt, True, color), (120, y))
                y += 38

        screen.blit(
            small_font.render("TAB - Switch Menu (Weapons/Potions/Equipment) | ESC - Back", True, (200, 200, 200)),
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

                elif event.key == pygame.K_TAB:
                    modes = ["weapons", "potions", "equipment"]
                    menu_mode = modes[(modes.index(menu_mode) + 1) % len(modes)]

                elif pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1

                    if menu_mode == "weapons":
                        if idx < len(weapon_items):
                            name, data = weapon_items[idx]
                            current_bonus = weapons[player["weapon"]]["bonus"]
                            wpn_price = discounted(data["price"])
                            if name == player["weapon"]:
                                show_msg_func(screen, "You already own this weapon!", font, small_font, clock)
                            elif data["bonus"] < current_bonus:
                                show_msg_func(screen, "This weapon is weaker than your current one!", font, small_font, clock)
                            elif player["gold"] >= wpn_price:
                                player["gold"] -= wpn_price
                                player["weapon"] = name
                                show_msg_func(screen, f"Purchased {name}!", font, small_font, clock)
                            else:
                                show_msg_func(screen, "Not enough gold!", font, small_font, clock)
                    elif menu_mode == "potions":
                        if idx < len(potion_items):
                            item = potion_items[idx]
                            if player["gold"] >= item["price"]:
                                player["gold"] -= item["price"]
                                key = item["key"]
                                player[key] = player.get(key, 0) + 1
                                show_msg_func(screen, f"🧪 Purchased {item['name']}!", font, small_font, clock)
                            else:
                                show_msg_func(screen, "❌ Not enough gold!", font, small_font, clock)
                    else:  # equipment
                        if idx < len(equip_list):
                            item = equip_list[idx]
                            eq_owned = player.setdefault("equipment", {})
                            eq_price = discounted(item["price"])
                            if eq_owned.get(item["slot"]) == item["name"]:
                                show_msg_func(screen, f"You already own {item['name']}!", font, small_font, clock)
                            elif player["gold"] >= eq_price:
                                player["gold"] -= eq_price
                                eq_owned[item["slot"]] = item["name"]
                                item["apply"](player)
                                show_msg_func(screen, f"Equipped {item['name']}! {item['desc']}", font, small_font, clock)
                            else:
                                show_msg_func(screen, "Not enough gold!", font, small_font, clock)

def draw_hp_bar(screen, x, y, w, h, current, max_hp, color):
    ratio = max(0, current / max_hp)
    pygame.draw.rect(screen, (60, 60, 60), (x, y, w, h))
    pygame.draw.rect(screen, color, (x, y, int(w * ratio), h))
    pygame.draw.rect(screen, (0, 0, 0), (x, y, w, h), 2)

def draw_text_slow_static(screen, text, x, y, max_w, small_font):
    """Utility to draw wrapped text without animation."""
    words = text.split(" ")
    line = ""
    for word in words:
        test = line + word + " "
        surface = small_font.render(test, True, (200, 200, 200))
        if surface.get_width() > max_w:
            screen.blit(small_font.render(line, True, (200, 200, 200)), (x, y))
            y += 25
            line = word + " "
        else:
            line = test
    screen.blit(small_font.render(line, True, (200, 200, 200)), (x, y))

def flash_sprite(sprite):
    flash = sprite.copy()
    flash.fill((255, 0, 0, 120), special_flags=pygame.BLEND_RGBA_ADD)
    return flash

def tint_sprite(sprite, color):
    tinted = sprite.copy()
    tinted.fill(color, special_flags=pygame.BLEND_RGB_ADD)
    return tinted

def show_stats_screen(screen, player, font, small_font, clock):
    running = True
    while running:
        clock.tick(60)
        screen.fill((12, 12, 20))
        title = font.render(f"{player['name']} the {player['class'].capitalize()}", True, (255, 215, 0))
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 40))

        # Left column: stats + upgrades
        lines = [
            f"Level {player['level']}  |  XP: {player['xp']} / {player['level'] * 60}",
            f"HP: {player['hp']} / {player['max_hp']}  |  Gold: {player['gold']}",
            f"Weapon: {player['weapon']}",
            "",
            "CLASS PASSIVE:",
            CLASS_PASSIVES.get(player["class"], ""),
        ]
        upgrades = player.get("upgrades", [])
        if upgrades:
            lines += ["", "ACTIVE UPGRADES:"] + [f"  + {u}" for u in upgrades]
        else:
            lines += ["", "No upgrades yet."]

        for i, line in enumerate(lines):
            if line in ("CLASS PASSIVE:", "ACTIVE UPGRADES:"):
                col = (255, 220, 100)
            elif line:
                col = (200, 200, 200)
            else:
                col = (0, 0, 0)
            screen.blit(small_font.render(line, True, col), (80, 120 + i * 28))

        # Right column: active quests
        quests = player.get("quests", [])
        if quests:
            q_header = small_font.render("ACTIVE QUESTS:", True, (255, 220, 100))
            screen.blit(q_header, (520, 120))
            q_type_icons = {"kill": "⚔️", "explore": "🗺️", "no_damage": "🛡️",
                            "no_potion": "💧", "gold": "💰", "noncombat": "🏛️"}
            for qi, q in enumerate(quests):
                done = q.get("completed", False)
                prog = q.get("progress", 0)
                goal = q.get("goal", 1)
                ratio = min(1.0, prog / max(1, goal))
                icon = q_type_icons.get(q["type"], "?")
                q_col = (120, 200, 120) if done else (200, 200, 200)
                q_desc = q.get("desc", q["id"]).format(goal=goal)
                q_line = f"{icon} {q_desc}"
                screen.blit(small_font.render(q_line[:52], True, q_col), (520, 155 + qi * 70))
                prog_txt = f"  Progress: {prog}/{goal}" + (" ✓" if done else "")
                screen.blit(small_font.render(prog_txt, True, q_col), (520, 178 + qi * 70))
                # Progress bar
                bar_x, bar_y = 520, 196 + qi * 70
                pygame.draw.rect(screen, (40, 40, 60), (bar_x, bar_y, 200, 8))
                pygame.draw.rect(screen, (80, 200, 80) if done else (80, 140, 200),
                                 (bar_x, bar_y, int(200 * ratio), 8))

        # Equipment section (bottom-left)
        eq = player.get("equipment", {})
        eq_header = small_font.render("EQUIPMENT:", True, (255, 220, 100))
        screen.blit(eq_header, (80, 390))
        eq_y = 412
        for slot in ("armor", "ring", "trinket"):
            item_name = eq.get(slot)
            if item_name:
                # Look up the item's description from EQUIPMENT constant
                desc = ""
                for it in EQUIPMENT.get(slot, []):
                    if it["name"] == item_name:
                        desc = it["desc"]
                        break
                eq_line = f"  [{slot.upper()}] {item_name}  — {desc}"
                col = (160, 220, 160)
            else:
                eq_line = f"  [{slot.upper()}] —"
                col = (80, 80, 80)
            screen.blit(small_font.render(eq_line, True, col), (80, eq_y))
            eq_y += 24

        hint = small_font.render("TAB or ESC to close", True, (80, 80, 80))
        screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 510))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_TAB, pygame.K_ESCAPE):
                running = False

def game_over_screen(screen, player, big_font, font, small_font, clock):
    quests_done = sum(1 for q in player.get("quests", []) if q.get("completed"))
    total_quests = len(player.get("quests", []))
    eq = player.get("equipment", {})
    eq_str = ", ".join(v for v in eq.values() if v) or "None"
    upgrades = player.get("upgrades", [])

    stat_lines = [
        (f"{player['name']} the {player['class'].capitalize()}", (255, 180, 60)),
        (f"Floor {player['floor']}   Level {player['level']}   XP {player['xp']}", (200, 200, 200)),
        (f"Enemies Slain: {player.get('enemies_killed', 0)}   Gold Earned: {player.get('gold_earned', 0)}", (200, 200, 200)),
        (f"Floors Cleared: {player.get('floors_cleared', 0)}   Quests Done: {quests_done}/{total_quests}", (200, 200, 200)),
        (f"Weapon: {player['weapon']}   Upgrades: {len(upgrades)}", (180, 180, 200)),
        (f"Equipment: {eq_str}", (160, 200, 160)),
    ]
    if player.get("active_curse"):
        stat_lines.append((f"Active Curse: {player['active_curse']}", (220, 80, 80)))
    if upgrades:
        upg_str = ", ".join(upgrades[:4]) + ("..." if len(upgrades) > 4 else "")
        stat_lines.append((f"Upgrades: {upg_str}", (160, 160, 220)))

    while True:
        clock.tick(60)
        screen.fill((8, 4, 4))

        title = big_font.render("YOU PERISHED", True, (200, 50, 50))
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 55))

        # Decorative line
        pygame.draw.line(screen, (120, 30, 30), (80, 130), (SCREEN_W - 80, 130), 2)

        for i, (line, col) in enumerate(stat_lines):
            txt = small_font.render(line, True, col)
            screen.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, 150 + i * 36))

        pygame.draw.line(screen, (80, 20, 20), (80, 380), (SCREEN_W - 80, 380), 1)

        prompt = small_font.render("Press any key to exit", True, (100, 80, 80))
        screen.blit(prompt, (SCREEN_W // 2 - prompt.get_width() // 2, 395))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                return

def victory_screen(screen, player, big_font, font, small_font, clock):
    ng_selected = 0  # 0 = exit, 1 = NG+
    while True:
        clock.tick(60)
        screen.fill((10, 10, 20))
        title = big_font.render("DUNGEON CONQUERED", True, (255, 215, 0))
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 60))
        lines = [
            f"Hero: {player['name']} the {player['class'].capitalize()}",
            f"Final Floor: {player['floor']}  |  Level: {player['level']}",
            f"Enemies Slain: {player.get('enemies_killed', 0)}",
            f"Gold Earned: {player.get('gold_earned', 0)}",
            f"Floors Cleared: {player.get('floors_cleared', 0)}",
        ]
        for i, line in enumerate(lines):
            txt = font.render(line, True, (220, 220, 160))
            screen.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, 160 + i * 50))
        # NG+ option
        ng_label = "> NEW GAME+ <" if ng_selected == 1 else "  NEW GAME+  "
        ng_color = (255, 140, 0) if ng_selected == 1 else (120, 80, 20)
        exit_label = "> EXIT <" if ng_selected == 0 else "  EXIT  "
        exit_color = (200, 200, 200) if ng_selected == 0 else (100, 100, 100)
        ng_txt = font.render(ng_label, True, ng_color)
        exit_txt = font.render(exit_label, True, exit_color)
        screen.blit(exit_txt, (SCREEN_W // 2 - exit_txt.get_width() // 2, 430))
        screen.blit(ng_txt,   (SCREEN_W // 2 - ng_txt.get_width() // 2,   480))
        hint = small_font.render("Arrows to select | ENTER to confirm | NG+ keeps upgrades, enemies are 1.5× harder", True, (90, 90, 90))
        screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 520))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_DOWN):
                    ng_selected = 1 - ng_selected
                elif event.key == pygame.K_RETURN:
                    if ng_selected == 1:
                        return "ng+"
                    return None

def modifier_select_screen(screen, player, font, small_font, clock, curse_choices, blessing_choices):
    """Floor modifier selection: player picks one curse and one blessing."""
    chosen_curse = None
    chosen_blessing = None
    phase = "curse"  # "curse" then "blessing"

    while chosen_curse is None or chosen_blessing is None:
        clock.tick(60)
        screen.fill((10, 10, 20))

        title = font.render("⚡ FLOOR MODIFIER — A deal with the dungeon", True, (255, 215, 0))
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 30))

        # Curse panel (left)
        cx = 80
        curse_header = font.render("☠️ Choose a Curse", True, (220, 80, 80) if phase == "curse" else (100, 50, 50))
        screen.blit(curse_header, (cx, 80))
        for i, c in enumerate(curse_choices):
            col = (220, 120, 120) if phase == "curse" else (80, 40, 40)
            if chosen_curse and chosen_curse["name"] == c["name"]:
                col = (255, 80, 80)
            n_txt = font.render(f"{i+1}. {c['name']}", True, col)
            d_txt = small_font.render(f"   {c['desc']}", True, (160, 80, 80) if phase == "curse" else (60, 30, 30))
            screen.blit(n_txt, (cx, 130 + i * 80))
            screen.blit(d_txt, (cx, 162 + i * 80))

        # Blessing panel (right)
        bx = 500
        bless_header = font.render("✨ Choose a Blessing", True, (255, 215, 0) if phase == "blessing" else (100, 85, 20))
        screen.blit(bless_header, (bx, 80))
        for i, b in enumerate(blessing_choices):
            col = (255, 220, 120) if phase == "blessing" else (100, 85, 30)
            if chosen_blessing and chosen_blessing["name"] == b["name"]:
                col = (255, 200, 0)
            n_txt = font.render(f"{i+1}. {b['name']}", True, col)
            d_txt = small_font.render(f"   {b['desc']}", True, (180, 160, 80) if phase == "blessing" else (80, 70, 30))
            screen.blit(n_txt, (bx, 130 + i * 80))
            screen.blit(d_txt, (bx, 162 + i * 80))

        phase_txt = "Press 1 or 2 to pick a CURSE" if phase == "curse" else "Press 1 or 2 to pick a BLESSING"
        hint = small_font.render(phase_txt, True, (150, 150, 150))
        screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 450))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_2):
                    idx = event.key - pygame.K_1
                    if phase == "curse" and idx < len(curse_choices):
                        chosen_curse = curse_choices[idx]
                        phase = "blessing"
                    elif phase == "blessing" and idx < len(blessing_choices):
                        chosen_blessing = blessing_choices[idx]

    chosen_curse["apply"](player)
    chosen_blessing["apply"](player)
    player["active_curse"] = chosen_curse["name"]
    player["active_blessing"] = chosen_blessing["name"]
    return chosen_curse, chosen_blessing


def upgrade_screen(screen, player, font, small_font, clock):
    import random as _random
    owned = set(player.get("upgrades", []))
    full_pool = list(UPGRADE_POOL) + CLASS_UPGRADES.get(player.get("class", ""), [])
    available = [u for u in full_pool if u["name"] not in owned]
    if len(available) < 3:
        available = full_pool  # fallback: allow repeats if pool exhausted
    choices = _random.sample(available, min(3, len(available)))
    selected = None
    while selected is None:
        clock.tick(60)
        screen.fill((15, 15, 25))
        title = font.render("LEVEL UP! Choose an upgrade:", True, (255, 215, 0))
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 80))
        for i, upg in enumerate(choices):
            txt = font.render(f"{i+1}. {upg['name']} — {upg['desc']}", True, (200, 200, 200))
            screen.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, 180 + i * 80))
        hint = small_font.render("Press 1, 2, or 3 to choose", True, (120, 120, 120))
        screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 430))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if pygame.K_1 <= event.key <= pygame.K_3:
                    idx = event.key - pygame.K_1
                    if idx < len(choices):
                        selected = choices[idx]
    selected["apply"](player)
    player.setdefault("upgrades", []).append(selected["name"])
    show_msg(screen, f"✨ {selected['name']} unlocked! {selected['desc']}", font, small_font, clock)
    # Check synergy bonuses
    for (upg_a, upg_b, bonus_fn, msg) in SYNERGIES:
        if upg_a in owned and selected["name"] == upg_b:
            bonus_fn(player)
            show_msg(screen, f"⚡ {msg}", font, small_font, clock)
        elif upg_b in owned and selected["name"] == upg_a:
            bonus_fn(player)
            show_msg(screen, f"⚡ {msg}", font, small_font, clock)


# ---------------------------------------------------------------------------
# Modifier pills — drawn over the overworld in the top-right corner
# ---------------------------------------------------------------------------

def draw_modifier_pills(screen, player, small_font):
    """Draw active curse and blessing as small colored pills in the top-right corner."""
    pill_x = SCREEN_W - 10
    pill_y = 8

    def _pill(text, bg_color, text_color):
        nonlocal pill_x
        surf = small_font.render(text, True, text_color)
        w = surf.get_width() + 14
        h = surf.get_height() + 6
        pill_x -= w + 6
        rect = pygame.Rect(pill_x, pill_y, w, h)
        pygame.draw.rect(screen, bg_color, rect, border_radius=6)
        pygame.draw.rect(screen, text_color, rect, 1, border_radius=6)
        screen.blit(surf, (pill_x + 7, pill_y + 3))

    if player.get("active_blessing"):
        _pill(player["active_blessing"], (40, 30, 5), (255, 200, 60))
    if player.get("active_curse"):
        _pill(player["active_curse"], (40, 10, 10), (220, 80, 80))


# ---------------------------------------------------------------------------
# Pause menu
# ---------------------------------------------------------------------------

def quest_journal_screen(screen, player, font, small_font, clock):
    """Full-screen quest journal overlay (BotW-style list). ESC or ENTER to close."""
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((6, 6, 14, 230))
    quests = player.get("quests", [])
    scroll = 0
    visible = 3
    card_h = 100

    while True:
        clock.tick(60)
        screen.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_W // 2 - 400, SCREEN_H // 2 - 210, 800, 420)
        pygame.draw.rect(screen, (16, 14, 26), panel, border_radius=18)
        pygame.draw.rect(screen, (120, 100, 180), panel, 2, border_radius=18)

        title = font.render("Quest Journal", True, (235, 220, 255))
        screen.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 16))
        sub = small_font.render(f"Floor {player.get('floor', 1)}", True, (150, 140, 180))
        screen.blit(sub, (panel.centerx - sub.get_width() // 2, panel.top + 54))

        if not quests:
            none_txt = small_font.render("No active quests on this floor.", True, (150, 150, 160))
            screen.blit(none_txt, (panel.centerx - none_txt.get_width() // 2, panel.centery))
        else:
            max_scroll = max(0, len(quests) - visible)
            scroll = min(scroll, max_scroll)
            y = panel.top + 88
            for q in quests[scroll:scroll + visible]:
                done = q.get("completed", False)
                prog = q.get("progress", 0)
                goal = q.get("goal", 1)
                ratio = min(1.0, prog / max(1, goal))

                card = pygame.Rect(panel.left + 24, y, panel.width - 48, 86)
                pygame.draw.rect(screen, (20, 30, 22) if done else (26, 24, 40), card, border_radius=10)
                pygame.draw.rect(screen, (70, 130, 80) if done else (70, 64, 100), card, 1, border_radius=10)

                desc_full = q.get("desc", q["id"]).format(goal=goal)
                qname, _, qdetail = desc_full.partition(":")
                name_col = (130, 200, 130) if done else (235, 225, 255)
                check = "  ✓" if done else ""
                screen.blit(small_font.render(qname + check, True, name_col), (card.left + 14, card.top + 10))
                detail_col = (120, 150, 120) if done else (190, 190, 205)
                screen.blit(small_font.render(qdetail.strip()[:60], True, detail_col), (card.left + 14, card.top + 34))

                bar_x, bar_y = card.left + 14, card.top + 62
                bar_w = card.width - 220
                pygame.draw.rect(screen, (40, 40, 58), (bar_x, bar_y, bar_w, 10), border_radius=4)
                pygame.draw.rect(screen, (90, 200, 110) if done else (90, 150, 230),
                                 (bar_x, bar_y, int(bar_w * ratio), 10), border_radius=4)
                screen.blit(small_font.render(f"{prog}/{goal}", True, (200, 200, 210)), (bar_x + bar_w + 12, bar_y - 5))

                reward_bits = []
                if q.get("reward_gold", 0) > 0:
                    reward_bits.append(f"+{q['reward_gold']}g")
                if q.get("reward_upgrade"):
                    reward_bits.append("+Upgrade")
                if reward_bits:
                    rwd = small_font.render("Reward: " + "  ".join(reward_bits), True, (210, 190, 110))
                    screen.blit(rwd, (card.right - rwd.get_width() - 14, card.top + 10))

                y += card_h

            if len(quests) > visible:
                more = small_font.render("UP/DOWN to scroll", True, (120, 120, 150))
                screen.blit(more, (panel.centerx - more.get_width() // 2, panel.bottom - 48))

        hint = small_font.render("ESC or ENTER to close", True, (120, 120, 150))
        screen.blit(hint, (panel.centerx - hint.get_width() // 2, panel.bottom - 26))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    return
                elif event.key in (pygame.K_UP, pygame.K_w):
                    scroll = max(0, scroll - 1)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    scroll = min(max(0, len(quests) - visible), scroll + 1)


def pause_menu(screen, player, font, small_font, clock, save_fn=None):
    """ESC pause overlay. Returns 'quit' if the player exits, None otherwise."""
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    selected = 0
    options = ["Resume", "Save", "Journal", "Save & Quit"]
    saved_flash = 0  # frames left to show the "Saved!" confirmation

    while True:
        clock.tick(60)
        screen.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_W // 2 - 200, SCREEN_H // 2 - 150, 400, 300)
        pygame.draw.rect(screen, (20, 20, 30), panel, border_radius=12)
        pygame.draw.rect(screen, (100, 100, 140), panel, 2, border_radius=12)

        title = font.render("PAUSED", True, (200, 200, 255))
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, panel.top + 18))

        for i, opt in enumerate(options):
            col = (255, 255, 255) if i == selected else (120, 120, 140)
            prefix = "> " if i == selected else "  "
            txt = font.render(prefix + opt, True, col)
            screen.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, panel.top + 70 + i * 48))

        if saved_flash > 0:
            saved_flash -= 1
            conf = small_font.render("Saved!", True, (120, 220, 120))
            screen.blit(conf, (SCREEN_W // 2 - conf.get_width() // 2, panel.bottom - 50))

        hint = small_font.render("Up/Down to navigate | ENTER to confirm | ESC to resume", True, (80, 80, 100))
        screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, panel.bottom - 26))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(options)
                elif event.key == pygame.K_RETURN:
                    if selected == 0:        # Resume
                        return None
                    elif selected == 1:      # Save
                        if save_fn:
                            save_fn()
                        saved_flash = 90
                    elif selected == 2:      # Journal
                        quest_journal_screen(screen, player, font, small_font, clock)
                    elif selected == 3:      # Save & Quit
                        if save_fn:
                            save_fn()
                        return "quit"


# ---------------------------------------------------------------------------
# Floor transition recap screen
# ---------------------------------------------------------------------------

def floor_transition_screen(screen, player, font, small_font, clock, theme_name):
    """Brief recap shown when entering a new floor."""
    quests_done = sum(1 for q in player.get("quests", []) if q.get("completed"))
    total_quests = len(player.get("quests", []))

    lines = [
        f"Floor {player['floor']}  —  {theme_name}",
        "",
        f"Level {player['level']}  |  HP {player['hp']}/{player['max_hp']}  |  Gold {player['gold']}",
        f"Quests completed last floor: {quests_done}/{total_quests}",
    ]
    if player.get("active_curse"):
        lines.append(f"Curse:    {player['active_curse']}")
    if player.get("active_blessing"):
        lines.append(f"Blessing: {player['active_blessing']}")

    start = pygame.time.get_ticks()
    duration = 3200  # auto-advance after 3.2 s

    while True:
        clock.tick(60)
        elapsed = pygame.time.get_ticks() - start

        screen.fill((8, 8, 18))
        # decorative top bar
        pygame.draw.rect(screen, (40, 30, 80), (0, 0, SCREEN_W, 6))

        header = font.render(f"-- DESCENDING TO FLOOR {player['floor']} --", True, (160, 120, 255))
        screen.blit(header, (SCREEN_W // 2 - header.get_width() // 2, 100))

        for i, line in enumerate(lines):
            if i == 0:
                col = (255, 215, 0)
                surf = font.render(line, True, col)
            elif line.startswith("Curse:"):
                col = (220, 80, 80)
                surf = small_font.render(line, True, col)
            elif line.startswith("Blessing:"):
                col = (255, 200, 60)
                surf = small_font.render(line, True, col)
            elif line == "":
                continue
            else:
                col = (180, 180, 200)
                surf = small_font.render(line, True, col)
            screen.blit(surf, (SCREEN_W // 2 - surf.get_width() // 2, 190 + i * 40))

        # countdown bar
        progress = min(1.0, elapsed / duration)
        bar_w = int((SCREEN_W - 200) * progress)
        pygame.draw.rect(screen, (40, 30, 70), (100, 420, SCREEN_W - 200, 6))
        pygame.draw.rect(screen, (120, 80, 220), (100, 420, bar_w, 6))

        hint = small_font.render("Press any key to continue...", True, (80, 80, 100))
        screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 450))

        pygame.display.flip()

        if elapsed >= duration:
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                return


# ---------------------------------------------------------------------------
# Corridor transition
# ---------------------------------------------------------------------------

def draw_corridor_transition(screen, clock, direction, floor_num, duration_ms=350):
    """Blocking corridor animation played when stepping through a door."""
    import math as _math
    from src.constants import FLOOR_DECORATION_COLORS
    colors = FLOOR_DECORATION_COLORS.get(floor_num, FLOOR_DECORATION_COLORS[1])
    glow_color = colors["glow"]

    start = pygame.time.get_ticks()
    while True:
        elapsed = pygame.time.get_ticks() - start
        if elapsed >= duration_ms:
            return
        t = elapsed / duration_ms  # 0..1

        screen.fill((22, 18, 28))
        # Tunnel walls
        pygame.draw.rect(screen, (40, 30, 22), (0, 0, SCREEN_W, 40))
        pygame.draw.rect(screen, (40, 30, 22), (0, SCREEN_H - 40, SCREEN_W, 40))
        # Side walls
        pygame.draw.rect(screen, (30, 22, 16), (0, 40, 60, SCREEN_H - 80))
        pygame.draw.rect(screen, (30, 22, 16), (SCREEN_W - 60, 40, 60, SCREEN_H - 80))

        # Moving torch light
        offsets = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
        ox, oy = offsets.get(direction, (0, 0))
        lx = int(SCREEN_W // 2 + ox * t * SCREEN_W * 0.4)
        ly = int(SCREEN_H // 2 + oy * t * SCREEN_H * 0.4)
        pulse = (_math.sin(elapsed * 0.02) + 1) / 2
        radius = int(80 + 20 * pulse)
        glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        r, g, b = glow_color
        pygame.draw.circle(glow_surf, (r, g, b, 35), (radius, radius), radius)
        pygame.draw.circle(glow_surf, (r, g, b, 55), (radius, radius), radius // 2)
        screen.blit(glow_surf, (lx - radius, ly - radius))

        # Vignette fade at edges
        alpha = int(180 * (1 - abs(t - 0.5) * 2))
        fade = pygame.Surface((SCREEN_W, SCREEN_H))
        fade.fill((0, 0, 0))
        fade.set_alpha(max(0, 100 - alpha))
        screen.blit(fade, (0, 0))

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
