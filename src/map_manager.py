import random
from src.constants import MAP_SIZE, MAX_FLOORS

def generate_floor(floor_num, visited_rooms):
    """Pre-generates a 5x5 grid for the current floor."""
    visited_rooms.clear()
    
    # Fill 5x5 grid with random events
    for x in range(MAP_SIZE):
        for y in range(MAP_SIZE):
            r = random.random()
            if r < 0.15:
                t = "merchant"
            elif r < 0.35:
                t = "trap"
            elif r < 0.60:
                t = "shrine"
            else:
                t = "enemy"
            visited_rooms[(x, y)] = t
            
    # Start room is always empty
    visited_rooms[(0, 0)] = "cleared"
    
    # Place the Exit (or Boss on final floor)
    exit_x = random.randint(2, 4)
    exit_y = random.randint(2, 4)
    
    if floor_num < MAX_FLOORS:
        visited_rooms[(exit_x, exit_y)] = "exit"
    else:
        visited_rooms[(exit_x, exit_y)] = "boss"

def get_room(room_pos, visited_rooms):
    """Returns the type of the room at the given position."""
    return visited_rooms.get(room_pos, "enemy")
