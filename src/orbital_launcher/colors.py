"""Orbital Launcher — Tactical Telemetry Palette.

Industrial brutalist — CRT terminal dark mode. All colors flow from here.
Background: #0A0A0A (deactivated CRT, not pure black)
Foreground: #EAEAEA (white phosphor)
Accent:    #E61919 (aviation/hazard red)
Terminal:  #4AF626 (single-use green, status only)
"""


def _rgb(r: float, g: float, b: float, a: float = 1.0) -> tuple:
    return (r, g, b, a)


CLR_BG = _rgb(0.039, 0.039, 0.039, 1.0)       # #0A0A0A  void
CLR_FG = _rgb(0.918, 0.918, 0.918, 1.0)        # #EAEAEA  phosphor white
CLR_ACCENT = _rgb(0.902, 0.098, 0.098, 1.0)    # #E61919  aviation red
CLR_DIM = _rgb(0.392, 0.392, 0.412, 1.0)       # #646469  muted telemetry
CLR_SURFACE = _rgb(0.059, 0.059, 0.071, 1.0)   # #0F0F12  elevated panel
CLR_VOID = _rgb(0.020, 0.020, 0.020, 1.0)      # #050505  deep void

# Derived: RGBA tuples with alpha baked in
CLR_BG_A75 = _rgb(*CLR_BG[:3], 0.75)
CLR_BG_A85 = _rgb(*CLR_BG[:3], 0.85)
CLR_BG_A90 = _rgb(*CLR_BG[:3], 0.90)
CLR_FG_A10 = _rgb(*CLR_FG[:3], 0.10)
CLR_FG_A50 = _rgb(*CLR_FG[:3], 0.50)
CLR_FG_A70 = _rgb(*CLR_FG[:3], 0.70)
CLR_FG_A90 = _rgb(*CLR_FG[:3], 0.90)
CLR_FG_A95 = _rgb(*CLR_FG[:3], 0.95)
CLR_ACCENT_A40 = _rgb(*CLR_ACCENT[:3], 0.40)
CLR_ACCENT_A50 = _rgb(*CLR_ACCENT[:3], 0.50)
CLR_ACCENT_A70 = _rgb(*CLR_ACCENT[:3], 0.70)
CLR_ACCENT_A80 = _rgb(*CLR_ACCENT[:3], 0.80)
CLR_SURFACE_A85 = _rgb(*CLR_SURFACE[:3], 0.85)
CLR_SURFACE_A90 = _rgb(*CLR_SURFACE[:3], 0.90)
