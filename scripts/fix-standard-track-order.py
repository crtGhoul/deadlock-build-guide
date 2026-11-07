#!/usr/bin/env python3
"""Rewrite the STANDARD builds' skill-up tracks to true chronological order.

Follow-up to scripts/fix-track-order.py (Cesar's decision, 2026-10-23): the
176 archetype tracks were fixed first; the Standard builds' tracks — the
`const skillups = {...}` literal authored directly in index.html (no
generator writes it; build-site.py never touches that region, so editing
index.html IS editing the source) — had the same class of issue in 11 of 44
heroes: the ultimate unlocked before the 4th unlock, which the game does
not allow (the ultimate takes the 4th unlock, at 3,800 gathered souls).

Each Standard step is an object {"ability": name, "tier": "unlock" | "1 AP"
| "2 AP" | "5 AP"} — 16 steps per hero. Reorder semantics are EXACTLY the
shipped simulator's deferral (same as fix-track-order.py): scan the authored
order and apply the first step that is currently legal; the only structural
blocker is an ultimate step that would unlock while fewer than 3 other
abilities are unlocked — it defers to the nearest legal position. A step is
only ever applied when it is its ability's earliest remaining step, so each
ability's tier sequence (unlock -> 1 AP -> 2 AP -> 5 AP) is preserved.

HARD INVARIANTS, asserted per hero before anything is written:
  - the multiset of (ability, tier) steps is identical before/after;
  - each ability's tier sequence is unchanged (only positions move);
  - the track stays 16 steps and every step names a real ability;
  - in the new order the ultimate is the 4th distinct ability (unlock #4);
  - the new order is fundable under the validator's greedy simulation.
If a hero cannot satisfy the invariants (or its authored format is not the
expected uniform shape), it is left untouched and reported.

Serialization guard: the literal must round-trip byte-identically through
json.dumps(..., separators=(',', ':')) BEFORE any edit is applied, so the
write changes nothing outside the reordered steps arrays.

Usage: python3 scripts/fix-standard-track-order.py [--dry-run]
"""
import json
import os
import re
import sys
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
INDEX = os.path.join(ROOT, 'index.html')
AP_MODEL = json.load(open(os.path.join(BASE, 'ap-model.json')))
ABILITY_NAMES = json.load(open(os.path.join(BASE, 'ability-names.json')))
AP_LEVELS = [(l['souls'], l['reward']) for l in AP_MODEL['levels']]
ULTIMATES = AP_MODEL['ultimates']
TIERS = ['unlock', '1 AP', '2 AP', '5 AP']


def locate_literal(content):
    """Return (start, end, parsed) of the `const skillups = {...}` literal."""
    m = re.search(r'(?:const|let|var)\s+skillups\s*=', content)
    assert m, 'skillups declaration not found'
    i = m.end()
    while content[i] in ' \t\n':
        i += 1
    assert content[i] == '{', 'skillups literal does not start with {'
    depth, instr, esc, j = 0, False, False, i
    while j < len(content):
        ch = content[j]
        if instr:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                instr = False
        else:
            if ch == '"':
                instr = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return i, j, json.loads(content[i:j + 1])
        j += 1
    raise AssertionError('unbalanced skillups literal')


def legal_order(steps, ult):
    """Simulator deferral on step objects: repeatedly apply the first
    pending step that is its ability's earliest remaining step and is not
    a structurally blocked ultimate unlock."""
    pending = list(steps)
    unlocked = []
    result = []
    while pending:
        seen = set()
        applied = False
        for i, st in enumerate(pending):
            nm = st['ability']
            if nm in seen:
                continue  # not this ability's earliest remaining step
            seen.add(nm)
            blocked = nm not in unlocked and nm == ult and len(unlocked) < 3
            if not blocked:
                pending.pop(i)
                result.append(st)
                if nm not in unlocked:
                    unlocked.append(nm)
                applied = True
                break
        if not applied:
            return None  # no applicable step — cannot fix without changing spends
    return result


def fundable(track_names):
    """The validator's greedy funding simulation, verbatim semantics."""
    unlocked, tokens, pool, ei = [], 0, 0, 0

    def grant():
        nonlocal tokens, pool, ei
        _souls, reward = AP_LEVELS[ei]
        ei += 1
        if reward == 'unlock':
            tokens += 1
        else:
            pool += 1

    for nm in track_names:
        if nm not in unlocked:
            while tokens == 0 and ei < len(AP_LEVELS):
                grant()
            if tokens == 0:
                return False
            tokens -= 1
            unlocked.append(nm)
        else:
            while pool == 0 and ei < len(AP_LEVELS):
                grant()
            if pool == 0:
                return False
            pool -= 1
    return True


def firsts(names):
    out = []
    for nm in names:
        if nm not in out:
            out.append(nm)
    return out


def tier_sequences(steps):
    per = {}
    for st in steps:
        per.setdefault(st['ability'], []).append(st['tier'])
    return per


def main():
    dry = '--dry-run' in sys.argv
    content = open(INDEX, encoding='utf-8').read()
    start, end, data = locate_literal(content)
    literal = content[start:end + 1]

    # Serialization guard: refuse to write unless the unmodified literal
    # round-trips byte-identically (keeps the diff confined to the steps).
    reser = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    assert reser == literal, 'skillups literal does not round-trip byte-identically — refusing to edit'

    stats = {'reordered': [], 'unchanged': 0, 'skipped': []}
    invariant_ok = 0
    for hero, entry in data.items():
        steps = entry.get('steps')
        abilities = ABILITY_NAMES.get(hero, [])
        ult = ULTIMATES.get(hero)
        reason = None
        new_steps = None
        if not isinstance(steps, list):
            reason = 'steps is not a list'
        elif hero not in ABILITY_NAMES or ult is None:
            reason = 'hero missing from ability-names.json / ap-model ultimates'
        elif any(not isinstance(st, dict) or tuple(st.keys()) != ('ability', 'tier')
                 or st['tier'] not in TIERS for st in steps):
            reason = 'step format is not the uniform {ability, tier} shape'
        elif any(st['ability'] not in abilities for st in steps):
            reason = 'a step names an ability outside the hero\'s set'
        elif any(ts != TIERS[:len(ts)] for ts in tier_sequences(steps).values()):
            reason = 'authored per-ability tier sequence is not a clean unlock/1/2/5 prefix'
        else:
            new_steps = legal_order(steps, ult)
            names = [st['ability'] for st in steps]
            new_names = [st['ability'] for st in new_steps] if new_steps else []
            if new_steps is None:
                reason = 'no legal order exists without changing spends'
            elif len(steps) != 16:
                reason = f'track has {len(steps)} steps, expected 16'
            elif Counter((st['ability'], st['tier']) for st in new_steps) != \
                    Counter((st['ability'], st['tier']) for st in steps):
                reason = 'step multiset changed'
            elif tier_sequences(new_steps) != tier_sequences(steps):
                reason = 'per-ability tier sequence changed'
            elif len(firsts(new_names)) != 4 or firsts(new_names).index(ult) != 3:
                reason = 'ultimate is not the 4th unlock in the new order'
            elif not fundable(new_names):
                reason = 'new order is not fundable under the greedy simulation'
        if reason:
            stats['skipped'].append(f'{hero}: {reason} — left untouched')
            continue
        invariant_ok += 1
        if new_steps != steps:
            stats['reordered'].append(hero)
            entry['steps'] = new_steps
        else:
            stats['unchanged'] += 1

    print(f'heroes processed: {len(data)}')
    print(f'invariants held:  {invariant_ok}/{len(data)}')
    print(f'tracks reordered: {len(stats["reordered"])}')
    for h in stats['reordered']:
        print(f'  FIXED {h}')
    print(f'already legal:    {stats["unchanged"]}')
    print(f'skipped:          {len(stats["skipped"])}')
    for s in stats['skipped']:
        print(f'  SKIP {s}')

    if stats['reordered'] and not dry:
        new_literal = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        new_content = content[:start] + new_literal + content[end + 1:]
        with open(INDEX, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'wrote index.html ({len(content)} -> {len(new_content)} bytes)')
    elif dry:
        print('(dry run — nothing written)')
    else:
        print('nothing to change — index.html untouched')


if __name__ == '__main__':
    main()
