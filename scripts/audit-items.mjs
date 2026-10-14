#!/usr/bin/env node
/**
 * Deadlock Meta Audit Script (Node.js ESM)
 * Cross-references hero build item prices, categories, and names in index.html
 * against the live Deadlock public assets API.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function fetchLiveItems() {
  const urls = [
    'https://assets.deadlock-api.com/v2/items',
    'https://api.deadlock-api.com/v1/assets/items'
  ];
  const headers = { 'User-Agent': 'Deadlock-Build-Auditor/1.0 (Mozilla/5.0)' };

  for (const url of urls) {
    try {
      const resp = await fetch(url, { headers });
      if (resp.ok) {
        const data = await resp.json();
        console.error(`Successfully fetched ${data.length} items from ${url}`);
        return data;
      }
    } catch (_err) {
      console.error(`Notice: ${url} failed, trying next endpoint...`);
    }
  }
  return null;
}

function extractItemsFromHtml(htmlPath) {
  const content = fs.readFileSync(htmlPath, 'utf8');
  const heroesMatch = content.match(/const heroes\s*=\s*(\[[\s\S]*?\]);\s*const alts/);
  const heroes = heroesMatch ? JSON.parse(heroesMatch[1]) : [];

  const altsMatch = content.match(/const alts\s*=\s*(\{[\s\S]*?\});\s*const portraits/);
  const alts = altsMatch ? JSON.parse(altsMatch[1]) : {};

  const buildItems = [];
  for (const h of heroes) {
    for (const it of h.build || []) {
      buildItems.push({
        hero: h.hero,
        build: 'Standard',
        name: it.name,
        price: it.price,
        category: it.category
      });
    }
  }

  for (const [heroName, altData] of Object.entries(alts)) {
    const variants = Array.isArray(altData) ? altData : [altData];
    for (const variant of variants) {
      const altName = variant.alt_name || 'Alternate';
      for (const it of variant.items || []) {
        buildItems.push({
          hero: heroName,
          build: altName,
          name: it.name,
          price: it.price,
          category: it.category
        });
      }
    }
  }

  return buildItems;
}

function mapSlotType(slotType) {
  if (!slotType) return 'Unknown';
  const s = String(slotType).toLowerCase();
  if (s.includes('weapon')) return 'Weapon';
  if (s.includes('armor') || s.includes('vitality')) return 'Vitality';
  if (s.includes('tech') || s.includes('spirit')) return 'Spirit';
  return slotType.charAt(0).toUpperCase() + slotType.slice(1);
}

async function runAudit() {
  const htmlPath = process.argv[2] || (fs.existsSync('index.html') ? 'index.html' : 'deadlock-build-guide/index.html');
  const outPath = process.argv[3] || 'audit-report.md';

  console.error('Running Deadlock Meta Audit (Node.js)...');
  const liveItems = await fetchLiveItems();
  if (!liveItems) {
    console.error('Failed to fetch live API data.');
    process.exit(1);
  }

  const liveByName = new Map();
  for (const it of liveItems) {
    if (it.name) liveByName.set(it.name.toLowerCase().trim(), it);
  }

  const buildItems = extractItemsFromHtml(htmlPath);
  const uniqueItems = new Map();
  for (const it of buildItems) {
    const key = it.name.toLowerCase().trim();
    if (!uniqueItems.has(key)) {
      uniqueItems.set(key, { ...it, heroes: [] });
    }
    uniqueItems.get(key).heroes.push(`${it.hero} (${it.build})`);
  }

  const discrepancies = [];
  let verifiedCount = 0;

  for (const [key, local] of uniqueItems.entries()) {
    const live = liveByName.get(key);
    if (!live) {
      discrepancies.push({
        type: 'Missing / Renamed Item',
        item: local.name,
        expected: 'Valid Deadlock Item in API',
        found: 'Not found in live items dataset',
        heroes: local.heroes.slice(0, 3).join(', ')
      });
      continue;
    }

    verifiedCount++;
    if (live.cost !== undefined && local.price !== undefined && live.cost !== local.price) {
      discrepancies.push({
        type: 'Price Stale',
        item: local.name,
        expected: `${live.cost.toLocaleString()} souls`,
        found: `${local.price.toLocaleString()} souls`,
        heroes: local.heroes.slice(0, 3).join(', ')
      });
    }

    if (live.item_slot_type) {
      const mapped = mapSlotType(live.item_slot_type);
      if (local.category && mapped !== local.category) {
        discrepancies.push({
          type: 'Category Stale',
          item: local.name,
          expected: mapped,
          found: local.category,
          heroes: local.heroes.slice(0, 3).join(', ')
        });
      }
    }
  }

  const nowStr = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  const report = [
    '# 🛡️ Deadlock Build Guide — Live Meta Audit Report',
    `*Generated on: \`${nowStr}\`*\n`,
    `- **Total items tracked in guides:** ${uniqueItems.size}`,
    `- **Verified in sync:** ${verifiedCount}`,
    `- **Discrepancies found:** ${discrepancies.length}\n`
  ];

  if (discrepancies.length > 0) {
    report.push('### ⚠️ Discrepancies Requiring Review\n');
    report.push('| Item Name | Issue | Expected (Live API) | Guide Setting | Affected Builds |');
    report.push('|---|---|---|---|---|');
    for (const d of discrepancies) {
      report.push(`| **${d.item}** | ${d.type} | \`${d.expected}\` | \`${d.found}\` | ${d.heroes} |`);
    }
  } else {
    report.push('### ✅ Audit Passed: All Items 100% Up-To-Date');
    report.push('All item names, categories, and prices across all 42 hero builds match Valve\'s live game database.');
  }

  const outputMd = report.join('\n');
  fs.writeFileSync(outPath, outputMd, 'utf8');
  console.log(outputMd);
}

runAudit().catch(err => {
  console.error(err);
  process.exit(1);
});
