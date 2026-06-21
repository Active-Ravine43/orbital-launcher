"""Orbital Launcher — Icosidodecahedron fixed 3D vertex lattice.

Archimedean solid: 30 vertices, 60 edges, all edges identical length.
Every vertex has exactly 4 equidistant neighbours (1/φ ≈ 0.618 on the
unit sphere).  The whole lattice rotates as a RIGID BODY — no point
ever shifts relative to another.  Drag = rotate the sphere.  Period.

Generated from the 30 edge-midpoints of a regular icosahedron,
projected to the unit sphere.
"""

from .config import cfg

ICOSIDODECAHEDRON_3D: list[tuple[float, float, float]] = [
    (0.000000000000000, 1.000000000000000, 0.000000000000000),   # lat=+90.0°
    (-0.309016994374947, 0.809016994374947, -0.500000000000000), # lat=+54.0°
    (-0.309016994374947, 0.809016994374947, 0.500000000000000),  # lat=+54.0°
    (0.309016994374947, 0.809016994374947, 0.500000000000000),   # lat=+54.0°
    (0.309016994374947, 0.809016994374947, -0.500000000000000),  # lat=+54.0°
    (-0.809016994374947, 0.500000000000000, -0.309016994374947), # lat=+30.0°
    (-0.809016994374947, 0.500000000000000, 0.309016994374947),  # lat=+30.0°
    (0.809016994374947, 0.500000000000000, 0.309016994374947),   # lat=+30.0°
    (0.809016994374947, 0.500000000000000, -0.309016994374947),  # lat=+30.0°
    (-0.500000000000000, 0.309016994374947, -0.809016994374947), # lat=+18.0°
    (-0.500000000000000, 0.309016994374947, 0.809016994374947),  # lat=+18.0°
    (0.500000000000000, 0.309016994374947, 0.809016994374947),   # lat=+18.0°
    (0.500000000000000, 0.309016994374947, -0.809016994374947),  # lat=+18.0°
    (-1.000000000000000, 0.000000000000000, 0.000000000000000),  # lat= +0.0°
    (0.000000000000000, 0.000000000000000, 1.000000000000000),   # lat= +0.0°
    (1.000000000000000, 0.000000000000000, 0.000000000000000),   # lat= +0.0°
    (0.000000000000000, 0.000000000000000, -1.000000000000000),  # lat= +0.0°
    (-0.500000000000000, -0.309016994374947, -0.809016994374947),# lat=-18.0°
    (-0.500000000000000, -0.309016994374947, 0.809016994374947), # lat=-18.0°
    (0.500000000000000, -0.309016994374947, 0.809016994374947),  # lat=-18.0°
    (0.500000000000000, -0.309016994374947, -0.809016994374947), # lat=-18.0°
    (-0.809016994374947, -0.500000000000000, -0.309016994374947),# lat=-30.0°
    (-0.809016994374947, -0.500000000000000, 0.309016994374947), # lat=-30.0°
    (0.809016994374947, -0.500000000000000, 0.309016994374947),  # lat=-30.0°
    (0.809016994374947, -0.500000000000000, -0.309016994374947), # lat=-30.0°
    (-0.309016994374947, -0.809016994374947, -0.500000000000000),# lat=-54.0°
    (-0.309016994374947, -0.809016994374947, 0.500000000000000), # lat=-54.0°
    (0.309016994374947, -0.809016994374947, 0.500000000000000),  # lat=-54.0°
    (0.309016994374947, -0.809016994374947, -0.500000000000000), # lat=-54.0°
    (0.000000000000000, -1.000000000000000, 0.000000000000000),   # lat=-90.0°
]


def _icosidodecahedron_vertex(index: int, total: int) -> tuple[float, float, float]:
    """Return (x, y, z) on the unit sphere for app *index* of *total*.

    Uses the icosidodecahedron vertex lattice — every vertex has 4 neighbours
    at identical chord distance  ≈ 0.618.  When N ≤ 30 every app gets a
    unique vertex; when N > 30 extra apps share vertices round-robin.
    """
    return ICOSIDODECAHEDRON_3D[index % len(ICOSIDODECAHEDRON_3D)]


def deterministic_params(app_name: str, index: int, total: int) -> dict:
    """Deterministic orbital parameters for an app.

    Position is a fixed 3D vertex of the icosidodecahedron.
    Speed and phase are ZERO — the lattice is a rigid body.
    Every vertex stays locked relative to every other vertex.
    The only motion is shared rotation (drag + drift).

    Shell assignment scales with app count (30 vertices per shell):
      1–30 apps  → 1 shell (midpoint radius, identical to classic behaviour)
     31–60 apps  → 2 shells (inner + outer)
     61–90 apps  → 3 shells (inner + mid + outer)
    """
    x, y, z = _icosidodecahedron_vertex(index, total)

    # Shell count and assignment — deterministic from index and total
    shells = min(3, (total - 1) // 30 + 1)   # 1, 2, or 3 shells
    shell = (index // 30) % shells           # which shell this app lands on

    # Radius linear-interpolated from inner to outer across active shells
    if shells == 1:
        radius = (cfg.inner_radius + cfg.outer_radius) / 2
    else:
        t = shell / (shells - 1)
        radius = cfg.inner_radius + t * (cfg.outer_radius - cfg.inner_radius)

    return {
        "x": x, "y": y, "z": z,
        "radius": radius,
        "speed": 0.0,           # rigid body — no per-vertex drift
        "phase": 0.0,           # rigid body — vertex stays put
        "shell": shell,
    }
