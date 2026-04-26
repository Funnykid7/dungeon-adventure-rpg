import pygame
import sys
import random
import os
from src.constants import SCREEN_W, SCREEN_H, MAP_SIZE, ROOM_W, ROOM_H
from src.entities import classes, weapons

def draw_hud(screen, player, small_font):
    """Draws an expanded HUD at the top of the screen."""
    hud_rect = pygame.Rect(0, 0, SCREEN_W, 80)
    pygame.draw.rect(screen, (24, 24, 24), hud_rect)
    pygame.draw.line(screen, (200, 200, 200), (0, 80), (SCREEN_W, 80), 3)

    # Line 1: Basic Stats
    stats1 = [
        f"HP: {player['hp']}/{player['max_hp']}",
        f"LV: {player['level']}",
        f"FLR: {player['floor']}",
        f"GOLD: {player['gold']}"
    ]
    
    # Line 2: Potions & Shortcuts
    stats2 = [
        f"POT(P): {player['potions']}",
        f"STR(5): {player.get('strength_potions', 0)}",
        f"DEF(6): {player.get('defense_potions', 0)}",
        f"SAVE: HOME"
    ]

    x_pos = 30
    for stat in stats1:
        txt = small_font.render(stat, True, (255, 255, 255))
        screen.blit(txt, (x_pos, 15))
        x_pos += 220
    
    x_pos = 30
    for stat in stats2:
        txt = small_font.render(stat, True, (200, 200, 200))
        screen.blit(txt, (x_pos, 45))
        x_pos += 220

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
        # Fade In requires the screen to have been drawn once
        for alpha in range(255, -1, -speed):
            fade_surface.set_alpha(alpha)
            # This is tricky because we need to redraw the game world under it.
            # Usually fade in is handled in the main loop. 
            # For simplicity, we'll focus on fade out which is more important for transitions.
            pass 

def show_msg(screen, text, font, small_font, clock):
    """Displays a message in a dialogue box with a scrolling effect."""
    visible_chars = 0
    scroll_speed = 0.5 # Characters per frame
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
        txt_surface = font.render(current_text, True, (255, 255, 255))
        screen.blit(txt_surface, (30, SCREEN_H - 100))

        # Prompt
        if visible_chars >= len(text):
            prompt = small_font.render("Press any key to continue...", True, (150, 150, 150))
            screen.blit(prompt, (SCREEN_W - 220, SCREEN_H - 35))

        pygame.display.flip()
        clock.tick(60)

def draw_minimap(screen, visited_rooms, current_room, small_font):
    """Draws a 5x5 grid in the corner showing explored rooms."""
    MAP_X, MAP_Y = SCREEN_W - 160, SCREEN_H - 160
    CELL_SIZE = 25
    
    # Draw Background
    bg_rect = pygame.Rect(MAP_X - 10, MAP_Y - 10, (CELL_SIZE * 5) + 20, (CELL_SIZE * 5) + 40)
    pygame.draw.rect(screen, (20, 20, 20), bg_rect)
    pygame.draw.rect(screen, (150, 150, 150), bg_rect, 2)
    
    title = small_font.render("MINIMAP", True, (200, 200, 200))
    screen.blit(title, (MAP_X, MAP_Y - 30))

    for x in range(MAP_SIZE):
        for y in range(MAP_SIZE):
            rect = pygame.Rect(MAP_X + x * CELL_SIZE, MAP_Y + y * CELL_SIZE, CELL_SIZE - 2, CELL_SIZE - 2)
            
            # Room Status
            room_data = visited_rooms.get((x, y))
            
            if (x, y) == current_room:
                color = (255, 255, 0) # Player Current - Yellow
            elif room_data and "cleared" in room_data:
                color = (80, 80, 80) # Visited/Cleared - Gray
            else:
                color = (30, 30, 30) # Unvisited - Dark
                
            pygame.draw.rect(screen, color, rect)
            
            # Show icons
            txt = ""
            if room_data == "merchant": txt = "M"
            elif room_data == "exit": txt = "E"
            elif room_data == "boss": txt = "B"
            elif room_data == "shrine": txt = "S"
                
            if txt and (x, y) == current_room:
                char = small_font.render(txt, True, (0, 0, 0))
                screen.blit(char, (rect.x + 5, rect.y + 2))

def start_screen(screen, big_font, font, small_font, SAVE_FILE, load_game_func, intro_gui_func, show_msg_func, clock):
    """Initial screen to New Game or Load Game."""
    has_save = os.path.exists(SAVE_FILE)
    selected = 0 # 0 for New Game, 1 for Load Game
    
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
            
            # Ensure new potion keys exist for compatibility
            data.setdefault("strength_potions", 0)
            data.setdefault("defense_potions", 0)
            data.setdefault("strength_turns", 0)
            data.setdefault("defense_turns", 0)
            
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
        "last_attack": None
    }

def merchant_gui(screen, player, merchant_bg, font, small_font, show_msg_func, clock):
    clock = clock
    running = True
    menu_mode = "weapons" # or "potions"

    # Filter out Dagger and sort by bonus/price
    weapon_items = [(n, d) for n, d in weapons.items() if n != "Dagger"]
    potion_items = [
        {"name": "Healing Potion", "price": 25, "key": "potions", "desc": "Restores 40 HP"},
        {"name": "Strength Potion", "price": 100, "key": "strength_potions", "desc": "1.5x Dmg (5 turns)"},
        {"name": "Defense Potion", "price": 100, "key": "defense_potions", "desc": "0.5x Dmg Recv (5 turns)"}
    ]

    while running:
        clock.tick(60)
        screen.blit(merchant_bg, (0, 0))

        panel = pygame.Rect(60, 60, 900, 420)
        pygame.draw.rect(screen, (24, 24, 24), panel)
        pygame.draw.rect(screen, (200, 180, 120), panel, 4)

        title_str = "WEAPON SHOP" if menu_mode == "weapons" else "POTION SHOP"
        title = font.render(title_str, True, (255, 220, 120))
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 80))

        gold_txt = font.render(f"Gold: {player['gold']}", True, (255, 220, 120))
        screen.blit(gold_txt, (700, 100))

        y = 140
        if menu_mode == "weapons":
            current_bonus = weapons[player["weapon"]]["bonus"]
            for i, (name, data) in enumerate(weapon_items):
                is_downgrade = data["bonus"] < current_bonus
                is_owned = name == player["weapon"]
                
                if is_owned:
                    color = (100, 255, 100) # Green for owned
                    status = "(Equipped)"
                elif is_downgrade:
                    color = (255, 100, 100) # Red for downgrade
                    status = "(Downgrade)"
                elif player['gold'] >= data['price']:
                    color = (255, 255, 255)
                    status = f"- {data['price']}g"
                else:
                    color = (100, 100, 100)
                    status = f"- {data['price']}g"

                txt = f"{i+1}. {name} (+{data['bonus']} ATK) {status}"
                screen.blit(font.render(txt, True, color), (120, y))
                y += 40
        else:
            for i, item in enumerate(potion_items):
                color = (255, 255, 255) if player['gold'] >= item['price'] else (100, 100, 100)
                txt = f"{i+1}. {item['name']} - {item['price']}g ({item['desc']})"
                screen.blit(font.render(txt, True, color), (120, y))
                y += 40

        screen.blit(
            small_font.render("TAB - Switch Menu | ESC - Back", True, (200, 200, 200)),
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
                    menu_mode = "potions" if menu_mode == "weapons" else "weapons"

                elif pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    
                    if menu_mode == "weapons":
                        if idx < len(weapon_items):
                            name, data = weapon_items[idx]
                            current_bonus = weapons[player["weapon"]]["bonus"]
                            
                            if name == player["weapon"]:
                                show_msg_func(screen, "🛡️ You already own this weapon!", font, small_font, clock)
                            elif data["bonus"] < current_bonus:
                                show_msg_func(screen, "❌ This weapon is weaker than your current one!", font, small_font, clock)
                            elif player["gold"] >= data["price"]:
                                player["gold"] -= data["price"]
                                player["weapon"] = name
                                show_msg_func(screen, f"⚔️ Purchased {name}!", font, small_font, clock)
                            else:
                                show_msg_func(screen, "❌ Not enough gold!", font, small_font, clock)
                    else:
                        if idx < len(potion_items):
                            item = potion_items[idx]
                            if player["gold"] >= item["price"]:
                                player["gold"] -= item["price"]
                                key = item["key"]
                                player[key] = player.get(key, 0) + 1
                                show_msg_func(screen, f"🧪 Purchased {item['name']}!", font, small_font, clock)
                            else:
                                show_msg_func(screen, "❌ Not enough gold!", font, small_font, clock)

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
