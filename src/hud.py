"""Compact top HUD. Only core stats — quests live in the pause journal."""
import pygame
from src.constants import SCREEN_W

HUD_HEIGHT = 60


def _hp_color(ratio):
    if ratio > 0.60:
        return (60, 200, 80)
    if ratio > 0.30:
        return (220, 180, 40)
    return (220, 50, 50)


def draw_hud(screen, player, small_font):
    """Two-row HUD: HP/level/XP/floor/gold on row 1; potions/weapon/NG+ on row 2."""
    pygame.draw.rect(screen, (18, 18, 26), (0, 0, SCREEN_W, HUD_HEIGHT))
    pygame.draw.line(screen, (45, 45, 60), (0, 30), (SCREEN_W, 30), 1)
    pygame.draw.line(screen, (200, 200, 200), (0, HUD_HEIGHT), (SCREEN_W, HUD_HEIGHT), 2)

    white = (255, 255, 255)
    gray = (170, 170, 170)
    gold_col = (255, 215, 90)

    # ---- Row 1 (y=8) ----
    screen.blit(small_font.render("HP", True, gray), (12, 8))
    hp_ratio = max(0.0, player["hp"] / max(1, player["max_hp"]))
    bar_x, bar_y, bar_w, bar_h = 42, 9, 180, 14
    pygame.draw.rect(screen, (60, 20, 20), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
    pygame.draw.rect(screen, _hp_color(hp_ratio), (bar_x, bar_y, int(bar_w * hp_ratio), bar_h), border_radius=3)
    pygame.draw.rect(screen, (180, 180, 180), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=3)
    screen.blit(small_font.render(f"{player['hp']}/{player['max_hp']}", True, white), (bar_x + bar_w + 8, 8))

    screen.blit(small_font.render(f"LV {player['level']}", True, white), (335, 8))
    xp_ratio = min(1.0, player["xp"] / max(1, player["level"] * 60))
    xbx, xby, xbw, xbh = 400, 12, 200, 9
    pygame.draw.rect(screen, (40, 40, 80), (xbx, xby, xbw, xbh), border_radius=3)
    pygame.draw.rect(screen, (80, 120, 255), (xbx, xby, int(xbw * xp_ratio), xbh), border_radius=3)
    pygame.draw.rect(screen, (90, 90, 140), (xbx, xby, xbw, xbh), 1, border_radius=3)

    screen.blit(small_font.render(f"FL:{player['floor']}", True, white), (632, 8))
    screen.blit(small_font.render(f"GOLD:{player['gold']}", True, gold_col), (700, 8))

    # ---- Row 2 (y=36) ----
    pot_line = (f"POT:{player.get('potions', 0)}   "
                f"STR:{player.get('strength_potions', 0)}   "
                f"DEF:{player.get('defense_potions', 0)}")
    screen.blit(small_font.render(pot_line, True, gray), (12, 36))

    wpn = player.get("weapon", "Dagger")
    wpn_short = wpn if len(wpn) <= 16 else wpn[:15] + "."
    screen.blit(small_font.render(f"WPN: {wpn_short}", True, white), (300, 36))

    buffs = []
    if player.get("strength_turns", 0) > 0:
        buffs.append(f"STR {player['strength_turns']}t")
    if player.get("defense_turns", 0) > 0:
        buffs.append(f"DEF {player['defense_turns']}t")
    if buffs:
        screen.blit(small_font.render("  ".join(buffs), True, (120, 200, 255)), (560, 36))

    if player.get("keys", 0):
        screen.blit(small_font.render(f"KEYS:{player['keys']}", True, (220, 200, 90)), (730, 36))

    if player.get("_ng_plus"):
        ng = small_font.render("NG+", True, (255, 140, 0))
        screen.blit(ng, (SCREEN_W - ng.get_width() - 12, 36))
