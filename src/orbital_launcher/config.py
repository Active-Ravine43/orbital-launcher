"""Orbital Launcher — configuration, constants, and paths.

Uses XDG_DATA_HOME for runtime data (apps_cache.json, state.json)
with automatic migration from the legacy rice directory on first run.

User overrides live in ``$XDG_CONFIG_HOME/orbital-launcher/config`` —
a simple KEY = VALUE file (like .env).  Edit it by hand, then restart
the launcher.  If the file is missing, it is created with documented
defaults.
"""

import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Runtime data paths (XDG standard) ──────────────────────────────

_XDG_DATA = Path(
    os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")
)
_XDG_CONFIG = Path(
    os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
)

DATA_DIR = _XDG_DATA / "orbital-launcher"
CONFIG_DIR = _XDG_CONFIG / "orbital-launcher"
CONFIG_FILE = CONFIG_DIR / "config"

CACHE_FILE = DATA_DIR / "apps_cache.json"
STATE_FILE = DATA_DIR / "state.json"
PID_FILE = "/tmp/orbital-launcher.pid"

DESKTOP_DIRS = [
    Path("/usr/share/applications"),
    Path.home() / ".local/share/applications",
]

# Legacy path — used for one-time migration
_LEGACY_DIR = Path.home() / ".config/rices/omega-blackred/orbital-launcher"


def _migrate_data():
    """Copy legacy data from the rice config directory if XDG path is empty."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for fname in ("apps_cache.json", "state.json"):
        new_path = DATA_DIR / fname
        old_path = _LEGACY_DIR / fname
        if old_path.exists() and not new_path.exists():
            try:
                shutil.copy2(old_path, new_path)
            except OSError:
                pass


# Run migration at import time — transparent, no user intervention needed
_migrate_data()


# ── Tunable constants ───────────────────────────────────────────────

@dataclass
class Cfg:
    """Tunable constants for the orbital launcher."""

    # Sphere
    inner_radius: float = 240
    outer_radius: float = 440
    lat_min: float = -60  # degrees
    lat_max: float = 60
    speed_min: float = 0.3  # degrees/sec
    speed_max: float = 0.8
    drift_rate: float = 3.0  # degrees/sec natural orbit

    # Camera / projection — near-orthographic for uniform icon sizes
    camera_distance: float = 1500   # moderate distance → visible but restrained depth
    camera_offset: float = 0        # no bias

    # Rendering
    base_icon_size: float = 36       # logical px; multiplied by dpi_scale at runtime
    omega_font_size: float = 220     # large — the centerpiece anchor; scaled by dpi

    # Central image — replace the omega glyph with a custom PNG
    central_image_path: Optional[str] = "GOW_Omega.png"  # filename in ~/Pictures, ~/path, or absolute
    central_image_size: float = 280           # display size in logical px; scaled by dpi

    # Icon theme — empty string = system default
    icon_theme_name: str = ""

    label_font_size: float = 14               # scaled by dpi at render time
    alpha_min: float = 0.30
    alpha_max: float = 1.0
    filtered_alpha: float = 0.08
    hover_scale: float = 1.30
    search_bar_height: float = 40
    search_bar_width: float = 420
    search_bar_margin_top: float = 18
    search_bar_corner_radius: float = 0       # 0 = rigid (default), 8 = rounded
    icon_scale_floor: float = 0.45  # minimum scale — keeps icons ≥~20px at 44 base

    # Interaction
    drag_sensitivity: float = 0.5  # degrees per pixel (snappy)
    scroll_sensitivity: float = 0.10
    zoom_min: float = 0.3
    zoom_max: float = 3.0

    # Animation
    fps_active_interval: int = 16      # ms (~60fps) when sphere visible
    fps_idle_interval: int = 1000      # ms (1fps) when sphere hidden

    # Misc
    scanlines_enabled: bool = False  # toggle CRT scanline effect
    scanline_opacity: float = 0.03

    # Runtime — set at startup
    dpi_scale: float = 1.0
    reduced_motion: bool = False  # set from GTK animation setting


cfg = Cfg()


# ═══════════════════════════════════════════════════════════════════════
# User config file (KEY = VALUE, like .env)
# ═══════════════════════════════════════════════════════════════════════

_DEFAULT_CONFIG = """\
# Orbital Launcher — user configuration
# Edit this file and restart the launcher for changes to take effect.
# Lines starting with # are ignored.

# ── Visual ──────────────────────────────────────────────────────────

# Path to a custom center image (PNG).  Leave empty for the omega glyph.
# Supports absolute paths, ~/ paths, or filenames in ~/Pictures/
central_image = GOW_Omega.png

# Center image display size in logical pixels (64–400)
central_image_size = 280

# Accent colour: a hex colour (#E61919), or "system" to detect from GTK theme
accent_color = #E61919

# Icon theme name.  Leave empty to use the system default.
icon_theme =

# Base icon size in logical pixels (24–96)
icon_size = 36

# Search bar width in logical pixels (200–800)
search_bar_width = 420

# Search bar corners: "rigid" (0 px, sharp) or "rounded" (8 px radius)
search_bar_corners = rigid

# CRT scanline overlay: "on" or "off"
scanlines = off

# ── Orbital ─────────────────────────────────────────────────────────

# Distance from center: inner shell radius (80–300)
inner_radius = 240

# Distance from center: outer shell radius (200–600)
outer_radius = 440

# Natural orbit drift speed in degrees/second (0 = no drift, 10 = fast)
drift_rate = 3.0
"""


# ── System accent detection ─────────────────────────────────────────

# Known GTK themes mapped to their accent colours (fallback lookup).
_THEME_ACCENT_MAP = {
    "Adwaita": "#3584E4",
    "Adwaita-dark": "#3584E4",
    "Breeze": "#3DAEE9",
    "Breeze-Dark": "#3DAEE9",
    "Arc": "#5294E2",
    "Arc-Dark": "#5294E2",
    "Arc-Darker": "#5294E2",
    "Numix": "#F0544C",
    "Matcha": "#76A97A",
    "Matcha-dark": "#76A97A",
    "Yaru": "#E95420",
    "Yaru-dark": "#E95420",
    "Pop": "#48B9C7",
    "Pop-dark": "#48B9C7",
    "Nordic": "#88C0D0",
    "Nordic-darker": "#88C0D0",
    "Catppuccin-Mocha": "#F5C2E7",
    "Catppuccin-Latte": "#DC8A78",
    "Catppuccin-Frappe": "#F2D5CF",
    "Catppuccin-Macchiato": "#F4DBD6",
    "Tokyonight": "#7AA2F7",
    "Everforest": "#A7C080",
}


def _detect_system_accent() -> Optional[str]:
    """Try to extract the user's GTK theme accent colour.

    Checks, in order:
    1. ``~/.config/gtk-3.0/gtk.css`` for ``@define-color accent_color``
       or ``@define-color selected_bg_color``.
    2. ``~/.config/gtk-4.0/gtk.css`` (same strategy).
    3. Known theme preset via ``Gtk.Settings:gtk-theme-name``.
    4. Returns ``None`` if detection fails.
    """
    css_paths = [
        Path.home() / ".config/gtk-3.0/gtk.css",
        Path.home() / ".config/gtk-4.0/gtk.css",
    ]

    for css_path in css_paths:
        try:
            if css_path.exists():
                text = css_path.read_text()
                # Look for: @define-color accent_color #RRGGBB;
                for var in ("accent_color", "selected_bg_color",
                            "accent_bg_color"):
                    m = re.search(
                        rf'@define-color\s+{var}\s+(#[0-9A-Fa-f]{{6}})',
                        text,
                    )
                    if m:
                        return m.group(1)
        except Exception:
            pass

    # Fallback: known theme presets via GTK settings
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk
        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings:
            theme_name = gtk_settings.get_property("gtk-theme-name")
            if theme_name and theme_name in _THEME_ACCENT_MAP:
                return _THEME_ACCENT_MAP[theme_name]
    except Exception:
        pass

    return None


# ═══════════════════════════════════════════════════════════════════════
# Config loader
# ═══════════════════════════════════════════════════════════════════════


def load_user_config():
    """Parse the user config file and apply settings to ``cfg`` and ``palette``.

    If the config file doesn't exist it is created with documented defaults.
    Unknown keys are silently ignored.  Malformed values print a warning to
    stderr and fall back to their defaults.
    """
    from .colors import palette

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Seed the file if missing
    if not CONFIG_FILE.exists():
        try:
            CONFIG_FILE.write_text(_DEFAULT_CONFIG)
            print(
                f"[orbital-launcher] Config file created at {CONFIG_FILE}",
                file=sys.stderr,
            )
        except OSError as e:
            print(
                f"[orbital-launcher] Could not write config file: {e}",
                file=sys.stderr,
            )

    # Parse
    raw: dict[str, str] = {}
    try:
        for line in CONFIG_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            raw[key.strip()] = value.strip()
    except Exception as e:
        print(
            f"[orbital-launcher] Could not read config file: {e}  "
            f"Using defaults.",
            file=sys.stderr,
        )
        return

    print(
        f"[orbital-launcher] Loaded config from {CONFIG_FILE}",
        file=sys.stderr,
    )

    # ── Apply each key ──────────────────────────────────────────

    # --- accent_color ---
    accent_val = raw.get("accent_color", "#E61919")
    if accent_val.lower() == "system":
        detected = _detect_system_accent()
        if detected:
            try:
                palette.set_accent(detected)
                print(
                    f"[orbital-launcher] System accent detected: {detected}",
                    file=sys.stderr,
                )
            except ValueError:
                print(
                    f"[orbital-launcher] Detected accent '{detected}' invalid; "
                    f"using default.",
                    file=sys.stderr,
                )
        else:
            print(
                "[orbital-launcher] System accent detection failed; "
                "using default aviation red.",
                file=sys.stderr,
            )
    else:
        try:
            palette.set_accent(accent_val)
            print(
                f"[orbital-launcher] Accent colour: {accent_val}",
                file=sys.stderr,
            )
        except ValueError:
            print(
                f"[orbital-launcher] Invalid accent colour '{accent_val}'; "
                f"using default.",
                file=sys.stderr,
            )

    # --- icon_theme ---
    icon_theme_val = raw.get("icon_theme", "")
    cfg.icon_theme_name = icon_theme_val
    if icon_theme_val:
        print(
            f"[orbital-launcher] Icon theme: {icon_theme_val}",
            file=sys.stderr,
        )

    # --- central_image ---
    central_val = raw.get("central_image", "")
    # Allow empty string to mean "no image → omega glyph"
    cfg.central_image_path = central_val if central_val else None
    if cfg.central_image_path:
        print(
            f"[orbital-launcher] Center image: {cfg.central_image_path}",
            file=sys.stderr,
        )
    else:
        print(
            "[orbital-launcher] Center image: omega glyph (native)",
            file=sys.stderr,
        )

    # --- central_image_size ---
    cfg.central_image_size = _parse_float(
        raw, "central_image_size", 220, 64, 400
    )
    print(
        f"[orbital-launcher] Center image size: {cfg.central_image_size}",
        file=sys.stderr,
    )

    # --- icon_size ---
    cfg.base_icon_size = _parse_float(raw, "icon_size", 44, 24, 96)

    # --- search_bar_width ---
    cfg.search_bar_width = _parse_float(raw, "search_bar_width", 420, 200, 800)

    # --- search_bar_corners ---
    corners_val = raw.get("search_bar_corners", "rigid").lower()
    if corners_val == "rounded":
        cfg.search_bar_corner_radius = 8
    else:
        cfg.search_bar_corner_radius = 0  # rigid
    print(
        f"[orbital-launcher] Search bar corners: "
        f"{'rounded' if cfg.search_bar_corner_radius > 0 else 'rigid'}",
        file=sys.stderr,
    )

    # --- scanlines ---
    scan_val = raw.get("scanlines", "off").lower()
    cfg.scanlines_enabled = scan_val in ("on", "true", "yes", "1")
    if cfg.scanlines_enabled:
        print("[orbital-launcher] Scanlines: on", file=sys.stderr)

    # --- inner_radius ---
    cfg.inner_radius = _parse_float(raw, "inner_radius", 180, 80, 300)

    # --- outer_radius ---
    cfg.outer_radius = _parse_float(raw, "outer_radius", 350, 200, 600)

    # --- drift_rate ---
    cfg.drift_rate = _parse_float(raw, "drift_rate", 3.0, 0, 10)

    # Honour reduced-motion override: if drift was already zeroed by
    # reduced-motion detection, keep it zero regardless of config.
    # (reduced_motion is set later in app.py — this sets the starting point)


def _parse_float(
    raw: dict[str, str],
    key: str,
    default: float,
    lo: float,
    hi: float,
) -> float:
    """Parse a float from *raw*, clamped to [*lo*, *hi*]."""
    val_str = raw.get(key, str(default))
    try:
        val = float(val_str)
    except (ValueError, TypeError):
        print(
            f"[orbital-launcher] Invalid value for '{key}': {val_str!r} — "
            f"using default {default}",
            file=sys.stderr,
        )
        return default
    clamped = max(lo, min(hi, val))
    if clamped != val:
        print(
            f"[orbital-launcher] '{key}' value {val} clamped to {clamped}",
            file=sys.stderr,
        )
    return clamped
