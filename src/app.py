"""Orbital Launcher — GTK4 Application.

Multi-monitor: one window per display, each with its own renderer, search
state, and rotation.  Icon data, the central image, and launch-counts are
shared.  SIGUSR1 toggles all windows together.
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

from .config import cfg, DESKTOP_DIRS, PID_FILE, load_user_config
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
# Per-monitor view
# ═══════════════════════════════════════════════════════════════════════


class MonitorView:
    """One launcher window per display — independent search, rotation, zoom."""

    def __init__(self, app: "OrbitalLauncherApp", monitor: Gdk.Monitor):
        self.app = app
        self.monitor = monitor
        geo = monitor.get_geometry()
        self.geo = geo

        self.state = OrbitalState()
        self.renderer: Optional[Renderer] = None
        self.window: Optional[Gtk.Window] = None
        self.draw_area: Optional[Gtk.DrawingArea] = None
        self._accessible = None
        self._has_a11y = False

        # Drag state
        self._mouse_down = False
        self._press_start_x = 0.0
        self._press_start_y = 0.0
        self._drag_start_lon = 0.0
        self._drag_start_lat = 0.0

        self._build()

    # ── Build window + layer-shell + drawing area ─────────────────

    def _build(self):
        geo = self.geo

        # --- Window ---
        self.window = Gtk.Window(application=self.app)
        self.window.set_title("Orbital Launcher")
        self.window.set_decorated(False)
        self.window.set_resizable(False)
        self.window.set_default_size(geo.width, geo.height)

        if not LAYER_SHELL:
            self.window.fullscreen()

        # --- Layer-shell ---
        if LAYER_SHELL:
            try:
                Gtk4LayerShell.init_for_window(self.window)
                Gtk4LayerShell.set_monitor(self.window, self.monitor)
                Gtk4LayerShell.set_layer(self.window, Gtk4LayerShell.Layer.BOTTOM)
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
                print(
                    f"[orbital-launcher] Layer shell setup failed: {e}",
                    file=sys.stderr,
                )

        # --- Drawing area ---
        self.draw_area = Gtk.DrawingArea()
        self.draw_area.set_hexpand(True)
        self.draw_area.set_vexpand(True)
        self.draw_area.set_can_target(True)
        self.draw_area.set_focusable(True)

        self._has_a11y = (
            hasattr(Gtk, "AccessibleRole")
            and hasattr(Gtk, "AccessibleProperty")
            and hasattr(Gtk, "AccessibleState")
        )
        if self._has_a11y:
            try:
                self.draw_area.set_accessible_role(Gtk.AccessibleRole.GROUPING)
                self._accessible = self.draw_area.get_accessible()
                if self._accessible:
                    self._accessible.update_property(
                        Gtk.AccessibleProperty.LABEL, "Orbital Launcher"
                    )
                    self._accessible.update_property(
                        Gtk.AccessibleProperty.DESCRIPTION,
                        "3D spherical application launcher. Type to search. "
                        "Press Escape to dismiss.",
                    )
                    self._accessible.update_state(Gtk.AccessibleState.ENABLED, True)
            except Exception:
                self._has_a11y = False
                self._accessible = None

        self.renderer = Renderer(self.state)

        def draw_func(area, cr, w, h, _data):
            if self.renderer:
                self.renderer.draw(cr, w, h)

        self.draw_area.set_draw_func(draw_func, None)

        # --- Input controllers ---
        self._setup_input_controllers()

        # --- Keyboard ---
        self._setup_keyboard()

        self.window.set_child(self.draw_area)

    # ── Input controllers ──────────────────────────────────────────

    def _setup_input_controllers(self):
        da = self.draw_area
        DRAG_THRESHOLD = 6

        click_ctrl = Gtk.GestureClick()
        click_ctrl.set_button(1)

        def on_press(gesture, n_press, x, y):
            if n_press != 1:
                return
            self._mouse_down = True
            self._press_start_x = x
            self._press_start_y = y
            self._drag_start_lon = self.state.rotation_lon
            self._drag_start_lat = self.state.rotation_lat

        def on_release(gesture, n_press, x, y):
            if n_press != 1:
                return
            self._mouse_down = False
            self.state.dragging = False
            dx = x - self._press_start_x
            dy = y - self._press_start_y
            if math.sqrt(dx * dx + dy * dy) < DRAG_THRESHOLD:
                icon = self._hit_test(x, y)
                if icon is not None:
                    self.app._launch_app(self, icon)
            da.queue_draw()

        click_ctrl.connect("pressed", on_press)
        click_ctrl.connect("released", on_release)
        da.add_controller(click_ctrl)

        # --- Motion ---
        motion_ctrl = Gtk.EventControllerMotion()

        def on_motion(controller, x, y):
            self.app._last_active_view = self
            if self._mouse_down and self.state.visible:
                total_dx = x - self._press_start_x
                total_dy = y - self._press_start_y
                self.state.rotation_lon = (
                    self._drag_start_lon + total_dx * cfg.drag_sensitivity
                )
                self.state.rotation_lat = (
                    self._drag_start_lat + total_dy * cfg.drag_sensitivity
                )
                self.state.rotation_lat = max(-85, min(85, self.state.rotation_lat))
                self.state.dragging = True
                da.queue_draw()
            else:
                prev = self.state.hovered_icon
                icon = self._hit_test(x, y) if self.state.visible else None
                if icon is not prev:
                    self.state.hovered_icon = icon
                    da.queue_draw()

        motion_ctrl.connect("motion", on_motion)
        da.add_controller(motion_ctrl)

        # --- Scroll ---
        scroll_ctrl = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
        )

        def on_scroll(controller, dx, dy):
            self.state.zoom *= 1.0 + dy * cfg.scroll_sensitivity
            self.state.zoom = max(cfg.zoom_min, min(cfg.zoom_max, self.state.zoom))
            da.queue_draw()
            return True

        scroll_ctrl.connect("scroll", on_scroll)
        da.add_controller(scroll_ctrl)

    # ── Keyboard ───────────────────────────────────────────────────

    def _setup_keyboard(self):
        key_ctrl = Gtk.EventControllerKey()
        self.draw_area.add_controller(key_ctrl)

        def on_key_pressed(controller, keyval, keycode, state):
            if not self.state.visible:
                return False

            ARROW_KEYS = {
                Gdk.KEY_Up: (0, -1),
                Gdk.KEY_Down: (0, 1),
                Gdk.KEY_Left: (-1, 0),
                Gdk.KEY_Right: (1, 0),
            }
            if keyval in ARROW_KEYS:
                self._navigate_focus(*ARROW_KEYS[keyval])
                return True

            if keyval == Gdk.KEY_Tab:
                self._navigate_search_results()
                return True

            if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                if (
                    self.state.focused_icon is not None
                    and not self._is_filtered(self.state.focused_icon)
                ):
                    self._launch_focused()
                else:
                    self._launch_first_match()
                return True

            if keyval == Gdk.KEY_Escape:
                if self.state.focused_icon is not None:
                    self.state.focused_icon = None
                    self.draw_area.queue_draw()
                elif self.state.search_query:
                    self.state.search_query = ""
                    self.state.focused_icon = None
                    self._apply_search_filter()
                    self.draw_area.queue_draw()
                else:
                    self.hide()
                return True

            if keyval == Gdk.KEY_BackSpace:
                self.state.focused_icon = None
                self.state.search_query = self.state.search_query[:-1]
                self._apply_search_filter()
                self.draw_area.queue_draw()
                return True

            name = Gdk.keyval_name(keyval) or ""
            if keyval == Gdk.KEY_space:
                self.state.search_query += " "
                self.state.focused_icon = None
                self._apply_search_filter()
                self.draw_area.queue_draw()
                return True
            if (
                len(name) == 1
                and name.isprintable()
                and not (state & Gdk.ModifierType.CONTROL_MASK)
            ):
                self.state.search_query += name
                self.state.focused_icon = None
                self._apply_search_filter()
                self.draw_area.queue_draw()
                return True

            return False

        key_ctrl.connect("key-pressed", on_key_pressed)

    # ── Focus navigation ───────────────────────────────────────────

    def _navigate_focus(self, dx: float, dy: float):
        visible = [i for i in self.app._icons if not self._is_filtered(i)]
        if not visible:
            return

        if (
            self.state.focused_icon is None
            or self._is_filtered(self.state.focused_icon)
        ):
            target = visible[0]
            best_score = float("inf")
            for icon in visible:
                score = -(icon.sx * dx + icon.sy * dy)
                if score < best_score:
                    best_score = score
                    target = icon
            self.state.focused_icon = target
            self.draw_area.queue_draw()
            return

        cur = self.state.focused_icon
        best_icon = None
        best_score = float("inf")

        for icon in visible:
            if icon is cur:
                continue
            vx = icon.sx - cur.sx
            vy = icon.sy - cur.sy
            dist = math.sqrt(vx * vx + vy * vy)
            if dist < 1:
                continue
            dot = (vx * dx + vy * dy) / dist
            if dot < 0.1:
                continue
            score = dist / (dot + 0.01)
            if score < best_score:
                best_score = score
                best_icon = icon

        if best_icon is not None:
            self.state.focused_icon = best_icon
            self.draw_area.queue_draw()

    def _navigate_search_results(self):
        visible = [i for i in self.app._icons if not self._is_filtered(i)]
        if not visible:
            return
        if (
            self.state.focused_icon is None
            or self._is_filtered(self.state.focused_icon)
        ):
            self.state.focused_icon = visible[0]
        else:
            try:
                idx = visible.index(self.state.focused_icon)
                self.state.focused_icon = visible[(idx + 1) % len(visible)]
            except ValueError:
                self.state.focused_icon = visible[0]
        self.draw_area.queue_draw()

    def _launch_focused(self):
        if self.state.focused_icon is None:
            return
        self.app._launch_app(self, self.state.focused_icon)

    def _launch_first_match(self):
        if not self.state.search_query:
            return
        q = self.state.search_query.lower()
        for icon in self.app._icons:
            if q in icon.name.lower():
                self.app._launch_app(self, icon)
                return

    def _apply_search_filter(self):
        q = self.state.search_query.lower()
        self.state.filtered_icon_ids.clear()
        if q:
            for icon in self.app._icons:
                if q not in icon.name.lower():
                    self.state.filtered_icon_ids.add(id(icon))
    def _is_filtered(self, icon: IconEntry) -> bool:
        return id(icon) in self.state.filtered_icon_ids

    # ── Hit testing ───────────────────────────────────────────────

    def _hit_test(self, mx: float, my: float) -> Optional[IconEntry]:
        if not self.state.visible:
            return None
        for icon in reversed(
            sorted(self.app._icons, key=lambda i: i.zdepth)
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

    # ── Show / hide ───────────────────────────────────────────────

    def show(self):
        self.state.visible = True
        self.state.time_elapsed = 0.0
        self.state.search_query = ""
        self.state.focused_icon = None
        self.state.hovered_icon = None
        self._apply_search_filter()
        self.app._refresh_apps_if_stale()
        if cfg.reduced_motion:
            self.state.toggle_progress = 1.0
            self.state.toggle_animating = False
        else:
            self.state.toggle_animating = True
        if LAYER_SHELL:
            Gtk4LayerShell.set_layer(self.window, Gtk4LayerShell.Layer.OVERLAY)
        self.window.present()
        self.draw_area.grab_focus()
        self.draw_area.queue_draw()
        if self.app._update_timer_interval:
            self.app._update_timer_interval()

    def hide(self):
        self.state.visible = False
        if cfg.reduced_motion:
            self.state.toggle_progress = 0.0
            self.state.toggle_animating = False
        else:
            self.state.toggle_animating = True
        if LAYER_SHELL:
            Gtk4LayerShell.set_layer(self.window, Gtk4LayerShell.Layer.BOTTOM)
        self.draw_area.queue_draw()
        if self.app._update_timer_interval:
            self.app._update_timer_interval()


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
        self.views: list[MonitorView] = []
        self.icon_loader: Optional[IconLoader] = None
        self._icons: list[IconEntry] = []
        self._launch_counts: dict[str, int] = {}
        self._central_surf: Optional["cairo.ImageSurface"] = None
        self._timer_id: int = 0
        self._update_timer_interval = None
        self._last_active_view: Optional[MonitorView] = None

    # ── Init ──────────────────────────────────────────────────────

    def do_activate(self):
        if not self._acquire_lock():
            print("[orbital-launcher] Another instance is running. Exiting.")
            return

        self._setup_css()
        self._load_data()

        # Create one window per monitor
        display = Gdk.Display.get_default()
        if display:
            monitors = display.get_monitors()
            n = monitors.get_n_items() if monitors else 0
            for i in range(n):
                mon = monitors.get_item(i)
                view = MonitorView(self, mon)
                # Give each view a reference to the shared icons
                view.state.icons = self._icons
                view.state.launch_counts = self._launch_counts
                # Give each renderer the shared central image
                if self._central_surf is not None:
                    view.renderer.central_image_surface = self._central_surf
                self.views.append(view)

        self._setup_signals()
        self._start_animation()

        for v in self.views:
            v.window.present()
            v.draw_area.grab_focus()

    # ── Lock ──────────────────────────────────────────────────────

    def _acquire_lock(self) -> bool:
        try:
            fd = os.open(PID_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            with os.fdopen(fd, "w") as fh:
                fh.write(str(os.getpid()))
            atexit.register(self._release_lock)
            return True
        except FileExistsError:
            pass
        except OSError:
            pass

        try:
            with open(PID_FILE) as fh:
                old_pid = int(fh.read().strip())
            try:
                os.kill(old_pid, 0)
                self._write_target_monitor()
                os.kill(old_pid, signal.SIGUSR1)
                return False
            except OSError:
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
                except (FileExistsError, OSError):
                    return True
        except Exception:
            return True

    def _release_lock(self):
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass

    @staticmethod
    def _write_target_monitor():
        """Ask the compositor which display the cursor is on so the
        running instance can toggle only that monitor.

        Writes a tiny JSON object to ``/tmp/orbital-launcher-target``
        with *connector*, *x*, *y*, *width*, and *height* so the signal
        handler can match by connector name first, then fall back to
        geometry if the names don't align (rare Wayland edge-case)."""
        try:
            import subprocess
            r = subprocess.run(
                ["hyprctl", "cursorpos"], capture_output=True, text=True, timeout=1
            )
            if r.returncode != 0:
                return
            cx, cy = r.stdout.strip().split(",")
            cx, cy = float(cx.strip()), float(cy.strip())
        except Exception:
            return

        try:
            r = subprocess.run(
                ["hyprctl", "monitors", "-j"], capture_output=True, text=True, timeout=1
            )
            if r.returncode != 0:
                return
            import json
            for m in json.loads(r.stdout):
                if m["x"] <= cx < m["x"] + m["width"] and m["y"] <= cy < m["y"] + m["height"]:
                    payload = json.dumps({
                        "connector": m["name"],
                        "x": m["x"], "y": m["y"],
                        "width": m["width"], "height": m["height"],
                    })
                    with open("/tmp/orbital-launcher-target", "w") as fh:
                        fh.write(payload)
                    return
        except Exception:
            pass

    # ── CSS ───────────────────────────────────────────────────────

    def _setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(
            """
            window { background-color: transparent; background: none; }
            drawingarea { background-color: transparent; background: none; }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    # ── Data loading ──────────────────────────────────────────────

    def _load_data(self):
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

        load_user_config()

        # Reduced-motion
        try:
            gtk_settings = Gtk.Settings.get_default()
            if gtk_settings:
                if not gtk_settings.get_property("gtk-enable-animations"):
                    cfg.reduced_motion = True
                    if cfg.drift_rate == 3.0:
                        cfg.drift_rate = 0.0
                        print(
                            "[orbital-launcher] Reduced motion: drift disabled",
                            file=sys.stderr,
                        )
        except Exception:
            pass

        entries = desktop_scan()
        theme_name = cfg.icon_theme_name if cfg.icon_theme_name else None
        self.icon_loader = IconLoader(display, theme_name)

        def _sort_key(e):
            return hashlib.sha256(e["name"].encode()).hexdigest()

        entries.sort(key=_sort_key)
        total = len(entries)
        print(
            f"[orbital-launcher] Distributing {total} apps on "
            f"Fibonacci sphere",
            file=sys.stderr,
        )

        # Load persisted launch counts
        state_path = Path.home() / ".local/share/orbital-launcher/state.json"
        if state_path.exists():
            try:
                import json
                with open(state_path) as fh:
                    self._launch_counts = json.load(fh)
            except Exception:
                pass

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
                launch_count=self._launch_counts.get(
                    os.path.basename(e["desktop_file"]), 0
                ),
            )
            icon.surface = self.icon_loader.load(e["icon_name"])
            icons.append(icon)

        self._icons = icons
        print(
            f"[orbital-launcher] Loaded {len(icons)} apps from desktop files",
            file=sys.stderr,
        )

        # Load central image
        self._central_surf = None
        if cfg.central_image_path and self.icon_loader:
            try:
                raw = cfg.central_image_path
                if raw.startswith("~/"):
                    image_path = str(Path.home() / raw[2:])
                elif raw.startswith("/"):
                    image_path = raw
                else:
                    repo_root = Path(__file__).resolve().parent.parent.parent
                    candidate = str(repo_root / raw)
                    if os.path.exists(candidate):
                        image_path = candidate
                    else:
                        image_path = str(Path.home() / "Pictures" / raw)

                load_size = int(cfg.central_image_size * cfg.dpi_scale * 2)
                surf = self.icon_loader._pixbuf_to_surface(image_path, load_size)
                if surf is not None:
                    self._central_surf = surf
                    print(
                        f"[orbital-launcher] Central image loaded: {image_path}",
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
                    f"[orbital-launcher] Central image load error: {e}",
                    file=sys.stderr,
                )

    # ── Live refresh ────────────────────────────────────────────────

    def _refresh_apps_if_stale(self):
        """Rescan desktop files on every toggle so newly installed apps
        appear without a restart.  Compares by desktop-file path and
        only rebuilds the icon lattice when the set of apps changed."""
        entries = desktop_scan(force=True)
        entries.sort(key=lambda e: hashlib.sha256(e["name"].encode()).hexdigest())

        # Fast path — same set of .desktop files, nothing to do
        old_paths = {icon.desktop_file for icon in self._icons}
        new_paths = {e["desktop_file"] for e in entries}
        if old_paths == new_paths:
            return

        added = new_paths - old_paths
        removed = old_paths - new_paths
        if added:
            print(f"[orbital-launcher] New apps detected: {len(added)}",
                  file=sys.stderr)
        if removed:
            print(f"[orbital-launcher] Apps removed: {len(removed)}",
                  file=sys.stderr)

        total = len(entries)
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
                launch_count=self._launch_counts.get(
                    os.path.basename(e["desktop_file"]), 0
                ),
            )
            icon.surface = self.icon_loader.load(e["icon_name"])
            icons.append(icon)

        self._icons = icons
        for v in self.views:
            v.state.icons = icons
        print(f"[orbital-launcher] Refreshed — {total} apps", file=sys.stderr)

    # ── App launching ─────────────────────────────────────────────

    def _launch_app(self, view: MonitorView, icon: IconEntry):
        key = os.path.basename(icon.desktop_file)
        self._launch_counts[key] = self._launch_counts.get(key, 0) + 1
        # Persist
        import json
        state_path = Path.home() / ".local/share/orbital-launcher/state.json"
        try:
            with open(state_path, "w") as fh:
                json.dump(self._launch_counts, fh, indent=2)
        except Exception:
            pass

        try:
            if icon.terminal:
                term = os.environ.get("TERMINAL", "kitty")
                cmd = [term, "--", "sh", "-c", icon.exec_cmd]
            else:
                cmd = ["sh", "-c", icon.exec_cmd]

            subprocess.Popen(
                cmd,
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"[orbital-launcher] Launched: {icon.name}", file=sys.stderr)
        except Exception as e:
            print(
                f"[orbital-launcher] Failed to launch {icon.name}: {e}",
                file=sys.stderr,
            )

        # Hide only the view that launched
        view.hide()

    # ── Animation ─────────────────────────────────────────────────

    def _start_animation(self):
        active_interval = cfg.fps_active_interval
        idle_interval = cfg.fps_idle_interval

        def tick():
            delta = active_interval / max(cfg.toggle_animation_ms, 1)
            anim_ended = False
            for v in self.views:
                # Advance toggle animation
                if v.state.toggle_animating:
                    if v.state.visible:
                        v.state.toggle_progress = min(1.0, v.state.toggle_progress + delta)
                        if v.state.toggle_progress >= 1.0:
                            v.state.toggle_animating = False
                            anim_ended = True
                    else:
                        v.state.toggle_progress = max(0.0, v.state.toggle_progress - delta)
                        if v.state.toggle_progress <= 0.0:
                            v.state.toggle_animating = False
                            anim_ended = True

                # Rotational drift
                if v.state.visible and not v.state.dragging:
                    v.state.time_elapsed += active_interval / 1000.0

                v.draw_area.queue_draw()

            if anim_ended:
                update_interval()

            return GLib.SOURCE_CONTINUE

        def update_interval():
            any_active = any(
                v.state.visible or v.state.toggle_animating for v in self.views
            )
            interval = active_interval if any_active else idle_interval
            if self._timer_id:
                GLib.source_remove(self._timer_id)
            self._timer_id = GLib.timeout_add(interval, tick)

        self._update_timer_interval = update_interval
        self._timer_id = GLib.timeout_add(active_interval, tick)
        # Immediately adjust to correct interval for current state
        # (all views start hidden → 1000ms idle)
        update_interval()

    # ── Signals ───────────────────────────────────────────────────

    def _setup_signals(self):
        def handle_usr1(signum, frame):
            # Read target monitor descriptor written by _write_target_monitor()
            # (hyprctl cursorpos + monitor geometry lookup).
            # Match by connector name first, then geometry as fallback.
            # Falls back to the last-active-view heuristic if the file
            # isn't available (e.g. non-Hyprland compositor).
            target = None
            try:
                import json
                with open("/tmp/orbital-launcher-target") as fh:
                    info = json.load(fh)
                if info:
                    # 1. Try connector name
                    connector = info.get("connector", "")
                    for v in self.views:
                        if connector and v.monitor.get_connector() == connector:
                            target = v
                            break
                    # 2. Fallback: match by geometry
                    if target is None:
                        gx, gy = info.get("x"), info.get("y")
                        gw, gh = info.get("width"), info.get("height")
                        if gx is not None:
                            for v in self.views:
                                vg = v.monitor.get_geometry()
                                if vg.x == gx and vg.y == gy and vg.width == gw and vg.height == gh:
                                    target = v
                                    break
            except Exception:
                pass

            if target is None:
                target = self._last_active_view

            if target is not None:
                if target.state.visible:
                    target.hide()
                else:
                    target.show()
            else:
                any_visible = any(v.state.visible for v in self.views)
                if any_visible:
                    for v in self.views:
                        v.hide()
                else:
                    for v in self.views:
                        v.show()
            if self._update_timer_interval:
                self._update_timer_interval()

        signal.signal(signal.SIGUSR1, handle_usr1)

        def on_shutdown(*args):
            self._release_lock()

        self.connect("shutdown", on_shutdown)


# ═══════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════


def main():
    app = OrbitalLauncherApp()
    return app.run(sys.argv)
