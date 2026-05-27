"""
Room-event logic extracted from main.py.
All functions take explicit state parameters (no module globals).
"""
import random
import pygame
import sys

from src.constants import QUEST_POOL, EQUIPMENT, COMPANION_ROLES, COMPANION_ROLE_DESCS
from src.entities import ENEMY_STATS, FLOOR_ENEMY_NAMES
from src.ui import show_msg, draw_hp_bar, flash_sprite, tint_sprite
from src.utils import sound


# ---------------------------------------------------------------------------
# Quest management
# ---------------------------------------------------------------------------

def assign_quests(player):
    """Pick 2 random quests from the pool and assign them for the current floor."""
    chosen = random.sample(QUEST_POOL, min(2, len(QUEST_POOL)))
    quests = []
    for q in chosen:
        goal = q["goal_mult"](player["floor"])
        quests.append({
            "id": q["id"],
            "desc": q["desc"],
            "type": q["type"],
            "goal": goal,
            "progress": 0,
            "completed": False,
            "reward_gold": q["reward_gold"],
            "reward_upgrade": q["reward_upgrade"],
        })
    player["quests"] = quests


def check_quests(player, event_type, screen, font, small_font, clock, upgrade_fn=None):
    """Update quest progress after a game event; grant rewards on completion."""
    for q in player.get("quests", []):
        if q.get("completed"):
            continue
        matched = False
        if q["type"] == event_type and event_type in ("kill", "explore", "no_damage", "no_potion", "noncombat"):
            q["progress"] += 1
            matched = q["progress"] >= q["goal"]
        elif q["type"] == "gold" and event_type == "gold":
            q["progress"] = player.get("floor_gold_earned", 0)
            matched = q["progress"] >= q["goal"]
        if matched:
            q["completed"] = True
            msg = f"Quest Complete: {q['desc'].format(goal=q['goal'])}!"
            if q["reward_gold"] > 0:
                player["gold"] += q["reward_gold"]
                player["floor_gold_earned"] = player.get("floor_gold_earned", 0) + q["reward_gold"]
                msg += f" +{q['reward_gold']}g"
            show_msg(screen, msg, font, small_font, clock)
            if q["reward_upgrade"] and upgrade_fn:
                upgrade_fn()


# ---------------------------------------------------------------------------
# Chest room
# ---------------------------------------------------------------------------

def chest_room(player, visited_rooms, current_room, screen, font, small_font, clock, upgrade_fn=None):
    gold_gain = random.randint(30, 60) + player["floor"] * 10
    gold_gain = int(gold_gain * player.get("_blessing_gold_mult", 1.0))
    player["gold"] += gold_gain
    player["floor_gold_earned"] = player.get("floor_gold_earned", 0) + gold_gain
    sound("coin")
    msg = f"You find a chest! Gained {gold_gain} gold!"
    if random.random() < 0.4:
        player["potions"] += 1
        msg += " And a Healing Potion!"
    if random.random() < 0.25:
        player["keys"] = player.get("keys", 0) + 1
        msg += " And a Key!"
    show_msg(screen, msg, font, small_font, clock)
    if random.random() < 0.20:
        all_equip = [item for items in EQUIPMENT.values() for item in items]
        found = random.choice(all_equip)
        slot = next(s for s, items in EQUIPMENT.items() if found in items)
        eq_owned = player.setdefault("equipment", {})
        if eq_owned.get(slot) != found["name"]:
            eq_owned[slot] = found["name"]
            found["apply"](player)
            show_msg(screen, f"Found equipment: {found['name']}! ({found['desc']})", font, small_font, clock)
    visited_rooms[current_room] = "cleared_chest"
    check_quests(player, "noncombat", screen, font, small_font, clock, upgrade_fn=upgrade_fn)
    check_quests(player, "gold", screen, font, small_font, clock)


# ---------------------------------------------------------------------------
# Puzzle room
# ---------------------------------------------------------------------------

def puzzle_room(player, visited_rooms, current_room, screen, font, small_font, clock, gain_xp_fn=None):
    from src.constants import SCREEN_W
    if visited_rooms.get(current_room) == "cleared_puzzle":
        show_msg(screen, "You've already solved this puzzle.", font, small_font, clock)
        return
    sequence = [random.choice(["Upper", "Middle", "Lower"]) for _ in range(3)]
    reveal_until = pygame.time.get_ticks() + 2500
    phase = "reveal"
    player_input = []

    while True:
        clock.tick(60)
        now = pygame.time.get_ticks()
        screen.fill((10, 10, 30))
        pygame.draw.rect(screen, (40, 30, 80), (100, 80, 760, 380))
        pygame.draw.rect(screen, (120, 80, 200), (100, 80, 760, 380), 3)
        title = font.render("PUZZLE ROOM  — Remember the sequence!", True, (200, 160, 255))
        screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 100))

        if phase == "reveal":
            countdown = max(0, (reveal_until - now) // 1000 + 1)
            for i, pos in enumerate(sequence):
                txt = font.render(f"{i+1}. {pos}", True, (255, 255, 100))
                screen.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, 190 + i * 60))
            hint = small_font.render(f"Memorize the sequence... ({countdown}s)", True, (180, 180, 180))
            screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 420))
            if now >= reveal_until:
                phase = "input"
        else:
            shown = small_font.render(f"Repeat: {' > '.join(player_input) or '?'}  ({len(player_input)}/3)", True, (200, 220, 200))
            screen.blit(shown, (SCREEN_W // 2 - shown.get_width() // 2, 220))
            hint = small_font.render("1 = Upper   2 = Middle   3 = Lower", True, (150, 150, 150))
            screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 360))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and phase == "input":
                key_map = {pygame.K_1: "Upper", pygame.K_2: "Middle", pygame.K_3: "Lower"}
                if event.key in key_map:
                    player_input.append(key_map[event.key])
                    if len(player_input) == 3:
                        if player_input == sequence:
                            xp_gain, gold_gain = 50, 40
                            player["gold"] += gold_gain
                            player["floor_gold_earned"] = player.get("floor_gold_earned", 0) + gold_gain
                            show_msg(screen, f"Correct! Puzzle solved! +{xp_gain} XP +{gold_gain}g", font, small_font, clock)
                            if gain_xp_fn:
                                gain_xp_fn(player, xp_gain, show_msg, screen, font, small_font, clock)
                        else:
                            player["hp"] = max(0, player["hp"] - 20)
                            show_msg(screen, "Wrong sequence! The trap springs! -20 HP", font, small_font, clock)
                        visited_rooms[current_room] = "cleared_puzzle"
                        check_quests(player, "noncombat", screen, font, small_font, clock)
                        return


# ---------------------------------------------------------------------------
# Miniboss room
# ---------------------------------------------------------------------------

def do_miniboss(player, visited_rooms, current_room, screen, font, small_font, clock,
               ng_plus_mult, fctx):
    from src.combat import fight
    mb_hp = int((200 + player["floor"] * 30) * ng_plus_mult)
    mb_name = f"Floor {player['floor']} Guardian"
    show_msg(screen, "A powerful guardian blocks your path!", font, small_font, clock)
    result = fight(
        screen, player,
        {"name": mb_name, "hp": mb_hp, "max_hp": mb_hp, "enrage_threshold": 0.4},
        fctx.battle_bg, fctx.player_img, fctx.dungeon_lord_img,
        font, small_font, clock, show_msg, draw_hp_bar, None, flash_sprite, tint_sprite,
        fctx.divine_fn, fctx.gain_xp_fn,
        fctx.use_potion_fn, fctx.use_str_fn, fctx.use_def_fn,
        fctx.play_battle_fn, fctx.play_explore_fn
    )
    if result:
        bonus_gold = int(random.randint(50, 80) * player.get("_blessing_gold_mult", 1.0))
        player["gold"] += bonus_gold
        player["gold_earned"] = player.get("gold_earned", 0) + bonus_gold
        player["floor_gold_earned"] = player.get("floor_gold_earned", 0) + bonus_gold
        player["potions"] += 1
        player["keys"] = player.get("keys", 0) + 1
        show_msg(screen, f"Guardian defeated! +{bonus_gold}g, a Healing Potion, and a Key!", font, small_font, clock)
        visited_rooms[current_room] = "cleared"
    return result


# ---------------------------------------------------------------------------
# Event room
# ---------------------------------------------------------------------------

def event_room(player, visited_rooms, current_room, screen, font, small_font, clock, fctx=None):
    from src.constants import SCREEN_W
    from src.combat import fight

    if visited_rooms.get(current_room) == "cleared_event":
        show_msg(screen, "This room is quiet now.", font, small_font, clock)
        return

    event_pool = ["ambush", "wandering_merchant", "dark_blessing", "cursed_shrine"]
    if player.get("companion") is None:
        event_pool.append("free_companion")
    chosen = random.choice(event_pool)

    if chosen == "ambush":
        show_msg(screen, "Ambush! A weakened enemy springs from the shadows!", font, small_font, clock)
        enemy_name = random.choice(FLOOR_ENEMY_NAMES.get(player["floor"], ["Dungeon Fiend"]))
        stats = ENEMY_STATS.get(enemy_name, {})
        e_hp = int((80 + player["floor"] * 25) * 0.5 * stats.get("hp_mult", 1.0))
        result = fight(
            screen, player,
            {"name": f"Ambush {enemy_name}", "hp": e_hp, "max_hp": e_hp,
             "atk_range": stats.get("atk_range", (12, 22)),
             "atk_weights": stats.get("atk_weights", [1, 1, 1]),
             "def_weights": stats.get("def_weights", [1, 1, 1])},
            fctx.battle_bg, fctx.player_img, fctx.enemy_img,
            font, small_font, clock, show_msg, draw_hp_bar, None, flash_sprite, tint_sprite,
            fctx.divine_fn, fctx.gain_xp_fn,
            fctx.use_potion_fn, fctx.use_str_fn, fctx.use_def_fn,
            fctx.play_battle_fn, fctx.play_explore_fn
        )
        if result:
            bonus = int(random.randint(20, 40) * 1.5 * player.get("_blessing_gold_mult", 1.0))
            player["gold"] += bonus
            player["floor_gold_earned"] = player.get("floor_gold_earned", 0) + bonus
            show_msg(screen, f"Bonus loot from the ambush! +{bonus}g", font, small_font, clock)
            check_quests(player, "kill", screen, font, small_font, clock)

    elif chosen == "wandering_merchant":
        show_msg(screen, "A wandering merchant offers a quick deal! (20% discount)", font, small_font, clock)
        disc_potions = [
            {"name": "Healing Potion (20% off)", "price": 20, "key": "potions"},
            {"name": "Strength Potion (20% off)", "price": 80, "key": "strength_potions"},
        ]
        waiting = True
        while waiting:
            clock.tick(60)
            screen.fill((20, 15, 30))
            title = font.render("Wandering Merchant", True, (255, 200, 80))
            screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 160))
            for i, item in enumerate(disc_potions):
                col = (255, 255, 255) if player["gold"] >= item["price"] else (100, 100, 100)
                txt = font.render(f"{i+1}. {item['name']}  {item['price']}g", True, col)
                screen.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2, 240 + i * 60))
            hint = small_font.render("1 / 2 to buy   ESC to leave", True, (120, 120, 120))
            screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 390))
            pygame.display.flip()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        waiting = False
                    elif ev.key in (pygame.K_1, pygame.K_2):
                        item = disc_potions[ev.key - pygame.K_1]
                        if player["gold"] >= item["price"]:
                            player["gold"] -= item["price"]
                            player[item["key"]] = player.get(item["key"], 0) + 1
                            show_msg(screen, f"Bought {item['name']}!", font, small_font, clock)
                        else:
                            show_msg(screen, "Not enough gold!", font, small_font, clock)
                        waiting = False
        check_quests(player, "noncombat", screen, font, small_font, clock)

    elif chosen == "dark_blessing":
        waiting = True
        while waiting:
            clock.tick(60)
            screen.fill((10, 10, 20))
            title = font.render("Dark Blessing — Choose your boon:", True, (180, 100, 255))
            screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 180))
            opt1 = font.render("1.  +20 Max HP  (permanent)", True, (100, 255, 100))
            opt2 = font.render("2.  +5 flat Attack bonus  (permanent)", True, (255, 150, 80))
            screen.blit(opt1, (SCREEN_W // 2 - opt1.get_width() // 2, 270))
            screen.blit(opt2, (SCREEN_W // 2 - opt2.get_width() // 2, 330))
            pygame.display.flip()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_1:
                        player["max_hp"] += 20
                        player["hp"] = min(player["hp"] + 20, player["max_hp"])
                        show_msg(screen, "Max HP increased by 20!", font, small_font, clock)
                        waiting = False
                    elif ev.key == pygame.K_2:
                        player["_atk_bonus"] = player.get("_atk_bonus", 0) + 5
                        show_msg(screen, "Attack bonus +5!", font, small_font, clock)
                        waiting = False
        check_quests(player, "noncombat", screen, font, small_font, clock)

    elif chosen == "cursed_shrine":
        player["hp"] = min(player["max_hp"], player["hp"] + 40)
        effect = random.choice(["poison", "bleed", "stun"])
        show_msg(screen, f"A cursed shrine heals 40 HP — but inflicts {effect.upper()} at your next fight!", font, small_font, clock)
        player[f"_pending_status_{effect}"] = True
        check_quests(player, "noncombat", screen, font, small_font, clock)

    else:  # free_companion
        from src.overworld_features import init_companion
        role = random.choice(COMPANION_ROLES)
        desc = COMPANION_ROLE_DESCS[role]
        show_msg(screen, "A small slime is trapped in a cage! You break it open.", font, small_font, clock)
        show_msg(screen, f"The slime bonds with you! Role: {role.upper()} — {desc}", font, small_font, clock)
        init_companion(player, role, screen.get_width() // 2, screen.get_height() // 2)
        check_quests(player, "noncombat", screen, font, small_font, clock)

    visited_rooms[current_room] = "cleared_event"
