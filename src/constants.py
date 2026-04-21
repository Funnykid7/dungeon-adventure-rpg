import pygame

# Screen Dimensions
SCREEN_W, SCREEN_H = 960, 540
ROOM_W, ROOM_H = 960, 540

# Game Settings
SAVE_FILE = "dungeon_save.json"
MAP_SIZE = 5
MAX_FLOORS = 3
FLASH_DURATION = 10
DOOR_COOLDOWN_TIME = 20
TILE_SIZE = 48
DOOR_SIZE = 48
DOOR_PADDING = 8

# Audio Paths
BATTLE_MUSIC = "assets/audio/battle_music.mp3"
EXPLORE_MUSIC = "assets/audio/game_world.mp3"

# Door Zones
door_zones = {
    "up": pygame.Rect(432, 85, 96, 48),
    "down": pygame.Rect(432, 456, 96, 48),
    "left": pygame.Rect(36, 216, 48, 96),
    "right": pygame.Rect(876, 216, 48, 96),
}
