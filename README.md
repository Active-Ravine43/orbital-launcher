# Orbital App Launcher

A 3D spherical icon-cloud application launcher for Linux. Desktop entries orbit a Fibonacci-sphere lattice around a central glyph — drag to rotate, type to filter, click to launch. Built for Wayland/Hyprland with GTK4, Cairo, and the layer-shell protocol.

![Orbital Launcher](.github/orbital-preview.png)

## Features

- **Fibonacci-sphere layout** — icons distributed at mathematically equidistant points; the whole sphere rotates as a rigid body.
- **Drag-to-rotate** — click and drag any axis. Momentum carries.
- **Search-as-you-type** — filter by `.desktop` entry name in real time. Non-matches fade to near-invisible.
- **Keyboard navigation** — arrow keys hop between visible icons via nearest-neighbor; Enter launches; Escape clears or dismisses.
- **SIGUSR1 toggle** — bind `toggle.sh` to a key in Hyprland. The launcher overlays without spawning a new process.
- **Multi-monitor** — one overlay per display. Each maintains independent rotation, zoom, and search state.
- **Auto-refresh** — detects `.desktop` file changes on each show. Newly installed apps appear without restart.
- **Launch-count persistence** — tracks frequency; state survives reboots.
- **App cache** — scanned `.desktop` entries serialized to JSON. First launch is instant, subsequent launches skip the walk.
- **CRT layer** — optional scanline and noise-grain overlays.
- **FPS adaptation** — 60 fps when visible, 1 fps when hidden. Zero CPU burn while idle.

## Visual Design

Industrial Brutalist — raw, structurally-expressed, no ornament. Near-black void (`#0A0A0A`), aviation hazard red (`#E61919`) as the sole accent, sharp 0px corner radius on every element, monospace typography throughout, and depth conveyed by alpha falloff and scale rather than shadows. Icons are recolored to red monochrome. Fallback icons render as a mechanical badge with an initial letter, a red-left-edge stripe, and a diagonal corner notch.

See [`DESIGN.md`](DESIGN.md) for the full design system.

## Requirements

| Dependency | Arch package |
|---|---|
| Python ≥ 3.10 | `python` |
| PyGObject (GTK4 bindings) | `python-gobject` |
| GTK4 | `gtk4` |
| GTK4 Layer Shell | `gtk4-layer-shell` |
| Cairo (Python) | `python-cairo` |

A Hyprland compositor is assumed but not strictly required — the launcher works on any wlroots-based Wayland compositor with layer-shell support.

## Installation

```bash
# 1. Install system dependencies (Arch / CachyOS)
sudo pacman -S python python-gobject gtk4 gtk4-layer-shell python-cairo

# 2. Clone into your rice directory (or anywhere you like)
git clone https://github.com/active-ravine43/orbital-launcher.git \
  ~/.config/rices/orbital-launcher

# 3. Copy and edit the config
cd ~/.config/rices/orbital-launcher
cp default_config config
# Edit `config` to set central_image, accent_color, etc.

# 4. Symlink the launcher script into PATH
mkdir -p ~/.local/bin
ln -s "$(pwd)/toggle.sh" ~/.local/bin/orbital-launcher
```

## Usage

### Launch directly

```bash
python ~/.config/rices/orbital-launcher/launcher.py
```

### Toggle with a keybind (Hyprland)

Add to `~/.config/hypr/hyprland.conf`:

```ini
bind = SUPER, O, exec, ~/.config/rices/orbital-launcher/toggle.sh
```

`toggle.sh` detects which monitor the cursor is on, sends `SIGUSR1` to the running instance, or spawns a new one if none is alive.

### Bar widget (Noctalia)

```json
{
  "widgetType": "CustomButton",
  "label": "Orbital App Launcher",
  "icon": "omega",
  "leftClickExec": "/home/<user>/.local/bin/orbital-launcher"
}
```

## Configuration

Edit the `config` file (key=value, one per line):

| Key | Default | Description |
|---|---|---|
| `central_image` | *empty* | Path to a PNG; empty draws the Omega glyph |
| `accent_color` | `#E61919` | Hex colour or `"system"` for GTK theme accent |
| `icon_theme` | `"system"` | System icon theme override |
| `icon_size` | `48` | Rendered icon size in px |
| `search_bar_width` | `320` | Search bar width in px |
| `inner_radius` | `0.4` | Inner sphere radius (fraction of viewport) |
| `outer_radius` | `0.9` | Outer sphere radius when fully zoomed out (fraction of viewport) |
| `drift_rate` | `0.0015` | Auto-rotation radians per frame |
| `scanlines` | `false` | Enable CRT scanline overlay |
| `toggle_animation_ms` | `200` | Show/hide animation duration in ms |

## Project Structure

```
orbital-launcher/
├── launcher.py          # Entry point
├── toggle.sh            # SIGUSR1 toggle script (bind to key)
├── config               # User configuration (gitignored)
├── default_config       # Tracked default config
├── DESIGN.md            # Design system
├── PRODUCT.md           # Product specification
├── README.md
├── LICENSE
└── src/
    ├── __init__.py      # Package init, version
    ├── __main__.py      # python -m orbital_launcher
    ├── app.py           # GTK4 Application + per-monitor views
    ├── config.py        # XDG paths, config parsing
    ├── colors.py        # Palette singleton
    ├── icons.py         # Icon loading, recolouring, fallback badges
    ├── renderer.py      # Cairo renderer — frame drawing
    ├── scanner.py       # .desktop file scanner + cache
    ├── lattice.py       # Fibonacci sphere vertex lattice
    ├── math3d.py        # 3D rotation + perspective projection
    └── state.py         # Mutable runtime state
```

## License

MIT — see [`LICENSE`](LICENSE).
