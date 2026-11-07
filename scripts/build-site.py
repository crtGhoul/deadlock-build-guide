#!/usr/bin/env python3
"""Build the 3-archetype site: payloads -> archetypes.js -> patched index.html.

Steps:
  1. Verify the proto encoder by byte-identical re-encoding every existing
     Standard payload (proves the encoder before generating 129 new ones).
  2. Generate per-archetype in-game paste payloads (Weapon/Spirit/Vitality).
  3. Emit assets/data/archetypes.js (data + itemdb + upgrades + payloads).
  4. Patch index.html: script tag, CSS, archetype UI JS, renderBuild hooks.
  5. Verify: node --check the inline script, validator, verify_integrity.py.

Usage: python3 scripts/build-site.py   (run from repo root)
"""
import base64
import glob
import json
import os
import re
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'scripts'))
from protoenc import decode_build, read_varint, encode_build

ARCH_LABEL = {'weapon': 'Weapon', 'spirit': 'Spirit', 'vitality': 'Vitality', 'nuke': 'Nuke', 'cn': 'CN'}


def parse_fields(buf):
    fields = []
    j = 0
    while j < len(buf):
        tag, j = read_varint(buf, j)
        f, w = tag >> 3, tag & 7
        if w == 0:
            v, j = read_varint(buf, j)
            fields.append((f, v))
        elif w == 2:
            ln, j = read_varint(buf, j)
            fields.append((f, buf[j:j + ln]))
            j += ln
        elif w == 5:
            fields.append((f, buf[j:j + 4]))
            j += 4
        else:
            raise ValueError(f'wire {w}')
    return fields


def parse_payload(p):
    top = {}
    for f, v in parse_fields(decode_build(p)):
        top.setdefault(f, []).append(v)
    hid, ts, name = top[1][0], top[4][0], top[5][0].decode()
    phases = []
    for c in [v for f, v in parse_fields(top[10][0]) if f == 1]:
        cf = {}
        for f, v in parse_fields(c):
            cf.setdefault(f, []).append(v)
        tag = cf[2][0].decode()
        phase = 'early' if 'Early' in tag else ('mid' if 'Mid' in tag else 'late')
        ids = [v for f, v in
               (x for im in cf.get(1, []) for x in parse_fields(im)) if f == 1]
        phases.append((phase, ids))
    return hid, ts, name, phases


def main():
    html_path = os.path.join(BASE, 'index.html')
    html = open(html_path, encoding='utf-8').read()

    # ---------- 1. encoder verification ----------
    bins_m = re.search(r'const gameBuildsBin = (\{.*?\});\n', html, re.S)
    assert bins_m, 'gameBuildsBin not found'
    bins = json.loads(bins_m.group(1))
    hero_ids = {}
    for hero, builds in bins.items():
        hid, ts, name, phases = parse_payload(builds['Standard'])
        hero_ids[hero] = hid
        assert encode_build(hid, name, phases, ts) == builds['Standard'], \
            f'encoder mismatch for {hero}'
    print(f'[1/5] encoder verified byte-identical on {len(bins)} Standard payloads')

    # ---------- 2. archetype payloads ----------
    item_ids = json.load(open(os.path.join(BASE, 'scripts', 'items_map.json')))
    files = sorted(glob.glob(os.path.join(BASE, 'data', 'archetypes', '*.json')))
    assert len(files) == 44, f'expected 44 archetype files, got {len(files)}'
    payloads = {}
    ts_now = int(time.time())
    for fp in files:
        d = json.load(open(fp))
        hero = d['name']
        assert hero in hero_ids, f'no hero_id for {hero}'
        hid = hero_ids[hero]
        pm = {}
        for akey, a in d['archetypes'].items():
            def ids_of(items):
                out = []
                for it in items:
                    nm = it if isinstance(it, str) else it['name']
                    assert nm in item_ids, f'{hero}/{akey}: no item id for {nm!r}'
                    out.append(item_ids[nm])
                return out
            phases = [
                ('early', ids_of(a['phases']['p1']['items'])),
                ('mid', ids_of(a['phases']['p2']['items'])),
                ('late', ids_of(a['phases']['p3']['final_loadout'])),
            ]
            pm[ARCH_LABEL[akey]] = encode_build(
                hid, f'{hero} - {ARCH_LABEL[akey]}', phases, ts_now)
        payloads[hero] = pm
    # round-trip check on generated payloads
    for hero, pm in payloads.items():
        for label, p in pm.items():
            hid2, _, name2, ph2 = parse_payload(p)
            assert hid2 == hero_ids[hero] and name2 == f'{hero} - {label}'
            assert [p for p, _ in ph2] == ['early', 'mid', 'late']
    print(f'[2/5] generated {sum(len(v) for v in payloads.values())} archetype payloads, round-trip OK')

    # ---------- 3. archetypes.js ----------
    itemdb = json.load(open(os.path.join(BASE, 'scripts', 'itemdb.json')))
    comps = json.load(open(os.path.join(BASE, 'scripts', 'components.json')))
    byclass = json.load(open(os.path.join(BASE, 'scripts', 'classmap.json')))
    upgrades = {}
    for target, clist in comps.items():
        if target not in itemdb:
            continue
        for c in clist:
            # components.json values are display names for current items and
            # class names for older ones — resolve via classmap first, then
            # fall back to the value itself when it is a live item name.
            # (Classmap-only lookup silently produced an EMPTY map: every
            # value in the current components.json is a display name.)
            nm = byclass.get(c) or (c if c in itemdb else None)
            if nm and nm in itemdb and not nm.startswith('upgrade_'):
                upgrades[nm] = target
    data = {}
    for fp in files:
        d = json.load(open(fp))
        data[d['name']] = {'meta_archetype': d['meta_archetype'],
                           'archetypes': d['archetypes']}
    slim_db = {n: {'cost': v['cost'], 'cat': v['cat'], 'active': v['active']}
               for n, v in itemdb.items() if not n.startswith('upgrade_')}
    itemstats = json.load(open(os.path.join(BASE, 'scripts', 'itemstats.json')))
    scaling = json.load(open(os.path.join(BASE, 'scripts', 'abilityscaling.json')))
    # AP economy (scripts/ap-model.json, Prompt 31): compact levels as
    # [souls, 'U'|'A'] pairs + tier costs + per-hero ultimate names.
    ap_model = json.load(open(os.path.join(BASE, 'scripts', 'ap-model.json')))
    slim_ap = {
        'levels': [[l['souls'], 'U' if l['reward'] == 'unlock' else 'A']
                   for l in ap_model['levels']],
        'tierCosts': ap_model['tier_costs'],
        'tierAt': ap_model['tier_at_ap'],
        'ults': ap_model['ultimates'],
        'totalAp': ap_model['total_ap'],
    }
    # Item tooltips (scripts/itemtooltips.json) exported with short keys:
    # c=cost t=tier g=cat a=active(1) d=cooldown i=imbue(1) f=fx lines s=stat lines
    tooltips = json.load(open(os.path.join(BASE, 'scripts', 'itemtooltips.json')))
    slim_tips = {}
    for n, e in tooltips.items():
        s = {'c': e['cost'], 't': e['tier'], 'g': e['cat']}
        if e['active']:
            s['a'] = 1
        if 'cd' in e:
            s['d'] = e['cd']
        if e['imbue']:
            s['i'] = 1
        if e.get('fx'):
            s['f'] = e['fx']
        if e.get('stats'):
            s['s'] = e['stats']
        slim_tips[n] = s
    js = ('window.ARCHETYPE_DATA = ' + json.dumps(data, separators=(',', ':')) + ';\n'
          'window.ARCHETYPE_ITEMDB = ' + json.dumps(slim_db, separators=(',', ':')) + ';\n'
          'window.ARCHETYPE_UPGRADES = ' + json.dumps(upgrades, separators=(',', ':')) + ';\n'
          'window.ARCHETYPE_PAYLOADS = ' + json.dumps(payloads, separators=(',', ':')) + ';\n'
          'window.ARCHETYPE_ITEMSTATS = ' + json.dumps(itemstats, separators=(',', ':')) + ';\n'
          'window.ABILITY_SCALING = ' + json.dumps(scaling, separators=(',', ':')) + ';\n'
          'window.ITEM_TOOLTIPS = ' + json.dumps(slim_tips, separators=(',', ':')) + ';\n'
          'window.AP_MODEL = ' + json.dumps(slim_ap, separators=(',', ':')) + ';\n')
    out_dir = os.path.join(BASE, 'assets', 'data')
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, 'archetypes.js'), 'w').write(js)
    print(f'[3/5] wrote assets/data/archetypes.js ({len(js)//1024} KB)')

    # ---------- 4. patch index.html ----------
    # Idempotent: the checked-in index.html already carries these injections
    # from the previous run. Each patch below is skipped when its result is
    # already present, so re-running never double-injects and never wipes
    # hand edits (META filter chips, pages.dev canonical URLs).
    def rep(old, new, count=1):
        nonlocal html
        if new in html:
            return  # already applied
        assert html.count(old) >= 1, f'anchor not found: {old[:80]!r}'
        html = html.replace(old, new, count)

    # 4a. script tag before the main inline script
    rep('  <script>\n    const heroes = ',
        '  <script src="assets/data/archetypes.js"></script>\n  <script>\n    const heroes = ')

    # 4b. merge archetype payloads into gameBuildsBin (after its declaration line)
    merge_stmt = 'Object.entries(window.ARCHETYPE_PAYLOADS||{}).forEach(([hh,mm])=>{ gameBuildsBin[hh]=Object.assign({},gameBuildsBin[hh],mm); });'
    if merge_stmt not in html:
        mline = re.search(r'^    const gameBuildsBin = \{.*?\};$', html, re.M)
        assert mline, 'gameBuildsBin line not found'
        html = (html[:mline.end()] + '\n    ' + merge_stmt + html[mline.end():])

    # 4c. CSS — SYNC: strip every previously injected arch CSS block (older
    # runs appended one per CSS change; the duplicates were pure bloat) and
    # insert exactly one fresh copy of assets-src/arch-ui.css.
    css = open(os.path.join(BASE, 'assets-src', 'arch-ui.css')).read()
    css_block = '/* ===== 3-archetype UI ===== */\n' + css.rstrip() + '\n'
    html, n_css = re.subn(r'/\* ===== 3-archetype UI ===== \*/\n.*?\n(?=/\* ===== 3-archetype UI ===== \*/|</style>)',
                          '', html, flags=re.S)
    assert '</style>' in html
    html = html.replace('</style>', css_block + '</style>', 1)
    print(f'    [4c] arch CSS synced (removed {n_css} stale block(s))')

    # 4d. archetype UI JS — SYNC the inlined copy with assets-src/arch-ui.js.
    # The block starts at the marker right after the gameBuildsBin merge
    # statement and ends right before the original script's `const phases`.
    uijs = open(os.path.join(BASE, 'assets-src', 'arch-ui.js')).read()
    anchor = "gameBuildsBin[hh]=Object.assign({},gameBuildsBin[hh],mm); });"
    js_marker = '/* ===== 3-Archetype UI (injected by scripts/build-site.py) ===== */'
    if js_marker not in html:
        assert html.count(anchor) == 1, 'merge anchor not unique'
        html = html.replace(anchor, anchor + '\n' + uijs)
    else:
        a_idx = html.find(anchor)
        start = html.find(js_marker, a_idx)
        assert start != -1, 'JS marker not found after merge anchor'
        end = html.find("    const phases = [{key:'early'", start)
        assert end != -1, 'JS block end anchor (const phases) not found'
        html = html[:start] + uijs.rstrip() + '\n\n' + html[end:]
        print('    [4d] arch UI JS synced from assets-src/arch-ui.js')

    # 4e. renderBuild: archetype-aware mode reset (keep legacy alts working)
    # 4e-migration: patch the already-injected 4-mode list to 5-mode first.
    rep("if(archDataFor(h.hero)){ const _ak=String(activeBuildMode||'').toLowerCase(); if(!['weapon','spirit','vitality','nuke'].includes(_ak) && activeBuildMode!=='standard') activeBuildMode='standard'; }",
        "if(archDataFor(h.hero)){ const _ak=String(activeBuildMode||'').toLowerCase(); if(!['weapon','spirit','vitality','nuke','cn'].includes(_ak) && activeBuildMode!=='standard') activeBuildMode='standard'; }")
    rep("if(archDataFor(h.hero)){ const _ak=String(activeBuildMode||'').toLowerCase(); if(!['weapon','spirit','vitality'].includes(_ak) && activeBuildMode!=='standard') activeBuildMode='standard'; }"
        " else if(activeBuildMode!=='standard' && !alternateOptions.some(variant=>variant.alt_name===activeBuildMode)) activeBuildMode='standard';",
        "if(archDataFor(h.hero)){ const _ak=String(activeBuildMode||'').toLowerCase(); if(!['weapon','spirit','vitality','nuke','cn'].includes(_ak) && activeBuildMode!=='standard') activeBuildMode='standard'; }"
        " else if(activeBuildMode!=='standard' && !alternateOptions.some(variant=>variant.alt_name===activeBuildMode)) activeBuildMode='standard';")

    # 4f. let-ify the section consts we override (context-specific reps below)

    rep('const phaseHtml=renderTimeline(buildItems, h.hero)+renderFinalBuild(h.hero, buildItems, isAlternate?alternate.alt_name:null);',
        'let phaseHtml=renderTimeline(buildItems, h.hero)+renderFinalBuild(h.hero, buildItems, isAlternate?alternate.alt_name:null);')
    rep('const buildItems=isAlternate?alternate.items:h.build;',
        'let buildItems=isAlternate?alternate.items:h.build;')
    rep('const abilityHtml=extra ? `', 'let abilityHtml=extra ? `')
    rep('const situationalHtml=extra ? `', 'let situationalHtml=extra ? `')
    rep('const altIntro=isAlternate?`', 'let altIntro=isAlternate?`')
    rep('const tabsHtml=`<div class="build-tabs"', 'let tabsHtml=`<div class="build-tabs"')

    # 4g. archetype override block before buildView.innerHTML
    override = """
      // ===== 3-archetype view override (injected by build-site.py) =====
      let archMode=null, archDatum=null;
      {
        const ad=archDataFor(h.hero);
        if(ad){
          const ak=String(activeBuildMode||'').toLowerCase();
          if(['weapon','spirit','vitality','nuke','cn'].includes(ak)) archMode=ak;
          else if(activeBuildMode==='standard') archMode=ad.meta_archetype;
          if(archMode){
            archDatum=ad; activeBuildMode=archMode;
            const A=ad.archetypes[archMode];
            buildItems=enrichArchItems(A);
            tabsHtml=archTabsHtml(h,ad,archMode);
            altIntro=archIntroHtml(h,ad,archMode);
            abilityHtml=archSkillHtml(h,A);
            skillupHtml='';
            phaseHtml=archPhasesHtml(h,A,archMode);
            situationalHtml=archCountersHtml(A);
          }
        }
      }
"""
    # 4g-migration: the override block is already injected in the checked-in
    # html; patch its mode list in place so the 4g rep below then sees its
    # (updated) override as already-applied and does not double-inject.
    rep("          if(['weapon','spirit','vitality','nuke'].includes(ak)) archMode=ak;",
        "          if(['weapon','spirit','vitality','nuke','cn'].includes(ak)) archMode=ak;")
    rep('      buildView.innerHTML=`', override + '      buildView.innerHTML=`')

    # 4h. hide legacy roadmap-head + legend in archetype mode
    rep("""        <div class="roadmap-head"><h3>${isAlternate?alternate.alt_name:'Standard'} purchase order</h3><div class="direction"><strong>START</strong> · read left to right · <strong>FINISH →</strong></div></div>
        <div class="legend" aria-label="Item category legend"><span class="weapon-key"><i class="dot"></i>Weapon</span><span class="vitality-key"><i class="dot"></i>Vitality</span><span class="spirit-key"><i class="dot"></i>Spirit</span></div>""",
        """        ${archMode?'':`<div class="roadmap-head"><h3>${isAlternate?alternate.alt_name:'Standard'} purchase order</h3><div class="direction"><strong>START</strong> · read left to right · <strong>FINISH →</strong></div></div>
        <div class="legend" aria-label="Item category legend"><span class="weapon-key"><i class="dot"></i>Weapon</span><span class="vitality-key"><i class="dot"></i>Vitality</span><span class="spirit-key"><i class="dot"></i>Spirit</span></div>`}""")

    # 4i. copy-button buildName (second declaration site)
    rep("let buildName=isAlternate?alternate.alt_name:'Standard';\n\n      copyBuildButton.addEventListener",
        "let buildName=(typeof archMode!=='undefined'&&archMode)?archCap(archMode):(isAlternate?alternate.alt_name:'Standard');\n\n      copyBuildButton.addEventListener")

    # 4j. openExportModal archetype branches
    # 4j-migration: patch the already-injected 4-mode list to 5-mode first.
    rep("      const archM = (()=>{ const ad=archDataFor(h.hero); const ak=String(activeBuildMode||'').toLowerCase(); return (ad && ['weapon','spirit','vitality','nuke'].includes(ak)) ? ak : null; })();",
        "      const archM = (()=>{ const ad=archDataFor(h.hero); const ak=String(activeBuildMode||'').toLowerCase(); return (ad && ['weapon','spirit','vitality','nuke','cn'].includes(ak)) ? ak : null; })();")
    rep("      const archM = (()=>{ const ad=archDataFor(h.hero); const ak=String(activeBuildMode||'').toLowerCase(); return (ad && ['weapon','spirit','vitality'].includes(ak)) ? ak : null; })();\n"
        "      let buildName = archM ? archCap(archM) : (isAlternate ? alternate.alt_name : 'Standard');\n"
        "      let buildItems = archM ? enrichArchItems(archDataFor(h.hero).archetypes[archM]) : (isAlternate ? alternate.items : h.build);",
        "      const archM = (()=>{ const ad=archDataFor(h.hero); const ak=String(activeBuildMode||'').toLowerCase(); return (ad && ['weapon','spirit','vitality','nuke','cn'].includes(ak)) ? ak : null; })();\n"
        "      let buildName = archM ? archCap(archM) : (isAlternate ? alternate.alt_name : 'Standard');\n"
        "      let buildItems = archM ? enrichArchItems(archDataFor(h.hero).archetypes[archM]) : (isAlternate ? alternate.items : h.build);")
    rep("      if(textCardInput) textCardInput.value = buildPlainText(h, buildName, buildItems, extra, skillup);",
        "      if(textCardInput) textCardInput.value = archM ? archPlainText(h.hero, buildName, archDataFor(h.hero).archetypes[archM]) : buildPlainText(h, buildName, buildItems, extra, skillup);")

    # 4k. updateModalChecklist archetype branch
    # 4k-migration: patch the already-injected 4-mode list to 5-mode first.
    rep("      const archM2 = (()=>{ const ad=archDataFor(h.hero); const ak=String(activeBuildMode||'').toLowerCase(); return (ad && ['weapon','spirit','vitality','nuke'].includes(ak)) ? ak : null; })();",
        "      const archM2 = (()=>{ const ad=archDataFor(h.hero); const ak=String(activeBuildMode||'').toLowerCase(); return (ad && ['weapon','spirit','vitality','nuke','cn'].includes(ak)) ? ak : null; })();")
    rep("      const archM2 = (()=>{ const ad=archDataFor(h.hero); const ak=String(activeBuildMode||'').toLowerCase(); return (ad && ['weapon','spirit','vitality'].includes(ak)) ? ak : null; })();\n"
        "      const buildItems = archM2 ? enrichArchItems(archDataFor(h.hero).archetypes[archM2]) : (alternate ? alternate.items : h.build);",
        "      const archM2 = (()=>{ const ad=archDataFor(h.hero); const ak=String(activeBuildMode||'').toLowerCase(); return (ad && ['weapon','spirit','vitality','nuke','cn'].includes(ak)) ? ak : null; })();\n"
        "      const buildItems = archM2 ? enrichArchItems(archDataFor(h.hero).archetypes[archM2]) : (alternate ? alternate.items : h.build);")

    # 4l. deep-link init accepts archetype slugs
    # 4l-migration: patch the already-injected 4-mode list to 5-mode first.
    rep("              else if(archDataFor(foundName) && ['weapon','spirit','vitality','nuke'].includes(buildSlug)) activeBuildMode = buildSlug;",
        "              else if(archDataFor(foundName) && ['weapon','spirit','vitality','nuke','cn'].includes(buildSlug)) activeBuildMode = buildSlug;")
    rep("              if(matchedAlt) activeBuildMode = matchedAlt.alt_name;\n"
        "              else if(archDataFor(foundName) && ['weapon','spirit','vitality'].includes(buildSlug)) activeBuildMode = buildSlug;",
        "              if(matchedAlt) activeBuildMode = matchedAlt.alt_name;\n"
        "              else if(archDataFor(foundName) && ['weapon','spirit','vitality','nuke','cn'].includes(buildSlug)) activeBuildMode = buildSlug;")

    open(html_path, 'w', encoding='utf-8').write(html)
    print('[4/5] patched index.html')

    # ---------- 5. verify ----------
    # 5a. JS syntax check on the inline script
    script_m = re.search(r'  <script>\n(.*?)\n  </script>', html, re.S)
    assert script_m, 'inline script not found'
    open('/tmp/check-inline.js', 'w').write(script_m.group(1))
    r = subprocess.run(['node', '--check', '/tmp/check-inline.js'],
                       capture_output=True, text=True)
    assert r.returncode == 0, f'node --check failed:\n{r.stderr[:2000]}'
    print('[5/5] node --check: inline script OK')
    r = subprocess.run([sys.executable, 'scripts/validate-archetypes.py',
                        'data/archetypes/*.json'], cwd=BASE,
                       capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr[-500:])
    assert r.returncode == 0
    r = subprocess.run([sys.executable, 'scripts/verify_integrity.py'], cwd=BASE,
                       capture_output=True, text=True)
    print('verify_integrity:', r.stdout.strip().splitlines()[-3:])
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-500:]
    print('BUILD OK')


if __name__ == '__main__':
    main()
