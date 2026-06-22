"""Orbital Launcher — icon loading, fallback generation, and IconEntry data.

Resolves desktop app icons through GTK4 IconTheme with pixmap/hicolor
fallbacks. Icons are recolored to red monochrome unless they come from
a recognised red icon theme. Unresolvable icons get a mechanical badge
with the app's initial letter.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

import cairo  # pycairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gio", "2.0")

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio

from .colors import palette
from .config import cfg


# ═══════════════════════════════════════════════════════════════════════
# Icon loading
# ═══════════════════════════════════════════════════════════════════════


class IconLoader:
    """Resolve icon names to cairo.ImageSurface via GTK4 IconTheme + fallbacks."""

    def __init__(self, display: Gdk.Display, theme_name: Optional[str] = None):
        self._cache: dict[str, Optional["cairo.ImageSurface"]] = {}
        self._display = display
        if theme_name:
            self._theme = Gtk.IconTheme.new()
            self._theme.set_theme_name(theme_name)
        else:
            self._theme = Gtk.IconTheme.get_for_display(display)

    def load(self, icon_name: str) -> Optional["cairo.ImageSurface"]:
        if icon_name in self._cache:
            return self._cache[icon_name]

        surf = self._resolve(icon_name)
        self._cache[icon_name] = surf
        return surf

    def _resolve(self, icon_name: str) -> Optional["cairo.ImageSurface"]:
        if not icon_name:
            return None

        size = int(cfg.base_icon_size * cfg.dpi_scale * 2)  # DPI-aware 2x

        # Step 0: Absolute path — used by Steam / non-standard desktop entries.
        # Keep original colours (no red recolor) for custom artwork.
        if icon_name.startswith("/") and os.path.exists(icon_name):
            return self._pixbuf_to_surface_raw(icon_name, size)

        # Step 1: GTK IconTheme lookup (GTK4 API)
        paintable = None
        try:
            paintable = self._theme.lookup_icon(
                icon_name, None, size, 1,
                Gtk.TextDirection.NONE, Gtk.IconLookupFlags(0),
            )
        except Exception:
            pass

        if paintable:
            # 1a: prefer file-backed icons (fast, PNG round-trip)
            try:
                gfile = paintable.get_file()
                if gfile:
                    fpath = gfile.get_path()
                    if fpath and os.path.exists(fpath):
                        return self._pixbuf_to_surface(fpath, size)
            except Exception:
                pass

            # 1b: icon in theme cache / resource — render the paintable directly
            surf = self._paintable_to_surface(paintable, size)
            if surf is not None:
                return surf

        # Step 2: pixmaps fallback
        for ext in (".svg", ".png"):
            fpath = f"/usr/share/pixmaps/{icon_name}{ext}"
            if os.path.exists(fpath):
                return self._pixbuf_to_surface(fpath, size)

        # Step 3: try hicolor directly
        for subsize in ["48x48", "64x64", "128x128", "scalable"]:
            for ext in (".png", ".svg"):
                fpath = f"/usr/share/icons/hicolor/{subsize}/apps/{icon_name}{ext}"
                if os.path.exists(fpath):
                    return self._pixbuf_to_surface(fpath, size)

        return None

    @staticmethod
    def _recolor_red(pb: GdkPixbuf.Pixbuf) -> GdkPixbuf.Pixbuf:
        """Return a new GdkPixbuf recolored to red duotone (luminance→accent)."""
        rowstride = pb.get_rowstride()
        n_channels = pb.get_n_channels()
        w, h = pb.get_width(), pb.get_height()
        pixels = bytearray(pb.get_pixels())
        ar, ag, ab = palette.accent[:3]

        for y in range(h):
            for x in range(w):
                off = y * rowstride + x * n_channels
                r = pixels[off]
                g = pixels[off + 1]
                b = pixels[off + 2]
                lum = 0.299 * r + 0.587 * g + 0.114 * b
                pixels[off] = int(ar * lum)
                pixels[off + 1] = int(ag * lum)
                pixels[off + 2] = int(ab * lum)

        return GdkPixbuf.Pixbuf.new_from_data(
            memoryview(pixels),
            GdkPixbuf.Colorspace.RGB,
            pb.get_has_alpha(),
            pb.get_bits_per_sample(),
            w, h, rowstride, None,
        )

    def _pixbuf_to_surface(self, path: str, size: int) -> "cairo.ImageSurface":
        """Load an image file to a Cairo ImageSurface. Uses PNG round-trip
        to avoid Python-level pixel loops — all work happens in C."""
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
        except Exception:
            return None

        # Recolor non-theme icons to red — icons already from bes-sade-light-red
        # (the user's chosen red theme) are left in their native colour.
        if "bes-sade-light-red" not in path:
            pb = self._recolor_red(pb)

        return self._pixbuf_render(pb)

    def _pixbuf_to_surface_raw(self, path: str, size: int) -> "cairo.ImageSurface":
        """Load an image file WITHOUT recolouring — for game artwork
        and other custom icons that should keep their original colours."""
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
        except Exception:
            return None
        return self._pixbuf_render(pb)

    def _pixbuf_render(self, pb: GdkPixbuf.Pixbuf) -> "cairo.ImageSurface":
        """Encode pixbuf to PNG in C, decode in C — zero Python pixels."""
        try:
            ok, png_bytes = pb.save_to_bufferv("png", [], [])
            if ok:
                import io
                stream = io.BytesIO(png_bytes)
                return cairo.ImageSurface.create_from_png(stream)
        except Exception:
            pass

        # Fallback: pixel copy for formats where PNG round-trip fails
        return self._pixbuf_to_surface_slow(pb)

    def _pixbuf_to_surface_slow(self, pb: GdkPixbuf.Pixbuf) -> "cairo.ImageSurface":
        """Slow fallback: Python pixel copy. Only used if PNG round-trip fails."""
        w, h = pb.get_width(), pb.get_height()
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        buf = memoryview(surf.get_data())

        pixels = pb.get_pixels()
        rowstride = pb.get_rowstride()
        n_channels = pb.get_n_channels()
        surf_stride = surf.get_stride()

        for y in range(h):
            for x in range(w):
                poff = y * rowstride + x * n_channels
                r = pixels[poff]
                g = pixels[poff + 1]
                b = pixels[poff + 2]
                a = pixels[poff + 3] if n_channels >= 4 else 255
                soff = y * surf_stride + x * 4
                buf[soff] = b
                buf[soff + 1] = g
                buf[soff + 2] = r
                buf[soff + 3] = a

        surf.mark_dirty()
        return surf

    def _paintable_to_surface(
        self, paintable, size: int
    ) -> Optional["cairo.ImageSurface"]:
        """Render a Gdk.Paintable to a Cairo ImageSurface via GskSnapshot.

        Handles icons served from theme caches and GResource bundles where
        get_file() returns None but the pixel data is renderable.
        """
        try:
            import gi

            gi.require_version("Gsk", "4.0")
            from gi.repository import Gsk

            snapshot = Gtk.Snapshot()
            paintable.snapshot(snapshot, size, size)
            node = snapshot.to_node()
            if node is None:
                return None

            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
            cr = cairo.Context(surf)
            renderer = Gsk.CairoRenderer()
            renderer.render(cr, node)
            return surf
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════════════
# Fallback icon generation
# ═══════════════════════════════════════════════════════════════════════


def make_fallback_icon(letter: str) -> "cairo.ImageSurface":
    """Draw a square mechanical badge — industrial brutalist fallback.

    Alpha values are tuned for mask-based rendering: the surface is used
    as an alpha mask filled with the accent colour, so higher alpha = brighter.
    The letter is brightest (α=1.0), background is dim (α=0.45), and the
    left-edge accent stripe is a bright structural element (α=0.85).
    """
    size = int(cfg.base_icon_size * cfg.dpi_scale * 2)
    inset = max(2, int(4 * cfg.dpi_scale))
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surf)

    # Dim background — recedes in mask rendering
    cr.rectangle(inset, inset, size - 2 * inset, size - 2 * inset)
    cr.set_source_rgba(*palette.surface[:3], 0.45)
    cr.fill()

    # Bright accent left-edge strikethrough
    cr.rectangle(inset, inset, max(1, 1 * cfg.dpi_scale), size - 2 * inset)
    cr.set_source_rgba(*palette.accent[:3], 0.85)
    cr.fill()

    # Top-right corner notch (mechanical detail)
    cr.move_to(size - inset - 8, inset)
    cr.line_to(size - inset, inset + 8)
    cr.set_source_rgba(*palette.accent[:3], 0.60)
    cr.set_line_width(1.5)
    cr.stroke()

    # Letter — maximum alpha for legibility against dim background
    cr.select_font_face("Monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(size * 0.45)
    xb, yb, tw, th, dx, dy = cr.text_extents(letter.upper())
    cr.move_to(size / 2 - tw / 2 - xb, size / 2 - th / 2 - yb)
    cr.set_source_rgba(*palette.fg[:3], 1.0)
    cr.show_text(letter.upper())

    return surf


# ═══════════════════════════════════════════════════════════════════════
# Icon entry data class
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class IconEntry:
    name: str
    icon_name: str
    exec_cmd: str
    terminal: bool
    desktop_file: str
    # Fixed 3D vertex on the unit sphere — never moves relative to the lattice
    base_x: float = 0.0
    base_y: float = 0.0
    base_z: float = 0.0
    radius: float = 250
    speed: float = 0.5
    phase: float = 0
    shell: int = 1
    # Runtime
    surface: Optional["cairo.ImageSurface"] = None
    launch_count: int = 0
    # Per-frame projection cache
    sx: float = 0
    sy: float = 0
    zdepth: float = 0
    scale: float = 1.0
