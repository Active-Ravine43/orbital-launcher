# Orbital Launcher

**3D Spherical Icon Cloud — an industrial brutalist application launcher for Linux.**

Renders all your installed applications as icons floating in a 3D spherical cloud orbiting a central Omega symbol. Built with GTK4 + Cairo on Wayland (X11 fallback).

![Orbital Launcher](GOW_Omega.png)

## Design

**Industrial brutalist** — raw, honest, structurally expressed. Dark CRT void background, aviation red accent, monospace typography, zero rounded corners, zero shadows. Every element is justified by function.

- **3D icon cloud** — Icons placed on deterministic fixed vertices of an icosidodecahedron (Archimedean solid, 30 vertices, up to 3 concentric shells)
- **Spatial memory** — Every app gets a fixed vertex. Your apps are always in the same 3D position
- **Keyboard-first** — Arrow keys navigate, Tab cycles, typing filters. Full accessibility announcements via ATK
- **Kinetic presence** — Natural drift rotation. Drag to rotate, scroll to zoom, click to launch
- **Smart CPU usage** — 60fps when visible, 1fps when hidden (near-zero idle cost)

## Dependencies

### Arch Linux
```bash
sudo pacman -S gtk4 python-cairo python-gobject
# Optional — layer-shell overlay mode (recommended for Wayland):
sudo pacman -S gtk4-layer-shell
```

### Other distributions
- Python ≥ 3.10
- GTK 4
- PyGObject (`python-gobject` / `python3-gi`)
- PyCairo (`python-cairo` / `python3-cairo`)
- Optional: `gtk4-layer-shell` for Wayland background layer support

## Installation

```bash
git clone git@github.com:Active-Ravine43/orbital-launcher.git
cd orbital-launcher
```

No build step required. Runs directly with Python.

## Usage

### Quick start

```bash
python launcher.py &
```

### Toggle with a keybind (recommended)

Bind a key (e.g. Super+O) to run `toggle.sh`:

**Hyprland** (`~/.config/hypr/hyprland.conf`):
```
bind = SUPER, O, exec, /path/to/orbital-launcher/toggle.sh
```

**Sway** (`~/.config/sway/config`):
```
bindsym $mod+o exec /path/to/orbital-launcher/toggle.sh
```

The `toggle.sh` script auto-locates `launcher.py` relative to itself — works from any clone location.

### Controls

| Action | Input |
|---|---|
| Rotate sphere | Click + drag |
| Zoom in/out | Scroll wheel |
| Launch app | Click icon |
| Search apps | Type anywhere |
| Navigate focus | Arrow keys |
| Cycle results | Tab |
| Launch focused | Enter |
| Clear / dismiss | Escape |

## Configuration

Edit `src/orbital_launcher/config.py` — the `Cfg` dataclass contains all tunable constants. No settings UI by design.

Notable options:
- `central_image_path` — replace the Omega glyph with a custom PNG image
- `scanlines_enabled` — toggle CRT scanline overlay
- `drift_rate` — natural orbit speed (set to 0 to disable)
- `base_icon_size` — icon size at rest (44px default, ≥44 for WCAG 2.5.5)

## Project Structure

```
orbital-launcher/
├── launcher.py              # entry point
├── toggle.sh                # keybind helper
├── src/
│   └── orbital_launcher/    # Python package
│       ├── app.py           # GTK4 application
│       ├── renderer.py      # Cairo drawing
│       ├── icons.py         # icon loading + fallbacks
│       ├── scanner.py       # .desktop file parser
│       ├── lattice.py       # icosidodecahedron geometry
│       ├── math3d.py        # 3D rotation & projection
│       ├── state.py         # runtime state + persistence
│       ├── config.py        # configuration + paths
│       └── colors.py        # color palette
├── DESIGN.md                # full design system spec
├── PRODUCT.md               # product brief
└── .impeccable/             # design tokens (impeccable tool)
```

## License

MIT — see [LICENSE](LICENSE).
