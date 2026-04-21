import random
from src.utils import sound

def use_potion(player, show_msg_func, screen, font, small_font, clock, in_combat=False):
    if player.get("potions", 0) <= 0:
        if not in_combat: show_msg_func(screen, "❌ No potions left.", font, small_font, clock)
        return False
    heal = 40
    player["potions"] -= 1
    player["hp"] = min(player["max_hp"], player["hp"] + heal)
    sound("heal")
    if not in_combat: show_msg_func(screen, f"🧪 Healed {heal} HP.", font, small_font, clock)
    return True

def use_strength_potion(player, show_msg_func, screen, font, small_font, clock, in_combat=False):
    if player.get("strength_potions", 0) <= 0:
        if not in_combat: show_msg_func(screen, "❌ No strength potions.", font, small_font, clock)
        return False
    player["strength_potions"] -= 1
    player["strength_turns"] = 5
    if not in_combat: show_msg_func(screen, "💪 Strength increased for 5 turns!", font, small_font, clock)
    return True

def use_defense_potion(player, show_msg_func, screen, font, small_font, clock, in_combat=False):
    if player.get("defense_potions", 0) <= 0:
        if not in_combat: show_msg_func(screen, "❌ No defense potions.", font, small_font, clock)
        return False
    player["defense_potions"] -= 1
    player["defense_turns"] = 5
    if not in_combat: show_msg_func(screen, "🛡️ Defense increased for 5 turns!", font, small_font, clock)
    return True

def divine_intervention(player, show_msg_func, screen, font, small_font, clock):
    if player.get("revived"):
        return False
    if random.random() <= 0.3:
        sound("level")
        show_msg_func(screen, "✨ THE GODS INTERVENE! You have been restored!", font, small_font, clock)
        player["hp"] = player["max_hp"]
        player["revived"] = True
        return True
    return False

def gain_xp(player, amount, show_msg_func, screen, font, small_font, clock):
    player["xp"] += amount
    leveled_up = False
    
    while True:
        xp_required = player["level"] * 60
        if player["xp"] >= xp_required:
            player["xp"] -= xp_required
            player["level"] += 1
            player["max_hp"] += 10
            player["hp"] = player["max_hp"]
            leveled_up = True
        else:
            break
            
    if leveled_up:
        sound("level")
        show_msg_func(screen, f"📈 LEVEL UP! You are now level {player['level']}!", font, small_font, clock)
