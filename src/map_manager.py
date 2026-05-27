import random
from src.constants import MAP_SIZE, MAX_FLOORS, FLOOR_THEMES

def generate_floor(floor_num, visited_rooms):
    visited_rooms.clear()

    theme = FLOOR_THEMES.get(floor_num, FLOOR_THEMES[1])
    e_w = theme["enemy_w"]
    m_w = theme["merchant_w"]

    # New room type weights (fixed): puzzle 8%, elite 5%, locked 4%, event 5%
    # Reduce enemy and shrine each by ~11% to make room
    puzzle_w = 0.08
    elite_w  = 0.05
    locked_w = 0.04 if floor_num >= 2 else 0.0   # no locked rooms on floor 1
    event_w  = 0.05
    new_w    = puzzle_w + elite_w + locked_w + event_w  # 0.22

    # Scale down enemy and shrine proportionally
    e_adj = max(0.10, e_w - new_w * (e_w / (e_w + 0.25)))
    s_adj = max(0.05, 0.25 - new_w * (0.25 / (e_w + 0.25)))

    chest_end   = 0.10
    merch_end   = chest_end + m_w
    trap_end    = merch_end + 0.15
    shrine_end  = trap_end + s_adj
    puzzle_end  = shrine_end + puzzle_w
    elite_end   = puzzle_end + elite_w
    locked_end  = elite_end + locked_w
    event_end   = locked_end + event_w
    # remainder goes to enemy

    for x in range(MAP_SIZE):
        for y in range(MAP_SIZE):
            r = random.random()
            if r < chest_end:
                t = "chest"
            elif r < merch_end:
                t = "merchant"
            elif r < trap_end:
                t = "trap"
            elif r < shrine_end:
                t = "shrine"
            elif r < puzzle_end:
                t = "puzzle"
            elif r < elite_end:
                t = "elite"
            elif r < locked_end:
                t = "locked"
            elif r < event_end:
                t = "event"
            else:
                t = "enemy"
            visited_rooms[(x, y)] = t

    # Guarantee at least 1 puzzle and 1 event per floor
    all_cells = [(x, y) for x in range(MAP_SIZE) for y in range(MAP_SIZE) if (x, y) != (0, 0)]
    replaceable = [c for c in all_cells if visited_rooms[c] in ("enemy", "shrine", "trap")]
    random.shuffle(replaceable)
    for required, cell_list_check in [("puzzle", "puzzle"), ("event", "event")]:
        if not any(visited_rooms[c] == required for c in all_cells):
            if replaceable:
                visited_rooms[replaceable.pop()] = required

    # Softlock prevention: if locked rooms exist but no chest, guarantee one chest
    if any(v == "locked" for v in visited_rooms.values()):
        if not any(v == "chest" for v in visited_rooms.values()):
            candidates = [c for c in all_cells if visited_rooms[c] == "enemy"]
            if candidates:
                visited_rooms[random.choice(candidates)] = "chest"

    # Start room is always empty
    visited_rooms[(0, 0)] = "cleared"

    # Place a miniboss on floors 2+
    if floor_num >= 2:
        candidates = [
            (x, y) for x in range(MAP_SIZE) for y in range(MAP_SIZE)
            if visited_rooms.get((x, y)) in ("enemy", "shrine", "trap") and (x, y) != (0, 0)
        ]
        if candidates:
            visited_rooms[random.choice(candidates)] = "miniboss"

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
