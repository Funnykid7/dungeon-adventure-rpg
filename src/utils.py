import time
import pygame

def divider():
    print("\n" + "=" * 60)

def sound(kind):
    sounds = {
        "attack": "\a",
        "hit": "\a\a",
        "block": "\a",
        "heal": "\a\a",
        "level": "\a\a\a",
        "boss": "\a\a\a\a",
        "death": "\a\a\a\a\a"
    }
    print(sounds.get(kind, ""), end="", flush=True)

def load_img(path):
    return pygame.image.load(path).convert_alpha()
