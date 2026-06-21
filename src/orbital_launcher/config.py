"""Orbital Launcher — configuration, constants, and paths.

Uses XDG_DATA_HOME for runtime data (apps_cache.json, state.json)
with automatic migration from the legacy rice directory on first run.
"""

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Runtime data paths (XDG standard) ──────────────────────────────

_XDG_DATA = Path(
    os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")
)
DATA_DIR = _XDG_DATA / "orbital-launcher"
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
    inner_radius: float = 180
    outer_radius: float = 350
    lat_min: float = -60  # degrees
    lat_max: float = 60
    speed_min: float = 0.3  # degrees/sec
    speed_max: float = 0.8
    drift_rate: float = 3.0  # degrees/sec natural orbit

    # Camera / projection — near-orthographic for uniform icon sizes
    camera_distance: float = 1500   # moderate distance → visible but restrained depth
    camera_offset: float = 0        # no bias

    # Rendering
    base_icon_size: float = 44       # logical px; multiplied by dpi_scale at runtime (≥44 per WCAG 2.5.5)
    omega_font_size: float = 220     # large — the centerpiece anchor; scaled by dpi

    # Central image — replace the omega glyph with a custom PNG
    central_image_path: Optional[str] = "GOW_Omega.png"  # filename in ~/Pictures, ~/path, or absolute
    central_image_size: float = 220           # display size in logical px; scaled by dpi

    label_font_size: float = 14               # scaled by dpi at render time
    alpha_min: float = 0.20
    alpha_max: float = 1.0
    filtered_alpha: float = 0.08
    hover_scale: float = 1.30
    search_bar_height: float = 40
    search_bar_width: float = 420
    search_bar_margin_top: float = 18
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
