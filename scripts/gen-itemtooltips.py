#!/usr/bin/env python3
"""Generate scripts/itemtooltips.json from the live Deadlock assets API.

Dataset = itemdb.json's buyable set (cost in {800,1600,3200,6400}, names not
starting with 'upgrade_'). Every field comes from the item's API record at
https://api.deadlock-api.com/v1/assets/items — nothing is hand-authored.

Per item (keyed by item name, itemdb.json style):
  cost   souls cost (cross-checked against itemdb)
  tier   1-4, derived from cost (800/1600/3200/6400)
  cat    Weapon | Vitality | Spirit (itemdb; cross-checked vs API slot)
  active bool, from the resolved API record's is_active_item
  cd     active cooldown in seconds (AbilityCooldown) — actives only, else omitted
  imbue  bool, from the API record's imbue marker
  fx     list of effect lines: the cleaned description text plus any
         section loc_strings it does not already cover (multi-effect items
         like Silencer carry one line per passive), omitted when absent
  stats  ordered bonus lines built from the API's own tooltip_sections
         display manifest (elevated -> important -> plain properties per
         attribute, sections in API order, deduped, zero/label-less/internal
         properties skipped; AbilityCooldown never appears here — actives
         surface it via `cd`)

Duplicate API names are disambiguated by preferring type='upgrade', then the
record whose cost matches itemdb, then shopable=True (e.g. Silencer has a
legacy active record and the live passive 'upgrade_proc_silence' record).

Usage: python3 scripts/gen-itemtooltips.py   (run from repo root)
"""
import html as htmlmod
import json
import os
import re
import sys
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = 'https://api.deadlock-api.com/v1/assets/items'
COSTS = {800: 1, 1600: 2, 3200: 3, 6400: 4}
OUT = os.path.join(BASE, 'scripts', 'itemtooltips.json')

warnings = []


def fmt_num(x):
    """Trim a numeric value the way the shop prints it: 25.0 -> '25'."""
    f = float(x)
    if f == int(f):
        return str(int(f))
    return ('%f' % f).rstrip('0').rstrip('.')


def fmt_value(prop):
    """Format one property as '<value>' (label appended by caller)."""
    raw = prop.get('value')
    prefix = prop.get('prefix') or ''
    postfix = prop.get('postfix') or ''
    if raw is None:
        return None
    s = str(raw).strip()
    if s == '':
        return None
    try:
        num = float(s)
        numeric = True
    except ValueError:
        num, numeric = None, False
    if numeric:
        if num == 0:
            return None  # zero bonuses are not displayed by the shop
        body = fmt_num(abs(num)) if prefix == '{s:sign}' else fmt_num(num)
        if prefix == '{s:sign}':
            sign = '+' if num >= 0 else '-'
            out = sign + body
        elif prefix:
            out = prefix + body if not body.startswith('-') else body
        else:
            out = body
    else:
        # value already carries its unit/sign (e.g. '15m', '-1.5m', '1.75m')
        out = s
        if prefix == '{s:sign}' and not out.startswith(('+', '-')):
            out = '+' + out
        elif prefix and not out.startswith(prefix) and not out.startswith('-'):
            out = prefix + out
    # append the unit unless the value string already ends with it
    unit = postfix.strip()
    if unit and not out.rstrip().endswith(unit):
        out += postfix
    return out


def clean_text(txt):
    if not txt or not txt.strip():
        return None
    txt = re.sub(r'<[^>]+>', '', txt)          # spans + inline SVG icons
    txt = htmlmod.unescape(txt)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt or None


def effect_lines(rec):
    """Effect text in the game's own order: section loc_strings in
    tooltip_sections order (deduped); the description usually duplicates
    one of them — when it doesn't, it leads the list."""
    lines = []
    for section in rec.get('tooltip_sections') or []:
        for attr in section.get('section_attributes') or []:
            loc = clean_text(attr.get('loc_string'))
            if not loc:
                continue
            if any(loc in prev or prev in loc for prev in lines):
                continue
            lines.append(loc)
    desc = clean_text((rec.get('description') or {}).get('desc'))
    if desc and not any(desc in prev or prev in desc for prev in lines):
        lines.insert(0, desc)
    return lines


def stat_lines(rec):
    props = rec.get('properties') or {}
    seen, lines = set(), []
    for section in rec.get('tooltip_sections') or []:
        for attr in section.get('section_attributes') or []:
            ordered = ((attr.get('elevated_properties') or [])
                       + (attr.get('important_properties') or [])
                       + (attr.get('properties') or []))
            for key in ordered:
                if key in seen or key == 'AbilityCooldown':
                    continue
                seen.add(key)
                prop = props.get(key)
                if not prop or not prop.get('label'):
                    continue  # StatusEffect* refs + internal thresholds
                val = fmt_value(prop)
                if val is None:
                    continue
                lines.append(f"{val} {prop['label']}")
    return lines


def pick_record(records, name, dbrec):
    cands = [r for r in records if r.get('name') == name and r.get('type') == 'upgrade']
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    for c in cands:
        if c.get('cost') == dbrec['cost'] and c.get('shopable'):
            return c
    for c in cands:
        if c.get('shopable'):
            return c
    for c in cands:
        if c.get('cost') == dbrec['cost']:
            return c
    return cands[0]


def main():
    itemdb = json.load(open(os.path.join(BASE, 'scripts', 'itemdb.json')))
    buyable = {n: v for n, v in itemdb.items()
               if not n.startswith('upgrade_') and v['cost'] in COSTS}
    req = urllib.request.Request(API_URL, headers={'User-Agent': 'dbg-tooltip-gen'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        records = json.load(resp)
    print(f'API records: {len(records)} | itemdb buyable set: {len(buyable)}')

    out = {}
    for name in sorted(buyable):
        db = buyable[name]
        rec = pick_record(records, name, db)
        if rec is None:
            warnings.append(f'{name}: NO API record (type=upgrade)')
            continue
        if rec.get('cost') != db['cost']:
            warnings.append(f"{name}: cost API {rec.get('cost')} != itemdb {db['cost']}")
        slot = (rec.get('item_slot_type') or '').capitalize()
        if slot and slot != db['cat']:
            warnings.append(f"{name}: category API {slot} != itemdb {db['cat']}")
        entry = {
            'cost': db['cost'],
            'tier': COSTS[db['cost']],
            'cat': db['cat'],
            'active': bool(rec.get('is_active_item')),
        }
        if entry['active'] != bool(db['active']):
            warnings.append(
                f"{name}: is_active API {entry['active']} != itemdb {bool(db['active'])}"
                f" (record {rec.get('class_name')})")
        if entry['active']:
            cd_raw = (rec.get('properties') or {}).get('AbilityCooldown', {}).get('value')
            try:
                cd = float(cd_raw)
            except (TypeError, ValueError):
                cd = 0
            if cd > 0:
                entry['cd'] = int(cd) if cd == int(cd) else cd
            elif cd_raw is None:
                warnings.append(f'{name}: active but AbilityCooldown property missing')
            # cd == 0 in the API is explicit: toggle / one-shot actives
            # (Blood Tribute, Golden Goose Egg) genuinely have no cooldown.
        imbue = bool(rec.get('imbue'))
        if imbue != bool(db['imbue']):
            warnings.append(f"{name}: imbue API {imbue} != itemdb {bool(db['imbue'])}")
        entry['imbue'] = imbue
        fx = effect_lines(rec)
        if fx:
            entry['fx'] = fx
        entry['stats'] = stat_lines(rec)
        out[name] = entry

    with open(OUT, 'w') as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write('\n')
    print(f'wrote {OUT}: {len(out)} items')
    empty_stats = [n for n, e in out.items() if not e['stats'] and 'fx' not in e]
    print(f'items with neither stats nor fx: {len(empty_stats)} {empty_stats[:10]}')
    print(f'actives: {sum(1 for e in out.values() if e["active"])}'
          f' | with cd: {sum(1 for e in out.values() if "cd" in e)}'
          f' | imbue: {sum(1 for e in out.values() if e["imbue"])}')
    for w in warnings:
        print('WARN:', w)
    if len(out) != len(buyable):
        print(f'COUNT MISMATCH: generated {len(out)} != buyable {len(buyable)}')
        sys.exit(1)
    print('GEN OK')


if __name__ == '__main__':
    main()
