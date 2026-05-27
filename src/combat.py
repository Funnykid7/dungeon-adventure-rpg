import pygame
import random
import sys
from src.constants import FLASH_DURATION, SCREEN_H, SCREEN_W
from src.entities import classes, weapons
from src.utils import sound

def fight(screen, player, enemy, battle_bg, player_img, enemy_img, font, small_font, clock, 
          show_msg_func, draw_hp_bar_func, show_battle_messages_func, 
          flash_sprite_func, tint_sprite_func, divine_intervention_func, 
          gain_xp_func, use_potion_func, use_strength_potion_func, use_defense_potion_func,
          play_battle_music_func, play_explore_music_func):
    
    global battle_messages, waiting_for_input, skip_timer

    play_battle_music_func()

    # Blood Pact curse: lose HP at fight start
    if player.get("_curse_combat_start_dmg", 0) > 0:
        player["hp"] -= player["_curse_combat_start_dmg"]

    # Cursed Shrine pending status effects (applied at next fight)
    for status in ("poison", "bleed", "stun"):
        key = f"_pending_status_{status}"
        if player.pop(key, False):
            if status == "poison":
                player_statuses["poison"] = 3
            elif status == "bleed":
                player_statuses["bleed"] = 3
            elif status == "stun":
                player_statuses["stun"] = 1

    waiting_for_input = False
    battle_messages = []
    skip_timer = 0

    player_flash_timer = 0
    enemy_flash_timer = 0
    player_anim_timer = 0
    enemy_anim_timer = 0
    msg_char_index = 0
    scroll_speed = 0.5

    shake_timer = 0
    shake_x, shake_y = 0, 0
    damage_numbers = []
    death_anim_timer = 0
    crit_flash_timer = 0
    boss_turn_counter = 0
    malice_warning = False
    enemy_enraged = False
    enrage_threshold = enemy["max_hp"] // 2
    phase2_triggered = False

    # Status effects on player: {name: turns_remaining}
    player_statuses = {}  # "poison":3, "stun":1, "bleed":4
    player_stunned = False   # consumed each defend phase
    blessing_free_dodge_used = False  # Guardian Spirit — first dodge per fight

    # Class active ability
    ability_used = False
    ability_active = {}      # flags set by ability (smoke_screen, aimed_shot, etc.)
    monk_consecutive = 0     # tracks consecutive same-position attacks for Momentum

    running = True
    action = None
    attack_pos = None
    defense_mode = False
    enemy_attack_pos = None

    while running and (enemy["hp"] > 0 or death_anim_timer > 0) and player["hp"] > 0:
        clock.tick(60)
        current_time = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if waiting_for_input:
                    if current_time > skip_timer:
                        if battle_messages:
                            msg = battle_messages[0]
                            if msg_char_index < len(msg):
                                msg_char_index = len(msg)
                            else:
                                battle_messages.pop(0)
                                msg_char_index = 0
                                skip_timer = current_time + 400
                        if not battle_messages:
                            waiting_for_input = False
                    continue

                if defense_mode:
                    if event.key == pygame.K_1:
                        def_pos = "upper"
                    elif event.key == pygame.K_2:
                        def_pos = "middle"
                    elif event.key == pygame.K_3:
                        def_pos = "lower"
                    else: continue

                    battle_messages.append(f"You braced for an {def_pos.upper()} attack!")
                    enemy_anim_timer = 15 # Start enemy lunge
                    if def_pos == enemy_attack_pos:
                        battle_messages.append("🛡️ PERFECT BLOCK! Damage negated!")
                        enemy_dmg = 0
                        # Iron Fortress: reflect on perfect block
                        reflect = player.get("_reflect_dmg", 0)
                        if reflect > 0 and enemy["hp"] > 0:
                            enemy["hp"] = max(0, enemy["hp"] - reflect)
                            enemy_flash_timer = FLASH_DURATION
                            battle_messages.append(f"⚔️ Iron Fortress reflects {reflect} damage!")
                    else:
                        battle_messages.append(f"❌ Wrong stance! The attack was {enemy_attack_pos.upper()}!")
                        enemy_dmg = random.randint(*enemy.get("atk_range", (12, 22))) + player["floor"] * 3
                        if player.get("defense_turns", 0) > 0:
                            enemy_dmg = int(enemy_dmg * 0.5)
                            battle_messages.append("🛡️ Potion reduced the impact!")
                        if player["class"] == "warrior": enemy_dmg = int(enemy_dmg * 0.8)
                        if enemy_enraged: enemy_dmg = int(enemy_dmg * 1.25)
                        enemy_dmg = int(enemy_dmg * (1 - player.get("_dmg_reduce", 0)))
                        # Smoke Screen: guaranteed dodge this hit
                        if ability_active.pop("smoke_screen", False):
                            battle_messages.append("💨 SMOKE SCREEN dodges the hit!")
                            sound("dodge")
                            enemy_dmg = 0
                        else:
                            # Guardian Spirit: first dodge per combat is guaranteed
                            guardian_free = (player.get("_blessing_free_dodge") and not blessing_free_dodge_used)
                            dodge_chance = (0.25 if player["class"] == "rogue" else 0) + player.get("_dodge_bonus", 0)
                            if enemy_dmg > 0 and (guardian_free or (dodge_chance > 0 and random.random() < dodge_chance)):
                                if guardian_free:
                                    battle_messages.append("✨ GUARDIAN SPIRIT! The first dodge is guaranteed!")
                                    blessing_free_dodge_used = True
                                else:
                                    battle_messages.append("💨 DODGE! You evaded the attack!")
                                sound("dodge")
                                enemy_dmg = 0
                        # Apply status effect on hit (Lucky Charm reduces proc chance)
                        if enemy_dmg > 0:
                            resist = player.get("_status_resist", 0)
                            for status, chance in enemy.get("status_chance", {}).items():
                                effective_chance = chance * (1 - resist)
                                is_elite_first_hit = enemy.get("elite") and not enemy.get("_elite_status_fired")
                                if is_elite_first_hit or random.random() < effective_chance:
                                    if is_elite_first_hit:
                                        enemy["_elite_status_fired"] = True
                                    if status == "poison" and player_statuses.get("poison", 0) == 0:
                                        player_statuses["poison"] = 3
                                        battle_messages.append("☠️ You are POISONED! (-8 HP for 3 turns)")
                                    elif status == "stun" and player_statuses.get("stun", 0) == 0:
                                        player_statuses["stun"] = 1
                                        battle_messages.append("💫 You are STUNNED! Next attack skipped!")
                                    elif status == "bleed":
                                        player_statuses["bleed"] = min(4, player_statuses.get("bleed", 0) + 2)
                                        battle_messages.append("🩸 You are BLEEDING! (-5 HP per turn)")

                    if enemy_dmg > 0:
                        sound("player_hit")
                        player["hp"] -= enemy_dmg
                        player_flash_timer = FLASH_DURATION
                        shake_timer = 8
                        damage_numbers.append({"x": 200, "y": 280, "value": enemy_dmg, "color": (255, 180, 80), "timer": 40})
                        battle_messages.append(f"Enemy hit you for {enemy_dmg} damage!")

                    defense_mode = False
                    enemy_attack_pos = None
                    skip_timer = current_time + 400
                    continue

                if event.key == pygame.K_1:
                    action = "attack"
                    attack_pos = "upper"
                elif event.key == pygame.K_2:
                    action = "attack"
                    attack_pos = "middle"
                elif event.key == pygame.K_3:
                    action = "attack"
                    attack_pos = "lower"
                elif event.key == pygame.K_4:
                    if use_potion_func(player, show_msg_func, screen, font, small_font, clock, in_combat=True):
                        action = "potion"
                        sound("potion")
                        battle_messages.append("🧪 You used a potion!")
                        skip_timer = current_time + 400
                elif event.key == pygame.K_5:
                    if use_strength_potion_func(player, show_msg_func, screen, font, small_font, clock, in_combat=True):
                        action = "potion"
                        sound("potion")
                        battle_messages.append("💪 Strength boosted!")
                        skip_timer = current_time + 400
                elif event.key == pygame.K_6:
                    if use_defense_potion_func(player, show_msg_func, screen, font, small_font, clock, in_combat=True):
                        action = "potion"
                        sound("potion")
                        battle_messages.append("🛡️ Defense boosted!")
                        skip_timer = current_time + 400
                elif event.key == pygame.K_7 and not ability_used:
                    pc = player["class"]
                    ability_used = True
                    if pc == "warrior":
                        ability_active["force_lower"] = True
                        battle_messages.append("🛡️ SHIELD BASH! Enemy forced to attack Lower next turn!")
                    elif pc == "mage":
                        dmg = int(random.randint(*classes[pc]["attack"]) * 2.5 + weapons[player["weapon"]]["bonus"])
                        enemy["hp"] = max(0, enemy["hp"] - dmg)
                        damage_numbers.append({"x": 620, "y": 180, "value": dmg, "color": (100, 180, 255), "timer": 50})
                        enemy_flash_timer = FLASH_DURATION
                        shake_timer = 10
                        sound("crit")
                        battle_messages.append(f"✨ ARCANE BLAST! {dmg} unblockable magic damage!")
                        if enemy["hp"] <= 0:
                            enemy["hp"] = 0
                            death_anim_timer = 20
                            sound("enemy_death")
                        action = "ability_no_turn"
                    elif pc == "rogue":
                        ability_active["smoke_screen"] = True
                        battle_messages.append("💨 SMOKE SCREEN! Next hit guaranteed dodge!")
                    elif pc == "paladin":
                        heal = int(player["max_hp"] * 0.4)
                        player["hp"] = min(player["max_hp"], player["hp"] + heal)
                        sound("heal")
                        battle_messages.append(f"✨ HOLY LIGHT! Restored {heal} HP!")
                        action = "ability_no_turn"
                    elif pc == "ranger":
                        ability_active["aimed_shot"] = True
                        battle_messages.append("🎯 AIMED SHOT! Next attack will auto-hit!")
                    elif pc == "monk":
                        ability_active["focus_strike"] = True
                        battle_messages.append("🥋 FOCUS STRIKE! Next attack is a guaranteed combo!")
                    skip_timer = current_time + 400
                elif event.key == pygame.K_7 and ability_used:
                    battle_messages.append("⚠️ Ability already used this fight!")
                    skip_timer = current_time + 400

        if action == "attack":
            battle_messages.clear()
            # Stun: skip attack phase but still defend
            if player_statuses.get("stun", 0) > 0:
                player_statuses["stun"] -= 1
                battle_messages.append("💫 STUNNED! You couldn't attack this turn!")
            else:
                battle_messages.append(f"You used {attack_pos.upper()} attack!")
                player_anim_timer = 15  # Start player lunge

                # Aimed Shot: bypass enemy block
                auto_hit = ability_active.pop("aimed_shot", False)
                # Shadow Step: first attack guaranteed (only first time)
                if player.get("_shadow_step") and not player.get("_shadow_step_used"):
                    auto_hit = True
                    player["_shadow_step_used"] = True

                enemy_def_pos = random.choices(["upper", "middle", "lower"], weights=enemy.get("def_weights", [1, 1, 1]))[0]
                if attack_pos == enemy_def_pos and not auto_hit:
                    battle_messages.append(f"🛡️ Enemy blocked your {attack_pos.upper()} attack!")
                else:
                    if auto_hit and attack_pos == enemy_def_pos:
                        battle_messages.append("🎯 AIMED SHOT cuts through the block!")
                    dmg = random.randint(*classes[player["class"]]["attack"])
                    dmg += (weapons[player["weapon"]]["bonus"] + player["level"] * 3
                            + player.get("_atk_bonus", 0)
                            + player.get("_companion_atk_bonus", 0))
                    if player.get("strength_turns", 0) > 0: dmg = int(dmg * 1.5)
                    if player["class"] == "mage" and attack_pos == "upper": dmg = int(dmg * 1.3)
                    # Curse/blessing attack multipliers
                    dmg = int(dmg * player.get("_curse_atk_mult", 1.0) * player.get("_blessing_atk_mult", 1.0))
                    # Arcane Surge: every 3rd upper attack auto-crits
                    mage_crit = (player.get("_arcane_surge") and attack_pos == "upper"
                                 and player.get("_arcane_surge_count", 0) % 3 == 2)
                    if mage_crit:
                        player["_arcane_surge_count"] = 0
                    elif player.get("_arcane_surge") and attack_pos == "upper":
                        player["_arcane_surge_count"] = player.get("_arcane_surge_count", 0) + 1
                    if player["class"] == "ranger" and (mage_crit or random.random() < (0.40 if player.get("_eagle_eye") else 0.25)):
                        dmg = int(dmg * 1.6)
                        crit_flash_timer = 5
                        sound("crit")
                        battle_messages.append("🎯 CRITICAL HIT!")
                    elif mage_crit:
                        dmg = int(dmg * 1.6)
                        crit_flash_timer = 5
                        sound("crit")
                        battle_messages.append("✨ ARCANE SURGE — Auto-crit!")
                    # Monk Momentum
                    if player["class"] == "monk" and player.get("last_attack") == attack_pos:
                        monk_consecutive += 1
                        if player.get("_momentum") and monk_consecutive >= 2:
                            dmg = int(dmg * 1.8)
                            battle_messages.append("🥋 MOMENTUM — MAX COMBO!")
                        else:
                            dmg = int(dmg * 1.4)
                            battle_messages.append("🥋 COMBO STRIKE!")
                    elif player["class"] == "monk":
                        monk_consecutive = 0
                    # Focus Strike
                    if ability_active.pop("focus_strike", False):
                        dmg = int(dmg * 1.4)
                        battle_messages.append("🥋 FOCUS STRIKE activated!")
                    # Warrior Iron Fortress reflect (applied after enemy hits, tracked here for clarity)
                    # (reflection is applied in defend phase)

                    sound("enemy_hit")
                    enemy["hp"] -= dmg
                    enemy_flash_timer = FLASH_DURATION
                    shake_timer = 8
                    damage_numbers.append({"x": 620, "y": 180, "value": dmg, "color": (255, 80, 80), "timer": 40})
                    battle_messages.append(f"💥 Dealt {dmg} damage!")

                    # Lifesteal (Ring of Vampirism)
                    if player.get("_lifesteal", 0) > 0:
                        ls_heal = max(1, int(dmg * player["_lifesteal"]))
                        player["hp"] = min(player["max_hp"], player["hp"] + ls_heal)
                        damage_numbers.append({"x": 200, "y": 240, "value": ls_heal, "color": (80, 255, 120), "timer": 40})

                    if enemy["hp"] <= 0:
                        enemy["hp"] = 0
                        death_anim_timer = 20
                        sound("enemy_death")

                    # Generic enrage at threshold (Dungeon Lord at 50%, others via enrage_threshold key)
                    e_threshold = enemy.get("enrage_threshold", 0.5 if enemy["name"] == "Dungeon Lord" else None)
                    if (e_threshold and not enemy_enraged and 0 < enemy["hp"] <= int(enemy["max_hp"] * e_threshold)):
                        enemy_enraged = True
                        shake_timer = 20
                        if enemy["name"] == "Dungeon Lord":
                            battle_messages.append("💀 THE DUNGEON LORD ENRAGES!")
                            battle_messages.append("\"Enough games... I'll END you myself!\"")
                        else:
                            battle_messages.append(f"⚠️ {enemy['name']} ENRAGES! It adapts to your attacks!")

            player["last_attack"] = attack_pos
            if player["class"] == "paladin" and player["hp"] > 0 and random.random() < 0.4:
                if player.get("_sacred_heal_bonus"):
                    heal = random.randint(15, 30)
                elif player.get("_sacred_ground"):
                    heal = random.randint(10, 25)
                else:
                    heal = random.randint(6, 15)
                player["hp"] = min(player["max_hp"], player["hp"] + heal)
                battle_messages.append(f"✨ Paladin heals {heal} HP!")

            # Malice Surge (Dungeon Lord only)
            if enemy["name"] in ("Dungeon Lord", "Dungeon Lord — Phase 2") and enemy["hp"] > 0:
                surge_interval = 1 if phase2_triggered else (2 if enemy_enraged else 3)
                boss_turn_counter += 1
                if boss_turn_counter % surge_interval == surge_interval - 1:
                    battle_messages.append("⚠️ The Dungeon Lord begins to channel dark energy...")
                    malice_warning = True
                elif boss_turn_counter % surge_interval == 0 and malice_warning:
                    surge_dmg = random.randint(20, 35)
                    player["hp"] -= surge_dmg
                    player_flash_timer = FLASH_DURATION
                    shake_timer = 12
                    damage_numbers.append({"x": 200, "y": 260, "value": surge_dmg, "color": (180, 0, 255), "timer": 40})
                    battle_messages.append(f"💀 MALICE SURGE! {surge_dmg} unblockable damage!")
                    malice_warning = False

            # Boss Phase 2 at 25% HP
            if (enemy["name"] == "Dungeon Lord" and not phase2_triggered
                    and 0 < enemy["hp"] <= enemy["max_hp"] // 4):
                phase2_triggered = True
                enemy["name"] = "Dungeon Lord — Phase 2"
                shake_timer = 25
                battle_messages.append("\"You think you've WON? I am UNDYING!\"")
                battle_messages.append("💀 PHASE 2 — Malice Surge now fires EVERY turn!")

            # Status DoT: poison and bleed tick each turn
            dot_total = 0
            for status in ("poison", "bleed"):
                if player_statuses.get(status, 0) > 0:
                    dmg_s = 8 if status == "poison" else 5
                    player["hp"] -= dmg_s
                    dot_total += dmg_s
                    player_statuses[status] -= 1
                    icon = "☠️" if status == "poison" else "🩸"
                    battle_messages.append(f"{icon} {status.capitalize()} deals {dmg_s} damage! ({player_statuses[status]} turns left)")
            if dot_total > 0:
                player_flash_timer = FLASH_DURATION
                damage_numbers.append({"x": 200, "y": 300, "value": dot_total, "color": (80, 200, 80), "timer": 40})

            # Prepare Enemy turn
            if enemy["hp"] > 0:
                atk_w = list(enemy.get("atk_weights", [1, 1, 1]))
                # Enraged miniboss adapts toward player's last attack
                if enemy_enraged and player.get("last_attack") and enemy["name"] != "Dungeon Lord — Phase 2":
                    pos_idx = {"upper": 0, "middle": 1, "lower": 2}.get(player["last_attack"], -1)
                    if pos_idx >= 0:
                        atk_w[pos_idx] += 2
                if ability_active.get("force_lower"):
                    del ability_active["force_lower"]
                    enemy_attack_pos = "lower"
                else:
                    enemy_attack_pos = random.choices(["upper", "middle", "lower"], weights=atk_w)[0]
                defense_mode = True

            player["strength_turns"] = max(0, player.get("strength_turns", 0) - 1)
            player["defense_turns"] = max(0, player.get("defense_turns", 0) - 1)
            action = None
            attack_pos = None
            skip_timer = current_time + 400

        elif action == "potion":
            if enemy["hp"] > 0:
                enemy_attack_pos = random.choices(["upper", "middle", "lower"], weights=enemy.get("atk_weights", [1, 1, 1]))[0]
                defense_mode = True

            if enemy["name"] in ("Dungeon Lord", "Dungeon Lord — Phase 2") and enemy["hp"] > 0:
                surge_interval = 1 if phase2_triggered else (2 if enemy_enraged else 3)
                boss_turn_counter += 1
                if boss_turn_counter % surge_interval == surge_interval - 1:
                    battle_messages.append("⚠️ The Dungeon Lord begins to channel dark energy...")
                    malice_warning = True
                elif boss_turn_counter % surge_interval == 0 and malice_warning:
                    surge_dmg = random.randint(20, 35)
                    player["hp"] -= surge_dmg
                    player_flash_timer = FLASH_DURATION
                    shake_timer = 12
                    damage_numbers.append({"x": 200, "y": 260, "value": surge_dmg, "color": (180, 0, 255), "timer": 40})
                    battle_messages.append(f"💀 MALICE SURGE! {surge_dmg} unblockable damage!")
                    malice_warning = False

            player["strength_turns"] = max(0, player.get("strength_turns", 0) - 1)
            player["defense_turns"] = max(0, player.get("defense_turns", 0) - 1)
            action = None
            skip_timer = current_time + 400

        elif action == "ability_no_turn":
            # Instant abilities (Arcane Blast, Holy Light) — no defend phase triggered
            player["strength_turns"] = max(0, player.get("strength_turns", 0) - 1)
            player["defense_turns"] = max(0, player.get("defense_turns", 0) - 1)
            action = None
            skip_timer = current_time + 400

        # Draw
        # Shake offset calculation
        if shake_timer > 0:
            shake_x = random.randint(-4, 4)
            shake_y = random.randint(-4, 4)
            shake_timer -= 1
        else:
            shake_x, shake_y = 0, 0

        screen.blit(battle_bg, (shake_x, shake_y))

        # Animation offsets
        p_off = 0
        if player_anim_timer > 0:
            p_off = player_anim_timer * 4
            player_anim_timer -= 1

        e_off = 0
        if enemy_anim_timer > 0:
            e_off = enemy_anim_timer * 4
            enemy_anim_timer -= 1

        # Player Indicators
        if player.get("strength_turns", 0) > 0:
            str_txt = small_font.render(f"STR ↑ ({player['strength_turns']})", True, (255, 100, 100))
            screen.blit(str_txt, (120 + shake_x, 460 + shake_y))
        if player.get("defense_turns", 0) > 0:
            def_txt = small_font.render(f"DEF ↑ ({player['defense_turns']})", True, (100, 100, 255))
            screen.blit(def_txt, (120 + shake_x, 485 + shake_y))

        if player_flash_timer > 0:
            screen.blit(tint_sprite_func(player_img, (180, 0, 0)), (120 + p_off + shake_x, 200 + shake_y))
            player_flash_timer -= 1
        else:
            screen.blit(player_img, (120 + p_off + shake_x, 200 + shake_y))

        # Enemy sprite: death animation, flash, or normal
        base_enemy_img = tint_sprite_func(enemy_img, (80, 0, 20)) if enemy_enraged else enemy_img
        if death_anim_timer > 0:
            death_img = base_enemy_img.copy()
            death_img.set_alpha(int((death_anim_timer / 20) * 255))
            dx = random.randint(-6, 6) if death_anim_timer > 5 else 0
            screen.blit(death_img, (600 - e_off + shake_x + dx, 80 + shake_y))
            death_anim_timer -= 1
            waiting_for_input = True
        elif enemy_flash_timer > 0:
            screen.blit(tint_sprite_func(base_enemy_img, (180, 0, 0)), (600 - e_off + shake_x, 80 + shake_y))
            enemy_flash_timer -= 1
        else:
            screen.blit(base_enemy_img, (600 - e_off + shake_x, 80 + shake_y))

        draw_hp_bar_func(screen, 180 + shake_x, 180 + shake_y, 120, 12, player["hp"], player["max_hp"], (80, 200, 80))
        screen.blit(font.render(player["name"], True, (255, 255, 255)), (180 + shake_x, 150 + shake_y))
        draw_hp_bar_func(screen, 620 + shake_x, 75 + shake_y, 120, 12, enemy["hp"], enemy["max_hp"], (220, 80, 80))
        screen.blit(font.render(enemy["name"], True, (255, 120, 120)), (570 + shake_x, 40 + shake_y))

        # Floating damage numbers
        for dn in damage_numbers[:]:
            dn["y"] -= 1
            dn["timer"] -= 1
            dmg_surf = small_font.render(f"-{dn['value']}", True, dn["color"])
            dmg_surf.set_alpha(min(255, dn["timer"] * 8))
            screen.blit(dmg_surf, (dn["x"] + shake_x, dn["y"] + shake_y))
            if dn["timer"] <= 0:
                damage_numbers.remove(dn)

        # Critical hit white flash (battle area only)
        if crit_flash_timer > 0:
            white_overlay = pygame.Surface((SCREEN_W, SCREEN_H - 140))
            white_overlay.fill((255, 255, 255))
            white_overlay.set_alpha(80)
            screen.blit(white_overlay, (0, 0))
            crit_flash_timer -= 1

        # Message box and HUD drawn without shake offset
        pygame.draw.rect(screen, (20, 20, 20), (0, SCREEN_H - 140, SCREEN_W, 140))
        pygame.draw.rect(screen, (200, 200, 200), (0, SCREEN_H - 140, SCREEN_W, 140), 4)

        if battle_messages:
            waiting_for_input = True
            msg = battle_messages[0]
            if msg_char_index < len(msg):
                msg_char_index += scroll_speed

            txt = font.render(msg[:int(msg_char_index)], True, (255, 255, 255))
            screen.blit(txt, (30, SCREEN_H - 110))

            if current_time < skip_timer:
                wait_txt = small_font.render("Wait...", True, (100, 100, 100))
                screen.blit(wait_txt, (SCREEN_W - 100, SCREEN_H - 30))
            else:
                cont_txt = small_font.render("Press any key to continue", True, (150, 150, 150))
                screen.blit(cont_txt, (SCREEN_W - 250, SCREEN_H - 30))
        else:
            waiting_for_input = False
            msg_char_index = 0
        if not waiting_for_input:
            if defense_mode:
                cmd_txt = font.render("🛡️ DEFEND! 1-High   2-Mid   3-Low", True, (120, 220, 255))
                screen.blit(cmd_txt, (30, SCREEN_H - 45))
            else:
                ability_names = {"warrior":"Shield Bash","mage":"Arcane Blast","rogue":"Smoke Screen",
                                 "paladin":"Holy Light","ranger":"Aimed Shot","monk":"Focus Strike"}
                ab_name = ability_names.get(player["class"], "Ability")
                ab_label = f"[USED] {ab_name}" if ability_used else f"7-{ab_name}"
                ab_color = (100, 100, 100) if ability_used else (255, 180, 50)
                cmd_txt = font.render("⚔️ 1-Upper  2-Mid  3-Lower  4-Heal  5-Str  6-Def", True, (255, 220, 120))
                ab_txt  = small_font.render(ab_label, True, ab_color)
                screen.blit(cmd_txt, (30, SCREEN_H - 45))
                screen.blit(ab_txt,  (30, SCREEN_H - 22))
                # Show active statuses
                status_x = SCREEN_W - 200
                for si, (sname, sturns) in enumerate(player_statuses.items()):
                    if sturns > 0:
                        icons = {"poison": "☠️", "stun": "💫", "bleed": "🩸"}
                        s_txt = small_font.render(f"{icons.get(sname,'?')} {sname.capitalize()} ({sturns})", True, (220, 80, 80))
                        screen.blit(s_txt, (status_x, SCREEN_H - 45 + si * 18))
        
        pygame.display.flip()

        if player["hp"] <= 0 and divine_intervention_func(player, show_msg_func, screen, font, small_font, clock):
            battle_messages.append("✨ DIVINE INTERVENTION!")
            continue

    if player["hp"] > 0:
        xp = int((25 + player["floor"] * 10) * (1 + player.get("_xp_bonus", 0)))
        gold_mult = player.get("_blessing_gold_mult", 1.0)
        gold = int((random.randint(15, 30) + player["floor"] * 5 + player.get("_gold_bonus", 0)) * gold_mult)
        show_msg_func(screen, f"🏆 Victory! Gained {xp} XP and {gold} gold!", font, small_font, clock)
        gain_xp_func(player, xp, show_msg_func, screen, font, small_font, clock)
        player["gold"] += gold
        player["gold_earned"] = player.get("gold_earned", 0) + gold
        player["floor_gold_earned"] = player.get("floor_gold_earned", 0) + gold
        player["enemies_killed"] = player.get("enemies_killed", 0) + 1
        
        pygame.mixer.music.fadeout(500)
        play_explore_music_func()
        return True # Victory
    
    pygame.mixer.music.fadeout(500)
    play_explore_music_func()
    return False # Defeat
