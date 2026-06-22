"""Orbital Launcher — Fibonacci sphere vertex lattice.

Uniform distribution of exactly N points on the unit sphere via the
golden-angle Fibonacci spiral.  Every point is nearly equidistant from
its neighbours at any count — no pole clumping, no visible grid lines.

Points are generated on-the-fly for the actual app count — no pre-computed
set, no subsampling.  The whole lattice rotates as a RIGID BODY — no point
ever shifts relative to another.  Drag = rotate the sphere.  Period.
"""

import math

from .config import cfg

# Golden ratio
_PHI = (1 + math.sqrt(5)) / 2


def _fibonacci_point(index: int, total: int) -> tuple[float, float, float]:
    """Return (x, y, z) on the unit sphere for point *index* of *total*.

    Uses the Fibonacci lattice (golden-angle spiral) so every point is
    nearly equidistant from its neighbours — no pole clumping, no swirl.
    """
    y = 1.0 - (2.0 * index + 1.0) / total
    r = math.sqrt(max(0.0, 1.0 - y * y))
    theta = 2.0 * math.pi * _PHI * index
    x = r * math.cos(theta)
    z = r * math.sin(theta)
    return (x, y, z)


def deterministic_params(app_name: str, index: int, total: int) -> dict:
    """Deterministic orbital parameters for an app.

    Position is a fixed vertex of the Fibonacci sphere.  Every app orbits
    at the same radius — the midpoint of the configured inner/outer range.
    Speed and phase are ZERO: the lattice is a rigid body; the only motion
    is shared rotation (drag + drift).
    """
    # Generate exactly N points for N apps — even distribution, no swirl
    x, y, z = _fibonacci_point(index, total)

    # Single sphere — radius scales proportional to √(app count) so
    # the sphere is always dense enough to read as a full 3D sphere,
    # not a sparse dome.  inner_radius sets the density multiplier.
    scale = math.sqrt(max(1, total))
    radius = cfg.inner_radius * scale
    # Clamp to outer_radius as an upper bound for very large collections
    if radius > cfg.outer_radius:
        radius = cfg.outer_radius

    return {
        "x": x,
        "y": y,
        "z": z,
        "radius": radius,
        "speed": 0.0,    # rigid body — no per-vertex drift
        "phase": 0.0,    # rigid body — vertex stays put
        "shell": 0,      # single sphere — no shells
    }
