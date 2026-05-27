import pygame
import math
import array

_sounds = {}
_initialized = False

def _make_tone(freq, duration, volume=0.45, wave="sine", decay=True):
    """Generate a pygame.mixer.Sound from a sine/square wave without external libs."""
    try:
        rate, size, channels = pygame.mixer.get_init()
        n = int(rate * duration)
        buf = array.array('h')
        peak = 32767 * volume
        for i in range(n):
            t = i / rate
            env = max(0.0, (1 - t / duration)) if decay else 1.0
            if wave == "sine":
                sample = int(peak * env * math.sin(2 * math.pi * freq * t))
            elif wave == "square":
                sample = int(peak * env * (1 if math.sin(2 * math.pi * freq * t) >= 0 else -1))
            elif wave == "noise":
                import random
                sample = int(peak * env * (random.random() * 2 - 1))
            else:
                sample = 0
            for _ in range(channels):
                buf.append(sample)
        return pygame.mixer.Sound(buffer=buf)
    except Exception:
        return None

def _init_sounds():
    global _sounds, _initialized
    _initialized = True
    defs = {
        "heal":        (523,  0.30, "sine",   True),
        "level":       (659,  0.50, "sine",   True),
        "revive":      (880,  0.60, "sine",   False),
        "player_hit":  (180,  0.15, "square", True),
        "enemy_hit":   (280,  0.12, "square", True),
        "crit":        (1046, 0.20, "sine",   True),
        "dodge":       (440,  0.10, "sine",   True),
        "enemy_death": (140,  0.40, "square", True),
        "potion":      (392,  0.20, "sine",   True),
        "coin":        (784,  0.15, "sine",   True),
    }
    for name, (freq, dur, wave, decay) in defs.items():
        try:
            s = pygame.mixer.Sound(f"assets/audio/sfx/{name}.wav")
        except Exception:
            s = _make_tone(freq, dur, wave=wave, decay=decay)
        if s:
            s.set_volume(0.4)
        _sounds[name] = s

def sound(kind):
    global _initialized
    if not _initialized:
        try:
            _init_sounds()
        except Exception:
            _initialized = True
            return
    s = _sounds.get(kind)
    if s:
        try:
            s.play()
        except Exception:
            pass

def load_img(path):
    return pygame.image.load(path).convert_alpha()
