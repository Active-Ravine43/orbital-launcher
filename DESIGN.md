---
name: Orbital Launcher
description: A 3D spherical icon cloud application launcher — industrial brutalist, CRT terminal aesthetic.
colors:
  void-bg: "#0A0A0A"
  phosphor-white: "#EAEAEA"
  aviation-red: "#E61919"
  muted-telemetry: "#646469"
  elevated-panel: "#0F0F12"
  terminal-green: "#4AF626"
  deep-void: "#050505"
typography:
  ui-mono:
    fontFamily: "Monospace, system-ui monospace"
    fontWeight: 700
    fontSize: "14px"
  omega-display:
    fontFamily: "Serif, system-ui serif"
    fontWeight: 700
    fontSize: "220px"
rounded:
  none: "0px"
spacing:
  search-bar-padding: "16px"
  label-pad-x: "8px"
  label-pad-y: "5px"
components:
  search-bar:
    backgroundColor: "{colors.elevated-panel}"
    textColor: "{colors.phosphor-white}"
    rounded: "{rounded.none}"
    height: "40px"
    width: "420px"
  search-bar-placeholder:
    textColor: "{colors.muted-telemetry}"
  hover-label:
    backgroundColor: "{colors.elevated-panel}"
    textColor: "{colors.phosphor-white}"
    rounded: "{rounded.none}"
  fallback-icon:
    backgroundColor: "{colors.elevated-panel}"
    textColor: "{colors.phosphor-white}"
    rounded: "{rounded.none}"
  omega-centerpiece:
    textColor: "{colors.aviation-red}"
  focus-indicator:
    textColor: "{colors.aviation-red}"
---

# Design System: Orbital Launcher

## 1. Overview

**Creative North Star: "The Declassified Blueprint"**

Orbital Launcher is a single-purpose Linux desktop launcher rendered as a 3D spherical icon cloud. Its visual language draws from military terminal displays, aviation instrument panels, and declassified engineering documents — raw, honest, structurally expressed. Every visual element is justified by function; decoration that doesn't serve the task is prohibited.

The interface lives in a dark void (#0A0A0A — the color of a deactivated CRT phosphor screen, not pure black). A single surgical accent (aviation hazard red, #E61919) marks structural edges, the central omega anchor, and the keyboard focus indicator. Text is exclusively monospace, set against the void with no intermediate surfaces except the elevated panel (#0F0F12) used sparingly for the search bar, hover labels, and fallback icon backgrounds.

Depth is conveyed through three simultaneous cues — alpha falloff, perspective scale, and painter's-sort layering — without wireframes, orbital path rings, or surface textures. The sphere is felt, not drawn. The interface rejects rounded corners entirely (0px radius everywhere), translucent materials, gradients, and shadows. It is flat-shaded and hard-edged by principle.

**Key Characteristics:**
- Single accent color (aviation red) used at ≤15% of any frame
- Zero border-radius — every rectangle has sharp mechanical corners
- Monospace typography throughout; Serif reserved for the omega glyph only
- Depth expressed through alpha + scale + layering, never shadows
- CRT textural overlays (noise grain, scanlines) are available but off by default
- No settings UI — all tuning is code-level configuration

## 2. Colors: The Phosphor Void Palette

A dark, high-contrast palette anchored by near-black void and phosphor white, with a single saturated accent (aviation hazard red) and a single-use status green.

### Primary
- **Aviation Red** (#E61919): The sole accent. Used for the omega centerpiece (80% alpha), structural left-edge strikethroughs on panels (70%), keyboard focus corner brackets (80%), the search cursor block (70%), and border strokes (40%). Never used as a background fill — it marks edges and anchors, not surfaces. At rest, the accent occupies ≤5% of any frame; under keyboard focus, ≤8%.

### Neutral
- **Void Background** (#0A0A0A): The full-frame background. The color of a deactivated CRT — near-black with the faintest warmth so it doesn't read as pure digital black. All content floats directly on this surface.
- **Phosphor White** (#EAEAEA): Primary text and icon color. The color of a bright CRT phosphor — not pure white, carrying a whisper of warmth. Used for icon rendering, search query text, hover labels, and fallback icon letters. At full alpha (1.0) it hits ~17:1 contrast against the void.
- **Muted Telemetry** (#646469): Secondary/dimmed text. Used only for the search bar placeholder `[ SEARCH ]` at 50% alpha. Never used for body text or labels.
- **Elevated Panel** (#0F0F12): The single intermediate surface. Used as background for the search bar, hover labels, and fallback icon badges. Sits perceptibly above the void — lighter and slightly cooler. Always at 85% alpha so the void bleeds through subtly.
- **Deep Void** (#050505): Darker-than-background. Used only for CRT texture overlays (noise grain and scanlines) at very low opacity (1.5–3%). Never used as a surface.
- **Terminal Green** (#4AF626): Reserved for future status indicators. Defined but not currently rendered in the interface.

### Named Rules
**The One Accent Rule.** Aviation red is the only accent color permitted in the interface. Terminal green is a status-only signal reserved for future use. No other saturated colors appear — the desktop icons themselves are recolored to red monochrome unless they come from a recognized red theme.

**The No-Round Rule.** Every rectangle, border, and panel has 0px border-radius. Sharp corners are the default and only option. If a corner appears rounded, it's a bug.

## 3. Typography: The Terminal Grid

**UI Font:** Monospace (system monospace stack — DejaVu Sans Mono, SF Mono, or similar, depending on platform)
**Display Font:** Serif (system serif stack) — used exclusively for the omega glyph
**Character:** Monospace throughout creates a terminal/telemetry coherence. The serif omega provides a single moment of classical contrast — the only non-monospace glyph in the entire interface, and it's a single character.

### Hierarchy
- **Omega Display** (Serif, Bold 700, 220px, line-height 1.0): The central anchor. Rendered in aviation red at 80% alpha. Single character only. Size scales with DPI.
- **Search Bar Text** (Monospace, Normal 400, 14px, line-height 1.0): Query text and placeholder. Query in phosphor white (90% alpha); placeholder `[ SEARCH ]` in muted telemetry (50% alpha). Size scales with DPI.
- **Hover Label** (Monospace, Bold 700, 14px, line-height 1.0): App name in phosphor white (95% alpha), prefixed with `>>> ` in terminal prompt style. Size scales with DPI.
- **Fallback Icon Letter** (Monospace, Bold 700, ~20px, line-height 1.0): Single uppercase initial letter in phosphor white at full alpha. Centered in the badge.

### Named Rules
**The Monospace Mandate.** All UI text — labels, search, fallback letters, telemetry — must be monospace. Serif is reserved exclusively for the omega glyph. Sans-serif fonts are prohibited.

## 4. Elevation: The Depth-Without-Shadow System

This system uses **zero shadows**. No `box-shadow`, no drop shadows, no blur-based elevation. Depth is conveyed through three simultaneous cues that compound:

1. **Alpha falloff with distance**: Icons farther from the camera render at lower opacity (range: 20%–100% alpha), emulating atmospheric perspective. Closer = brighter phosphor.
2. **Perspective scale**: A near-orthographic projection (camera distance 1500 units) applies gentle foreshortening — icons at the back of the sphere are smaller (down to 45% of base size).
3. **Painter's sort**: Icons are drawn back-to-front by z-depth, so near icons occlude far icons correctly. The omega centerpiece sits at z=0, splitting the sphere into behind-omega and front-omega layers.

Surfaces that need to read as "above" the void (search bar, hover label) use the Elevated Panel color (#0F0F12 at 85% alpha) for a subtle tonal lift — never a shadow.

### Named Rules
**The Flat-By-Default Rule.** No element casts a shadow. The interface is flat at rest. The only depth cues are the three projective cues listed above. If an element needs to read as elevated, use the Elevated Panel background color — nothing else.

## 5. Components

Every component shares: 0px border-radius, monospace typography, aviation red accent for structural edges, and phosphor white for text. There is one component vocabulary, applied uniformly.

### Search Bar
- **Shape:** Sharp rectangle, 420×40px logical (scales with DPI). No radius.
- **Background:** Elevated Panel (#0F0F12) at 85% alpha.
- **Border:** 1px aviation red at 40% alpha, all four edges.
- **Structural accent:** 1px aviation red at 70% alpha along the left edge — a mechanical strikethrough marking the input origin.
- **Placeholder:** `[ SEARCH ]` in muted telemetry at 50% alpha, monospace 14px.
- **Active query:** `[ >> <query> ]` in phosphor white at 90% alpha, monospace 14px.
- **Cursor:** A blinking rectangular block (7px × text height) in aviation red at 70% alpha, positioned after the query text.
- **Focus:** The bar is always "focused" when the launcher is visible — there's no unfocused state. Keyboard input goes directly to search.

### Hover Label
- **Shape:** Sharp rectangle, sized to text content. No radius.
- **Background:** Elevated Panel (#0F0F12) at 85% alpha.
- **Border:** 1px aviation red at 40% alpha, all four edges.
- **Structural accent:** 1px aviation red at 70% alpha along the left edge.
- **Text:** `>>> APPNAME` in monospace bold 14px, phosphor white at 95% alpha.
- **Position:** Centered below the hovered icon, offset by half the icon's on-screen size plus 8px.

### Fallback Icon Badge
- **Shape:** Square badge, sized to the base icon size. No radius.
- **Background:** Elevated Panel (#0F0F12) at 45% alpha.
- **Structural accent:** 1px aviation red at 85% alpha along the left edge.
- **Mechanical detail:** A diagonal notch in the top-right corner — aviation red at 60% alpha, 1.5px stroke.
- **Letter:** Single uppercase initial, monospace bold, phosphor white at 100% alpha, centered.

### Omega Centerpiece
- **Shape:** Single character "Ω" or a custom PNG image.
- **Glyph:** Serif bold 220px, aviation red at 80% alpha. Centered on screen.
- **Custom image:** When configured, renders a PNG at the specified size (default 220px) with 80% alpha. Falls back to the glyph if the image fails to load or isn't configured.
- **Depth position:** Fixed at z=0 — the equatorial plane of the sphere. Icons behind the omega are drawn first; icons in front are drawn after.

### Icons (Desktop Application Satellites)
- **Shape:** Variable — loaded from system icon themes or pixmaps, recolored to red monochrome.
- **Size:** 44px base (scales with DPI and perspective projection). On-screen range: ~20px (back of sphere) to ~88px (front, hovered).
- **Alpha:** Depth-mapped from 20% (far) to 100% (near).
- **Hover boost:** 1.30× scale multiplier on mouse hover.
- **Filtered state:** Icons not matching the current search query drop to 8% alpha — present but barely visible.

### Keyboard Focus Indicator
- **Shape:** Four corner brackets around the focused icon — top-left, top-right, bottom-right, bottom-left.
- **Color:** Aviation red at 80% alpha, 2px stroke.
- **Bracket length:** ~12px, proportional to icon size.
- **Visibility:** Shown only when keyboard focus is active. Hidden during mouse drag. Cleared on new search input.

## 6. Do's and Don'ts

### Do:
- **Do** use the Elevated Panel (#0F0F12) for any surface that must read above the void
- **Do** use aviation red (#E61919) exclusively for edges, borders, the omega, and focus — never as a surface fill
- **Do** keep all corners sharp (0px radius) on every rectangle and panel
- **Do** use monospace for all UI text; Serif is reserved for the omega glyph only
- **Do** convey depth through alpha falloff, perspective scale, and draw order — never shadows
- **Do** keep the interface to four elements: icons, omega, search bar, hover label
- **Do** let the void (#0A0A0A) dominate — the interface is sparse by design

### Don't:
- **Don't** use translucent frosted glass or blur effects (glassmorphism)
- **Don't** use rounded corners — not on cards, not on buttons, not on inputs. 0px radius everywhere
- **Don't** use colorful icon-grid layouts (macOS Launchpad, GNOME app grid)
- **Don't** render skeuomorphic 3D planet textures or orbital path rings — the sphere is implied, not drawn
- **Don't** add superfluous connecting lines or decorative geometry
- **Don't** add gradient text, box shadows, or repeating-linear-gradient stripes
- **Don't** introduce a second accent color — terminal green is reserved for future status use only
- **Don't** add settings UI, category filters, or configuration panels — the launcher does one thing
- **Don't** use sans-serif fonts anywhere in the interface
- **Don't** apply border-radius greater than 0px — if you see a rounded corner, it's wrong
