#!/usr/bin/env python3
"""Push the Prompts v2 update (31 simulator / 32v2 polish+share card / 33 build creator) to Codeberg
crtGhoul/deadlock-build-guide via the Contents API (create POST / update PUT
with sha). Codeberg is canonical while GitHub is frozen. Calm pacing, one
commit per file, 403 PushRejected -> 3.5s backoff, max 6 attempts.

Usage: python3 scripts/push-codeberg-tooltips.py   (run from repo root)
"""
import base64
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
MSG = "Prompts 31+32v2+33: AP progression simulator (game-data boon model), Build Creator with fail-closed Base64 share links, tooltip plaque polish, Production share card"

FILES = ["index.html", "assets/data/archetypes.js", "assets/share-card.jpg",
         "assets-src/arch-ui.css", "assets-src/arch-ui.js",
         "data/SCHEMA.md",
         "scripts/build-site.py", "scripts/validate-archetypes.py",
         "scripts/verify_integrity.py",
         "scripts/ap-model.json", "scripts/gen-ap-model.py",
         "scripts/push-codeberg-v2.py"]


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
        # Contents-API writes race the branch ref under load: on 403
        # PushRejected, back off 3s+ and retry (max 6 attempts).
        attempt = 0
        while True:
            attempt += 1
            cur, gcode = api("GET", f"/api/v1/repos/{REPO}/contents/{qpath}?ref={BRANCH}")
            if gcode == 200 and isinstance(cur, dict) and cur.get("sha"):
                body = {"branch": BRANCH, "sha": cur["sha"],
                        "message": MSG, "content": content}
                res, code = api("PUT", f"/api/v1/repos/{REPO}/contents/{qpath}", body)
                if attempt == 1: updated += 1
            elif gcode == 404:
                body = {"branch": BRANCH, "message": MSG, "content": content}
                res, code = api("POST", f"/api/v1/repos/{REPO}/contents/{qpath}", body)
                if attempt == 1: created += 1
            else:
                raise SystemExit(f"GET {path} failed: {gcode} {cur}")
            if code in (200, 201):
                break
            if code == 403 and attempt < 6:
                print(f"  {path}: 403 (attempt {attempt}) — backing off 3.5s")
                time.sleep(3.5)
                continue
            raise SystemExit(f"push {path} failed: {code} {res}")
        print(f"  pushed {i+1}/{len(FILES)}: {path}")
        time.sleep(0.6)  # calm pacing
    print(f"DONE: {len(FILES)} files ({created} created, {updated} updated)")


if __name__ == "__main__":
    main()
