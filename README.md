# 2048 Game for Nook

A sleek, native 2048 puzzle game built for [Nook](https://nooknotch.xyz/), the floating notch panel for Windows.

## Layout

- **Left**: Interactive 4×4 canvas board with fluid 90ms sliding animations.
- **Center**: Live stats (Score, Best, Top Tile), tactile D-pad cluster, and Undo & Restart action buttons.
- **Right**: Complete **How to Play** instructions and **Keybinds** reference.

## Controls & Keybinds

| Action | Keybinds / Input |
|---|---|
| **Move / Slide** | <kbd>←</kbd> <kbd>↑</kbd> <kbd>→</kbd> <kbd>↓</kbd> or <kbd>W</kbd> <kbd>A</kbd> <kbd>S</kbd> <kbd>D</kbd> or click board edges |
| **Undo Move** | <kbd>Backspace</kbd> or <kbd>U</kbd> or click Undo button |
| **Restart Game** | <kbd>R</kbd> or click Restart button |
| **Toggle Notch** | <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>G</kbd> (Global Windows hotkey) |
| **Close Panel** | <kbd>Esc</kbd> |

## Features

- **Sliding Animations**: Smooth 90ms ease-out glide animation on every move with chained input queuing.
- **Theme-Aware Aesthetics**: Tailored palette for both dark and light modes matching classic 2048 colors.
- **State Persistence**: Current board, score, and best score are saved in `NOOK_DATA_DIR` so your game is preserved across sessions.
- **Adaptive Tile Sizes**: Small (44×44), Wide (104×36), and Large (104×104) tile configurations in the notch.

## Testing

```bash
python check_plugin.py "c:\dev\code\nook games\2048"
```
