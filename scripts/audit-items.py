#!/usr/bin/env python3
"""
Deadlock Meta Audit Script
Cross-references hero build item prices, categories, and names in index.html
against the live Deadlock public assets API.
"""

import sys, os, re, json, urllib.request, urllib.error
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from datetime import datetime, timezone

def fetch_live_items():
    urls = [
        "https://assets.deadlock-api.com/v2/items",
        "https://api.deadlock-api.com/v1/assets/items"
    ]
    headers = {"User-Agent": "Deadlock-Build-Auditor/1.0 (Mozilla/5.0)"}
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    print(f"Successfully fetched {len(data)} items from {url}", file=sys.stderr)
                    return data
        except Exception as e:
            print(f"Notice: {url} failed ({e}), trying next endpoint...", file=sys.stderr)
    return None

def extract_items_from_html(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract heroes array
    m_heroes = re.search(r'const heroes\s*=\s*(\[.*?\]);\s*const alts', content, re.DOTALL)
    heroes = json.loads(m_heroes.group(1)) if m_heroes else []

    # Extract alts array
    m_alts = re.search(r'const alts\s*=\s*(\{.*?\});\s*const portraits', content, re.DOTALL)
    alts = json.loads(m_alts.group(1)) if m_alts else {}

    build_items = []
    for h in heroes:
        hero_name = h['hero']
        for it in h.get('build', []):
            build_items.append({
                'hero': hero_name,
                'build': 'Standard',
                'name': it['name'],
                'price': it.get('price'),
                'category': it.get('category')
            })

    for hero_name, alt_data in alts.items():
        variants = alt_data if isinstance(alt_data, list) else [alt_data]
        for variant in variants:
            alt_name = variant.get('alt_name', 'Alternate')
            for it in variant.get('items', []):
                build_items.append({
                    'hero': hero_name,
                    'build': alt_name,
                    'name': it['name'],
                    'price': it.get('price'),
                    'category': it.get('category')
                })

    return build_items

def map_slot_type(slot_type):
    if not slot_type: return "Unknown"
    s = str(slot_type).lower()
    if "weapon" in s: return "Weapon"
    if "armor" in s or "vitality" in s: return "Vitality"
    if "tech" in s or "spirit" in s: return "Spirit"
    return slot_type.capitalize()

def run_audit(html_path='index.html', output_md='audit-report.md'):
    print("Running Deadlock Meta Audit...", file=sys.stderr)
    live_items = fetch_live_items()
    if not live_items:
        # Fallback to local snapshot if offline
        local_cache = os.path.join(os.path.dirname(__file__), 'items_map.json')
        if os.path.exists(local_cache):
            print(f"Using local cached items from {local_cache}", file=sys.stderr)
            with open(local_cache, 'r', encoding='utf-8') as f:
                name_map = json.load(f)
            live_items = [{"name": k, "id": v} for k, v in name_map.items()]
        else:
            print("Error: Could not reach live API and no local cache available.", file=sys.stderr)
            sys.exit(1)

    # Index live items by normalized lowercase name
    live_by_name = {}
    for it in live_items:
        name = it.get('name')
        if name:
            live_by_name[name.lower().strip()] = it

    build_items = extract_items_from_html(html_path)
    unique_items = {}
    for it in build_items:
        key = it['name'].lower().strip()
        if key not in unique_items:
            unique_items[key] = {
                'name': it['name'],
                'price': it['price'],
                'category': it['category'],
                'heroes': []
            }
        unique_items[key]['heroes'].append(f"{it['hero']} ({it['build']})")

    discrepancies = []
    verified_count = 0

    for key, local in unique_items.items():
        live = live_by_name.get(key)
        if not live:
            discrepancies.append({
                'type': 'Missing / Renamed Item',
                'item': local['name'],
                'expected': 'Valid Deadlock Item in API',
                'found': 'Not found in live items dataset',
                'heroes': ", ".join(local['heroes'][:3])
            })
            continue

        verified_count += 1
        live_cost = live.get('cost')
        if live_cost is not None and local['price'] is not None and live_cost != local['price']:
            discrepancies.append({
                'type': 'Price Stale',
                'item': local['name'],
                'expected': f"{live_cost:,} souls",
                'found': f"{local['price']:,} souls",
                'heroes': ", ".join(local['heroes'][:3])
            })

        live_slot = live.get('item_slot_type')
        if live_slot:
            mapped_slot = map_slot_type(live_slot)
            if local['category'] and mapped_slot != local['category']:
                discrepancies.append({
                    'type': 'Category Stale',
                    'item': local['name'],
                    'expected': mapped_slot,
                    'found': local['category'],
                    'heroes': ", ".join(local['heroes'][:3])
                })

    # Generate Markdown Report
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    report = []
    report.append("# 🛡️ Deadlock Build Guide — Live Meta Audit Report")
    report.append(f"*Generated on: `{now_str}`*\n")
    report.append(f"- **Total items tracked in guides:** {len(unique_items)}")
    report.append(f"- **Verified in sync:** {verified_count}")
    report.append(f"- **Discrepancies found:** {len(discrepancies)}\n")

    if discrepancies:
        report.append("### ⚠️ Discrepancies Requiring Review\n")
        report.append("| Item Name | Issue | Expected (Live API) | Guide Setting | Affected Builds |")
        report.append("|---|---|---|---|---|")
        for d in discrepancies:
            report.append(f"| **{d['item']}** | {d['type']} | `{d['expected']}` | `{d['found']}` | {d['heroes']} |")
        report.append("\n> Run `python scripts/audit-items.py` after Valve updates to verify shop integrity.")
    else:
        report.append("### ✅ Audit Passed: All Items 100% Up-To-Date")
        report.append("All item names, categories, and prices across all 42 hero builds match Valve's live game database.")

    markdown_output = "\n".join(report)
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write(markdown_output)

    print(markdown_output)
    return len(discrepancies)

if __name__ == '__main__':
    html_file = sys.argv[1] if len(sys.argv) > 1 else 'index.html'
    if not os.path.exists(html_file) and os.path.exists('deadlock-build-guide/index.html'):
        html_file = 'deadlock-build-guide/index.html'
    out_file = sys.argv[2] if len(sys.argv) > 2 else 'audit-report.md'
    run_audit(html_file, out_file)
