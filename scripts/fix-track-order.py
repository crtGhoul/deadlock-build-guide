#!/usr/bin/env python3
"""Rewrite archetype skill tracks to true chronological order (AP model).

Cesar's decision (2026-10-23): the 176 archetype skill tracks in
data/archetypes/*.json were partly written as priority order — 68 take the
ultimate before the 4th unlock, which the game does not allow (the ultimate
needs the 4th unlock, at 3,800 gathered souls). This script reorders each
build's skill_order.track into the nearest legal chronological order and
rewrites skill_order.unlock[] to the track's actual unlock order.

Reorder semantics are EXACTLY the shipped simulator's (simLoadRecommended in
assets-src/arch-ui.js): scan the authored track from the front and apply the
first step that is currently legal; the only structural blocker is an
ultimate step that would unlock while fewer than 3 other abilities are
unlocked — that step defers to the nearest legal position. Everything else
keeps its authored relative order. Funding can never block a reorder: the
multiset of spends is unchanged (4 unlocks, <=32 AP total), and the greedy
simulation below (copied from validate-archetypes.py) is asserted per build.

HARD INVARIANTS, asserted per build before anything is written:
  - the multiset of track steps is identical before/after (only order moves);
  - per-ability AP totals (step count - 1) are identical;
  - the track stays 16 steps and every step names a real ability;
  - in the new order the ultimate is the 4th distinct ability (unlock #4);
  - the new order is fundable under the validator's greedy simulation.
If a build cannot satisfy the invariants, it is left untouched and reported.

Usage: python3 scripts/fix-track-order.py [--dry-run]
"""
import json
import os
import sys
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
AP_MODEL = json.load(open(os.path.join(BASE, 'ap-model.json')))
ABILITY_NAMES = json.load(open(os.path.join(BASE, 'ability-names.json')))
AP_LEVELS = [(l['souls'], l['reward']) for l in AP_MODEL['levels']]
ULTIMATES = AP_MODEL['ultimates']


def legal_order(track, ult):
    """Apply the simulator's deferral: repeatedly take the first pending
    step that is not a structurally blocked ultimate unlock."""
    pending = list(track)
    unlocked = []
    result = []
    while pending:
        for i, nm in enumerate(pending):
            blocked = nm not in unlocked and nm == ult and len(unlocked) < 3
            if not blocked:
                pending.pop(i)
                result.append(nm)
                if nm not in unlocked:
                    unlocked.append(nm)
                break
        else:
            return None  # no applicable step — cannot fix without changing spends
    return result


def fundable(track, abilities):
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

    for nm in track:
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


def firsts(track):
    out = []
    for nm in track:
        if nm not in out:
            out.append(nm)
    return out


def main():
    dry = '--dry-run' in sys.argv
    files = sorted(
        os.path.join(ROOT, 'data', 'archetypes', f)
        for f in os.listdir(os.path.join(ROOT, 'data', 'archetypes'))
        if f.endswith('.json'))
    stats = {'reordered': 0, 'unlock_only': 0, 'unchanged': 0, 'skipped': []}
    invariant_ok = 0
    total = 0
    for path in files:
        d = json.load(open(path))
        hero = d.get('name')
        abilities = ABILITY_NAMES.get(hero, [])
        ult = ULTIMATES.get(hero)
        file_changed = False
        for arch, build in d['archetypes'].items():
            total += 1
            so = build['skill_order']
            track, unlock = list(so['track']), list(so['unlock'])
            new_track = legal_order(track, ult)
            reason = None
            if new_track is None:
                reason = 'no legal order exists without changing spends'
            elif len(track) != 16:
                reason = f'track has {len(track)} steps, expected 16'
            elif any(nm not in abilities for nm in track):
                reason = 'track names an ability outside the hero\'s set'
            elif Counter(new_track) != Counter(track):
                reason = 'step multiset changed'
            elif any(new_track.count(nm) - 1 != track.count(nm) - 1 for nm in set(track)):
                reason = 'per-ability AP totals changed'
            elif firsts(new_track).index(ult) != 3:
                reason = 'ultimate is not the 4th unlock in the new order'
            elif not fundable(new_track, abilities):
                reason = 'new order is not fundable under the greedy simulation'
            if reason:
                stats['skipped'].append(f'{hero}/{arch}: {reason} — left untouched')
                continue
            invariant_ok += 1
            new_unlock = firsts(new_track)
            if new_track != track:
                stats['reordered'] += 1
                file_changed = True
            elif new_unlock != unlock:
                stats['unlock_only'] += 1
                file_changed = True
            else:
                stats['unchanged'] += 1
            so['track'] = new_track
            so['unlock'] = new_unlock
        if file_changed and not dry:
            with open(path, 'w') as f:
                f.write(json.dumps(d, separators=(',', ':')) + '\n')
    print(f'builds processed: {total}')
    print(f'invariants held:  {invariant_ok}/{total}')
    print(f'tracks reordered: {stats["reordered"]}')
    print(f'unlock[] only:    {stats["unlock_only"]}')
    print(f'fully unchanged:  {stats["unchanged"]}')
    print(f'skipped:          {len(stats["skipped"])}')
    for s in stats['skipped']:
        print(f'  SKIP {s}')
    if dry:
        print('(dry run — nothing written)')


if __name__ == '__main__':
    main()
