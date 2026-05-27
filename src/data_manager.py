import json
import os
import time

def save_game(player, save_file):
    with open(save_file, "w") as f:
        json.dump(player, f)

def load_game(save_file):
    if os.path.exists(save_file):
        with open(save_file, "r") as f:
            return json.load(f)
    return None
