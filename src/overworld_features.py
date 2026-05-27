"""
Overworld exploration features: ember particles, torch glow, wall secrets,
moving hazards, interactive objects, companion NPC, and room labels.
All functions take explicit state — no globals.
"""
import random
import math
import pygame
import sys

from src.constants import (SCREEN_W, SCREEN_H, ROOM_W, ROOM_H,
                            FLOOR_DECORATION_COLORS, LORE_FRAGMENTS, ROOM_LABELS)

# ---------------------------------------------------------------------------
# Animated decorations — ember particles + torch glow
# ---------------------------------------------------------------------------

TORCH_POSITIONS = [(80, 130), (ROOM_W - 80, 130)]

_torch_fallback = None


def _make_torch_surface():
    """Build a small programmatic pixel-art torch (cached after first call)."""
    global _torch_fallback
    if _torch_fallback is not None:
        return _torch_fallback
    surf = pygame.Surface((32, 64), pygame.SRCALPHA)
    pygame.draw.rect(surf, (90, 55, 20), (12, 30, 8, 34))      # brown handle
    pygame.draw.rect(surf, (50, 35, 10), (8, 26, 16, 10))      # dark holder ring
    pygame.draw.ellipse(surf, (220, 120, 20), (6, 6, 20, 24))  # flame body
    pygame.draw.ellipse(surf, (255, 220, 60), (10, 10, 12, 16))  # flame core
    _torch_fallback = surf
    return _torch_fallback


class EmberSystem:
    def __init__(self, max_particles=30):
        self.max = max_particles
        self.particles = []  # each: [x, y, vx, vy, life, max_life, r, g, b]

    def spawn(self, x, y, color):
        if len(self.particles) >= self.max:
            return
        r, g, b = color
        vx = random.uniform(-0.6, 0.6)
        vy = random.uniform(-1.5, -0.5)
        life = random.randint(30, 70)
        self.particles.append([float(x + random.randint(-8, 8)),
                                float(y), vx, vy, life, life, r, g, b])

    def update(self):
        alive = []
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[2] *= 0.98
            p[4] -= 1
            if p[4] > 0:
                alive.append(p)
        self.particles = alive

    def draw(self, screen):
        for p in self.particles:
            alpha_ratio = p[4] / p[5]
            r = int(p[6] * alpha_ratio)
            g = int(p[7] * alpha_ratio)
            b = int(p[8] * alpha_ratio)
            radius = max(1, int(2 * alpha_ratio))
            pygame.draw.circle(screen, (r, g, b), (int(p[0]), int(p[1])), radius)


def draw_torch_glow(screen, floor_num, torch_surf=None):
    """Draw pulsing translucent torch circles at both top corners."""
    colors = FLOOR_DECORATION_COLORS.get(floor_num, FLOOR_DECORATION_COLORS[1])
    r, g, b = colors["glow"]
    pulse = (math.sin(pygame.time.get_ticks() * 0.004) + 1) / 2  # 0..1
    radius = int(65 + 15 * pulse)

    glow_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
    alphas = [50, 35, 20]
    offsets = [0, 20, 38]
    for alpha, offset in zip(alphas, offsets):
        inner_r = max(1, radius - offset)
        pygame.draw.circle(glow_surf, (r, g, b, alpha),
                           (radius + 2, radius + 2), inner_r)

    for tx, ty in TORCH_POSITIONS:
        screen.blit(glow_surf, (tx - radius - 2, ty - radius - 2))

    _torch_to_draw = torch_surf if torch_surf is not None else _make_torch_surface()
    for tx, ty in TORCH_POSITIONS:
        screen.blit(_torch_to_draw, (tx - 16, ty - 58))


# ---------------------------------------------------------------------------
# Wall secrets
# ---------------------------------------------------------------------------

_SPECIAL_ROOM_TYPES = frozenset({
    "boss", "exit", "miniboss", "cleared", "cleared_merchant",
    "cleared_shrine", "cleared_trap", "cleared_chest",
    "cleared_puzzle", "cleared_locked", "cleared_event",
})

_WALL_ZONES = {
    "up":    pygame.Rect(0, 85, ROOM_W, 60),
    "down":  pygame.Rect(0, ROOM_H - 145, ROOM_W, 60),
    "left":  pygame.Rect(36, 0, 60, ROOM_H),
    "right": pygame.Rect(ROOM_W - 96, 0, 60, ROOM_H),
}


def generate_secrets(visited_rooms):
    """Return dict (x,y) -> secret info for ~40% of eligible rooms."""
    secrets = {}
    for pos, room_type in visited_rooms.items():
        if room_type in _SPECIAL_ROOM_TYPES:
            continue
        if random.random() < 0.40:
            wall = random.choice(["up", "down", "left", "right"])
            outcome = random.choices(
                ["gold", "potion", "lore", "trap"],
                weights=[40, 25, 25, 10]
            )[0]
            secrets[pos] = {"wall": wall, "found": False, "outcome": outcome}
    return secrets


def get_secret_inspect_zone(wall_dir):
    return _WALL_ZONES.get(wall_dir, pygame.Rect(0, 0, 0, 0))


def draw_secret_glow(screen, secret):
    """Draw a pulsing gold line on the wall edge if secret not found."""
    if secret is None or secret["found"]:
        return
    wall = secret["wall"]
    pulse = (math.sin(pygame.time.get_ticks() * 0.005) + 1) / 2
    alpha = int(100 + 140 * pulse)
    color = (255, 200, 40, alpha)
    shimmer = (255, 200, 40, int(alpha * 0.4))

    surf = pygame.Surface((ROOM_W, ROOM_H), pygame.SRCALPHA)
    thickness = 10
    if wall == "up":
        pygame.draw.rect(surf, color, (0, 85, ROOM_W, thickness))
        pygame.draw.rect(surf, shimmer, (0, 85 + thickness, ROOM_W, 8))
        pygame.draw.rect(surf, (255, 220, 80, int(alpha * 0.12)), (0, 85, ROOM_W, 25))
    elif wall == "down":
        pygame.draw.rect(surf, color, (0, ROOM_H - 90, ROOM_W, thickness))
        pygame.draw.rect(surf, shimmer, (0, ROOM_H - 90 - 8, ROOM_W, 8))
        pygame.draw.rect(surf, (255, 220, 80, int(alpha * 0.12)), (0, ROOM_H - 115, ROOM_W, 25))
    elif wall == "left":
        pygame.draw.rect(surf, color, (36, 0, thickness, ROOM_H))
        pygame.draw.rect(surf, shimmer, (36 + thickness, 0, 8, ROOM_H))
        pygame.draw.rect(surf, (255, 220, 80, int(alpha * 0.12)), (36, 0, 25, ROOM_H))
    elif wall == "right":
        pygame.draw.rect(surf, color, (ROOM_W - 42, 0, thickness, ROOM_H))
        pygame.draw.rect(surf, shimmer, (ROOM_W - 42 - 8, 0, 8, ROOM_H))
        pygame.draw.rect(surf, (255, 220, 80, int(alpha * 0.12)), (ROOM_W - 67, 0, 25, ROOM_H))
    screen.blit(surf, (0, 0))


def inspect_secret(player, secret, screen, font, small_font, clock):
    """Resolve a wall secret outcome and mark it found."""
    from src.ui import show_msg
    secret["found"] = True
    outcome = secret["outcome"]

    if outcome == "gold":
        gold = random.randint(20, 50)
        player["gold"] += gold
        player["floor_gold_earned"] = player.get("floor_gold_earned", 0) + gold
        show_msg(screen, f"Hidden cache! You find {gold} gold behind the wall.", font, small_font, clock)
    elif outcome == "potion":
        player["potions"] = player.get("potions", 0) + 1
        show_msg(screen, "A dusty alcove holds a Healing Potion!", font, small_font, clock)
    elif outcome == "lore":
        text = random.choice(LORE_FRAGMENTS)
        show_msg(screen, text, font, small_font, clock)
    elif outcome == "trap":
        dmg = random.randint(12, 22)
        player["hp"] = max(0, player["hp"] - dmg)
        show_msg(screen, f"A hidden dart trap fires! -{dmg} HP!", font, small_font, clock)


# ---------------------------------------------------------------------------
# Moving hazards
# ---------------------------------------------------------------------------

_HAZARD_BOUNDS = {"x_min": 50, "x_max": ROOM_W - 50,
                  "y_min": 105, "y_max": ROOM_H - 55}


def generate_hazards(room_type, floor_num):
    """Return list of hazard dicts appropriate for the room type."""
    hazards = []
    chance_by_type = {"elite": 0.60, "enemy": 0.20}
    chance = chance_by_type.get(room_type, 0.0)
    if random.random() >= chance:
        return hazards

    # Always at least 1 hazard; trap rooms get 2
    count = 2 if room_type == "trap" else 1
    for _ in range(count):
        htype = random.choice(["blade", "projectile"])
        if htype == "blade":
            x = float(random.randint(100, 500))
            y = float(random.randint(150, ROOM_H - 150))
            speed = 2.5 + floor_num * 0.4
            hazards.append({"type": "blade", "x": x, "y": y,
                             "vx": speed, "vy": 0.0, "last_hit": 0})
        else:
            x = float(random.randint(200, ROOM_W - 200))
            y = float(random.randint(150, ROOM_H - 150))
            speed = 2.0 + floor_num * 0.3
            angle = random.uniform(0, 2 * math.pi)
            hazards.append({"type": "projectile", "x": x, "y": y,
                             "vx": math.cos(angle) * speed,
                             "vy": math.sin(angle) * speed,
                             "last_hit": 0})
    return hazards


def update_hazards(hazards):
    """Move all hazards and bounce off room walls."""
    b = _HAZARD_BOUNDS
    for h in hazards:
        h["x"] += h["vx"]
        h["y"] += h["vy"]
        if h["type"] == "blade":
            if h["x"] < b["x_min"] or h["x"] + 120 > b["x_max"]:
                h["vx"] *= -1
                h["x"] = max(b["x_min"], min(h["x"], b["x_max"] - 120))
        else:
            if h["x"] < b["x_min"] or h["x"] > b["x_max"]:
                h["vx"] *= -1
                h["x"] = max(b["x_min"], min(h["x"], b["x_max"]))
            if h["y"] < b["y_min"] or h["y"] > b["y_max"]:
                h["vy"] *= -1
                h["y"] = max(b["y_min"], min(h["y"], b["y_max"]))


def draw_hazards(screen, hazards):
    """Draw each hazard with pixel-art style."""
    for h in hazards:
        if h["type"] == "blade":
            bx, by = int(h["x"]), int(h["y"]) - 7
            # Body
            pygame.draw.rect(screen, (55, 60, 70), (bx, by, 140, 14))
            # Center highlight strip
            pygame.draw.rect(screen, (200, 220, 240), (bx, by + 6, 140, 2))
            # Dark notches
            for nx in range(bx + 8, bx + 140, 16):
                pygame.draw.rect(screen, (30, 35, 45), (nx, by, 2, 4))
                pygame.draw.rect(screen, (30, 35, 45), (nx, by + 10, 2, 4))
            # Outer border
            pygame.draw.rect(screen, (150, 170, 190), (bx, by, 140, 14), 1)
        else:
            cx, cy = int(h["x"]), int(h["y"])
            pygame.draw.circle(screen, (40, 15, 60), (cx, cy), 11)
            pygame.draw.circle(screen, (160, 60, 220), (cx, cy), 8)
            pygame.draw.circle(screen, (220, 150, 255), (cx, cy), 4)
            pygame.draw.circle(screen, (255, 240, 255), (cx - 2, cy - 2), 1)


def check_hazard_damage(player, hazards, now):
    """Deal 8 damage if player overlaps a hazard (1.5s cooldown per hazard)."""
    if not hazards:
        return False
    px = player.get("_world_x", ROOM_W // 2) + 16
    py = player.get("_world_y", ROOM_H // 2) + 16
    player_rect = pygame.Rect(px, py, 32, 32)
    hit = False
    for h in hazards:
        if now - h["last_hit"] < 1500:
            continue
        if h["type"] == "blade":
            hrect = pygame.Rect(int(h["x"]), int(h["y"]) - 6, 120, 12)
        else:
            hrect = pygame.Rect(int(h["x"]) - 10, int(h["y"]) - 10, 20, 20)
        if player_rect.colliderect(hrect):
            player["hp"] = max(0, player["hp"] - 8)
            h["last_hit"] = now
            hit = True
    return hit


# ---------------------------------------------------------------------------
# Interactive objects — barrels and bookshelves
# ---------------------------------------------------------------------------

_SAFE_OBJECT_ZONES = [
    pygame.Rect(200, 150, 560, 240),   # center area
]
_DOOR_AVOID = [
    pygame.Rect(390, 85, 180, 60),     # up door
    pygame.Rect(390, 395, 180, 80),    # down door
    pygame.Rect(36, 180, 80, 160),     # left door
    pygame.Rect(844, 180, 80, 160),    # right door
]


def _object_position():
    """Pick a random position away from doors, in the walkable zone."""
    for _ in range(30):
        x = random.randint(100, ROOM_W - 140)
        y = random.randint(120, ROOM_H - 120)
        rect = pygame.Rect(x, y, 32, 48)
        if any(rect.colliderect(d) for d in _DOOR_AVOID):
            continue
        return x, y
    return random.randint(200, 700), random.randint(150, 350)


def generate_objects(room_type):
    return []


def draw_objects(screen, objects, small_font):
    """Draw each object with pixel-art style."""
    for obj in objects:
        x, y = obj["x"], obj["y"]
        interacted = obj["interacted"]

        if obj["type"] == "barrel":
            body_color = (50, 32, 12) if interacted else (95, 58, 22)
            # Body
            pygame.draw.rect(screen, body_color, (x, y, 28, 32), border_radius=4)
            # Top ellipse
            pygame.draw.ellipse(screen, (70, 42, 14), (x + 2, y, 24, 10))
            # Hoop lines
            pygame.draw.rect(screen, (140, 120, 80), (x, y + 10, 28, 2))
            pygame.draw.rect(screen, (140, 120, 80), (x, y + 22, 28, 2))
            # Left highlight
            if not interacted:
                pygame.draw.line(screen, (160, 130, 70), (x + 2, y + 3), (x + 2, y + 29))
        else:
            back_color = (25, 18, 10) if interacted else (38, 28, 15)
            # Back panel
            pygame.draw.rect(screen, back_color, (x, y - 12, 28, 50), border_radius=2)
            # Book rows
            book_colors = [(120, 30, 30), (30, 100, 100), (140, 110, 20), (20, 30, 80)]
            for row, bc in enumerate(book_colors):
                ry2 = y - 10 + row * 11
                pygame.draw.rect(screen, bc, (x + 2, ry2, 24, 9))
                pygame.draw.rect(screen, (15, 12, 8), (x + 2, ry2 + 9, 24, 1))
            # Shelf dividers
            pygame.draw.rect(screen, (90, 70, 45), (x, y - 12 + 16, 28, 2))
            pygame.draw.rect(screen, (90, 70, 45), (x, y - 12 + 34, 28, 2))

        if not interacted:
            # E-hint badge
            badge = pygame.Surface((16, 16), pygame.SRCALPHA)
            badge.fill((20, 18, 30, 210))
            pygame.draw.rect(badge, (180, 160, 80, 255), badge.get_rect(), 1, border_radius=3)
            e_char = small_font.render("E", True, (255, 255, 255))
            badge.blit(e_char, ((16 - e_char.get_width()) // 2, (16 - e_char.get_height()) // 2))
            screen.blit(badge, (x + 6, y - 20))


def interact_object(player, obj):
    """Resolve interaction with barrel or bookshelf. Returns (message, color) for toast display."""
    if obj["interacted"]:
        return None, None
    obj["interacted"] = True

    if obj["type"] == "bookshelf":
        text = random.choice(LORE_FRAGMENTS)
        return (text[:50] + "..." if len(text) > 50 else text), (200, 180, 120)

    # barrel
    roll = random.random()
    if roll < 0.30:
        dmg = random.randint(15, 25)
        player["hp"] = max(0, player["hp"] - dmg)
        if random.random() < 0.4:
            player["_pending_status_poison"] = True
            return f"Poison gas! -{dmg} HP + POISONED!", (180, 60, 200)
        else:
            return f"Barrel explodes! -{dmg} HP!", (220, 80, 80)
    else:
        return "The barrel is empty.", (160, 160, 160)


def draw_toasts(screen, toasts, small_font, now):
    """Draw floating toast notifications. Mutates list removing expired ones."""
    alive = []
    for t in toasts:
        age = now - t["born_ms"]
        if age > t["duration"]:
            continue
        alpha = 255
        if age > t["duration"] - 400:
            alpha = int(255 * (t["duration"] - age) / 400)
        w = t["w"]
        surf = pygame.Surface((w, 26), pygame.SRCALPHA)
        surf.fill((10, 8, 20, min(220, alpha)))
        r, g, b = t["color"]
        pygame.draw.rect(surf, (r, g, b, alpha), surf.get_rect(), 1, border_radius=4)
        label = small_font.render(t["text"], True, t["color"])
        surf.blit(label, (8, (26 - label.get_height()) // 2))
        screen.blit(surf, (t["x"], t["y"]))
        alive.append(t)
    toasts[:] = alive


# ---------------------------------------------------------------------------
# Companion NPC (slime partner)
# ---------------------------------------------------------------------------

def load_companion_sprites(target_size=(48, 48)):
    """Load slime1.png and slime2.png, return [surf1, surf2]."""
    sprites = []
    for fname in ("slime1.png", "slime2.png"):
        path = f"assets/overworld/partner/{fname}"
        try:
            surf = pygame.image.load(path).convert_alpha()
            surf = pygame.transform.scale(surf, target_size)
        except Exception:
            surf = pygame.Surface(target_size, pygame.SRCALPHA)
            surf.fill((80, 200, 80, 200))
        sprites.append(surf)
    return sprites


def update_companion(companion, target_x, target_y):
    """Smoothly move companion toward a position ~70px behind the player."""
    goal_x = target_x - 70
    goal_y = target_y + 10
    dx = goal_x - companion["x"]
    dy = goal_y - companion["y"]
    speed = 0.12
    companion["x"] += dx * speed
    companion["y"] += dy * speed

    companion["anim_timer"] = companion.get("anim_timer", 0) + 1
    if companion["anim_timer"] >= 20:
        companion["frame"] = 1 - companion.get("frame", 0)
        companion["anim_timer"] = 0


def draw_companion(screen, companion, companion_sprites):
    """Draw the companion slime sprite at its current position."""
    if companion is None or not companion_sprites:
        return
    frame = companion.get("frame", 0) % len(companion_sprites)
    surf = companion_sprites[frame]
    screen.blit(surf, (int(companion["x"]), int(companion["y"])))


def apply_companion_role(player, role):
    """Apply persistent player-dict effects for the given companion role."""
    if role == "combat":
        player["_companion_atk_bonus"] = 8
    elif role == "merchant":
        player["_companion_discount"] = 0.15


def init_companion(player, role, world_x, world_y):
    """Create and attach a companion to the player dict."""
    player["companion"] = {
        "role": role,
        "x": float(world_x - 70),
        "y": float(world_y + 10),
        "frame": 0,
        "anim_timer": 0,
    }
    apply_companion_role(player, role)


# ---------------------------------------------------------------------------
# Room entry label
# ---------------------------------------------------------------------------

def draw_room_label(screen, text, entered_at_ms, font, duration_ms=1500):
    """
    Draw a fading room-type label. Returns True while still visible,
    False when expired (caller should clear the timer).
    """
    if not text:
        return False
    elapsed = pygame.time.get_ticks() - entered_at_ms
    if elapsed >= duration_ms:
        return False

    fade_in = 300
    fade_out = 400
    if elapsed < fade_in:
        alpha = int(255 * elapsed / fade_in)
    elif elapsed > duration_ms - fade_out:
        alpha = int(255 * (duration_ms - elapsed) / fade_out)
    else:
        alpha = 255

    surf = font.render(text, True, (255, 220, 100))
    overlay = pygame.Surface((surf.get_width() + 40, surf.get_height() + 16), pygame.SRCALPHA)
    overlay.fill((10, 8, 20, max(0, alpha - 60)))
    screen.blit(overlay, (SCREEN_W // 2 - overlay.get_width() // 2, 200 - 8))
    surf.set_alpha(alpha)
    screen.blit(surf, (SCREEN_W // 2 - surf.get_width() // 2, 200))
    return True
