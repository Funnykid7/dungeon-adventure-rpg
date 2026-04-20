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
    
    global battle_messages, waiting_for_input
    
    play_battle_music_func()
    
    waiting_for_input = False
    battle_messages = []
    
    player_flash_timer = 0
    enemy_flash_timer = 0

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
                    if battle_messages:
                        battle_messages.pop(0)
                    if not battle_messages:
                        waiting_for_input = False
                    continue

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
                elif event.key == pygame.K_4:
                    if use_potion_func(player, show_msg_func, screen, font, small_font, clock, in_combat=True):
                        action = "potion"
                        battle_messages.append("You used a potion!")
                elif event.key == pygame.K_5:
                    if use_strength_potion_func(player, show_msg_func, screen, font, small_font, clock, in_combat=True):
                        action = "potion"
                        battle_messages.append("💪 Strength boosted!")
                elif event.key == pygame.K_6:
                    if use_defense_potion_func(player, show_msg_func, screen, font, small_font, clock, in_combat=True):
                        action = "potion"
                        battle_messages.append("🛡️ Defense boosted!")

                if not battle_messages:
                    waiting_for_input = False

        if action is not None:
            battle_messages.clear()
            if action == "attack":
                dmg = random.randint(*classes[player["class"]]["attack"])
                dmg += weapons[player["weapon"]]["bonus"] + player["level"] * 2
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
                battle_messages.append(f"You dealt {dmg} damage!")
                player["last_attack"] = attack_pos

                if player["class"] == "paladin" and player["hp"] > 0 and random.random() < 0.4:
                    heal = random.randint(5, 12)
                    player["hp"] = min(player["max_hp"], player["hp"] + heal)
                    battle_messages.append(f"Paladin heals {heal} HP!")

            if enemy["hp"] > 0:
                enemy_dmg = random.randint(10, 18) + player["floor"] * 2
                if action == "potion": enemy_dmg = int(enemy_dmg * 0.6)
                if player.get("defense_turns", 0) > 0:
                    enemy_dmg = int(enemy_dmg * 0.5)
                    battle_messages.append("🛡️ Damage reduced!")
                if player["class"] == "warrior": enemy_dmg = int(enemy_dmg * 0.8)
                if player["class"] == "rogue" and random.random() < 0.25:
                    enemy_dmg = 0
                    battle_messages.append("💨 You dodged the attack!")

                player["hp"] -= enemy_dmg
                if enemy_dmg > 0:
                    player_flash_timer = FLASH_DURATION
                    battle_messages.append(f"Enemy hit you for {enemy_dmg} damage!")

            player["strength_turns"] = max(0, player.get("strength_turns", 0) - 1)
            player["defense_turns"] = max(0, player.get("defense_turns", 0) - 1)
            action = None
            attack_pos = None

        # Draw
        screen.blit(battle_bg, (0, 0))
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

        pygame.draw.rect(screen, (32, 32, 32), (0, SCREEN_H - 140, SCREEN_W, 140))
        pygame.draw.rect(screen, (200, 200, 200), (0, SCREEN_H - 140, SCREEN_W, 140), 4)

        if battle_messages:
            waiting_for_input = True
            txt = font.render(battle_messages[0], True, (255, 255, 255))
            screen.blit(txt, (24, SCREEN_H - 110))
        else:
            waiting_for_input = False

        cmd_txt = font.render("     1-Upper   2-Middle   3-Lower   4-Heal   5-Str   6-Def", True, (255, 220, 120))
        screen.blit(cmd_txt, (24, SCREEN_H - 32))
        pygame.display.flip()

        if player["hp"] <= 0 and divine_intervention_func(player, show_msg_func, screen, font, small_font, clock):
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
