"""Orbital Launcher — Fibonacci sphere vertex lattice.

Uniform distribution of points on the unit sphere via the golden-angle
Fibonacci spiral.  Every point is nearly equidistant from its neighbours
at any count — no pole clumping, no visible grid lines.

The entire lattice rotates as a RIGID BODY — no point ever shifts
relative to another.  Drag = rotate the sphere.  Period.

We precompute 200 points at import time.  Each app gets a deterministic
vertex from this set (by sort index, modulo 200).  All icons sit on a
single sphere at the midpoint between ``inner_radius`` and
``outer_radius`` — no more concentric shells.
"""

import math

from .config import cfg

# Golden ratio
_PHI = (1 + math.sqrt(5)) / 2

# Number of points on the Fibonacci sphere.  200 is far more than any
# realistic desktop app collection; round-robin sharing kicks in beyond
# this count with virtually no visible collision.
_N = 200


def _build_fibonacci_sphere(n: int) -> list[tuple[float, float, float]]:
    """Return *n* (x, y, z) tuples evenly distributed on the unit sphere
    using the Fibonacci lattice (golden-angle spiral)."""
    points = []
    for i in range(n):
        # Latitude: uniform from +1 (north pole) to -1 (south pole)
        y = 1.0 - (2.0 * i + 1.0) / n
        # Radius of the latitude circle at this y
        r = math.sqrt(max(0.0, 1.0 - y * y))
        # Golden-angle increment ensures each new point lands in the
        # largest remaining gap
        theta = 2.0 * math.pi * _PHI * i
        x = r * math.cos(theta)
        z = r * math.sin(theta)
        points.append((x, y, z))
    return points


FIBONACCI_SPHERE: list[tuple[float, float, float]] = _build_fibonacci_sphere(_N)


def deterministic_params(app_name: str, index: int, total: int) -> dict:
    """Deterministic orbital parameters for an app.

    Position is a fixed vertex of the Fibonacci sphere.
    Every app orbits at the same radius — the midpoint of the configured
    inner/outer range.  Speed and phase are ZERO: the lattice is a rigid
    body; the only motion is shared rotation (drag + drift).
    """
    x, y, z = FIBONACCI_SPHERE[index % len(FIBONACCI_SPHERE)]

    # Single sphere — radius scales with √(app count) so the sphere
    # grows naturally as more apps are installed
    baseline = (cfg.inner_radius + cfg.outer_radius) / 2
    scale = math.sqrt(max(1, total) / 30)
    radius = baseline * scale

    return {
        "x": x,
        "y": y,
        "z": z,
        "radius": radius,
        "speed": 0.0,    # rigid body — no per-vertex drift
        "phase": 0.0,    # rigid body — vertex stays put
        "shell": 0,      # single sphere — no shells
    }
