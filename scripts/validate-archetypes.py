#!/usr/bin/env python3
"""Validate 3-archetype hero build JSONs against the live Deadlock shop.

Usage: python3 scripts/validate-archetypes.py data/archetypes/*.json
Exit 0 = all pass. Prints ERRORS (must fix) and WARNINGS (should fix).
"""
import json, sys, glob, os

BASE = os.path.dirname(os.path.abspath(__file__))
ITEMDB = json.load(open(os.path.join(BASE, 'itemdb.json')))
COMPONENTS = json.load(open(os.path.join(BASE, 'components.json')))
ABILITY_NAMES = json.load(open(os.path.join(BASE, 'ability-names.json')))
AP_MODEL = json.load(open(os.path.join(BASE, 'ap-model.json')))
AP_LEVELS = [(l['souls'], l['reward']) for l in AP_MODEL['levels']]  # (souls, 'unlock'|'ap')

ARCHES = {'weapon': 'Weapon', 'spirit': 'Spirit', 'vitality': 'Vitality'}
JUNK = ('upgrade_', ' - Disabled', ' v2')

errors, warnings = [], []

def err(hero, arch, msg): errors.append(f"[ERROR] {hero}/{arch}: {msg}")
def warn(hero, arch, msg): warnings.append(f"[WARN]  {hero}/{arch}: {msg}")

def check_ap_model(hero, arch, so):
    """Check one build's skill_order against the AP economy (scripts/ap-model.json).

    Reading (documented in ap-model.json): the 16-step track is a chronological
    spend sequence — an ability's first step is its unlock, later steps are
    +1 AP into it. Saving AP/unlocks is legal, so funding is tested with the
    greedy earliest simulation (advance level-ups only when a spend cannot be
    afforded). Hard errors: names outside the hero's ability set, >8 AP in one
    ability (1+2+5 is the max), an unfundable sequence. Warnings: game-rule
    deviations in the authored order — the ultimate taken before the 4th
    unlock, unlock[] not ending with the ultimate, track/unlock[] order drift.
    """
    abilities = ABILITY_NAMES.get(hero)
    if abilities is None:
        err(hero, arch, "no ability-names.json entry for hero — cannot AP-check")
        return
    ult = AP_MODEL['ultimates'].get(hero)
    track = so.get('track', [])
    unlock = so.get('unlock', [])
    for nm in list(track) + list(unlock):
        if nm not in abilities:
            err(hero, arch, f"skill name '{nm}' is not one of {hero}'s 4 abilities")
    counts = {}
    for nm in track:
        counts[nm] = counts.get(nm, 0) + 1
    for nm, c in counts.items():
        if c - 1 > 8:
            err(hero, arch, f"'{nm}' gets {c - 1} AP in the track — max is 8 (tiers cost 1+2+5)")
    # greedy funding simulation (ult rule deliberately NOT enforced here —
    # it is reported separately below so the two are never double-counted)
    unlocked, tokens, pool, ei = [], 0, 0, 0
    def grant():
        nonlocal tokens, pool, ei
        _souls, reward = AP_LEVELS[ei]; ei += 1
        if reward == 'unlock': tokens += 1
        else: pool += 1
    for nm in track:
        if nm not in abilities:
            continue
        if nm not in unlocked:
            while tokens == 0 and ei < len(AP_LEVELS): grant()
            if tokens == 0:
                err(hero, arch, "track cannot be funded: ran out of level-up unlocks"); return
            tokens -= 1; unlocked.append(nm)
        else:
            while pool == 0 and ei < len(AP_LEVELS): grant()
            if pool == 0:
                err(hero, arch, "track cannot be funded: ran out of level-up AP"); return
            pool -= 1
    # --- game-rule order warnings (reported, not silently fixed) ---
    firsts = []
    for nm in track:
        if nm not in firsts: firsts.append(nm)
    if ult and ult in firsts and firsts.index(ult) < 3:
        step = track.index(ult) + 1
        warn(hero, arch, f"AP model: ultimate '{ult}' is first taken at track step {step} "
             f"as unlock #{firsts.index(ult) + 1} — in game the ultimate needs the 4th unlock "
             f"(3,800 gathered souls); read the track's early steps as priority, not literal order")
    if ult and unlock and unlock[-1] != ult:
        warn(hero, arch, f"AP model: unlock[] ends with '{unlock[-1]}', not the ultimate '{ult}' "
             f"(the ultimate can only be unlocked 4th, at 3,800 souls)")
    if firsts != list(unlock):
        warn(hero, arch, "AP model: the track's unlock order differs from skill_order.unlock[]")

def check_item(hero, arch, name, ctx):
    if not name or not isinstance(name, str):
        err(hero, arch, f"{ctx}: bad item name {name!r}"); return None
    it = ITEMDB.get(name)
    if not it:
        err(hero, arch, f"{ctx}: '{name}' not in live shop item DB"); return None
    if name.startswith(JUNK) or ' - Disabled' in name or name.endswith(' v2'):
        err(hero, arch, f"{ctx}: '{name}' looks like an unreleased/disabled item"); return None
    return it

def validate_file(path):
    hero = os.path.basename(path).replace('.json', '')
    try:
        d = json.load(open(path))
    except Exception as e:
        err(hero, '-', f"invalid JSON: {e}"); return
    if d.get('hero') != hero:
        warn(hero, '-', f"hero field {d.get('hero')!r} != filename")
    meta = d.get('meta_archetype')
    if meta not in ARCHES:
        err(hero, '-', f"meta_archetype must be one of {list(ARCHES)}"); return
    archs = d.get('archetypes', {})
    if set(archs.keys()) != set(ARCHES) | {'nuke', 'cn'}:
        err(hero, '-', f"archetypes must be {list(ARCHES)} + 'nuke' + 'cn', got {list(archs.keys())}"); return
    for akey, a in archs.items():
        if akey == 'nuke':
            # NUKE: 4th signature-ability build. Never the META pick; its
            # primary category is declared per hero (Spirit, or Weapon for
            # Rat King whose grenade scales with weapon damage).
            primary = a.get('primary_category')
            if primary not in ('Spirit', 'Weapon'):
                err(hero, akey, f"nuke primary_category must be Spirit/Weapon, got {primary!r}")
            if a.get('is_meta'):
                err(hero, akey, "nuke must not be is_meta (META stays one of the 3 archetypes)")
        elif akey == 'cn':
            # CN: 5th Chinese-community tempo build. Never the META pick;
            # its primary category is declared per hero (Spirit, Weapon,
            # or Vitality) and it must carry its CN note + source line.
            primary = a.get('primary_category')
            if primary not in ('Spirit', 'Weapon', 'Vitality'):
                err(hero, akey, f"cn primary_category must be Spirit/Weapon/Vitality, got {primary!r}")
            if a.get('is_meta'):
                err(hero, akey, "cn must not be is_meta (META stays one of the 3 archetypes)")
            for f in ('cn_note', 'cn_source'):
                if not a.get(f): err(hero, akey, f"cn missing '{f}'")
        else:
            primary = ARCHES[akey]
            if bool(a.get('is_meta')) != (akey == meta):
                err(hero, akey, f"is_meta={a.get('is_meta')} but meta_archetype={meta}")
        for f in ('label', 'tagline', 'kit_synergy'):
            if not a.get(f): err(hero, akey, f"missing '{f}'")
        # --- skill order ---
        so = a.get('skill_order', {})
        if len(so.get('unlock', [])) != 4:
            err(hero, akey, f"skill_order.unlock must have 4 abilities")
        mp = so.get('max_priority', {})
        if not all(k in mp for k in ('1', '2', '5')):
            err(hero, akey, "skill_order.max_priority needs keys '1','2','5'")
        if len(so.get('track', [])) != 16:
            err(hero, akey, f"skill_order.track must have 16 steps, got {len(so.get('track', []))}")
        check_ap_model(d.get('name') or hero, akey, so)
        # --- phases ---
        ph = a.get('phases', {})
        p1 = ph.get('p1', {}).get('items', [])
        if not (4 <= len(p1) <= 6):
            err(hero, akey, f"p1 must have 4-6 items, got {len(p1)}")
        spike_sum = 0
        for it in p1:
            rec = check_item(hero, akey, it.get('name'), 'p1')
            if not it.get('why'): err(hero, akey, f"p1 '{it.get('name')}' missing 'why'")
            if rec and rec['cat'] == primary: spike_sum += rec['cost']
        if spike_sum != 4800:
            err(hero, akey, f"p1 primary-category ({primary}) spend = {spike_sum}, must hit the 4800 spike exactly")
        p2 = ph.get('p2', {}).get('items', [])
        if not (3 <= len(p2) <= 8):
            err(hero, akey, f"p2 should have 3-8 items, got {len(p2)}")
        for it in p2:
            check_item(hero, akey, it.get('name'), 'p2')
            if not it.get('why'): err(hero, akey, f"p2 '{it.get('name')}' missing 'why'")
        p3 = ph.get('p3', {})
        lo = p3.get('final_loadout', [])
        if len(lo) != 12:
            err(hero, akey, f"p3.final_loadout must be exactly 12 items, got {len(lo)}")
        if len(set(lo)) != len(lo):
            err(hero, akey, "p3.final_loadout has duplicates")
        actives = 0
        early_names = {it.get('name') for it in p1 + p2}
        for name in lo:
            rec = check_item(hero, akey, name, 'final_loadout')
            if rec and rec['active']: actives += 1
            for comp in COMPONENTS.get(name, []):
                if comp not in early_names and comp not in lo:
                    warn(hero, akey, f"final '{name}' upgrades from '{comp}' which is never bought early (wasted souls)")
        if actives > 4:
            err(hero, akey, f"final_loadout has {actives} actives, cap is 4 (Z/X/C/V)")
        for s in p3.get('sell_upgrade', []):
            if not (s.get('from') and s.get('to')):
                err(hero, akey, "sell_upgrade entries need 'from' and 'to'")
            check_item(hero, akey, s.get('to'), 'sell_upgrade.to')
        if not p3.get('win_condition'):
            err(hero, akey, "p3 missing 'win_condition'")
        # --- nuke signature block ---
        if akey == 'nuke':
            ba = a.get('best_ability', {})
            for f in ('name', 'why', 'scaling'):
                if not ba.get(f): err(hero, akey, f"best_ability missing '{f}'")
            alts = ba.get('alternates', [])
            if len(alts) > 2:
                err(hero, akey, f"best_ability.alternates max 2, got {len(alts)}")
            for alt in alts:
                if not (alt.get('name') and alt.get('when')):
                    err(hero, akey, f"alternates entries need name+when: {alt}")
            stack = a.get('imbue_stack', [])
            if not stack:
                err(hero, akey, "imbue_stack is empty")
            for nm in stack:
                check_item(hero, akey, nm, 'imbue_stack')
        # --- counters ---
        co = a.get('counters', {})
        if akey != 'nuke':  # nuke ships the lighter counters module (swaps only)
            for k in ('vs_danny', 'vs_baba', 'vs_violet'):
                if not co.get(k): err(hero, akey, f"counters missing '{k}'")
        swaps = co.get('swaps', [])
        if len(swaps) < 3:
            err(hero, akey, f"counters.swaps needs >=3 entries, got {len(swaps)}")
        for s in swaps:
            if not (s.get('vs') and s.get('out') and s.get('in')):
                err(hero, akey, f"counters.swaps entry needs vs/out/in: {s}")
                continue
            check_item(hero, akey, s['in'], 'counter swap in')
            # 'out' may be a category placeholder like "a 1600 sustain item"; validate only if it's a real item
            if s['out'] in ITEMDB: check_item(hero, akey, s['out'], 'counter swap out')
        # --- situational counter-buys ("in case this, buy that") ---
        sit = a.get('situational')
        if sit is None:
            err(hero, akey, "missing 'situational' counter-buy array (run scripts/gen-counterbuys.py)")
        else:
            if not (5 <= len(sit) <= 7):
                err(hero, akey, f"situational must have 5-7 rules, got {len(sit)}")
            final_set = set(lo)
            seen_buys, seen_sells = set(), set()
            for r in sit:
                if not (r.get('when') and r.get('note')):
                    err(hero, akey, f"situational rule needs non-empty when/note: {r}")
                    continue
                buy = r.get('buy')
                buy_rec = check_item(hero, akey, buy, 'situational buy')
                if buy in seen_buys:
                    err(hero, akey, f"situational buys '{buy}' twice in one build")
                seen_buys.add(buy)
                sell = r.get('sell')
                if buy in final_set:
                    # already-owned variant: no sell, and the note must say so
                    if sell is not None:
                        err(hero, akey, f"situational '{buy}' is in the final 12 but has sell={sell!r} (owned variant must sell nothing)")
                    if 'already in this build' not in r['note'].lower():
                        err(hero, akey, f"situational owned variant '{buy}' note must say it is already in this build")
                else:
                    if sell not in final_set:
                        err(hero, akey, f"situational sell {sell!r} for buy '{buy}' is not in the final 12")
                        continue
                    if sell in seen_sells:
                        err(hero, akey, f"situational sells '{sell}' in more than one rule")
                    seen_sells.add(sell)
                    if buy_rec:
                        sell_rec = ITEMDB.get(sell) or {}
                        after = actives - (1 if sell_rec.get('active') else 0) + (1 if buy_rec['active'] else 0)
                        if after > 4:
                            err(hero, akey, f"situational swap {sell} -> {buy} leaves {after} actives (cap 4)")

def main():
    files = []
    for pat in sys.argv[1:]:
        files.extend(glob.glob(pat))
    if not files:
        print("usage: validate-archetypes.py data/archetypes/*.json"); sys.exit(2)
    for f in sorted(files): validate_file(f)
    for w in warnings: print(w)
    for e in errors: print(e)
    print(f"\n{len(files)} heroes | {len(errors)} errors | {len(warnings)} warnings")
    sys.exit(1 if errors else 0)

if __name__ == '__main__':
    main()
