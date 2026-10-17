# Deadlock Build Guide

Full builds for all 43 playable Deadlock heroes — exact left-to-right buy order, ability priority + 16-step skill-up track, situational items, combos, and alternate builds where a hero genuinely has one.

**Live:** https://crtghoul.github.io/deadlock-build-guide/

`index.html` plus the `assets/` directory with hero portraits, ability icons, item icons, and crosshair previews. The page is fully static — no server needed. Per-hero share pages live in `heroes/` (hero-specific OpenGraph previews that redirect into the guide); regenerate them with `python3 scripts/generate_hero_pages.py` after adding a hero, and run `python3 scripts/verify_integrity.py` before pushing.
