import json
import os
import time

def slow(text, d=0.02):
    for c in text:
        print(c, end="", flush=True)
        time.sleep(d)
    print()

def save_game(player, save_file):
    with open(save_file, "w") as f:
        json.dump(player, f)
    slow("💾 Game saved.")

def load_game(save_file):
    if os.path.exists(save_file):
        with open(save_file, "r") as f:
            slow("📂 Save loaded.")
            return json.load(f)
    return None
