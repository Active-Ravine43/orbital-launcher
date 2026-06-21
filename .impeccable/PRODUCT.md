# Product

## Register

product

## Users

Single power-user on a CachyOS/Hyprland desktop. The launcher is an alternative to the flat Noctalia Shell app launcher — used when they want a visually distinctive, spatially-aware way to find and launch apps.

## Product Purpose

An orbital 3D spherical icon cloud application launcher. Renders `.desktop` application icons as floating satellites orbiting a central Omega symbol. Provides visual depth cues, spatial memory (deterministic placement), and kinetic interaction (drag rotation, scroll zoom) as an alternative to flat list/tile launchers.

## Brand Personality

**Industrial brutalist** — raw, honest, structurally expressed. Dark void background, surgical red accents, utilitarian typography, no decoration that doesn't serve function. The interface feels like a precision instrument, not a consumer product.

## Anti-references

- No translucent frosted glass / blur effects (glassmorphism)
- No rounded, friendly, consumer-soft aesthetic
- No colorful icon-grid launchers (macOS Launchpad, GNOME app grid)
- No skeuomorphic 3D planet renders — the sphere is implied, not textured
- No superfluous connecting lines or orbital path rings

## Design Principles

1. **Structure expressed** — the 3D sphere is felt through depth cues (scale, alpha), not rendered geometry
2. **Every pixel earns its place** — nothing decorative; the omega, the icons, the search bar are the entire interface
3. **Kinetic over static** — drift rotation and drag give the launcher presence without ornament
4. **Single purpose** — launch apps; no settings, no categories, no configuration UI

## Accessibility & Inclusion

- Keyboard-driven: full search and launch from keyboard
- Reduced motion: drift rotation rate is configurable; could obey `prefers-reduced-motion`
- High contrast: dark background (#050512) with bright foreground ensures readability
- Icon fallbacks: colored disc + initial letter for unresolvable icons
