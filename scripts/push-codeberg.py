#!/usr/bin/env python3
"""Push the 3-archetype site update to Codeberg crtGhoul/deadlock-build-guide
via the Contents API (create POST / update PUT with sha). Codeberg is the
canonical host while GitHub is frozen. Calm pacing, one commit per file.

Usage: python3 scripts/push-codeberg.py   (run from repo root)
"""
import base64
import glob as _g
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
import dynamic_credentials as dc

API = "https://codeberg.org"
ALLOWED = ["codeberg.org"]
REPO = "crtGhoul/deadlock-build-guide"
BRANCH = "main"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MSG = "3-archetype builds (Weapon/Spirit/Vitality) + simpler hero picker; Cloudflare is the live URL"

FILES = ["index.html", "README.md", "data/SCHEMA.md", "assets/data/archetypes.js",
         "scripts/build-site.py", "scripts/protoenc.py", "scripts/classmap.json",
         "scripts/generate_hero_pages.py", "scripts/push-dbg.py",
         "scripts/push-codeberg.py",
         "assets-src/arch-ui.css", "assets-src/arch-ui.js"]
FILES += [f"heroes/{s}.html" for s in
          ["abrams", "apollo", "bebop", "billy", "calico", "celeste", "drifter", "dynamo",
           "graves", "grey-talon", "haze", "holliday", "infernus", "ivy", "kelvin",
           "lady-geist", "lash", "mcginnis", "mina", "mirage", "mo-krill", "paige",
           "paradox", "pocket", "rem", "seven", "shiv", "silver", "sinclair", "the-doorman",
           "venator", "victor", "vindicta", "viscous", "vyper", "warden", "wraith", "yamato",
           "rat-king", "baba", "solomon", "deadman-danny", "violet"]]
FILES += sorted(p.replace(BASE + "/", "")
                for p in _g.glob(os.path.join(BASE, "data", "archetypes", "*.json")))


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API + path, data=data,
        headers={"Accept": "application/json",
                 "User-Agent": "muse-codeberg-skill",
                 "Content-Type": "application/json"},
        method=method)
    dc.add_surrogate_to_request(req, "custom.codeberg", entry_name="access_token",
                                allowed_hosts=ALLOWED)
    try:
        return dc.read_json_response(urllib.request.urlopen(req)), 200
    except urllib.error.HTTPError as exc:
        try:
            err = dc.read_json_response(exc)
        except Exception:
            err = {"message": f"HTTP {exc.code}"}
        return err, exc.code


def main():
    created = updated = 0
    for i, path in enumerate(FILES):
        full = os.path.join(BASE, path)
        assert os.path.isfile(full), f"missing: {path}"
        with open(full, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        qpath = urllib.parse.quote(path, safe="/")
        existing, code = api("GET", f"/api/v1/repos/{REPO}/contents/{qpath}?ref={BRANCH}")
        if code == 200 and isinstance(existing, dict) and existing.get("sha"):
            body = {"branch": BRANCH, "sha": existing["sha"],
                    "message": MSG, "content": content}
            res, code = api("PUT", f"/api/v1/repos/{REPO}/contents/{qpath}", body)
            updated += 1
        elif code == 404:
            body = {"branch": BRANCH, "message": MSG, "content": content}
            res, code = api("POST", f"/api/v1/repos/{REPO}/contents/{qpath}", body)
            created += 1
        else:
            raise SystemExit(f"GET {path} failed: {code} {existing}")
        if code not in (200, 201):
            raise SystemExit(f"push {path} failed: {code} {res}")
        if (i + 1) % 20 == 0:
            print(f"  pushed {i+1}/{len(FILES)}")
        time.sleep(0.15)  # calm pacing
    print(f"DONE: {len(FILES)} files ({created} created, {updated} updated)")


if __name__ == "__main__":
    main()
