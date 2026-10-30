import copy
import ctypes
import json
import random
import sys
import threading
import time
import nook

# Initialize Nook plugin
app = nook.Plugin()

# Tile appearance configuration (classic 2048 color scheme)
TILE_CONFIG = {
    2: {"bg": "#EEE4DA", "fg": "#776E65", "size": 18},
    4: {"bg": "#EDE0C8", "fg": "#776E65", "size": 18},
    8: {"bg": "#F2B179", "fg": "#FFFFFF", "size": 18},
    16: {"bg": "#F59563", "fg": "#FFFFFF", "size": 16},
    32: {"bg": "#F67C5F", "fg": "#FFFFFF", "size": 16},
    64: {"bg": "#F65E3B", "fg": "#FFFFFF", "size": 16},
    128: {"bg": "#EDCF72", "fg": "#FFFFFF", "size": 14},
    256: {"bg": "#EDCC61", "fg": "#FFFFFF", "size": 14},
    512: {"bg": "#EDC850", "fg": "#FFFFFF", "size": 14},
    1024: {"bg": "#EDC53F", "fg": "#FFFFFF", "size": 11},
    2048: {"bg": "#EDC22E", "fg": "#FFFFFF", "size": 11},
}
DEFAULT_TILE_CONFIG = {"bg": "#3C3A32", "fg": "#FFFFFF", "size": 10}


class Game2048:
    def __init__(self):
        self.grid = [[0] * 4 for _ in range(4)]
        self.score = 0
        self.best_score = 0
        self.game_over = False
        self.won = False
        self.win_acknowledged = False
        self.history = None

    def reset(self):
        self.grid = [[0] * 4 for _ in range(4)]
        self.score = 0
        self.game_over = False
        self.won = False
        self.win_acknowledged = False
        self.history = None
        self.spawn_tile()
        self.spawn_tile()

    def spawn_tile(self):
        empty = [(r, c) for r in range(4) for c in range(4) if self.grid[r][c] == 0]
        if not empty:
            return False
        r, c = random.choice(empty)
        self.grid[r][c] = 4 if random.random() < 0.1 else 2
        return True

    def max_tile(self):
        return max(max(row) for row in self.grid)

    def _check_game_over(self):
        for r in range(4):
            for c in range(4):
                if self.grid[r][c] == 0:
                    self.game_over = False
                    return
        for r in range(4):
            for c in range(4):
                val = self.grid[r][c]
                if r + 1 < 4 and self.grid[r + 1][c] == val:
                    self.game_over = False
                    return
                if c + 1 < 4 and self.grid[r][c + 1] == val:
                    self.game_over = False
                    return
        self.game_over = True

    def undo(self):
        if self.history:
            self.grid, self.score = self.history
            self.history = None
            self.game_over = False
            return True
        return False

    def to_dict(self):
        return {
            "grid": self.grid,
            "score": self.score,
            "best_score": self.best_score,
            "game_over": self.game_over,
            "won": self.won,
            "win_acknowledged": self.win_acknowledged,
        }

    def from_dict(self, data):
        if not data:
            self.reset()
            return
        self.grid = data.get("grid", [[0] * 4 for _ in range(4)])
        self.score = data.get("score", 0)
        self.best_score = data.get("best_score", 0)
        self.game_over = data.get("game_over", False)
        self.won = data.get("won", False)
        self.win_acknowledged = data.get("win_acknowledged", False)
        if all(self.grid[r][c] == 0 for r in range(4) for c in range(4)):
            self.reset()


def calculate_slide(grid, direction):
    """Computes tile movement vectors, resulting grid, and points gained."""
    moves = []
    new_grid = [[0] * 4 for _ in range(4)]
    gained = 0

    if direction == "left":
        for r in range(4):
            target_c = 0
            last_merged = False
            row_vals = []
            for c in range(4):
                val = grid[r][c]
                if val == 0:
                    continue
                if target_c > 0 and not last_merged and row_vals[target_c - 1] == val:
                    dest = target_c - 1
                    moves.append({"from": (r, c), "to": (r, dest), "val": val, "merge": True})
                    row_vals[dest] *= 2
                    gained += row_vals[dest]
                    last_merged = True
                else:
                    dest = target_c
                    moves.append({"from": (r, c), "to": (r, dest), "val": val, "merge": False})
                    row_vals.append(val)
                    target_c += 1
                    last_merged = False
            for c in range(len(row_vals)):
                new_grid[r][c] = row_vals[c]

    elif direction == "right":
        for r in range(4):
            target_c = 3
            last_merged = False
            row_vals = {}
            for c in [3, 2, 1, 0]:
                val = grid[r][c]
                if val == 0:
                    continue
                if target_c < 3 and not last_merged and row_vals.get(target_c + 1) == val:
                    dest = target_c + 1
                    moves.append({"from": (r, c), "to": (r, dest), "val": val, "merge": True})
                    row_vals[dest] *= 2
                    gained += row_vals[dest]
                    last_merged = True
                else:
                    dest = target_c
                    moves.append({"from": (r, c), "to": (r, dest), "val": val, "merge": False})
                    row_vals[dest] = val
                    target_c -= 1
                    last_merged = False
            for c, v in row_vals.items():
                new_grid[r][c] = v

    elif direction == "up":
        for c in range(4):
            target_r = 0
            last_merged = False
            col_vals = []
            for r in range(4):
                val = grid[r][c]
                if val == 0:
                    continue
                if target_r > 0 and not last_merged and col_vals[target_r - 1] == val:
                    dest = target_r - 1
                    moves.append({"from": (r, c), "to": (dest, c), "val": val, "merge": True})
                    col_vals[dest] *= 2
                    gained += col_vals[dest]
                    last_merged = True
                else:
                    dest = target_r
                    moves.append({"from": (r, c), "to": (dest, c), "val": val, "merge": False})
                    col_vals.append(val)
                    target_r += 1
                    last_merged = False
            for r in range(len(col_vals)):
                new_grid[r][c] = col_vals[r]

    elif direction == "down":
        for c in range(4):
            target_r = 3
            last_merged = False
            col_vals = {}
            for r in [3, 2, 1, 0]:
                val = grid[r][c]
                if val == 0:
                    continue
                if target_r < 3 and not last_merged and col_vals.get(target_r + 1) == val:
                    dest = target_r + 1
                    moves.append({"from": (r, c), "to": (dest, c), "val": val, "merge": True})
                    col_vals[dest] *= 2
                    gained += col_vals[dest]
                    last_merged = True
                else:
                    dest = target_r
                    moves.append({"from": (r, c), "to": (dest, c), "val": val, "merge": False})
                    col_vals[dest] = val
                    target_r -= 1
                    last_merged = False
            for r, v in col_vals.items():
                new_grid[r][c] = v

    return moves, new_grid, gained


# Game instance & state
game = Game2048()
saved = app.load("state")
game.from_dict(saved)

# Animation & threading state
state_lock = threading.Lock()
is_animating = False
pending_direction = None
app_running = True


def save_state():
    app.save("state", game.to_dict())


def build_board_canvas(anim_moves=None, anim_p=None):
    shapes = []
    bg_color = "#25211E" if app.dark else "#BBADA0"
    shapes.append(nook.rect(0, 0, 180, 180, radius=6, fill=bg_color))

    cell_w, cell_h = 38, 38
    margin = 5
    gap = 6

    # 1. Background empty cell slots
    empty_cell_bg = "#38332E" if app.dark else "#CDC1B4"
    for r in range(4):
        for c in range(4):
            x = margin + c * (cell_w + gap)
            y = margin + r * (cell_h + gap)
            shapes.append(nook.rect(x, y, cell_w, cell_h, radius=4, fill=empty_cell_bg))

    # 2. Moving or static tiles
    if anim_moves and anim_p is not None:
        for m in anim_moves:
            fr_r, fr_c = m["from"]
            to_r, to_c = m["to"]
            val = m["val"]

            start_x = margin + fr_c * (cell_w + gap)
            start_y = margin + fr_r * (cell_h + gap)
            target_x = margin + to_c * (cell_w + gap)
            target_y = margin + to_r * (cell_h + gap)

            curr_x = round(start_x + (target_x - start_x) * anim_p, 1)
            curr_y = round(start_y + (target_y - start_y) * anim_p, 1)

            cfg = TILE_CONFIG.get(val, DEFAULT_TILE_CONFIG)
            shapes.append(nook.rect(curr_x, curr_y, cell_w, cell_h, radius=4, fill=cfg["bg"]))
            shapes.append(nook.label(
                round(curr_x + 19, 1), round(curr_y + 19, 1),
                str(val),
                size=cfg["size"],
                color=cfg["fg"],
                anchor="center",
                bold=True
            ))
    else:
        for r in range(4):
            for c in range(4):
                val = game.grid[r][c]
                if val == 0:
                    continue
                x = margin + c * (cell_w + gap)
                y = margin + r * (cell_h + gap)
                cfg = TILE_CONFIG.get(val, DEFAULT_TILE_CONFIG)
                shapes.append(nook.rect(x, y, cell_w, cell_h, radius=4, fill=cfg["bg"]))
                shapes.append(nook.label(
                    x + 19, y + 19,
                    str(val),
                    size=cfg["size"],
                    color=cfg["fg"],
                    anchor="center",
                    bold=True
                ))

    # 3. Game Over / Win overlays
    if game.game_over and not anim_moves:
        shapes.append(nook.rect(0, 0, 180, 180, radius=6, fill="#1B1917DD"))
        shapes.append(nook.label(90, 68, "GAME OVER", size=18, color="#FFFFFF", anchor="center", bold=True))
        shapes.append(nook.label(90, 96, f"Score: {game.score:,}", size=13, color="#EDE0C8", anchor="center"))
        shapes.append(nook.label(90, 122, "Click or press R to restart", size=11, color="dim", anchor="center"))
    elif game.won and not game.win_acknowledged and not anim_moves:
        shapes.append(nook.rect(0, 0, 180, 180, radius=6, fill="#EDC22EDD"))
        shapes.append(nook.label(90, 68, "YOU WIN!", size=20, color="#FFFFFF", anchor="center", bold=True))
        shapes.append(nook.label(90, 96, "2048 Reached!", size=13, color="#FFFFFF", anchor="center", bold=True))
        shapes.append(nook.label(90, 122, "Click to Continue", size=11, color="#FFFFFF", anchor="center"))

    return nook.canvas(height=180, width=180, id="board", shapes=shapes, tooltip="Arrow keys or click board to slide")


def build_page_view(anim_moves=None, anim_p=None):
    top_tile = game.max_tile()

    return nook.row([
        # 1. Left Section: Board Canvas & Subcaption
        nook.column([
            build_board_canvas(anim_moves=anim_moves, anim_p=anim_p),
            nook.text("Click board edges or use keys", size="small", color="dim"),
        ], gap=4, align="center"),

        # 2. Middle Section: Live Stats & D-Pad Controls
        nook.column([
            # Score Cards Row
            nook.row([
                nook.card([
                    nook.text("SCORE", size="small", color="dim", bold=True),
                    nook.text(f"{game.score:,}", size="body", bold=True),
                ], padding=4),
                nook.card([
                    nook.text("BEST", size="small", color="dim", bold=True),
                    nook.text(f"{game.best_score:,}", size="body", bold=True),
                ], padding=4),
                nook.card([
                    nook.text("TOP", size="small", color="dim", bold=True),
                    nook.text(str(top_tile), size="body", color="accent", bold=True),
                ], padding=4),
            ], gap=4),

            # D-pad & Controller Card
            nook.card([
                nook.column([
                    nook.row([
                        nook.spacer(),
                        nook.button("btn_up", icon="arrow-up", tooltip="Up (↑ / W)"),
                        nook.spacer(),
                    ]),
                    nook.row([
                        nook.button("btn_left", icon="arrow-left", tooltip="Left (← / A)"),
                        nook.button("btn_down", icon="arrow-down", tooltip="Down (↓ / S)"),
                        nook.button("btn_right", icon="arrow-right", tooltip="Right (→ / D)"),
                    ], gap=4, align="center"),
                ], gap=2, align="center"),
            ], padding=6),

            # Quick Actions Row
            nook.row([
                nook.button("btn_undo", label="Undo", icon="arrow-u-up-left", width=0, tooltip="Undo (Backspace / U)"),
                nook.button("btn_restart", label="Restart", icon="arrow-counter-clockwise", width=0, tooltip="New Game (R)"),
            ], gap=4),
        ], gap=4, align="center"),

        # 3. Right Section: Instructions & Keybinds
        nook.column([
            nook.card([
                # Instructions
                nook.column([
                    nook.row([
                        nook.icon("info", size=14, color="accent"),
                        nook.text("HOW TO PLAY", size="small", bold=True, color="accent"),
                    ], align="center", gap=4),
                    nook.text(
                        "Slide matching tiles into each other to merge them (2+2=4, 4+4=8...). Reach 2048 to win!",
                        size="small", color="dim", wrap=True
                    ),
                ], gap=2),

                nook.divider(),

                # Keybinds
                nook.column([
                    nook.row([
                        nook.icon("keyboard", size=14, color="accent"),
                        nook.text("KEYBINDS", size="small", bold=True, color="accent"),
                    ], align="center", gap=4),
                    nook.row([
                        nook.text("Move", size="small", color="dim"),
                        nook.spacer(),
                        nook.text("↑ ↓ ← → / WASD", size="small", bold=True, mono=True),
                    ], align="center"),
                    nook.row([
                        nook.text("Undo", size="small", color="dim"),
                        nook.spacer(),
                        nook.text("Backspace / U", size="small", bold=True, mono=True),
                    ], align="center"),
                    nook.row([
                        nook.text("Restart", size="small", color="dim"),
                        nook.spacer(),
                        nook.text("R", size="small", bold=True, mono=True),
                    ], align="center"),
                    nook.row([
                        nook.text("Close", size="small", color="dim"),
                        nook.spacer(),
                        nook.text("Esc", size="small", bold=True, mono=True),
                    ], align="center"),
                ], gap=3),
            ], padding=6, gap=4),
        ], gap=4, align="center"),
    ], gap=8, align="center")


PAGE_ACTIONS = [
    {"id": "undo", "icon": "arrow-u-up-left", "tooltip": "Undo move (Backspace / U)"},
    {"id": "restart", "icon": "arrow-counter-clockwise", "tooltip": "New game (R)"},
]


def draw():
    top_tile = game.max_tile()
    size = app.tile_size or "wide"

    # Tile view
    if size == "small":
        tile_view = nook.column([
            nook.icon("grid-four", size=18, color="accent"),
            nook.text(str(top_tile if top_tile > 0 else "2048"), size="small", bold=True),
        ], align="center", justify="center", gap=1)
    elif size == "large":
        tile_view = nook.column([
            nook.row([
                nook.icon("grid-four", size=20, color="accent"),
                nook.text("2048", size="title", bold=True),
            ], align="center", gap=6),
            nook.text(f"Score: {game.score:,}", size="body", bold=True),
            nook.text(f"Best: {game.best_score:,}", size="small", color="dim"),
            nook.row([
                nook.button("tile_restart", icon="arrow-counter-clockwise", tooltip="New Game"),
                nook.button("tile_play", label="Play", icon="game-controller", primary=True, width=0, tooltip="Open 2048"),
            ], gap=6),
        ], align="center", justify="center", gap=4)
    else:  # "wide"
        tile_view = nook.row([
            nook.icon("grid-four", size=26, color="accent"),
            nook.column([
                nook.text("2048", size="title", bold=True),
                nook.text(f"{game.score:,} pts", size="small", color="dim"),
            ], gap=0),
        ], align="center", gap=8)

    app.tile(tile_view)

    # Page view
    app.page(build_page_view(), actions=PAGE_ACTIONS)

    # Badge updates
    if game.won and not game.win_acknowledged:
        app.badge_glyph("trophy")
    else:
        app.clear_badge()


def _run_slide_animation(moves, new_grid, gained):
    global is_animating, pending_direction
    frames = 4
    duration = 0.09  # 90 ms smooth glide
    step_time = duration / frames

    for f in range(1, frames + 1):
        t = f / frames
        # Quadratic ease-out
        p = 1 - (1 - t) * (1 - t)
        app.page(build_page_view(anim_moves=moves, anim_p=p), actions=PAGE_ACTIONS)
        if f < frames:
            time.sleep(step_time)

    with state_lock:
        game.grid = new_grid
        game.score += gained
        if game.score > game.best_score:
            game.best_score = game.score
        game.spawn_tile()
        if game.max_tile() >= 2048 and not game.won:
            game.won = True
        game._check_game_over()
        save_state()
        is_animating = False

        next_dir = pending_direction
        pending_direction = None

    draw()

    if next_dir:
        trigger_move(next_dir)


def trigger_move(direction):
    global is_animating, pending_direction

    if game.game_over:
        return

    with state_lock:
        if is_animating:
            pending_direction = direction
            return

        moves, new_grid, gained = calculate_slide(game.grid, direction)
        if new_grid == game.grid:
            return

        game.history = (copy.deepcopy(game.grid), game.score)
        is_animating = True

    threading.Thread(target=_run_slide_animation, args=(moves, new_grid, gained), daemon=True).start()


def trigger_undo():
    global is_animating, pending_direction
    with state_lock:
        if is_animating:
            return
        if game.undo():
            save_state()
    draw()


def trigger_restart():
    global is_animating, pending_direction
    with state_lock:
        is_animating = False
        pending_direction = None
        game.reset()
        save_state()
    draw()


# Canvas interaction handler
@app.on("board")
def handle_board_click(event):
    if game.game_over:
        trigger_restart()
        return

    if game.won and not game.win_acknowledged:
        with state_lock:
            game.win_acknowledged = True
            save_state()
        draw()
        return

    val = event.get("value")
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except Exception:
            val = {}
    elif not isinstance(val, dict):
        val = {}

    x = val.get("x", 90)
    y = val.get("y", 90)
    dx = x - 90
    dy = y - 90

    if abs(dx) > abs(dy):
        if dx > 15:
            trigger_move("right")
        elif dx < -15:
            trigger_move("left")
    else:
        if dy > 15:
            trigger_move("down")
        elif dy < -15:
            trigger_move("up")


# Direction button handlers
@app.on("btn_up")
def on_btn_up(event):
    trigger_move("up")


@app.on("btn_down")
def on_btn_down(event):
    trigger_move("down")


@app.on("btn_left")
def on_btn_left(event):
    trigger_move("left")


@app.on("btn_right")
def on_btn_right(event):
    trigger_move("right")


# Action button handlers
@app.on("btn_restart")
def on_btn_restart(event):
    trigger_restart()


@app.on("restart")
def on_action_restart(event):
    trigger_restart()


@app.on("tile_restart")
def on_tile_restart(event):
    trigger_restart()


@app.on("btn_undo")
def on_btn_undo(event):
    trigger_undo()


@app.on("undo")
def on_action_undo(event):
    trigger_undo()


@app.on("tile_play")
def on_tile_play(event):
    app.open_page()


# Nook lifecycle messages
@app.on_message("hotkey")
def on_hotkey(msg):
    app.open_page()


@app.on_message("theme")
def on_theme(msg):
    draw()


@app.on_message("layout")
def on_layout(msg):
    draw()


@app.on_message("shutdown")
def on_shutdown(msg):
    global app_running
    app_running = False


# Keyboard listener thread (active only while page_open is True)
def keyboard_listener_loop():
    user32 = ctypes.windll.user32

    # Virtual key mappings
    dir_keys = {
        0x25: "left",    # Arrow Left
        0x26: "up",      # Arrow Up
        0x27: "right",   # Arrow Right
        0x28: "down",    # Arrow Down
        0x41: "left",    # A
        0x57: "up",      # W
        0x44: "right",   # D
        0x53: "down",    # S
    }

    action_keys = {
        0x08: "undo",    # Backspace
        0x55: "undo",    # U
        0x52: "restart", # R
        0x1B: "esc",     # Escape
    }

    down_keys = set()

    while app_running:
        if not app.page_open:
            time.sleep(0.08)
            continue

        # Check directional keys
        for vk, direction in dir_keys.items():
            pressed = bool(user32.GetAsyncKeyState(vk) & 0x8000)
            if pressed and vk not in down_keys:
                down_keys.add(vk)
                trigger_move(direction)
            elif not pressed and vk in down_keys:
                down_keys.discard(vk)

        # Check action keys
        for vk, act in action_keys.items():
            pressed = bool(user32.GetAsyncKeyState(vk) & 0x8000)
            if pressed and vk not in down_keys:
                down_keys.add(vk)
                if act == "undo":
                    trigger_undo()
                elif act == "restart":
                    trigger_restart()
                elif act == "esc":
                    app.close_page()
            elif not pressed and vk in down_keys:
                down_keys.discard(vk)

        time.sleep(0.015)


threading.Thread(target=keyboard_listener_loop, daemon=True).start()

# Initial render and run
draw()
app.run()
