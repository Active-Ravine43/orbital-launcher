"""Orbital Launcher — Cairo renderer.

Handles all drawing: icons, omega centerpiece, hover labels, search bar,
CRT noise/scanline overlays, and keyboard focus indicators.

Depth is conveyed through three simultaneous cues — alpha falloff,
perspective scale, and painter's-sort layering — without wireframes,
orbital path rings, or surface textures.
"""

from typing import Optional

import cairo  # pycairo

from .colors import (
    CLR_ACCENT_A40,
    CLR_ACCENT_A70,
    CLR_ACCENT_A80,
    CLR_DIM,
    CLR_FG_A90,
    CLR_FG_A95,
    CLR_SURFACE_A85,
    CLR_VOID,
)
from .config import cfg
from .icons import IconEntry, make_fallback_icon
from .math3d import _rotate_x, _rotate_y, project_rotated
from .state import OrbitalState


class Renderer:
    """Handles all Cairo drawing for the orbital launcher."""

    def __init__(self, state: OrbitalState):
        self.state = state
        self.central_image_surface: Optional["cairo.ImageSurface"] = None
        # Pre-rendered texture caches (invalidated on window resize)
        self._noise_surface: Optional["cairo.ImageSurface"] = None
        self._scanline_surface: Optional["cairo.ImageSurface"] = None
        self._cached_width: int = 0
        self._cached_height: int = 0

    def draw(self, cr: cairo.Context, width: float, height: float):
        """Main draw callback — renders one full frame."""
        # Clear to transparent
        cr.save()
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.restore()

        cr.set_operator(cairo.OPERATOR_OVER)

        # Project all icons — full 3D rigid-body rotation pipeline.
        # base_x/y/z are fixed vertices of the icosidodecahedron —
        # they never change relative to each other.  Drag = rotate the
        # entire lattice; no vertex drifts.
        projected = []
        cx, cy = width / 2, height / 2
        for icon in self.state.icons:
            # 1. Fixed 3D vertex, scaled by zoom + configured radius
            r = icon.radius * self.state.zoom
            x = icon.base_x * r
            y = icon.base_y * r
            z = icon.base_z * r

            # 2. X-axis rotation (vertical drag tilts the rigid lattice)
            x, y, z = _rotate_x(x, y, z, self.state.rotation_lat)

            # 3. Y-axis rotation (horizontal drag + drift + per-icon speed)
            total_y_rot = (
                self.state.rotation_lon
                + cfg.drift_rate * self.state.time_elapsed
                + icon.speed * self.state.time_elapsed
                + icon.phase / 0.017453292519943295  # DEG
            )
            x, y, z = _rotate_y(x, y, z, total_y_rot)

            # 4. Perspective projection to screen
            sx, sy, zd, scale = project_rotated(x, y, z, cx, cy)
            icon.sx = sx
            icon.sy = sy
            icon.zdepth = zd
            icon.scale = scale
            projected.append(icon)

        # Painter's sort: farthest first (lowest z → draw first)
        projected.sort(key=lambda i: i.zdepth)

        # Split icons into behind-omega (z < 0) and front-omega (z >= 0).
        # Omega sits at z=0 — the sphere's center plane.
        behind = [i for i in projected if i.zdepth < 0]
        front = [i for i in projected if i.zdepth >= 0]

        # 1. Draw icons behind the omega
        if self.state.visible:
            for icon in behind:
                self._draw_icon(cr, icon)

        # 2. Draw omega (always visible, between back and front layers)
        self._draw_omega(cr, width / 2, height / 2)

        # 3. Draw icons in front of the omega
        if self.state.visible:
            for icon in front:
                self._draw_icon(cr, icon)

        # Draw hover label
        if (
            self.state.visible
            and self.state.hovered_icon is not None
            and not self.state.dragging
        ):
            self._draw_hover_label(cr, self.state.hovered_icon)

        # Draw search bar
        if self.state.visible:
            self._draw_search_bar(cr, width)

        # CRT textural overlays (last, above everything)
        self._draw_noise(cr, width, height)
        self._draw_scanlines(cr, width, height)

    def _draw_icon(self, cr: cairo.Context, icon: IconEntry):
        """Draw a single icon at its projected screen position."""
        size = cfg.base_icon_size * icon.scale

        # Depth-based alpha — phosphor brightness over distance
        z_range = cfg.outer_radius - (-cfg.outer_radius)
        z_norm = (icon.zdepth + cfg.outer_radius) / max(z_range, 1)
        alpha = cfg.alpha_min + z_norm * (cfg.alpha_max - cfg.alpha_min)
        alpha = max(0.0, min(1.0, alpha))

        if icon.filtered_out:
            alpha *= cfg.filtered_alpha

        # Hover boost
        hover_scale = 1.0
        if icon is self.state.hovered_icon and not self.state.dragging:
            hover_scale = cfg.hover_scale

        effective_size = size * hover_scale

        surf = icon.surface
        if surf is None:
            letter = icon.name[0].upper() if icon.name else "?"
            surf = make_fallback_icon(letter)
            icon.surface = surf

        if surf is None:
            return

        cr.save()
        cr.translate(icon.sx, icon.sy)
        sw = surf.get_width()
        sh = surf.get_height()
        scale_x = effective_size / sw
        scale_y = effective_size / sh
        cr.scale(scale_x, scale_y)

        cr.set_source_surface(surf, -sw / 2, -sh / 2)
        cr.paint_with_alpha(alpha)

        # ── Keyboard focus indicator: corner brackets ──────────────
        if icon is self.state.focused_icon and not self.state.dragging:
            cr.save()
            half_w = sw / 2
            half_h = sh / 2
            bracket_len = min(12, half_w * 0.35, half_h * 0.35)
            cr.set_source_rgba(*CLR_ACCENT_A80)
            cr.set_line_width(2)
            # Top-left
            cr.move_to(-half_w, -half_h + bracket_len)
            cr.line_to(-half_w, -half_h)
            cr.line_to(-half_w + bracket_len, -half_h)
            # Top-right
            cr.move_to(half_w - bracket_len, -half_h)
            cr.line_to(half_w, -half_h)
            cr.line_to(half_w, -half_h + bracket_len)
            # Bottom-right
            cr.move_to(half_w, half_h - bracket_len)
            cr.line_to(half_w, half_h)
            cr.line_to(half_w - bracket_len, half_h)
            # Bottom-left
            cr.move_to(-half_w + bracket_len, half_h)
            cr.line_to(-half_w, half_h)
            cr.line_to(-half_w, half_h - bracket_len)
            cr.stroke()
            cr.restore()

        cr.restore()

    def _draw_omega(self, cr: cairo.Context, cx: float, cy: float):
        """Draw the central piece — custom PNG image, or omega glyph as fallback."""
        cr.save()

        if self.central_image_surface is not None:
            # ── Custom PNG centerpiece ──
            surf = self.central_image_surface
            sw = surf.get_width()
            sh = surf.get_height()
            max_dim = max(sw, sh)
            draw_scale = cfg.central_image_size * cfg.dpi_scale / max_dim if max_dim > 0 else 1.0
            cr.save()
            cr.translate(cx, cy)
            cr.scale(draw_scale, draw_scale)
            cr.set_source_surface(surf, -sw / 2, -sh / 2)
            cr.paint_with_alpha(0.80)
            cr.restore()
        else:
            # ── Omega glyph fallback ──
            cr.select_font_face(
                "Serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD
            )
            cr.set_font_size(cfg.omega_font_size * cfg.dpi_scale)
            xb, yb, tw, th, dx, dy = cr.text_extents("Ω")
            cr.move_to(cx - tw / 2 - xb, cy - th / 2 - yb)
            cr.set_source_rgba(*CLR_ACCENT_A80)
            cr.show_text("Ω")

        cr.restore()

    def _draw_hover_label(self, cr: cairo.Context, icon: IconEntry):
        """Draw app name label — industrial ASCII-framed telemetry tag."""
        cr.save()

        prefix = ">>> "
        text = prefix + icon.name.upper()
        cr.select_font_face(
            "Monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD
        )
        dpi = cfg.dpi_scale
        cr.set_font_size(cfg.label_font_size * dpi)
        xb, yb, tw, th, dx, dy = cr.text_extents(text)

        pad_x, pad_y = 8 * dpi, 5 * dpi
        lx = icon.sx - tw / 2 - pad_x
        ly = icon.sy + cfg.base_icon_size * icon.scale * cfg.hover_scale / 2 + 8 * dpi
        lw = tw + pad_x * 2
        lh = th + pad_y * 2

        # Background — square rect, no radius
        cr.rectangle(lx, ly, lw, lh)
        cr.set_source_rgba(*CLR_SURFACE_A85)
        cr.fill()

        # Accent left edge — mechanical strikethrough
        cr.rectangle(lx, ly, max(1, 1 * dpi), lh)
        cr.set_source_rgba(*CLR_ACCENT_A70)
        cr.fill()

        # Border — full rect, no radius
        cr.rectangle(lx, ly, lw, lh)
        cr.set_source_rgba(*CLR_ACCENT_A40)
        cr.set_line_width(max(1, dpi))
        cr.stroke()

        # Text — monospace phosphor
        cr.move_to(lx + pad_x - xb, ly + lh - pad_y - yb - th)
        cr.set_source_rgba(*CLR_FG_A95)
        cr.show_text(text)

        cr.restore()

    def _draw_search_bar(self, cr: cairo.Context, win_width: float):
        """Draw the search bar — industrial telemetry input panel. DPI-aware."""
        cr.save()

        dpi = cfg.dpi_scale
        bw = cfg.search_bar_width * dpi
        bh = cfg.search_bar_height * dpi
        bx = (win_width - bw) / 2
        by = cfg.search_bar_margin_top * dpi

        # Background — square rect
        cr.rectangle(bx, by, bw, bh)
        cr.set_source_rgba(*CLR_SURFACE_A85)
        cr.fill()

        # Accent left-edge strikethrough
        cr.rectangle(bx, by, max(1, 1 * dpi), bh)
        cr.set_source_rgba(*CLR_ACCENT_A70)
        cr.fill()

        # Border — all edges, no radius
        cr.rectangle(bx, by, bw, bh)
        cr.set_source_rgba(*CLR_ACCENT_A40)
        cr.set_line_width(max(1, dpi))
        cr.stroke()

        # Label frame prefix — `[ SEARCH ]` or `[ >> QUERY ]`
        query = self.state.search_query.upper()
        is_placeholder = not query
        if is_placeholder:
            display = "[ SEARCH ]"
        else:
            display = f"[ >> {query} ]" if len(query) <= 28 else f"[ >> {query[:26]}.. ]"

        cr.select_font_face(
            "Monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL
        )
        cr.set_font_size(14 * dpi)
        xb, yb, tw, th, dx, dy = cr.text_extents(display)

        tx = bx + 16 * dpi
        ty = by + bh / 2 - th / 2 - yb

        if is_placeholder:
            cr.set_source_rgba(*CLR_DIM[:3], 0.50)
        else:
            cr.set_source_rgba(*CLR_FG_A90)

        cr.move_to(tx, ty)
        cr.show_text(display)

        # Cursor — blinking block character (mechanical)
        if not is_placeholder and self.state.search_focused:
            clx = tx + tw + 4 * dpi
            cr.set_source_rgba(*CLR_ACCENT_A70)
            cr.rectangle(clx, ty - 1, 7 * dpi, th + 2)
            cr.fill()

        cr.restore()

    def _rebuild_texture_caches(self, w: int, h: int):
        """Pre-render noise and scanline textures to cairo.ImageSurface.
        Called when the window size changes — these are static per size."""
        if w < 1 or h < 1:
            return
        if w == self._cached_width and h == self._cached_height:
            return
        self._cached_width = w
        self._cached_height = h

        # ── Noise grain surface ──
        self._noise_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ncr = cairo.Context(self._noise_surface)
        ncr.set_source_rgba(*CLR_VOID[:3], 0.015)
        ncr.set_line_width(0.3)
        step = 4
        y = 0
        while y < h:
            ncr.move_to(0, y)
            ncr.line_to(w, y)
            y += step
        ncr.stroke()

        # ── Scanline surface ──
        self._scanline_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        scr = cairo.Context(self._scanline_surface)
        scr.set_source_rgba(*CLR_VOID[:3], cfg.scanline_opacity)
        line_spacing = 3
        y = 0
        while y < h:
            scr.rectangle(0, y, w, 1)
            y += line_spacing
        scr.fill()

    def _draw_scanlines(self, cr: cairo.Context, w: float, h: float):
        """Overlay pre-rendered CRT scanline texture."""
        if not cfg.scanlines_enabled:
            return
        self._rebuild_texture_caches(int(w), int(h))
        if self._scanline_surface is not None:
            cr.save()
            cr.set_source_surface(self._scanline_surface, 0, 0)
            cr.paint()
            cr.restore()

    def _draw_noise(self, cr: cairo.Context, w: float, h: float):
        """Blit pre-rendered noise grain texture."""
        self._rebuild_texture_caches(int(w), int(h))
        if self._noise_surface is not None:
            cr.save()
            cr.set_source_surface(self._noise_surface, 0, 0)
            cr.paint()
            cr.restore()
