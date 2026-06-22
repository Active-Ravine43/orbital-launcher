"""Orbital Launcher — 3D rotation & perspective projection.

Rigid-body rotation: the entire icosidodecahedron lattice rotates as one unit.
No vertex moves relative to any other vertex. Drag = rotate the sphere.
"""

import math

from .config import cfg

PI = math.pi
TAU = 2 * PI
DEG = PI / 180


def _spherical_to_cartesian(lat_deg: float, lon_deg: float, radius: float
                            ) -> tuple[float, float, float]:
    """Convert spherical coords (degrees) to 3D Cartesian. Y is up."""
    lat = lat_deg * DEG
    lon = lon_deg * DEG
    x = radius * math.cos(lat) * math.sin(lon)
    y = radius * math.sin(lat)
    z = radius * math.cos(lat) * math.cos(lon)
    return x, y, z


def _rotate_x(x: float, y: float, z: float, angle_deg: float
              ) -> tuple[float, float, float]:
    """Rotate around X-axis — tilts the sphere forward/backward."""
    a = angle_deg * DEG
    ca, sa = math.cos(a), math.sin(a)
    return x, y * ca - z * sa, y * sa + z * ca


def _rotate_y(x: float, y: float, z: float, angle_deg: float
              ) -> tuple[float, float, float]:
    """Rotate around Y-axis — spins the sphere left/right."""
    a = angle_deg * DEG
    ca, sa = math.cos(a), math.sin(a)
    return x * ca + z * sa, y, -x * sa + z * ca


def project_rotated(
    x: float,
    y: float,
    z: float,
    cx: float,
    cy: float,
) -> tuple[float, float, float, float]:
    """
    Project a 3D point (already rotated) to 2D screen position.
    Returns (screen_x, screen_y, z_depth, scale_factor).
    """
    z_eff = cfg.camera_distance / (cfg.camera_distance - z + cfg.camera_offset)
    sx = cx + x * z_eff
    sy = cy - y * z_eff
    scale = max(cfg.icon_scale_floor, min(2.0, z_eff))
    return sx, sy, z, scale
