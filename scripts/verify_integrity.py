import json, re, os
from pathlib import Path

index_path = Path(__file__).parent.parent / 'index.html'
if not index_path.exists():
    index_path = Path('index.html')

with open(index_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Check heroes
m_heroes = re.search(r'const heroes\s*=\s*(\[.*?\]);\s*const alts', content, re.DOTALL)
heroes = json.loads(m_heroes.group(1))
print(f"Total heroes: {len(heroes)} (expected 42)")
assert len(heroes) == 42, f"Expected 42 heroes, got {len(heroes)}"

# 2. Check skillups
m_skillups = re.search(r'const skillups\s*=\s*(\{.*?\});', content, re.DOTALL)
skillups = json.loads(m_skillups.group(1))
print(f"Total heroes with skillups: {len(skillups)}")
assert len(skillups) == 42, f"Expected 42 heroes with skillups, got {len(skillups)}"

for name, s in skillups.items():
    assert len(s['steps']) == 16, f"Hero {name} skillup track has {len(s['steps'])} steps, expected 16"

# 3. Check extras (combos, situational)
m_extras = re.search(r'const extras\s*=\s*(\{.*?\});', content, re.DOTALL)
extras = json.loads(m_extras.group(1))
print(f"Total heroes with extras: {len(extras)}")
assert len(extras) == 42, f"Expected 42 heroes with extras, got {len(extras)}"

# 4. Check crosshairs count
crosshairs_matches = re.findall(r'class="crosshair-card"', content)
print(f"Total crosshair cards: {len(crosshairs_matches)} (expected 24)")
assert len(crosshairs_matches) == 24, f"Expected 24 crosshairs, got {len(crosshairs_matches)}"

# 5. Check in-game build binary strings
m_bin = re.search(r'const gameBuildsBin\s*=\s*(\{.*?\});', content, re.DOTALL)
bins = json.loads(m_bin.group(1))
print(f"Total heroes with gameBuildsBin: {len(bins)}")
assert len(bins) == 42, f"Expected 42 heroes in gameBuildsBin, got {len(bins)}"

non_kluv = []
decomp_errors = []
total_builds = 0

import base64
try:
    import zstandard as zstd
    dctx = zstd.ZstdDecompressor()
except ImportError:
    dctx = None

for h, bdict in bins.items():
    for bname, bstr in bdict.items():
        total_builds += 1
        if not bstr.startswith('KLUv'):
            non_kluv.append(f"{h} ({bname})")
        if dctx:
            try:
                raw = base64.b64decode(bstr)
                decomp = dctx.decompress(raw)
                if len(decomp) < 20:
                    decomp_errors.append(f"{h} ({bname}) payload too small")
            except Exception as e:
                decomp_errors.append(f"{h} ({bname}): {e}")

print(f"Total builds verified: {total_builds}")
print(f"Non-KLUv builds: {non_kluv}")
assert len(non_kluv) == 0, f"Found non-KLUv builds: {non_kluv}"
assert len(decomp_errors) == 0, f"Decompression errors: {decomp_errors}"

print("INTEGRITY CHECK 100% PASSED!")

