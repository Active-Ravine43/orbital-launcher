"""Orbital Launcher — Tactical Telemetry Palette.

Industrial brutalist — CRT terminal dark mode.  All colours flow from here.
The Palette class holds base colours as mutable lists; derived alpha-baked
tuples are regenerated via ``recompute_derived()``.  Call ``palette.set_accent()``
to change the accent colour at runtime — all derived tuples update immediately.

Background: #0A0A0A (deactivated CRT, not pure black)
Foreground: #EAEAEA (white phosphor)
Accent:    #E61919 (aviation/hazard red) — default; overridable via config
"""


def _rgb(r: float, g: float, b: float, a: float = 1.0) -> tuple:
    return (r, g, b, a)


class Palette:
    """Mutable colour palette.

    Base colours are stored as lists so they can be updated in place.
    Derived alpha-baked tuples are recomputed after any base change.
    """

    def __init__(self):
        # ── Base colours (lists — mutated in place by set_accent) ──
        self.bg: list = [0.039, 0.039, 0.039, 1.0]       # #0A0A0A  void
        self.fg: list = [0.918, 0.918, 0.918, 1.0]        # #EAEAEA  phosphor white
        self.accent: list = [0.902, 0.098, 0.098, 1.0]    # #E61919  aviation red
        self.dim: list = [0.392, 0.392, 0.412, 1.0]       # #646469  muted telemetry
        self.surface: list = [0.059, 0.059, 0.071, 1.0]   # #0F0F12  elevated panel
        self.void: list = [0.020, 0.020, 0.020, 1.0]      # #050505  deep void

        # Derived alpha-baked tuples — populated by recompute_derived()
        self.bg_a75: tuple = ()
        self.bg_a85: tuple = ()
        self.bg_a90: tuple = ()
        self.fg_a10: tuple = ()
        self.fg_a50: tuple = ()
        self.fg_a70: tuple = ()
        self.fg_a90: tuple = ()
        self.fg_a95: tuple = ()
        self.accent_a40: tuple = ()
        self.accent_a50: tuple = ()
        self.accent_a70: tuple = ()
        self.accent_a80: tuple = ()
        self.surface_a85: tuple = ()
        self.surface_a90: tuple = ()

        self.recompute_derived()

    def recompute_derived(self):
        """Regenerate all alpha-baked tuples from current base colours."""
        self.bg_a75 = _rgb(*self.bg[:3], 0.75)
        self.bg_a85 = _rgb(*self.bg[:3], 0.85)
        self.bg_a90 = _rgb(*self.bg[:3], 0.90)
        self.fg_a10 = _rgb(*self.fg[:3], 0.10)
        self.fg_a50 = _rgb(*self.fg[:3], 0.50)
        self.fg_a70 = _rgb(*self.fg[:3], 0.70)
        self.fg_a90 = _rgb(*self.fg[:3], 0.90)
        self.fg_a95 = _rgb(*self.fg[:3], 0.95)
        self.accent_a40 = _rgb(*self.accent[:3], 0.40)
        self.accent_a50 = _rgb(*self.accent[:3], 0.50)
        self.accent_a70 = _rgb(*self.accent[:3], 0.70)
        self.accent_a80 = _rgb(*self.accent[:3], 0.80)
        self.surface_a85 = _rgb(*self.surface[:3], 0.85)
        self.surface_a90 = _rgb(*self.surface[:3], 0.90)

    def set_accent(self, hex_str: str):
        """Parse a hex colour like ``#E61919`` and update the accent.

        All derived alpha-baked tuples are recomputed automatically.
        """
        h = hex_str.lstrip("#")
        if len(h) != 6:
            raise ValueError(
                f"Accent colour must be 6-digit hex, got: {hex_str!r}"
            )
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        self.accent[:] = [r, g, b, 1.0]
        self.recompute_derived()

    def reset_to_default(self):
        """Restore the default aviation-red accent."""
        self.accent[:] = [0.902, 0.098, 0.098, 1.0]
        self.recompute_derived()


# Module-level singleton — import this everywhere:
#
#     from .colors import palette
#     cr.set_source_rgba(*palette.accent_a80)
#
palette = Palette()
