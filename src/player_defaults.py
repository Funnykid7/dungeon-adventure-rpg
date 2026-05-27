"""
Central definition of player dict defaults.
Used by intro_gui and ensure_player_keys for save-compatibility.
"""
from src.entities import classes

PLAYER_DEFAULTS = {
    "name": "Hero",
    "class": "warrior",
    "hp": 150,
    "max_hp": 150,
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
    "active_curse": None,
    "active_blessing": None,
    "upgrades": [],
    "companion": None,
}


def ensure_player_keys(player):
    """Apply all missing keys from PLAYER_DEFAULTS to an existing player dict.
    Safe to call on loaded saves from older versions."""
    for key, default in PLAYER_DEFAULTS.items():
        if key not in player:
            # Deep-copy mutable defaults
            if isinstance(default, dict):
                player[key] = dict(default)
            elif isinstance(default, list):
                player[key] = list(default)
            else:
                player[key] = default
    # equipment sub-keys
    eq = player.setdefault("equipment", {})
    for slot in ("armor", "ring", "trinket"):
        eq.setdefault(slot, None)
    return player


class FightCtx:
    """Bundles all fight() dependencies so callers pass one object instead of 12 args."""
    __slots__ = (
        "battle_bg", "player_img", "enemy_img", "dungeon_lord_img",
        "divine_fn", "gain_xp_fn",
        "use_potion_fn", "use_str_fn", "use_def_fn",
        "play_battle_fn", "play_explore_fn",
    )

    def __init__(self, battle_bg, player_img, enemy_img, dungeon_lord_img,
                 divine_fn, gain_xp_fn,
                 use_potion_fn, use_str_fn, use_def_fn,
                 play_battle_fn, play_explore_fn):
        self.battle_bg = battle_bg
        self.player_img = player_img
        self.enemy_img = enemy_img
        self.dungeon_lord_img = dungeon_lord_img
        self.divine_fn = divine_fn
        self.gain_xp_fn = gain_xp_fn
        self.use_potion_fn = use_potion_fn
        self.use_str_fn = use_str_fn
        self.use_def_fn = use_def_fn
        self.play_battle_fn = play_battle_fn
        self.play_explore_fn = play_explore_fn

    def run(self, screen, player, enemy, font, small_font, clock,
            show_msg_fn, draw_hp_fn, flash_fn, tint_fn,
            img_override=None, play_music_override=None):
        """Run fight() with all stored context. img_override replaces enemy_img;
        play_music_override replaces the battle-music callback (e.g. boss music)."""
        from src.combat import fight
        return fight(
            screen, player, enemy,
            self.battle_bg, self.player_img, img_override or self.enemy_img,
            font, small_font, clock,
            show_msg_fn, draw_hp_fn, None, flash_fn, tint_fn,
            self.divine_fn, self.gain_xp_fn,
            self.use_potion_fn, self.use_str_fn, self.use_def_fn,
            play_music_override or self.play_battle_fn,
            self.play_explore_fn,
        )
