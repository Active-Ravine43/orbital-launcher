"""Orbital Launcher — GTK4 Application.

Main application class: window setup, layer shell, input controllers,
keyboard navigation, animation timer, signal handling, and app launching.
"""

import atexit
import hashlib
import math
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

import cairo  # pycairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gio", "2.0")

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio

from .config import cfg, PID_FILE
from .icons import IconLoader, IconEntry
from .lattice import deterministic_params
from .renderer import Renderer
from .scanner import desktop_scan
from .state import OrbitalState

# ─── Optional layer-shell ───────────────────────────────────────────
LAYER_SHELL = False
try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell
    LAYER_SHELL = True
except (ValueError, ImportError):
    print("[orbital-launcher] Gtk4LayerShell not available; using fallback window mode")
    print("[orbital-launcher] Install: sudo pacman -S gtk4-layer-shell")


# ═══════════════════════════════════════════════════════════════════════
# GTK4 Application
# ═══════════════════════════════════════════════════════════════════════


class OrbitalLauncherApp(Gtk.Application):
    """Main GTK4 application for the Orbital Launcher."""

    def __init__(self):
        super().__init__(
            application_id="dev.omega.orbital-launcher",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        self.state = OrbitalState()
        self.renderer: Optional[Renderer] = None
        self.window: Optional[Gtk.Window] = None
        self.draw_area: Optional[Gtk.DrawingArea] = None
        self.icon_loader: Optional[IconLoader] = None
        self._timer_id: int = 0
        self._drag_start_lon: float = 0
        self._drag_start_lat: float = 0
        self._mouse_x: float = 0
        self._mouse_y: float = 0

    # ── Init ──────────────────────────────────────────────────────

    def do_activate(self):
        """Create the window and start the launcher."""
        # Prevent duplicate instances
        if not self._acquire_lock():
            print("[orbital-launcher] Another instance is running. Exiting.")
            return

        self._setup_window()
        self._setup_css()
        self._setup_layer_shell()
        self._setup_drawing_area()
        self._setup_input_controllers()
        self._setup_keyboard()
        self._setup_signals()
        self._load_data()
        self._start_animation()
        self.window.present()

    # ── Lock ──────────────────────────────────────────────────────

    def _acquire_lock(self) -> bool:
        """Atomically acquire PID file lock. Returns False if another instance
        holds the lock (signals the old instance to show itself)."""
        try:
            # Try atomic creation first — O_EXCL fails if file exists
            fd = os.open(PID_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            with os.fdopen(fd, "w") as fh:
                fh.write(str(os.getpid()))
            atexit.register(self._release_lock)
            return True
        except FileExistsError:
            # File exists — check if the old process is alive
            pass
        except OSError:
            # Permission issues — try fallback check
            pass

        try:
            with open(PID_FILE) as fh:
                old_pid = int(fh.read().strip())
            try:
                os.kill(old_pid, 0)
                # Old process exists — signal it to show and exit
                os.kill(old_pid, signal.SIGUSR1)
                return False
            except OSError:
                # Stale PID — remove and retry atomically
                try:
                    os.remove(PID_FILE)
                except OSError:
                    pass
                try:
                    fd = os.open(PID_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                    with os.fdopen(fd, "w") as fh:
                        fh.write(str(os.getpid()))
                    atexit.register(self._release_lock)
                    return True
                except FileExistsError:
                    return False
                except OSError:
                    return True  # proceed even if lock fails
        except Exception:
            return True  # proceed even if lock fails

    def _release_lock(self):
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass

    # ── Window ────────────────────────────────────────────────────

    def _setup_window(self):
        self.window = Gtk.Window(application=self)
        self.window.set_title("Orbital Launcher")
        self.window.set_decorated(False)
        self.window.set_resizable(False)

        # Fullscreen on the monitor where the cursor is
        display = Gdk.Display.get_default()
        if display:
            mon = None
            monitors = display.get_monitors()
            if monitors and monitors.get_n_items() > 0:
                # Try to detect which monitor the cursor is on
                try:
                    seat = display.get_default_seat()
                    if seat:
                        pointer = seat.get_pointer()
                        if pointer:
                            ok, px, py = pointer.get_position()
                            if ok:
                                mon = display.get_monitor_at_point(px, py)
                except Exception:
                    pass
                # Fallback to primary monitor
                if mon is None:
                    mon = monitors.get_item(0)
                geo = mon.get_geometry()
                self.window.set_default_size(geo.width, geo.height)

        self.window.fullscreen()

        # Try to stay below normal windows
        try:
            surface = self.window.get_surface()
            if surface:
                surface.set_input_region(
                    cairo.Region(cairo.RectangleInt(0, 0, 9999, 9999))
                )
        except Exception:
            pass

    def _setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(
            """
            window {
                background-color: transparent;
                background: none;
            }
            drawingarea {
                background-color: transparent;
                background: none;
            }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _setup_layer_shell(self):
        """Configure window as a layer-shell background overlay."""
        if not LAYER_SHELL:
            return

        try:
            Gtk4LayerShell.init_for_window(self.window)
            Gtk4LayerShell.set_layer(
                self.window, Gtk4LayerShell.Layer.BACKGROUND
            )
            Gtk4LayerShell.set_anchor(self.window, Gtk4LayerShell.Edge.TOP, True)
            Gtk4LayerShell.set_anchor(self.window, Gtk4LayerShell.Edge.BOTTOM, True)
            Gtk4LayerShell.set_anchor(self.window, Gtk4LayerShell.Edge.LEFT, True)
            Gtk4LayerShell.set_anchor(self.window, Gtk4LayerShell.Edge.RIGHT, True)
            Gtk4LayerShell.set_exclusive_zone(self.window, 0)
            Gtk4LayerShell.set_keyboard_mode(
                self.window, Gtk4LayerShell.KeyboardMode.ON_DEMAND
            )
            Gtk4LayerShell.set_namespace(self.window, "orbital-launcher")
        except Exception as e:
            print(f"[orbital-launcher] Layer shell setup failed: {e}", file=sys.stderr)

    # ── Drawing area ──────────────────────────────────────────────

    def _setup_drawing_area(self):
        self.draw_area = Gtk.DrawingArea()
        self.draw_area.set_hexpand(True)
        self.draw_area.set_vexpand(True)
        self.draw_area.set_can_target(True)
        self.draw_area.set_focusable(True)

        # ── Accessibility: expose the launcher to AT (GTK ≥4.10) ──
        self._accessible = None
        self._has_a11y = (
            hasattr(Gtk, "AccessibleRole")
            and hasattr(Gtk, "AccessibleProperty")
            and hasattr(Gtk, "AccessibleState")
        )
        if self._has_a11y:
            try:
                self.draw_area.set_accessible_role(Gtk.AccessibleRole.WIDGET)
                self._accessible = self.draw_area.get_accessible()
                if self._accessible:
                    self._accessible.update_property(
                        Gtk.AccessibleProperty.LABEL, "Orbital Launcher"
                    )
                    self._accessible.update_property(
                        Gtk.AccessibleProperty.DESCRIPTION,
                        "3D spherical application launcher. Type to search apps. "
                        "Press Escape to dismiss.",
                    )
                    self._accessible.update_state(
                        Gtk.AccessibleState.ENABLED, True
                    )
            except Exception:
                self._has_a11y = False
                self._accessible = None

        self.renderer = Renderer(self.state)

        def draw_func(area, cr, w, h, _data):
            if self.renderer:
                self.renderer.draw(cr, w, h)

        self.draw_area.set_draw_func(draw_func, None)

    def _announce_accessible(self, message: str):
        """Push a state-change announcement to the ATK layer."""
        if not getattr(self, '_has_a11y', False):
            return
        if not getattr(self, '_accessible', None):
            return
        try:
            self._accessible.update_property(
                Gtk.AccessibleProperty.DESCRIPTION, message
            )
            self._accessible.update_state(
                Gtk.AccessibleState.SELECTED, True
            )
            self._accessible.update_state(
                Gtk.AccessibleState.SELECTED, False
            )
        except Exception:
            pass

    # ── Input controllers ─────────────────────────────────────────

    def _setup_input_controllers(self):
        """Wire up drag, scroll, click, and motion — unified, conflict-free."""
        da = self.draw_area
        self._mouse_down = False
        self._press_start_x = 0.0
        self._press_start_y = 0.0
        DRAG_THRESHOLD = 6  # pixels — below this = click, above = drag

        # --- Click-to-launch + press/release tracking ---
        click_ctrl = Gtk.GestureClick()
        click_ctrl.set_button(1)  # left button only

        def on_press(gesture, n_press, x, y):
            if n_press != 1:
                return
            self._mouse_down = True
            self._press_start_x = x
            self._press_start_y = y
            # Snapshot: rotation at press time — drag is absolute, not delta
            self._drag_start_lon = self.state.rotation_lon
            self._drag_start_lat = self.state.rotation_lat

        def on_release(gesture, n_press, x, y):
            if n_press != 1:
                return
            self._mouse_down = False
            self.state.dragging = False

            # Below threshold → it was a click, not a drag
            dx = x - self._press_start_x
            dy = y - self._press_start_y
            if math.sqrt(dx * dx + dy * dy) < DRAG_THRESHOLD:
                icon = self._hit_test(x, y)
                if icon is not None:
                    self._launch_app(icon)
                    self.state.visible = False
                    self._update_timer_interval()
            self.draw_area.queue_draw()

        click_ctrl.connect("pressed", on_press)
        click_ctrl.connect("released", on_release)
        da.add_controller(click_ctrl)

        # --- Motion: absolute-offset drag when mouse is down; hover otherwise ---
        motion_ctrl = Gtk.EventControllerMotion()

        def on_motion(controller, x, y):
            self._mouse_x = x
            self._mouse_y = y

            if self._mouse_down and self.state.visible:
                # Absolute offset from press position → 1:1 mouse-to-sphere mapping
                total_dx = x - self._press_start_x
                total_dy = y - self._press_start_y
                # Right drag → icons follow right (positive Y-rotation)
                # Up drag → icons follow up (negative X-rotation)
                self.state.rotation_lon = self._drag_start_lon + total_dx * cfg.drag_sensitivity
                self.state.rotation_lat = self._drag_start_lat + total_dy * cfg.drag_sensitivity
                self.state.rotation_lat = max(-85, min(85, self.state.rotation_lat))
                self.state.dragging = True
                self.draw_area.queue_draw()
            else:
                # Hover detection
                prev = self.state.hovered_icon
                icon = self._hit_test(x, y) if self.state.visible else None
                if icon is not prev:
                    self.state.hovered_icon = icon
                    if icon is not None:
                        self._announce_accessible("Hovered: %s" % icon.name)
                    self.draw_area.queue_draw()

        motion_ctrl.connect("motion", on_motion)
        da.add_controller(motion_ctrl)

        # --- Scroll to zoom ---
        scroll_ctrl = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
        )

        def on_scroll(controller, dx, dy):
            self.state.zoom *= 1.0 + dy * cfg.scroll_sensitivity
            self.state.zoom = max(cfg.zoom_min, min(cfg.zoom_max, self.state.zoom))
            self.draw_area.queue_draw()
            return True

        scroll_ctrl.connect("scroll", on_scroll)
        da.add_controller(scroll_ctrl)

    # ── Keyboard / search ─────────────────────────────────────────

    def _setup_keyboard(self):
        """Set up keyboard input for search filtering and icon navigation."""
        key_ctrl = Gtk.EventControllerKey()
        self.draw_area.add_controller(key_ctrl)

        def on_key_pressed(controller, keyval, keycode, state):
            if not self.state.visible:
                return False

            # ── Arrow keys: navigate focus between visible icons ──
            ARROW_KEYS = {
                Gdk.KEY_Up: (0, -1),
                Gdk.KEY_Down: (0, 1),
                Gdk.KEY_Left: (-1, 0),
                Gdk.KEY_Right: (1, 0),
            }
            if keyval in ARROW_KEYS:
                dx, dy = ARROW_KEYS[keyval]
                self._navigate_focus(dx, dy)
                return True

            # ── Tab: cycle through search results ──
            if keyval == Gdk.KEY_Tab:
                self._navigate_search_results()
                return True

            # Enter — launch focused icon, or first match
            if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                if self.state.focused_icon is not None and not self.state.focused_icon.filtered_out:
                    self._launch_focused()
                else:
                    self._launch_first_match()
                return True

            # Escape — clear search / blur focus, or collapse sphere
            if keyval == Gdk.KEY_Escape:
                if self.state.focused_icon is not None:
                    self.state.focused_icon = None
                    self._announce_accessible("Focus cleared")
                    self.draw_area.queue_draw()
                elif self.state.search_query:
                    self.state.search_query = ""
                    self.state.focused_icon = None
                    self._apply_search_filter()
                    self._announce_accessible("Search cleared — %d apps shown" % self._count_visible())
                    self.draw_area.queue_draw()
                else:
                    self.state.visible = False
                    self._update_timer_interval()
                    self._announce_accessible("Orbital Launcher hidden")
                    self.draw_area.queue_draw()
                return True

            # BackSpace
            if keyval == Gdk.KEY_BackSpace:
                self.state.focused_icon = None
                self.state.search_query = self.state.search_query[:-1]
                self._apply_search_filter()
                self._announce_accessible(
                    "Search: \"%s\" — %d match%s" % (
                        self.state.search_query,
                        self._count_visible(),
                        "es" if self._count_visible() != 1 else "",
                    )
                )
                self.draw_area.queue_draw()
                return True

            # Printable characters
            name = Gdk.keyval_name(keyval) or ""
            if len(name) == 1 and name.isprintable() and not (state & Gdk.ModifierType.CONTROL_MASK):
                self.state.search_query += name
                self.state.focused_icon = None
                self._apply_search_filter()
                self._announce_accessible(
                    "Search: \"%s\" — %d match%s" % (
                        self.state.search_query,
                        self._count_visible(),
                        "es" if self._count_visible() != 1 else "",
                    )
                )
                self.draw_area.queue_draw()
                return True

            return False

        key_ctrl.connect("key-pressed", on_key_pressed)

        # Set the window child — drawing area fills the window directly
        self.window.set_child(self.draw_area)

    def _navigate_focus(self, dx: float, dy: float):
        """Move keyboard focus to the nearest visible icon in the given
        screen-space direction. Uses projected screen positions (sx, sy)."""
        visible = [i for i in self.state.icons if not i.filtered_out]
        if not visible:
            return

        if self.state.focused_icon is None or self.state.focused_icon.filtered_out:
            # No focus yet — pick the icon nearest to center in the given direction
            target = visible[0]
            best_score = float("inf")
            for icon in visible:
                # Score: how well-aligned with the direction from center
                score = -(icon.sx * dx + icon.sy * dy)
                if score < best_score:
                    best_score = score
                    target = icon
            self.state.focused_icon = target
            self._announce_accessible("Focused: %s" % target.name)
            self.draw_area.queue_draw()
            return

        cur = self.state.focused_icon
        best_icon = None
        best_score = float("inf")

        for icon in visible:
            if icon is cur:
                continue
            # Vector from current to candidate
            vx = icon.sx - cur.sx
            vy = icon.sy - cur.sy
            dist = math.sqrt(vx * vx + vy * vy)
            if dist < 1:
                continue

            # Cosine similarity with the desired direction
            dot = (vx * dx + vy * dy) / dist

            # Penalize icons in the wrong direction heavily
            if dot < 0.1:
                continue

            # Score: closer and better-aligned = lower
            score = dist / (dot + 0.01)
            if score < best_score:
                best_score = score
                best_icon = icon

        if best_icon is not None:
            self.state.focused_icon = best_icon
            self._announce_accessible("Focused: %s" % best_icon.name)
            self.draw_area.queue_draw()

    def _navigate_search_results(self):
        """Tab through search results — cycle focus among visible icons."""
        visible = [i for i in self.state.icons if not i.filtered_out]
        if not visible:
            return

        if self.state.focused_icon is None or self.state.focused_icon.filtered_out:
            self.state.focused_icon = visible[0]
        else:
            try:
                idx = visible.index(self.state.focused_icon)
                self.state.focused_icon = visible[(idx + 1) % len(visible)]
            except ValueError:
                self.state.focused_icon = visible[0]

        self._announce_accessible("Focused: %s" % self.state.focused_icon.name)
        self.draw_area.queue_draw()

    def _launch_focused(self):
        """Launch the currently keyboard-focused icon."""
        if self.state.focused_icon is None:
            return
        icon = self.state.focused_icon
        self._launch_app(icon)
        self.state.visible = False
        self.state.focused_icon = None
        self.state.search_query = ""
        self._apply_search_filter()
        self._update_timer_interval()
        self.draw_area.queue_draw()

    def _launch_first_match(self):
        """Launch the first app matching the current search query."""
        if not self.state.search_query:
            return
        q = self.state.search_query.lower()
        for icon in self.state.icons:
            if q in icon.name.lower():
                self._launch_app(icon)
                self.state.visible = False
                self.state.search_query = ""
                self._apply_search_filter()
                self._update_timer_interval()
                self.draw_area.queue_draw()
                return

    def _apply_search_filter(self):
        q = self.state.search_query.lower()
        for icon in self.state.icons:
            icon.filtered_out = bool(q and q not in icon.name.lower())

    def _count_visible(self) -> int:
        """Return the number of icons not filtered out by search."""
        return sum(1 for i in self.state.icons if not i.filtered_out)

    # ── Hit testing ───────────────────────────────────────────────

    def _hit_test(self, mx: float, my: float) -> Optional[IconEntry]:
        """Find the front-most icon under cursor position (mx, my)."""
        if not self.state.visible:
            return None

        # Check icons front-to-back (reverse of draw order)
        for icon in reversed(
            sorted(self.state.icons, key=lambda i: i.zdepth)
        ):
            size = cfg.base_icon_size * icon.scale
            hover_boost = (
                cfg.hover_scale
                if icon is self.state.hovered_icon and not self.state.dragging
                else 1.0
            )
            half = size * hover_boost / 2
            if abs(mx - icon.sx) < half and abs(my - icon.sy) < half:
                return icon
        return None

    # ── Data loading ──────────────────────────────────────────────

    def _load_data(self):
        """Scan desktops, build icon list, pre-load surfaces."""
        # Load state
        self.state.load_state()

        # Detect DPI scale factor from primary monitor
        display = Gdk.Display.get_default()
        if display:
            monitors = display.get_monitors()
            if monitors and monitors.get_n_items() > 0:
                mon = monitors.get_item(0)
                cfg.dpi_scale = mon.get_scale_factor()
                print(
                    f"[orbital-launcher] DPI scale factor: {cfg.dpi_scale}",
                    file=sys.stderr,
                )

        # Detect reduced-motion preference from GTK settings
        try:
            gtk_settings = Gtk.Settings.get_default()
            if gtk_settings:
                animations_enabled = gtk_settings.get_property(
                    "gtk-enable-animations"
                )
                if not animations_enabled:
                    cfg.reduced_motion = True
                    cfg.drift_rate = 0.0
                    print(
                        "[orbital-launcher] Reduced motion: drift disabled",
                        file=sys.stderr,
                    )
        except Exception:
            pass

        # Scan or load cache
        entries = desktop_scan()

        # Get display for icon loader
        self.icon_loader = IconLoader(display)

        # Sort entries deterministically so each app gets a stable lattice index.
        # Hash the name, sort by that hash — same order every launch.
        def _sort_key(e):
            return hashlib.sha256(e["name"].encode()).hexdigest()
        entries.sort(key=_sort_key)

        # Build icon entries — each gets a fixed vertex on the icosidodecahedron
        total = len(entries)
        shells = min(3, (total - 1) // 30 + 1)
        print(
            f"[orbital-launcher] Distributing {total} apps on icosidodecahedron "
            f"(30 vertices × {shells} shell{'s' if shells > 1 else ''}"
            f" = {30 * shells} unique positions)",
            file=sys.stderr,
        )
        icons = []
        for i, e in enumerate(entries):
            params = deterministic_params(e["name"], i, total)
            icon = IconEntry(
                name=e["name"],
                icon_name=e["icon_name"],
                exec_cmd=e["exec"],
                terminal=e["terminal"],
                desktop_file=e["desktop_file"],
                base_x=params["x"],
                base_y=params["y"],
                base_z=params["z"],
                radius=params["radius"],
                speed=params["speed"],
                phase=params["phase"],
                shell=params["shell"],
                launch_count=self.state.launch_counts.get(
                    os.path.basename(e["desktop_file"]), 0
                ),
            )
            # Pre-load surface
            icon.surface = self.icon_loader.load(e["icon_name"])
            icons.append(icon)

        self.state.icons = icons
        print(
            f"[orbital-launcher] Loaded {len(icons)} apps from desktop files",
            file=sys.stderr,
        )

        # Load central image (replaces omega glyph when configured)
        if cfg.central_image_path and self.icon_loader and self.renderer:
            try:
                # Resolve path: absolute, ~/-relative, relative to repo root, or Pictures dir
                raw = cfg.central_image_path
                if raw.startswith("~/"):
                    image_path = str(Path.home() / raw[2:])
                elif raw.startswith("/"):
                    image_path = raw
                else:
                    # Try repo root first, then Pictures dir
                    repo_root = Path(__file__).resolve().parent.parent.parent
                    candidate = str(repo_root / raw)
                    if os.path.exists(candidate):
                        image_path = candidate
                    else:
                        image_path = str(Path.home() / "Pictures" / raw)

                load_size = int(cfg.central_image_size * cfg.dpi_scale * 2)
                surf = self.icon_loader._pixbuf_to_surface(
                    image_path, load_size
                )
                if surf is not None:
                    self.renderer.central_image_surface = surf
                    print(
                        f"[orbital-launcher] Central image loaded: "
                        f"{image_path}",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"[orbital-launcher] Central image failed to decode: "
                        f"{image_path} — falling back to omega glyph",
                        file=sys.stderr,
                    )
            except Exception as e:
                print(
                    f"[orbital-launcher] Central image load error: {e} — "
                    f"falling back to omega glyph",
                    file=sys.stderr,
                )

    # ── App launching ─────────────────────────────────────────────

    def _launch_app(self, icon: IconEntry):
        """Launch an application from its desktop entry."""
        self.state.increment_launch(icon.desktop_file)

        try:
            if icon.terminal:
                term = os.environ.get("TERMINAL", "kitty")
                cmd = [term, "--", "sh", "-c", icon.exec_cmd]
            else:
                cmd = ["sh", "-c", icon.exec_cmd]

            subprocess.Popen(
                cmd,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._announce_accessible("Launched %s" % icon.name)
            print(f"[orbital-launcher] Launched: {icon.name}", file=sys.stderr)
        except Exception as e:
            print(
                f"[orbital-launcher] Failed to launch {icon.name}: {e}",
                file=sys.stderr,
            )

    # ── Animation ─────────────────────────────────────────────────

    def _start_animation(self):
        """Smart timer: 60fps when visible, 1fps when hidden (saves CPU)."""
        active_interval = cfg.fps_active_interval
        idle_interval = cfg.fps_idle_interval

        def tick():
            if self.state.visible:
                if not self.state.dragging:
                    self.state.time_elapsed += active_interval / 1000.0
                self.draw_area.queue_draw()
                return GLib.SOURCE_CONTINUE
            else:
                # Idle: slow redraw for potential window events
                self.draw_area.queue_draw()
                return GLib.SOURCE_CONTINUE

        def update_interval():
            """Switch timer interval based on visibility."""
            interval = active_interval if self.state.visible else idle_interval
            if self._timer_id:
                GLib.source_remove(self._timer_id)
            self._timer_id = GLib.timeout_add(interval, tick)

        self._update_timer_interval = update_interval
        self._timer_id = GLib.timeout_add(active_interval, tick)

    # ── Signals ───────────────────────────────────────────────────

    def _setup_signals(self):
        """Set up SIGUSR1 handler for toggle."""
        def handle_usr1(signum, frame):
            self.state.visible = not self.state.visible
            if self.state.visible:
                self.state.time_elapsed = 0.0  # reset animation phase
                self._announce_accessible("Orbital Launcher shown — %d apps available" % len(self.state.icons))
            else:
                self._announce_accessible("Orbital Launcher hidden")
            # Switch timer interval: fast when visible, slow when hidden
            if hasattr(self, '_update_timer_interval'):
                self._update_timer_interval()
            self.draw_area.queue_draw()

        signal.signal(signal.SIGUSR1, handle_usr1)

        # Cleanup on shutdown
        def on_shutdown(*args):
            self.state.save_state()
            self._release_lock()

        self.connect("shutdown", on_shutdown)


# ═══════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════


def main():
    app = OrbitalLauncherApp()
    return app.run(sys.argv)
