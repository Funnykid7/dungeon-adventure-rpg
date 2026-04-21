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
    
    waiting_for_input = False
    battle_messages = []
    skip_timer = 0
    
    player_flash_timer = 0
    enemy_flash_timer = 0

    running = True
    action = None
    attack_pos = None
    defense_mode = False
    enemy_attack_pos = None

    while running and enemy["hp"] > 0 and player["hp"] > 0:
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
                            battle_messages.pop(0)
                            skip_timer = current_time + 800 # 1.5s delay between pops
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
                    if def_pos == enemy_attack_pos:
                        battle_messages.append("🛡️ PERFECT BLOCK! Damage negated!")
                        enemy_dmg = 0
                    else:
                        battle_messages.append(f"❌ Wrong stance! The attack was {enemy_attack_pos.upper()}!")
                        enemy_dmg = random.randint(12, 22) + player["floor"] * 3
                        if player.get("defense_turns", 0) > 0:
                            enemy_dmg = int(enemy_dmg * 0.5)
                            battle_messages.append("🛡️ Potion reduced the impact!")
                        if player["class"] == "warrior": enemy_dmg = int(enemy_dmg * 0.8)
                    
                    if enemy_dmg > 0:
                        player["hp"] -= enemy_dmg
                        player_flash_timer = FLASH_DURATION
                        battle_messages.append(f"Enemy hit you for {enemy_dmg} damage!")
                    
                    defense_mode = False
                    enemy_attack_pos = None
                    skip_timer = current_time + 800
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
                        battle_messages.append("🧪 You used a potion!")
                        skip_timer = current_time + 800
                elif event.key == pygame.K_5:
                    if use_strength_potion_func(player, show_msg_func, screen, font, small_font, clock, in_combat=True):
                        action = "potion"
                        battle_messages.append("💪 Strength boosted!")
                        skip_timer = current_time + 800
                elif event.key == pygame.K_6:
                    if use_defense_potion_func(player, show_msg_func, screen, font, small_font, clock, in_combat=True):
                        action = "potion"
                        battle_messages.append("🛡️ Defense boosted!")
                        skip_timer = current_time + 800

        if action == "attack":
            battle_messages.clear()
            battle_messages.append(f"You used {attack_pos.upper()} attack!")
            
            enemy_def_pos = random.choice(["upper", "middle", "lower"])
            if attack_pos == enemy_def_pos:
                battle_messages.append(f"🛡️ Enemy blocked your {attack_pos.upper()} attack!")
            else:
                dmg = random.randint(*classes[player["class"]]["attack"])
                dmg += weapons[player["weapon"]]["bonus"] + player["level"] * 3
                if player.get("strength_turns", 0) > 0: dmg = int(dmg * 1.5)
                if player["class"] == "mage" and attack_pos == "upper": dmg = int(dmg * 1.3)
                if player["class"] == "ranger" and random.random() < 0.25:
                    dmg = int(dmg * 1.6)
                    battle_messages.append("🎯 CRITICAL HIT!")
                if player["class"] == "monk" and player.get("last_attack") == attack_pos:
                    dmg = int(dmg * 1.4)
                    battle_messages.append("🥋 COMBO STRIKE!")

                enemy["hp"] -= dmg
                enemy_flash_timer = FLASH_DURATION
                battle_messages.append(f"💥 Dealt {dmg} damage!")
            
            player["last_attack"] = attack_pos
            if player["class"] == "paladin" and player["hp"] > 0 and random.random() < 0.4:
                heal = random.randint(6, 15)
                player["hp"] = min(player["max_hp"], player["hp"] + heal)
                battle_messages.append(f"✨ Paladin heals {heal} HP!")

            # Prepare Enemy turn
            if enemy["hp"] > 0:
                enemy_attack_pos = random.choice(["upper", "middle", "lower"])
                defense_mode = True
            
            player["strength_turns"] = max(0, player.get("strength_turns", 0) - 1)
            player["defense_turns"] = max(0, player.get("defense_turns", 0) - 1)
            action = None
            attack_pos = None
            skip_timer = current_time + 800

        elif action == "potion":
            if enemy["hp"] > 0:
                enemy_attack_pos = random.choice(["upper", "middle", "lower"])
                defense_mode = True
            
            player["strength_turns"] = max(0, player.get("strength_turns", 0) - 1)
            player["defense_turns"] = max(0, player.get("defense_turns", 0) - 1)
            action = None
            skip_timer = current_time + 800

        # Draw
        screen.blit(battle_bg, (0, 0))
        
        # Player Indicators
        if player.get("strength_turns", 0) > 0:
            str_txt = small_font.render(f"STR ↑ ({player['strength_turns']})", True, (255, 100, 100))
            screen.blit(str_txt, (120, 460))
        if player.get("defense_turns", 0) > 0:
            def_txt = small_font.render(f"DEF ↑ ({player['defense_turns']})", True, (100, 100, 255))
            screen.blit(def_txt, (120, 485))

        if player_flash_timer > 0:
            screen.blit(flash_sprite_func(player_img), (120, 200))
            player_flash_timer -= 1
        else:
            screen.blit(player_img, (120, 200))

        if enemy_flash_timer > 0:
            screen.blit(tint_sprite_func(enemy_img, (180, 0, 0)), (600, 80))
            enemy_flash_timer -= 1
        else:
            screen.blit(enemy_img, (600, 80))

        draw_hp_bar_func(screen, 180, 180, 120, 12, player["hp"], player["max_hp"], (80, 200, 80))
        screen.blit(font.render(player["name"], True, (255,255,255)), (180, 150))
        draw_hp_bar_func(screen, 620, 75, 120, 12, enemy["hp"], enemy["max_hp"], (220, 80, 80))
        screen.blit(font.render(enemy["name"], True, (255,120,120)), (570, 40))

        pygame.draw.rect(screen, (20, 20, 20), (0, SCREEN_H - 140, SCREEN_W, 140))
        pygame.draw.rect(screen, (200, 200, 200), (0, SCREEN_H - 140, SCREEN_W, 140), 4)

        if battle_messages:
            waiting_for_input = True
            txt = font.render(battle_messages[0], True, (255, 255, 255))
            screen.blit(txt, (30, SCREEN_H - 110))
            if current_time < skip_timer:
                wait_txt = small_font.render("Wait...", True, (100, 100, 100))
                screen.blit(wait_txt, (SCREEN_W - 100, SCREEN_H - 30))
            else:
                cont_txt = small_font.render("Press any key to continue", True, (150, 150, 150))
                screen.blit(cont_txt, (SCREEN_W - 250, SCREEN_H - 30))
        else:
            waiting_for_input = False

        if not waiting_for_input:
            if defense_mode:
                cmd_txt = font.render("🛡️ DEFEND! 1-High   2-Mid   3-Low", True, (120, 220, 255))
            else:
                cmd_txt = font.render("⚔️ ATTACK! 1-Upper  2-Middle  3-Lower  4-Heal  5-Str  6-Def", True, (255, 220, 120))
            screen.blit(cmd_txt, (30, SCREEN_H - 45))
        
        pygame.display.flip()

        if player["hp"] <= 0 and divine_intervention_func(player, show_msg_func, screen, font, small_font, clock):
            battle_messages.append("✨ DIVINE INTERVENTION!")
            continue

    if player["hp"] > 0:
        xp = 25 + player["floor"] * 10
        gold = random.randint(15, 30) + player["floor"] * 5
        show_msg_func(screen, f"🏆 Victory! Gained {xp} XP and {gold} gold!", font, small_font, clock)
        gain_xp_func(player, xp, show_msg_func, screen, font, small_font, clock)
        player["gold"] += gold
        
        pygame.mixer.music.fadeout(500)
        play_explore_music_func()
        return True # Victory
    
    pygame.mixer.music.fadeout(500)
    play_explore_music_func()
    return False # Defeat
