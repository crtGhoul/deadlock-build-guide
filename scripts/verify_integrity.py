"""Integrity check for the Deadlock Build Guide index.html.

Verifies hero/data counts and that every in-game build payload is a real
Zstandard frame that decompresses. Bump EXPECTED_HEROES when a new hero ships.
"""
import base64
import json
import re
import sys
from pathlib import Path

EXPECTED_HEROES = 43
EXPECTED_BUILDS = 70  # 43 heroes, 27 of them with an alt tab (69 + Violet Standard)
EXPECTED_CROSSHAIRS = 24

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

fb = extract_literal('finalBuilds')
check('Violet' in fb, 'Violet present in finalBuilds')
check(len(fb['Violet']['standard']['items']) > 0, 'Violet final build non-empty')

check(content.count('43 heroes') >= 1, 'hero count text updated to 43')
check('Violet released' in content, 'Violet changelog entry present')

if failures:
    print(f'\nINTEGRITY CHECK FAILED ({len(failures)} failures)')
    sys.exit(1)
print('\nINTEGRITY CHECK 100% PASSED!')
