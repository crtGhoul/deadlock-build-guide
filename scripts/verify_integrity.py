"""Integrity check for the Deadlock Build Guide index.html.

Verifies hero/data counts and that every in-game build payload is a real
Zstandard frame that decompresses. Bump EXPECTED_HEROES when a new hero ships.
"""
import base64
import json
import re
import sys
from pathlib import Path

EXPECTED_HEROES = 44
EXPECTED_BUILDS = 71  # 44 heroes, 27 of them with an alt tab (70 + Harrow Standard)
EXPECTED_CROSSHAIRS = 24
EXPECTED_ARCH_PAYLOADS = 220  # in assets/data/archetypes.js: 44 heroes x 5 build paths (Weapon/Spirit/Vitality/Nuke/CN)

index_path = Path(__file__).parent.parent / 'index.html'
content = index_path.read_text(encoding='utf-8')


def extract_literal(decl):
    """Return the parsed JSON literal following `const <decl> =` (depth-aware)."""
    m = re.search(r'(?:const|let|var)\s+' + re.escape(decl) + r'\s*=', content)
    assert m, f'declaration not found: {decl}'
    i = m.end()
    while content[i] in ' \t\n':
        i += 1
    assert content[i] in '[{', f'unexpected literal start for {decl}'
    open_c, close_c = content[i], (']' if content[i] == '[' else '}')
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
            elif ch == open_c:
                depth += 1
            elif ch == close_c:
                depth -= 1
                if depth == 0:
                    return json.loads(content[i:j + 1])
        j += 1
    raise AssertionError(f'unbalanced literal for {decl}')


failures = []


def check(cond, msg):
    print(('PASS' if cond else 'FAIL') + f': {msg}')
    if not cond:
        failures.append(msg)


heroes = extract_literal('heroes')
check(len(heroes) == EXPECTED_HEROES, f'{len(heroes)} heroes (expected {EXPECTED_HEROES})')
check('Violet' in [h['hero'] for h in heroes], 'Violet present in heroes')
violet = next(h for h in heroes if h['hero'] == 'Violet')
check(len(violet['build']) == 16, f"Violet build has {len(violet['build'])} items (expected 16)")

skillups = extract_literal('skillups')
check(len(skillups) == EXPECTED_HEROES, f'{len(skillups)} skillup tracks (expected {EXPECTED_HEROES})')
for name, s in skillups.items():
    if len(s['steps']) != 16:
        check(False, f'{name} skillup track has {len(s["steps"])} steps, expected 16')
        break
else:
    check(True, 'all skillup tracks have 16 steps')

# --- Standard skillup tracks: AP legality (permanent guard) ---
# Every Standard track must read in true chronological order under the
# game's AP economy (scripts/ap-model.json): the ultimate is the 4th
# unlock and every spend is fundable in sequence (greedy simulation:
# advance level-ups only when a spend cannot be afforded — saving is
# legal). Mirrors the archetype validator's AP checks.
_ap_path = Path(__file__).parent / 'ap-model.json'
_ap = json.loads(_ap_path.read_text(encoding='utf-8')) if _ap_path.exists() else None
check(_ap is not None, 'scripts/ap-model.json present for Standard track AP checks')
if _ap:
    _levels = [(l['souls'], l['reward']) for l in _ap['levels']]
    _ults = _ap['ultimates']

    def _fundable(names):
        unlocked, tokens, pool, ei = [], 0, 0, 0

        def grant():
            nonlocal tokens, pool, ei
            _s, r = _levels[ei]
            ei += 1
            if r == 'unlock':
                tokens += 1
            else:
                pool += 1

        for nm in names:
            if nm not in unlocked:
                while tokens == 0 and ei < len(_levels):
                    grant()
                if tokens == 0:
                    return False
                tokens -= 1
                unlocked.append(nm)
            else:
                while pool == 0 and ei < len(_levels):
                    grant()
                if pool == 0:
                    return False
                pool -= 1
        return True

    _std_bad = []
    for name, s in skillups.items():
        _names = [st['ability'] for st in s['steps']]
        _firsts = []
        for _n in _names:
            if _n not in _firsts:
                _firsts.append(_n)
        _ult = _ults.get(name)
        if len(_firsts) != 4 or _ult not in _firsts or _firsts.index(_ult) != 3:
            _std_bad.append(f'{name}: ultimate is not the 4th unlock')
        elif not _fundable(_names):
            _std_bad.append(f'{name}: track not fundable in order')
    check(not _std_bad,
          f'Standard skillup tracks AP-legal: {EXPECTED_HEROES - len(_std_bad)}/{EXPECTED_HEROES} '
          f'(ult is 4th unlock + fundable under the AP model)'
          + (f'; illegal: {_std_bad}' if _std_bad else ''))

extras = extract_literal('extras')
check(len(extras) == EXPECTED_HEROES, f'{len(extras)} extras entries (expected {EXPECTED_HEROES})')
check('Violet' in extras, 'Violet present in extras')

crosshairs = re.findall(r'class="crosshair-card"', content)
check(len(crosshairs) == EXPECTED_CROSSHAIRS,
      f'{len(crosshairs)} crosshair cards (expected {EXPECTED_CROSSHAIRS})')

bins = extract_literal('gameBuildsBin')
check(len(bins) == EXPECTED_HEROES, f'{len(bins)} heroes in gameBuildsBin (expected {EXPECTED_HEROES})')

try:
    import zstandard as zstd
    dctx = zstd.ZstdDecompressor()
except ImportError:
    dctx = None
    check(False, 'zstandard library installed (required for payload decompression checks)')

non_kluv, decomp_errors, total_builds = [], [], 0
for h, bdict in bins.items():
    for bname, bstr in bdict.items():
        total_builds += 1
        if not bstr.startswith('KLUv'):
            non_kluv.append(f'{h} ({bname})')
        if dctx:
            try:
                raw = base64.b64decode(bstr)
                assert raw[:4] == b'\x28\xb5\x2f\xfd', 'not a Zstd frame'
                decomp = dctx.decompress(raw)
                assert len(decomp) >= 20, 'payload too small'
            except Exception as e:
                decomp_errors.append(f'{h} ({bname}): {e}')

check(total_builds == EXPECTED_BUILDS, f'{total_builds} builds total (expected {EXPECTED_BUILDS})')
check(not non_kluv, f'non-KLUv builds: {non_kluv}' if non_kluv else 'all payloads start with KLUv')
if dctx:
    check(not decomp_errors, f'decompression errors: {decomp_errors}' if decomp_errors else 'all payloads are valid Zstd frames')
check('Violet' in bins and 'Standard' in bins['Violet'], 'Violet Standard payload present')

# --- archetype payloads (assets/data/archetypes.js) ---
arch_path = Path(__file__).parent.parent / 'assets' / 'data' / 'archetypes.js'
arch_text = arch_path.read_text(encoding='utf-8')
pm = re.search(r'window\.ARCHETYPE_PAYLOADS = (\{.*?\});\n', arch_text, re.S)
check(pm is not None, 'ARCHETYPE_PAYLOADS present in archetypes.js')
arch_payloads = json.loads(pm.group(1)) if pm else {}
arch_total, arch_bad = 0, []
for h, bdict in arch_payloads.items():
    for bname, bstr in bdict.items():
        arch_total += 1
        if not bstr.startswith('KLUv'):
            arch_bad.append(f'{h} ({bname}) not KLUv')
        elif dctx:
            try:
                raw = base64.b64decode(bstr)
                assert raw[:4] == b'\x28\xb5\x2f\xfd', 'not a Zstd frame'
                assert len(dctx.decompress(raw)) >= 20, 'payload too small'
            except Exception as e:
                arch_bad.append(f'{h} ({bname}): {e}')
check(arch_total == EXPECTED_ARCH_PAYLOADS,
      f'{arch_total} archetype payloads (expected {EXPECTED_ARCH_PAYLOADS})')
check(not arch_bad, f'archetype payload errors: {arch_bad}' if arch_bad else 'all archetype payloads are valid Zstd frames')
check(all('Nuke' in (arch_payloads.get(h) or {}) for h in arch_payloads) and len(arch_payloads) == EXPECTED_HEROES,
      'every hero has a Nuke payload')
check(all('CN' in (arch_payloads.get(h) or {}) for h in arch_payloads) and len(arch_payloads) == EXPECTED_HEROES,
      'every hero has a CN payload')
# CN data block: every hero's cn entry carries a non-empty note + source.
_cn_bad = []
for f in sorted((Path(__file__).parent.parent / 'data' / 'archetypes').glob('*.json')):
    d = json.loads(Path(f).read_text(encoding='utf-8'))
    cn = (d.get('archetypes') or {}).get('cn') or {}
    if not cn.get('cn_note') or not cn.get('cn_source'):
        _cn_bad.append(d.get('hero'))
check(not _cn_bad,
      f'CN note + source present on all 44 heroes'
      + (f'; missing: {_cn_bad}' if _cn_bad else ''))

fb = extract_literal('finalBuilds')
check('Violet' in fb, 'Violet present in finalBuilds')
check(len(fb['Violet']['standard']['items']) > 0, 'Violet final build non-empty')

check(content.count('44 heroes') >= 1, 'hero count text updated to 44')
check('Violet released' in content, 'Violet changelog entry present')

# --- item tooltip coverage (Prompt 32) ---
# Every item referenced by ANY build — Standard (heroes/extras/finalBuilds
# literals), all four archetype paths, counter swaps, sell/upgrade chains,
# imbue stacks, situational picks — must exist in scripts/itemtooltips.json,
# or its plaque degrades to the name+cost fallback.
import glob as _glob
tips_path = Path(__file__).parent / 'itemtooltips.json'
tips = json.loads(tips_path.read_text(encoding='utf-8')) if tips_path.exists() else {}
referenced = set()


def walk_refs(node):
    if isinstance(node, dict):
        if 'out' in node and 'in' in node:
            referenced.add(node['out']); referenced.add(node['in'])
        if 'from' in node and 'to' in node:
            referenced.add(node['from']); referenced.add(node['to'])
        if isinstance(node.get('buy'), str):
            referenced.add(node['buy'])
        for key in ('imbue_stack', 'sold'):
            v = node.get(key)
            if isinstance(v, list):
                referenced.update(x for x in v if isinstance(x, str))
        v = node.get('items')
        if isinstance(v, list):
            for x in v:
                if isinstance(x, str):
                    referenced.add(x)
                elif isinstance(x, dict) and isinstance(x.get('name'), str):
                    referenced.add(x['name'])
        for v in node.values():
            walk_refs(v)
    elif isinstance(node, list):
        for x in node:
            walk_refs(x)


for f in sorted(_glob.glob(str(Path(__file__).parent.parent / 'data' / 'archetypes' / '*.json'))):
    walk_refs(json.loads(Path(f).read_text(encoding='utf-8')))
walk_refs(heroes)
walk_refs(extras)
walk_refs(fb)
referenced.discard(None)
missing_tips = sorted(n for n in referenced if n not in tips)
check(not missing_tips,
      f'item tooltip coverage: {len(referenced) - len(missing_tips)}/{len(referenced)} build-referenced items '
      f'in the {len(tips)}-item tooltip dataset' + (f'; missing: {missing_tips}' if missing_tips else ''))
check('window.ITEM_TOOLTIPS' in arch_text, 'ITEM_TOOLTIPS exported in archetypes.js')
check('data-item-tip' in content, 'data-item-tip hooks present in index.html renderers')

# --- Prompts 31/33: AP simulator + build creator ---
check('window.AP_MODEL' in arch_text, 'AP_MODEL (Prompt 31) exported in archetypes.js')
check('data-sim-root' in content and 'simLoadRecommended' in content,
      'ability progression simulator present in index.html')
check('crParseShare' in content and 'buildCreator' in content,
      'build creator + sanitized share-link import present in index.html')
check('archCnPanelHtml' in content and 'arch-tab-cn' in content and "'cn'" in content,
      'CN tab + panel present in index.html')

# --- situational counter-buys (gen-counterbuys.py) ---
# Every archetype build carries 5-7 {when, buy, sell, note} rules; every buy
# must have tooltip data (the Counter-buys panel renders plaques for them).
sit_builds, sit_rules, sit_missing = 0, 0, []
for f in sorted(_glob.glob(str(Path(__file__).parent.parent / 'data' / 'archetypes' / '*.json'))):
    d = json.loads(Path(f).read_text(encoding='utf-8'))
    for akey, arch in d.get('archetypes', {}).items():
        sit = arch.get('situational')
        if isinstance(sit, list) and sit:
            sit_builds += 1
            sit_rules += len(sit)
            for r in sit:
                if isinstance(r, dict) and r.get('buy') not in tips:
                    sit_missing.append(f"{d.get('hero')}/{akey}: {r.get('buy')}")
check(sit_builds == 220, f'situational counter-buys present on {sit_builds}/220 archetype builds ({sit_rules} rules)')
check(not sit_missing,
      f'situational tooltip coverage: all counter-buy items in the tooltip dataset'
      + (f'; missing: {sit_missing}' if sit_missing else ''))
check('archSituationalHtml' in content, 'Counter-buys panel renderer present in index.html')
check('archShoppingText' in content, 'shopping-list text export present in index.html')

if failures:
    print(f'\nINTEGRITY CHECK FAILED ({len(failures)} failures)')
    sys.exit(1)
print('\nINTEGRITY CHECK 100% PASSED!')
