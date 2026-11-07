#!/usr/bin/env python3
"""Push the 3-archetype site update to crtGhoul/deadlock-build-guide via the
git-database API. Single calm push: blobs (paced) -> tree -> commit -> ref.

Usage: python3 scripts/push-dbg.py   (run from repo root; committed to repo)
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/templates/skill/bin")
import dynamic_credentials as dc

API = "https://api.github.com"
ALLOWED = ["api.github.com"]
REPO = "crtGhoul/deadlock-build-guide"
BRANCH = "main"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Explicit change list for the 3-archetype expansion (built 2026-10-18).
FILES = ["index.html", "data/SCHEMA.md", "assets/data/archetypes.js",
         "scripts/build-site.py", "scripts/protoenc.py", "scripts/classmap.json",
         "scripts/generate_hero_pages.py", "scripts/push-dbg.py",
         "assets-src/arch-ui.css", "assets-src/arch-ui.js"]
FILES += [f"heroes/{s}.html" for s in
          ["abrams","apollo","bebop","billy","calico","celeste","drifter","dynamo",
           "graves","grey-talon","haze","holliday","infernus","ivy","kelvin",
           "lady-geist","lash","mcginnis","mina","mirage","mo-krill","paige",
           "paradox","pocket","rem","seven","shiv","silver","sinclair","the-doorman",
           "venator","victor","vindicta","viscous","vyper","warden","wraith","yamato",
           "rat-king","baba","solomon","deadman-danny","violet"]]
import glob as _g
FILES += sorted(p.replace(BASE + "/", "")
                for p in _g.glob(os.path.join(BASE, "data", "archetypes", "*.json")))


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API + path, data=data,
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "muse-github-skill",
                 "Content-Type": "application/json"},
        method=method)
    dc.add_surrogate_to_request(req, "custom.github", entry_name="access_token",
                                allowed_hosts=ALLOWED)
    try:
        return dc.read_json_response(urllib.request.urlopen(req))
    except urllib.error.HTTPError as exc:
        try:
            err = dc.read_json_response(exc)
        except Exception:
            err = {"message": f"HTTP {exc.code}"}
        raise SystemExit(f"API {method} {path} failed: {exc.code} {err}")


def main():
    ref = api("GET", f"/repos/{REPO}/git/ref/heads/{BRANCH}")
    parent_sha = ref["object"]["sha"]
    print(f"remote {BRANCH} tip: {parent_sha}")

    entries = []
    for i, path in enumerate(FILES):
        full = os.path.join(BASE, path)
        assert os.path.isfile(full), f"missing: {path}"
        with open(full, "rb") as f:
            content = f.read()
        blob = api("POST", f"/repos/{REPO}/git/blobs",
                   {"content": base64.b64encode(content).decode(),
                    "encoding": "base64"})
        entries.append({"path": path, "mode": "100644", "type": "blob",
                        "sha": blob["sha"]})
        if (i + 1) % 20 == 0:
            print(f"  blobs {i+1}/{len(FILES)}")
        time.sleep(0.25)  # calm pacing: not a burst

    base_tree = api("GET", f"/repos/{REPO}/git/commits/{parent_sha}")["tree"]["sha"]
    new_tree = api("POST", f"/repos/{REPO}/git/trees",
                   {"base_tree": base_tree, "tree": entries})["sha"]
    print(f"new tree: {new_tree}")

    msg = ("3-archetype builds: Weapon/Spirit/Vitality per hero\n\n"
           "Every hero now has three complete, switchable build archetypes with a "
           "marked META pick: exact 4.8k category spike, 12-slot final loadouts "
           "(max 4 actives), per-archetype ability priority + 16-step tracks, "
           "sell/upgrade paths, win conditions, meta counters, and copy-paste "
           "in-game import payloads (129 generated, encoder byte-verified).")
    commit = api("POST", f"/repos/{REPO}/git/commits", {
        "message": msg, "tree": new_tree, "parents": [parent_sha],
        "author": {"name": "crtGhoul", "email": "crtghoul@users.noreply.github.com"}})
    print(f"new commit: {commit['sha']}")

    api("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}", {"sha": commit["sha"]})
    print(f"pushed {REPO} {BRANCH} -> {commit['sha']}")


if __name__ == "__main__":
    main()
