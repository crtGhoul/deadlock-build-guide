#!/usr/bin/env python3
"""Generate per-hero share pages under heroes/<slug>.html.

GitHub Pages serves one static head for the guide, and link scrapers
(Discord/Reddit) do not run JS, so the ?hero=<slug> deep link can never
carry hero-specific OpenGraph tags. Each generated page carries that
hero's OG/Twitter metadata and immediately redirects into the guide at
/?hero=<slug> (preserving any ?build= param). Re-run after adding a hero.
"""
import html
import json
import re
from pathlib import Path

REPO = Path(__file__).parent.parent
BASE = "https://deadlock-build-guide.pages.dev"
content = (REPO / "index.html").read_text(encoding="utf-8")


def extract(decl):
    m = re.search(r"(?:const|let|var)\s+" + re.escape(decl) + r"\s*=", content)
    i = m.end()
    while content[i] in " \t\n":
        i += 1
    open_c, close_c = content[i], ("]" if content[i] == "[" else "}")
    depth, instr, esc, j = 0, False, False, i
    while j < len(content):
        ch = content[j]
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
        else:
            if ch == '"':
                instr = True
            elif ch == open_c:
                depth += 1
            elif ch == close_c:
                depth -= 1
                if depth == 0:
                    return json.loads(content[i:j + 1])
        j += 1
    raise AssertionError(decl)


def slug(text):
    return re.sub(r"^-|-+$", "", re.sub(r"[^a-z0-9]+", "-", str(text).lower()))


heroes = extract("heroes")
alts = extract("alts")
tiers = extract("tiers")
portraits = extract("portraits")
tier_of = {h: t for t, names in tiers.items() if isinstance(names, list) for h in names}

out_dir = REPO / "heroes"
out_dir.mkdir(exist_ok=True)
written = []
for h in heroes:
    name = h["hero"]
    s = slug(name)
    tier = tier_of.get(name, "")
    has_alt = name in alts
    desc = (f"{name} builds for Deadlock ({h['role']}, {tier} tier): five complete builds "
            f"\u2014 Weapon, Spirit, Vitality, NUKE, and CN (\u2605 META pick marked) \u2014 each with exact buy order, "
            f"ability priority, 16-step skill-up track, sell/upgrade path, late-game win condition "
            f"and meta counters, with a copy-paste in-game import.")
    title = f"{name} Build \u2014 Deadlock Build Guide"
    portrait = portraits.get(name, "")
    img_url = portrait if portrait.startswith("http") else f"{BASE}/{portrait}"
    canonical = f"{BASE}/?hero={s}"
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(desc, quote=True)}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="Deadlock Build Guide">
  <meta property="og:title" content="{html.escape(title, quote=True)}">
  <meta property="og:description" content="{html.escape(desc, quote=True)}">
  <meta property="og:url" content="{BASE}/heroes/{s}.html">
  <meta property="og:image" content="{img_url}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{html.escape(title, quote=True)}">
  <meta name="twitter:description" content="{html.escape(desc, quote=True)}">
  <meta name="twitter:image" content="{img_url}">
  <script>
    (function () {{
      var q = new URLSearchParams(window.location.search);
      var target = "../?hero={s}";
      if (q.get("build")) target += "&build=" + encodeURIComponent(q.get("build"));
      window.location.replace(target);
    }})();
  </script>
</head>
<body>
  <h1>{html.escape(name)} Build</h1>
  <p>{html.escape(desc)}</p>
  <p>{html.escape(h.get("tip", ""))}</p>
  <p><a href="../?hero={s}">Open the full {html.escape(name)} build in the Deadlock Build Guide</a></p>
</body>
</html>
"""
    (out_dir / f"{s}.html").write_text(page, encoding="utf-8")
    written.append(s)

print(f"wrote {len(written)} hero pages: {', '.join(written)}")
