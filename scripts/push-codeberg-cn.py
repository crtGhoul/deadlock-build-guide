#!/usr/bin/env python3
"""Push the CN tab (5th build path, Chinese-community builds for all 44
heroes) to Codeberg crtGhoul/deadlock-build-guide via the Contents API
(create POST / update PUT with sha). Codeberg is canonical while GitHub
is frozen. Calm pacing, one commit per file, 403 PushRejected -> 3.5s
backoff, max 6 attempts.

Usage: python3 scripts/push-codeberg-cn.py   (run from repo root)
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
MSG = "CN tab: 5th build path for all 44 heroes — Chinese-community tempo builds from Chinese-language guides (deadlock.coach/zh-CN, deadlockdb.wiki/zh, worldlock.org/zh-cn, games.gg, metabot.gg, deadlocklabs.gg); 24 heroes cite a specific guide page, 20 carry the honest consensus label; same pipeline (validator 44 heroes 0 errors 0 warnings, 220 payloads, tooltips, counter-buys, simulator); META stays default, deep link ?build=cn; hero pages synced to the live tiers literal; changelog #34"

FILES = [
    'data/archetypes/abrams.json',
    'data/archetypes/apollo.json',
    'data/archetypes/baba.json',
    'data/archetypes/bebop.json',
    'data/archetypes/billy.json',
    'data/archetypes/calico.json',
    'data/archetypes/celeste.json',
    'data/archetypes/deadman-danny.json',
    'data/archetypes/drifter.json',
    'data/archetypes/dynamo.json',
    'data/archetypes/graves.json',
    'data/archetypes/grey-talon.json',
    'data/archetypes/haze.json',
    'data/archetypes/holliday.json',
    'data/archetypes/infernus.json',
    'data/archetypes/ivy.json',
    'data/archetypes/kelvin.json',
    'data/archetypes/lady-geist.json',
    'data/archetypes/lash.json',
    'data/archetypes/mcginnis.json',
    'data/archetypes/mina.json',
    'data/archetypes/mirage.json',
    'data/archetypes/mo-krill.json',
    'data/archetypes/nurse-harrow.json',
    'data/archetypes/paige.json',
    'data/archetypes/paradox.json',
    'data/archetypes/pocket.json',
    'data/archetypes/rat-king.json',
    'data/archetypes/rem.json',
    'data/archetypes/seven.json',
    'data/archetypes/shiv.json',
    'data/archetypes/silver.json',
    'data/archetypes/sinclair.json',
    'data/archetypes/solomon.json',
    'data/archetypes/the-doorman.json',
    'data/archetypes/venator.json',
    'data/archetypes/victor.json',
    'data/archetypes/vindicta.json',
    'data/archetypes/violet.json',
    'data/archetypes/viscous.json',
    'data/archetypes/vyper.json',
    'data/archetypes/warden.json',
    'data/archetypes/wraith.json',
    'data/archetypes/yamato.json',
    'heroes/abrams.html',
    'heroes/apollo.html',
    'heroes/baba.html',
    'heroes/bebop.html',
    'heroes/billy.html',
    'heroes/calico.html',
    'heroes/celeste.html',
    'heroes/deadman-danny.html',
    'heroes/drifter.html',
    'heroes/dynamo.html',
    'heroes/graves.html',
    'heroes/grey-talon.html',
    'heroes/haze.html',
    'heroes/holliday.html',
    'heroes/infernus.html',
    'heroes/ivy.html',
    'heroes/kelvin.html',
    'heroes/lady-geist.html',
    'heroes/lash.html',
    'heroes/mcginnis.html',
    'heroes/mina.html',
    'heroes/mirage.html',
    'heroes/mo-krill.html',
    'heroes/nurse-harrow.html',
    'heroes/paige.html',
    'heroes/paradox.html',
    'heroes/pocket.html',
    'heroes/rat-king.html',
    'heroes/rem.html',
    'heroes/seven.html',
    'heroes/shiv.html',
    'heroes/silver.html',
    'heroes/sinclair.html',
    'heroes/solomon.html',
    'heroes/the-doorman.html',
    'heroes/venator.html',
    'heroes/victor.html',
    'heroes/vindicta.html',
    'heroes/violet.html',
    'heroes/viscous.html',
    'heroes/vyper.html',
    'heroes/warden.html',
    'heroes/wraith.html',
    'heroes/yamato.html',
    'index.html',
    'assets/data/archetypes.js',
    'scripts/gen-cn.py',
    'scripts/validate-archetypes.py',
    'scripts/build-site.py',
    'scripts/verify_integrity.py',
    'scripts/generate_hero_pages.py',
    'assets-src/arch-ui.js',
    'assets-src/arch-ui.css',
    'data/SCHEMA.md',
    'scripts/push-codeberg-cn.py',
]

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
