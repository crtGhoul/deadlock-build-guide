#!/usr/bin/env python3
"""Resume the CN push: for each of the 99 CN files, fetch Codeberg's raw
bytes, compare SHA-256 to local, and push ONLY mismatches (the first
push-codeberg-cn.py run died mid-heroes-section when /tmp was wiped and
its process went with it; its per-file commits are atomic, so a file is
either landed or not — the SHA comparison is the resume logic).

Same Contents API pattern as push-codeberg-cn.py: create POST / update
PUT with sha, 403 PushRejected -> 3.5s backoff, max 6 attempts, ~0.6s
pacing. Log goes to stdout (redirect to a workspace file, NOT /tmp).

Usage: python3 scripts/push-codeberg-cn-resume.py   (run from repo root)
"""
import base64
import hashlib
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

FILES = []
import glob as _glob
FILES += sorted(_glob.glob('data/archetypes/*.json'))
FILES += sorted(_glob.glob('heroes/*.html'))
FILES += ['index.html', 'assets/data/archetypes.js', 'scripts/gen-cn.py',
          'scripts/validate-archetypes.py', 'scripts/build-site.py',
          'scripts/verify_integrity.py', 'scripts/generate_hero_pages.py',
          'assets-src/arch-ui.js', 'assets-src/arch-ui.css', 'data/SCHEMA.md',
          'scripts/push-codeberg-cn.py', 'scripts/push-codeberg-cn-resume.py']


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


def raw_bytes(path):
    qpath = urllib.parse.quote(path, safe="/")
    req = urllib.request.Request(
        f"{API}/{REPO}/raw/branch/{BRANCH}/{qpath}",
        headers={"User-Agent": "muse-codeberg-skill"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def main():
    print(f"resume check over {len(FILES)} files", flush=True)
    skipped = pushed = 0
    for i, path in enumerate(FILES):
        full = os.path.join(BASE, path)
        assert os.path.isfile(full), f"missing: {path}"
        local = open(full, "rb").read()
        try:
            remote = raw_bytes(path)
        except Exception as e:
            print(f"  {path}: raw fetch failed ({e}) — will push anyway", flush=True)
            remote = b"__fetch_failed__"
        if remote is not None and hashlib.sha256(remote).hexdigest() == hashlib.sha256(local).hexdigest():
            skipped += 1
            print(f"  ok {i+1}/{len(FILES)}: {path} (already landed)", flush=True)
            continue
        content = base64.b64encode(local).decode()
        qpath = urllib.parse.quote(path, safe="/")
        attempt = 0
        while True:
            attempt += 1
            cur, gcode = api("GET", f"/api/v1/repos/{REPO}/contents/{qpath}?ref={BRANCH}")
            if gcode == 200 and isinstance(cur, dict) and cur.get("sha"):
                body = {"branch": BRANCH, "sha": cur["sha"],
                        "message": MSG, "content": content}
                res, code = api("PUT", f"/api/v1/repos/{REPO}/contents/{qpath}", body)
            elif gcode == 404:
                body = {"branch": BRANCH, "message": MSG, "content": content}
                res, code = api("POST", f"/api/v1/repos/{REPO}/contents/{qpath}", body)
            else:
                raise SystemExit(f"GET {path} failed: {gcode} {cur}")
            if code in (200, 201):
                break
            if code == 403 and attempt < 6:
                print(f"  {path}: 403 (attempt {attempt}) — backing off 3.5s", flush=True)
                time.sleep(3.5)
                continue
            raise SystemExit(f"push {path} failed: {code} {res}")
        pushed += 1
        print(f"  pushed {i+1}/{len(FILES)}: {path}", flush=True)
        time.sleep(0.6)
    print(f"DONE: {len(FILES)} files checked, {skipped} already landed, {pushed} pushed", flush=True)


if __name__ == "__main__":
    main()
