"""Orbital Launcher — mutable runtime state with launch-count persistence."""

import json
import os
from typing import Optional

from .config import STATE_FILE
from .icons import IconEntry


class OrbitalState:
    """Mutable runtime state for the orbital launcher."""

    def __init__(self):
        self.icons: list[IconEntry] = []
        self.visible: bool = True
        self.zoom: float = 1.0
        self.rotation_lon: float = 0.0  # manual drag offset
        self.rotation_lat: float = 0.0  # manual drag offset (tilt)
        self.time_elapsed: float = 0.0
        self.search_query: str = ""
        self.search_focused: bool = False
        self.hovered_icon: Optional[IconEntry] = None
        self.focused_icon: Optional[IconEntry] = None  # keyboard focus
        self.dragging: bool = False
        self.launch_counts: dict[str, int] = {}

    def load_state(self):
        """Load persisted launch counts. Seeds file if missing."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE) as fh:
                    self.launch_counts = json.load(fh)
            except Exception:
                self.launch_counts = {}
        else:
            self.launch_counts = {}
            self.save_state()  # seed the file

    def save_state(self):
        """Save launch counts to disk."""
        try:
            with open(STATE_FILE, "w") as fh:
                json.dump(self.launch_counts, fh, indent=2)
        except Exception:
            pass

    def increment_launch(self, desktop_file: str):
        key = os.path.basename(desktop_file)
        self.launch_counts[key] = self.launch_counts.get(key, 0) + 1
        self.save_state()
