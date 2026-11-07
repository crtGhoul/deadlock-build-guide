/* ===== 3-Archetype UI (injected by scripts/build-site.py) ===== */
function archDataFor(heroName){ return (window.ARCHETYPE_DATA||{})[heroName] || null; }
function archItemDb(){ return window.ARCHETYPE_ITEMDB || {}; }
function archCap(s){ if(s === 'cn') return 'CN'; return s.charAt(0).toUpperCase()+s.slice(1); }

/* Flatten one archetype into item entries with live shop data. */
function enrichArchItems(arch){
  const db = archItemDb();
  const out = [];
  const push = (list, phase) => {
    list.forEach(it => {
      const name = (typeof it === 'string') ? it : it.name;
      const rec = db[name] || {};
      out.push({
        name,
        category: rec.cat || 'Weapon',
        price: rec.cost || 0,
        note: (it && typeof it === 'object' && it.why) || '',
        phase,
        active: !!rec.active
      });
    });
  };
  push(arch.phases.p1.items, 'early');
  push(arch.phases.p2.items, 'mid');
  push(arch.phases.p3.final_loadout.map(n => ({name:n})), 'late');
  return out;
}

/* Upgrade badges from the live component chains. */
function archComputeUpgrades(items){
  const tree = window.ARCHETYPE_UPGRADES || {};
  const to = new Map(), from = new Map();
  items.forEach((item, idx) => {
    const target = tree[item.name];
    if(!target) return;
    const tIdx = items.findIndex((o, oi) => oi > idx && o.name === target);
    if(tIdx !== -1){ to.set(idx, {num:tIdx+1, name:target}); from.set(tIdx, {num:idx+1, name:item.name}); }
  });
  return {to, from};
}

function archItemCard(item, num, heroName, archMode, upgrades){
  const cls = safeClass(item.category);
  const purchased = isItemPurchased(heroName, archMode, num);
  const upTo = upgrades.to.get(num-1), upFrom = upgrades.from.get(num-1);
  const upHtml = upTo
    ? `<span class="upgrade-badge to" title="Upgrades into #${upTo.num} ${upTo.name}">Upgrades to #${upTo.num}</span>`
    : upFrom
      ? `<span class="upgrade-badge from" title="Upgrades from #${upFrom.num} ${upFrom.name} (Saves 1 Slot)">Upgrades from #${upFrom.num} (Saves 1 Slot)</span>`
      : '';
  const activeTag = item.active ? `<span class="data-tag" title="Active item — uses a Z/X/C/V slot">ACTIVE</span>` : '';
  return `<article class="item ${cls}${purchased?' is-purchased':''}" data-item-num="${num}" data-item-tip="${item.name}" role="button" tabindex="0" title="Click to check off in live match (${num}. ${item.name})" aria-pressed="${purchased}">
    <span class="purchase-badge" aria-hidden="true">✓</span>
    <span class="number">${num}</span>
    ${imageOrFallback(itemIcons[item.name], item.name+' icon', 'item-icon', 'item-fallback', item.name.charAt(0))}
    <h4>${item.name}</h4>
    <div class="item-meta"><span class="price">${item.price.toLocaleString()} souls</span><span class="category">${item.category}</span>${activeTag}</div>
    ${upHtml}
    ${item.note ? `<p>${item.note}</p>` : ''}
  </article>`;
}

function archTabsHtml(h, archData, archMode){
  const order = ['weapon','spirit','vitality','nuke','cn'];
  const tabs = order.map(k => {
    const a = archData.archetypes[k];
    if(!a) return '';
    const meta = k === archData.meta_archetype;
    const extra = k === 'nuke' ? ' arch-tab-nuke' : (k === 'cn' ? ' arch-tab-cn' : '');
    return `<button class="build-tab arch-tab${extra}" type="button" role="tab" aria-selected="${archMode===k}" data-build-mode="${k}"><span class="arch-dot"></span>${a.label}${meta?'<span class="meta-badge">★ META</span>':''}</button>`;
  }).join('');
  return `<div class="build-tabs arch-tabs" role="tablist" aria-label="${h.hero} build archetypes">${tabs}</div>`;
}

/* CN community panel: what is distinctly Chinese about this build (tempo,
   item choices, lane style) plus the source line. The URL, when present, is
   rendered as a link; consensus builds say so plainly instead of naming a
   pro that was never found. */
function archCnPanelHtml(a){
  if(!a.cn_note) return '';
  const src = String(a.cn_source || '');
  const m = src.match(/https?:\/\/\S+/);
  const srcHtml = m
    ? src.slice(0, m.index) + `<a href="${m[0]}" target="_blank" rel="noopener">${m[0]}</a>` + src.slice(m.index + m[0].length)
    : src;
  return `<section class="cn-panel" aria-label="Chinese community build">
    <div class="cn-head"><span class="cn-kicker">CN COMMUNITY BUILD — Chinese-meta tempo</span></div>
    <p class="cn-note">${a.cn_note}</p>
    ${src ? `<p class="cn-source"><strong>Source:</strong> ${srcHtml}</p>` : ''}
  </section>`;
}

/* NUKE signature panel: the named ability, its scaling, why it's the pick,
   the honest damage math (deep-dive heroes), and the imbue stack to assign. */
function archNukePanelHtml(a){
  const ba = a.best_ability;
  if(!ba) return '';
  const db = archItemDb();
  const chips = (a.imbue_stack || []).map(nm => {
    const rec = db[nm] || {};
    return `<article class="fb-item ${safeClass(rec.cat || '')} nuke-chip" data-item-tip="${nm}">${imageOrFallback(itemIcons[nm], nm+' icon','item-icon','item-fallback',nm.charAt(0))}<h4>${nm}</h4><span class="final-price">${(rec.cost||0).toLocaleString()} souls</span></article>`;
  }).join('');
  const alts = (ba.alternates || []).map(alt =>
    `<li><b>${alt.name}</b> — ${alt.when}</li>`).join('');
  return `<section class="nuke-panel" aria-label="Signature ability">
    <div class="nuke-head"><span class="nuke-kicker">✦ Signature ability — the imbue target</span><h4 class="nuke-ability">${ba.name}</h4><span class="nuke-scaling">${ba.scaling}</span></div>
    <p class="nuke-why">${ba.why}</p>
    ${a.damage_math ? `<p class="nuke-math"><strong>Damage math</strong>${a.damage_math}</p>` : ''}
    ${a.cooldown_build ? `<p class="nuke-note">⚠ Cooldown/uptime build — the supercharge is frequency and control, not a damage spike. The copy above says so plainly.</p>` : ''}
    <div class="nuke-stack"><span class="nuke-stack-label">Imbue stack — assign all of these to ${ba.name}:</span><div class="nuke-stack-items">${chips}</div></div>
    ${alts ? `<div class="nuke-alts"><span class="nuke-stack-label">Also viable</span><ul>${alts}</ul></div>` : ''}
  </section>`;
}

function archIntroHtml(h, archData, archMode){
  const a = archData.archetypes[archMode];
  const meta = archMode === archData.meta_archetype;
  return `<section class="arch-intro" aria-label="${a.label} build overview">
    <p class="arch-tagline">${a.tagline}${meta?' <span class="meta-badge">★ META PICK</span>':''}</p>
    <p class="arch-synergy"><strong>KIT SYNERGY</strong>${a.kit_synergy}</p>
  </section>` + (archMode === 'nuke' ? archNukePanelHtml(a) : '') + (archMode === 'cn' ? archCnPanelHtml(a) : '');
}

function archSkillHtml(h, a){
  const so = a.skill_order;
  const unlocks = so.unlock.map(n =>
    `<li class="ability-step">${imageOrFallback(abilityIcons[h.hero]?.[n], n+' ability icon','ability-priority-icon','ability-priority-fallback',n.charAt(0))}<span class="ability-name">${n}</span></li>`).join('');
  // Tree milestones come from the authored fields: unlock order (steps 1–4)
  // and max_priority ('1'/'2'/'5' = the order abilities are maxed in).
  const maxName = v => String(v || '').split(' — ')[0].trim();
  const rank = {};
  ['1', '2', '5'].forEach((k, i) => { const nm = maxName((so.max_priority || {})[k]); if(nm) rank[nm] = i + 1; });
  const prio = ['1', '2', '5'].map(k =>
    `<div class="max-prio-card"><b>${k} AP — MAX</b><span>${(so.max_priority || {})[k] || ''}</span></div>`).join('');
  const node = (label, lit, badge) =>
    `<div class="tree-node${lit ? ' lit' : ''}">${badge ? `<span class="tree-step">${badge}</span>` : ''}<span class="tree-label">${label}</span></div>`;
  const cols = so.unlock.map((n, i) => {
    const r = rank[n];
    return `<div class="tree-col">
      <button type="button" class="tree-ability" data-ability-info="${n}" data-hero-name="${h.hero}" title="Show scaling for ${n}">${imageOrFallback(abilityIcons[h.hero]?.[n], n+' ability icon', 'ability-priority-icon', 'ability-priority-fallback', n.charAt(0))}<span>${n}</span></button>
      ${node('Unlock', true, i + 1)}
      ${node('Tier 1 · 1 AP', !!r, '')}
      ${node('Tier 2 · 2 AP', !!r, '')}
      ${node('Tier 3 · 5 AP', !!r, r ? '★' + r : '')}
    </div>`;
  }).join('');
  return `<section class="guide-section ability-priority" aria-labelledby="arch-ability-title">
    <div class="section-head"><h3 id="arch-ability-title">Ability priority — ${a.label}</h3><span class="section-kicker">Max in this order</span></div>
    <div class="ability-panel">
      <div class="skillup-subhead"><h4>Unlocks</h4><span>Take these four abilities in order</span></div>
      <ol class="ability-order">${unlocks}</ol>
      <div class="skillup-subhead"><h4>Max priority</h4><span>Which ability to max at each breakpoint</span></div>
      <div class="max-prio">${prio}</div>
      <div class="skillup-subhead"><h4>Skill tree</h4><span>Numbered = unlock order · ★1/★2/★3 on Tier 3 = max order · click an ability for its scaling</span></div>
      <div class="tree-grid">${cols}</div>
      <div class="scaling-panel" hidden></div>
    </div>
    ${simSectionHtml(h, a)}
  </section>`;
}

/* Final-loadout totals from the API item-stat layer (scripts/itemstats.json).
   Conditional / range-based / imbue-scoped bonuses are summed at face value
   and flagged with "~" — never presented as guaranteed numbers. */
function archTotals(finalNames){
  const db = archItemDb();
  const stats = window.ARCHETYPE_ITEMSTATS || {};
  const t = { souls:0, wd:0, sp:0, spPct:0, br:0, sr:0, cdr:0, fr:0, cond:false };
  (finalNames || []).forEach(nm => {
    const d = db[nm]; if(d) t.souls += d.cost || 0;
    const s = stats[nm]; if(!s) return;
    ['wd','sp','spPct','br','sr','cdr','fr'].forEach(k => { if(s[k]) t[k] += s[k]; });
    if(s.cond) t.cond = true;
  });
  return t;
}

function archTotalsHtml(a){
  const t = archTotals(a.phases.p3.final_loadout);
  const tilde = t.cond ? '~' : '';
  const spEff = t.spPct ? Math.round(t.sp * (1 + t.spPct / 100)) : t.sp;
  const cell = (label, val) => val ? `<span class="tot"><span class="tot-label">${label}</span><b>${val}</b></span>` : '';
  return `<div class="arch-totals" role="region" aria-label="Final loadout totals">
    <span class="tot totals-title">Final loadout</span>
    <span class="tot"><span class="tot-label">Souls</span><b>${t.souls.toLocaleString()}</b></span>
    ${cell('Weapon Damage', t.wd ? `+${tilde}${t.wd}%` : '')}
    ${cell('Spirit Power', t.sp ? `+${t.spPct ? '~' : ''}${spEff}` : '')}
    ${cell('Bullet Resist', t.br ? `+${t.br}%` : '')}
    ${cell('Spirit Resist', t.sr ? `+${t.sr}%` : '')}
    ${cell('Cooldown Reduction', t.cdr ? `+${tilde}${t.cdr}%` : '')}
    ${cell('Fire Rate', t.fr ? `+${t.fr}%` : '')}
    <span class="totals-note">Totals from the final 12 slots. “~” includes conditional, range-based or single-ability (imbue) bonuses at face value — your in-game numbers vary by range, stacks and target.</span>
  </div>`;
}

function archPhasesHtml(h, a, archMode){
  const items = enrichArchItems(a);
  const upgrades = archComputeUpgrades(items);
  const p1 = a.phases.p1, p2 = a.phases.p2, p3 = a.phases.p3;
  // CN fallback: the spike category is the build's declared primary, not
  // the mode label (p1.spike is always authored for CN, so this only
  // matters if a spike line is ever missing).
  const spikeMode = archMode === 'cn' ? (a.primary_category || 'Spirit').toLowerCase() : archMode;
  const spikeCat = archCap(spikeMode);
  const spikeBonus = spikeMode==='weapon' ? '+49% weapon damage' : spikeMode==='vitality' ? '+34% max HP' : '+38 Spirit Power';
  const p1sub = `<span class="spike-note">⚡ ${p1.spike||('4800 '+spikeCat+' — '+spikeBonus+' spike')}</span>`;
  let n = 0;
  const cardCol = (key, title, sub) => {
    const list = items.filter(it => it.phase === key);
    if(!list.length) return '';
    const cards = list.map(it => { n+=1; return archItemCard(it, n, h.hero, archMode, upgrades); }).join('');
    return `<div class="board-col"><h4 class="board-col-title">${title}</h4>${sub?`<p class="board-note">${sub}</p>`:''}<div class="board-items">${cards}</div></div>`;
  };
  // Late = final-12 remainder (items not already bought in Early/Mid)
  const bought = new Set(items.filter(it => it.phase !== 'late').map(it => it.name));
  const byName = {}; items.forEach(it => { byName[it.name]=it; });
  const lateNames = (p3.final_loadout || []).filter(nm => !bought.has(nm));
  const lateCards = lateNames.map(nm => { const it = byName[nm] || { price:0, category:'' };
    return `<article class="fb-item ${safeClass(it.category)}" data-item-tip="${nm}">${imageOrFallback(itemIcons[nm], nm+' icon','item-icon','item-fallback',nm.charAt(0))}<h4>${nm}</h4><span class="final-price">${(it.price||0).toLocaleString()} souls</span></article>`;
  }).join('');
  const lateCol = `<div class="board-col"><h4 class="board-col-title">Late — completes the 12</h4><p class="board-note">With Early + Mid, this is your final 12-slot loadout.</p><div class="board-items board-items-compact">${lateCards || '<p class="board-empty">Final loadout is fully bought in Early + Mid.</p>'}</div></div>`;
  const swaps = ((a.counters && a.counters.swaps) || []).map(s =>
    `<div class="board-swap"><span class="board-swap-vs">vs ${s.vs}</span><span class="swap-out" data-item-tip="${s.out}">${s.out}</span><span class="swap-arrow">→</span><b data-item-tip="${s.in}">${s.in}</b></div>`).join('');
  const sitCol = `<div class="board-col board-col-sit"><h4 class="board-col-title">Situational</h4><p class="board-note">1-for-1 counter swaps — full notes in the counters section below.</p><div class="board-swaps">${swaps || '<p class="board-empty">No swaps — this build is the answer.</p>'}</div></div>`;
  const sellHtml = (p3.sell_upgrade||[]).length
    ? `<ul class="sell-list">${p3.sell_upgrade.map(s=>`<li><span class="sell-from" data-item-tip="${s.from}">${s.from}</span><span class="sell-arrow">→</span><b data-item-tip="${s.to}">${s.to}</b> — ${s.why}</li>`).join('')}</ul>` : '';
  return `
    <div class="roadmap-head"><h3>${a.label} build board</h3><div class="direction"><strong>START</strong> · buy Early → Mid → Late · <strong>FINISH</strong></div></div>
    <div class="legend" aria-label="Item category legend"><span class="weapon-key"><i class="dot"></i>Weapon</span><span class="vitality-key"><i class="dot"></i>Vitality</span><span class="spirit-key"><i class="dot"></i>Spirit</span></div>
    ${archTotalsHtml(a)}
    <div class="board-grid">
      ${cardCol('early', 'Early — ' + (p1.name || 'Laning & 4.8k Spike Rush'), p1sub)}
      ${cardCol('mid', 'Mid — ' + (p2.name || 'Mid-Game Power Spike'), '')}
      ${lateCol}
      ${sitCol}
    </div>
    <section class="guide-section final-build" aria-label="Final build">
      <div class="section-head"><h3>Final 12-Slot Loadout</h3><span class="section-kicker">What you end the game holding</span></div>
      ${sellHtml}
      <div class="win-condition"><strong>LATE-GAME WIN CONDITION</strong><p>${p3.win_condition}</p></div>
    </section>`;
}

/* Ability scaling panel — shows ONLY scaling the API actually publishes. */
document.addEventListener('click', e => {
  const btn = e.target.closest('[data-ability-info]');
  if(!btn) return;
  const panel = btn.closest('.ability-panel')?.querySelector('.scaling-panel');
  if(!panel) return;
  const hero = btn.dataset.heroName, ab = btn.dataset.abilityInfo;
  const list = (window.ABILITY_SCALING || {})[hero]?.[ab];
  if(!Array.isArray(list) || !list.length){
    panel.innerHTML = `<h5>${ab} — scaling</h5><p class="scaling-none">Scaling not published in API data for this ability — no numbers are shown rather than guessed.</p>`;
  } else {
    const rows = list.map(en => {
      const per = en.scale_type === 'ELevelUpBoons' ? 'per level-up boon' : 'per Spirit Power';
      return `<div class="scaling-row"><span>${en.prop} <span class="scaling-base">base ${en.base}</span></span><b>+${en.scale} ${per}</b></div>`;
    }).join('');
    panel.innerHTML = `<h5>${ab} — scaling (API data)</h5>${rows}<p class="scaling-note">Only properties the API publishes are listed — nothing here is estimated.</p>`;
  }
  panel.hidden = false;
});

/* Tiny WebAudio sound hints — no files, only after user interaction. */
let _tcCtx = null;
function tcSound(kind){
  try {
    if(localStorage.getItem('tc-sound') === 'off') return;
    const AC = window.AudioContext || window.webkitAudioContext;
    if(!AC) return;
    _tcCtx = _tcCtx || new AC();
    if(_tcCtx.state === 'suspended') _tcCtx.resume();
    const t = _tcCtx.currentTime;
    const o = _tcCtx.createOscillator(), g = _tcCtx.createGain();
    o.type = 'sine';
    o.frequency.setValueAtTime(kind === 'hero' ? 660 : 523, t);
    if(kind === 'hero') o.frequency.exponentialRampToValueAtTime(880, t + 0.09);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.045, t + 0.015);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.15);
    o.connect(g); g.connect(_tcCtx.destination);
    o.start(t); o.stop(t + 0.17);
  } catch(err) { /* sound is a hint, never an error */ }
}
document.addEventListener('click', e => {
  if(e.target.closest('[data-hero]')) tcSound('hero');
  else if(e.target.closest('[data-build-mode]')) tcSound('tab');
});

function archCountersHtml(a){
  const c = a.counters;
  const cards = [
    ['vs. Deadman Danny', c.vs_danny],
    ['vs. Baba', c.vs_baba],
    ['vs. Violet', c.vs_violet]
  ].filter(([,txt]) => txt).map(([t,txt]) => `<div class="counter-card"><h4>${t}</h4><p>${txt}</p></div>`).join('');
  const swaps = (c.swaps||[]).map(s =>
    `<tr><td>${s.vs}</td><td class="swap-out" data-item-tip="${s.out}">${s.out}</td><td class="swap-in" data-item-tip="${s.in}">→ ${s.in}</td><td>${s.why}</td></tr>`).join('');
  return `<section class="guide-section arch-counters" aria-labelledby="arch-counters-title">
    <div class="section-head"><h3 id="arch-counters-title">Situational &amp; meta counters</h3><span class="section-kicker">Swap in when the match calls for it</span></div>
    ${cards ? `<div class="counter-cards">${cards}</div>` : ''}
    <div class="skillup-subhead"><h4>1-for-1 counter swaps</h4><span>Out → in</span></div>
    <table class="swap-table"><thead><tr><th>Threat</th><th>Out</th><th>In</th><th>Why</th></tr></thead><tbody>${swaps}</tbody></table>
    ${archSituationalHtml(a)}
  </section>`;
}

/* Counter-buys panel: the build's `situational` rules (gen-counterbuys.py).
   WHEN -> BUY (chip with cost + shop-plaque tooltip) -> sell the flex slot.
   Owned-variant rules (sell = null) say the answer is already in the build. */
function archSituationalHtml(a){
  const rules = a.situational || [];
  if(!rules.length) return '';
  const db = archItemDb();
  const OWNED_SUFFIX = ' Already in this build — buy it a phase earlier instead of waiting for the full build.';
  const rows = rules.map(r => {
    const rec = db[r.buy] || {};
    const owned = !r.sell;
    const note = owned ? String(r.note || '').split(OWNED_SUFFIX).join('') : (r.note || '');
    const sellHtml = owned
      ? `<span class="cb-owned">ALREADY IN THIS BUILD — buy it a phase earlier</span>`
      : `<span class="cb-sellwrap">instead of <span class="cb-sell" data-item-tip="${r.sell}">${r.sell}</span></span>`;
    return `<div class="cb-row">
      <p class="cb-when"><span class="cb-if">IF</span>${r.when}</p>
      <p class="cb-action"><span class="cb-buywrap">BUY <b class="cb-buy" data-item-tip="${r.buy}">${r.buy}</b> <span class="cb-cost">${(rec.cost || 0).toLocaleString('en-US')} souls</span></span>${sellHtml}</p>
      <p class="cb-note">${note}</p>
    </div>`;
  }).join('');
  return `<div class="arch-counterbuys">
    <div class="skillup-subhead"><h4>⚔ Counter-buys — if the game looks like this</h4><span>Conditional answers — swap the flex, keep the core</span></div>
    <div class="cb-list">${rows}</div>
  </div>`;
}

/* ===== Copy/paste text exports (detailed guide + compact shopping list) =====
   Both are plain ASCII on purpose: they get pasted into Notepad, Discord and
   the in-game browser, where smart punctuation mangles. archAscii maps the
   punctuation our data uses and drops anything still non-ASCII. */
function archAscii(s){
  return String(s == null ? '' : s)
    .replace(/—/g, ' - ').replace(/–/g, '-').replace(/→/g, '->')
    .replace(/×/g, 'x').replace(/≈/g, '~').replace(/·/g, '-')
    .replace(/[‘’]/g, "'").replace(/[“”]/g, '"')
    .replace(/✦/g, '').replace(/★/g, '*').replace(/⚠/g, '!')
    .replace(/[^\x20-\x7E\n]/g, '')
    .replace(/ {2,}/g, ' ');
}
function archFmt(n){ return Number(n || 0).toLocaleString('en-US'); }
function archModeSlug(arch, label){
  const L = String((arch && arch.label) || label || '').toLowerCase();
  if(L === 'cn') return 'cn';
  if(L.indexOf('nuke') !== -1) return 'nuke';
  if(L.indexOf('weapon') !== -1) return 'weapon';
  if(L.indexOf('vitality') !== -1) return 'vitality';
  return 'spirit';
}
function archGuideUrl(heroName, arch, label){
  const slug = (typeof toSlug === 'function') ? toSlug(heroName)
    : heroName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  return 'https://deadlock-build-guide.pages.dev/?hero=' + slug + '&build=' + archModeSlug(arch, label);
}

/* Purchase steps (p1 + p2) with real shop math: when a later item upgrades
   an earlier component (window.ARCHETYPE_UPGRADES chain), the shop charges
   only the difference — the component's price is credited once. */
function archBuySteps(arch){
  const db = archItemDb();
  const up = window.ARCHETYPE_UPGRADES || {};
  const compOf = {}; // target -> [component names]
  Object.keys(up).forEach(c => { (compOf[up[c]] = compOf[up[c]] || []).push(c); });
  const owned = new Map(); // component name -> price paid (unconsumed)
  const mkPhase = (ph, fallbackName) => {
    const rows = [];
    let spend = 0;
    ((ph && ph.items) || []).forEach(it => {
      const name = typeof it === 'string' ? it : it.name;
      const rec = db[name] || {};
      const price = rec.cost || 0;
      let pay = price;
      const used = [];
      (compOf[name] || []).forEach(c => {
        if(owned.has(c)){ pay -= owned.get(c); used.push(c); owned.delete(c); }
      });
      rows.push({ name, price, pay, comps: used,
                  why: (it && typeof it === 'object' && it.why) || '',
                  cat: rec.cat || '' });
      spend += pay;
      owned.set(name, price);
    });
    return { name: (ph && ph.name) || fallbackName, spike: (ph && ph.spike) || '', rows, spend };
  };
  const phases = [mkPhase(arch.phases.p1, 'Laning & 4.8k Spike Rush'),
                  mkPhase(arch.phases.p2, 'Mid-Game Power Spike')];
  const finalNames = arch.phases.p3.final_loadout || [];
  const finalTotal = finalNames.reduce((s, n) => s + ((db[n] || {}).cost || 0), 0);
  return { phases, finalNames, finalTotal };
}

function archOwnedSuffix(){ return ' Already in this build — buy it a phase earlier instead of waiting for the full build.'; }

/* The full guide document (Copy as text / export modal text card). */
function archPlainText(heroName, label, arch){
  const A = archAscii;
  const db = archItemDb();
  const lines = [];
  lines.push(`${heroName.toUpperCase()} - ${A(arch.label).toUpperCase().trim()} BUILD${arch.is_meta ? ' [META]' : ''}`);
  lines.push(`Guide: ${archGuideUrl(heroName, arch, label)}`);
  lines.push(`Tagline: ${A(arch.tagline)}`);
  if(arch.cn_note){
    lines.push('', 'CN COMMUNITY NOTE', A(arch.cn_note));
    if(arch.cn_source) lines.push(`CN source: ${A(arch.cn_source)}`);
  }
  if(arch.best_ability){
    const ba = arch.best_ability;
    lines.push('', 'SIGNATURE ABILITY',
      `${ba.name} - ${A(ba.scaling)}`,
      `Why this one: ${A(ba.why)}`,
      `Imbue stack (assign ALL to ${ba.name}): ${(arch.imbue_stack || []).map(n => `${n} (${archFmt((db[n] || {}).cost)})`).join(', ')}`);
    (ba.alternates || []).forEach(alt => lines.push(`Also viable: ${alt.name} - ${A(alt.when)}`));
    if(arch.cooldown_build) lines.push('NOTE: cooldown/uptime build - the supercharge is frequency and control, not a damage spike.');
    if(arch.damage_math) lines.push('', 'DAMAGE MATH', A(arch.damage_math));
  }
  const steps = archBuySteps(arch);
  lines.push('', 'BUY ORDER');
  let running = 0, num = 0;
  steps.phases.forEach((ph, pi) => {
    running += ph.spend;
    lines.push('', `PHASE ${pi + 1} - ${A(ph.name).toUpperCase()}${ph.spike ? ' (' + A(ph.spike) + ')' : ''}`);
    ph.rows.forEach(r => {
      num += 1;
      const upNote = r.comps.length ? ` (upgrades ${r.comps.join(' + ')} - you pay ${archFmt(r.pay)})` : '';
      lines.push(`${num}. ${r.name} - ${archFmt(r.price)} souls${upNote}${r.why ? ' - ' + A(r.why) : ''}`);
    });
    lines.push(`Phase spend: ${archFmt(ph.spend)} | Running total: ${archFmt(running)}`);
  });
  lines.push('', `FINAL 12 - total value ${archFmt(steps.finalTotal)} souls`);
  steps.finalNames.forEach((n, i) => {
    const rec = db[n] || {};
    lines.push(`${i + 1}. ${n} - ${archFmt(rec.cost)}${rec.cat ? ' (' + rec.cat + ')' : ''}`);
  });
  const so = arch.skill_order || {};
  lines.push('', 'SKILL ORDER',
    `Unlock: ${(so.unlock || []).join(' -> ')}`,
    `1 AP max: ${A((so.max_priority || {})['1'] || '')}`,
    `2 AP max: ${A((so.max_priority || {})['2'] || '')}`,
    `5 AP max: ${A((so.max_priority || {})['5'] || '')}`);
  const track = so.track || [];
  if(track.length){
    lines.push('16-step track:');
    for(let i = 0; i < track.length; i += 4){
      lines.push(` ${i + 1}-${Math.min(i + 4, track.length)}: ${track.slice(i, i + 4).join(', ')}`);
    }
  }
  const sit = arch.situational || [];
  if(sit.length){
    lines.push('', 'COUNTER-BUYS - IF THE GAME LOOKS LIKE THIS');
    sit.forEach(r => {
      const cost = archFmt((db[r.buy] || {}).cost);
      if(!r.sell){
        const note = A(String(r.note || '').split(archOwnedSuffix()).join(''));
        lines.push(`IF ${A(r.when)} -> ${r.buy} (${cost}) is ALREADY IN THIS BUILD - buy it a phase earlier. ${note}`);
      } else {
        lines.push(`IF ${A(r.when)} -> BUY ${r.buy} (${cost}) instead of ${r.sell} - ${A(r.note)}`);
      }
    });
  }
  const c = arch.counters || {};
  const named = [['Deadman Danny', c.vs_danny], ['Baba', c.vs_baba], ['Violet', c.vs_violet]].filter(([, t]) => t);
  if(named.length){
    lines.push('', 'NAMED COUNTERS');
    named.forEach(([n, t]) => lines.push(`vs ${n}: ${A(t)}`));
  }
  if((c.swaps || []).length){
    lines.push('', '1-FOR-1 COUNTER SWAPS');
    c.swaps.forEach(s => lines.push(`vs ${A(s.vs)}: ${s.out} -> ${s.in} - ${A(s.why)}`));
  }
  const p3 = arch.phases.p3;
  lines.push('', 'LATE GAME');
  (p3.sell_upgrade || []).forEach(s => lines.push(`${s.from} -> ${s.to} - ${A(s.why)}`));
  lines.push(`Win condition past 30k souls: ${A(p3.win_condition)}`);
  return lines.join('\n');
}

/* The compact second-monitor version: phases + totals + counter one-liners. */
function archShoppingText(heroName, label, arch){
  const A = archAscii;
  const db = archItemDb();
  const steps = archBuySteps(arch);
  const lines = [`${heroName.toUpperCase()} - ${A(arch.label).toUpperCase().trim()} - SHOPPING LIST`];
  let running = 0;
  steps.phases.forEach((ph, pi) => {
    running += ph.spend;
    const items = ph.rows.map(r => `${r.name} ${archFmt(r.price)}`).join(', ');
    lines.push(`P${pi + 1} (spend ${archFmt(ph.spend)}, running ${archFmt(running)}): ${items}`);
  });
  lines.push(`FINAL 12 (${archFmt(steps.finalTotal)}): ${steps.finalNames.join(', ')}`);
  if(arch.cn_note){
    lines.push(`CN NOTE: ${A(arch.cn_note)}`);
    if(arch.cn_source) lines.push(`CN SOURCE: ${A(arch.cn_source)}`);
  }
  const sit = arch.situational || [];
  if(sit.length){
    lines.push('COUNTERS:');
    sit.forEach(r => {
      const cost = archFmt((db[r.buy] || {}).cost);
      lines.push(r.sell
        ? `IF ${A(r.when)} -> BUY ${r.buy} ${cost} (sell ${r.sell})`
        : `IF ${A(r.when)} -> ${r.buy} ${cost} ALREADY IN BUILD - buy it a phase earlier`);
    });
  }
  return lines.join('\n');
}

/* ===== Item tooltip plaque (Prompt 32) — ONE delegated system =====
   Any element with data-item-tip="<Item Name>" gets the shop plaque, rendered
   from window.ITEM_TOOLTIPS (falling back to ARCHETYPE_ITEMDB name+cost, so a
   plaque is never empty). Desktop: hover / keyboard focus, ~120ms delay,
   flips near viewport edges, Esc dismisses, one at a time. Touch: the first
   tap pins the plaque AND still performs the card's own action (checklist
   toggle etc. — nothing is swallowed); tapping the same card again, or
   anywhere else, dismisses the pinned plaque. Mouse clicks never pin. */
(function(){
  const SHOW_MS = 120, HIDE_MS = 90;
  let tipEl = null, anchor = null, pinned = false, pinnedFor = null;
  let showTimer = 0, hideTimer = 0, stashedTitle = null, lastPointerType = 'mouse';

  function escT(s){ return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function tipData(name){
    const T = window.ITEM_TOOLTIPS || {}, D = window.ARCHETYPE_ITEMDB || {};
    const t = T[name];
    if(t) return { name: name, cost: t.c, tier: t.t, cat: t.g, active: !!t.a, cd: t.d, imbue: !!t.i, fx: t.f || [], stats: t.s || [] };
    const d = D[name];
    if(d){ const c = d.cost || 0; return { name: name, cost: c, tier: c >= 6400 ? 4 : c >= 3200 ? 3 : c >= 1600 ? 2 : 1, cat: d.category || '', active: !!d.active, cd: undefined, imbue: !!d.imbue, fx: [], stats: [] }; }
    return { name: name, cost: 0, tier: 0, cat: '', active: false, cd: undefined, imbue: false, fx: [], stats: [] };
  }
  function plaqueHtml(d){
    const sub = [
      d.tier ? '<span class="tip-tier">TIER ' + d.tier + '</span>' : '',
      d.cat ? '<span class="tip-cat">' + escT(d.cat) + '</span>' : '',
      d.cost ? '<span class="tip-cost"><i class="soul-gem" aria-hidden="true"></i>' + Number(d.cost).toLocaleString('en-US') + '</span>' : ''
    ].join('');
    const active = d.active
      ? '<div class="tip-active"><span class="tip-active-label">&#9670; ACTIVE</span>' + (d.cd != null ? '<span class="tip-cd">Cooldown ' + d.cd + 's</span>' : '') + '</div>'
      : '';
    const fx = d.fx.map(function(line){ return '<p class="tip-fx">' + escT(line) + '</p>'; }).join('');
    const stats = d.stats.length
      ? '<ul class="tip-stats">' + d.stats.map(function(s){ return '<li>' + escT(s) + '</li>'; }).join('') + '</ul>'
      : '';
    const imbue = d.imbue ? '<div class="tip-imbue">&#10022; Imbue item &mdash; supercharges the ability it is assigned to</div>' : '';
    return '<div class="tip-frame"><span class="tip-corners" aria-hidden="true"></span><div class="tip-name">' + escT(d.name) + '</div><div class="tip-sub">' + sub + '</div>' + active + fx + stats + imbue + '</div>';
  }
  function ensureEl(){
    if(!tipEl){
      tipEl = document.createElement('div');
      tipEl.className = 'item-tip';
      tipEl.setAttribute('role', 'tooltip');
      document.body.appendChild(tipEl);
    }
    return tipEl;
  }
  function place(target){
    if(!tipEl || !target.isConnected) return;
    const r = target.getBoundingClientRect();
    const tw = tipEl.offsetWidth, th = tipEl.offsetHeight;
    const vw = window.innerWidth, vh = window.innerHeight, M = 8;
    let left = Math.min(Math.max(r.left, M), Math.max(M, vw - tw - M));
    let top = r.bottom + 10;
    if(top + th > vh - M) top = r.top - th - 10;
    if(top < M) top = Math.min(Math.max(M, vh - th - M), r.bottom + 10);
    tipEl.style.left = left + 'px';
    tipEl.style.top = Math.max(M, top) + 'px';
  }
  function restoreTitle(){
    if(anchor && stashedTitle != null && anchor.isConnected) anchor.setAttribute('title', stashedTitle);
    stashedTitle = null;
  }
  function show(target, pin){
    const name = target.getAttribute('data-item-tip');
    if(!name) return;
    clearTimeout(hideTimer);
    const el = ensureEl();
    if(anchor && anchor !== target) restoreTitle();
    anchor = target; pinned = !!pin; pinnedFor = pin ? target : null;
    if(target.hasAttribute('title')){ stashedTitle = target.getAttribute('title'); target.removeAttribute('title'); }
    const d = tipData(name);
    el.innerHTML = plaqueHtml(d);
    el.setAttribute('data-cat', d.cat || '');
    el.classList.add('show');
    place(target);
  }
  function hide(){
    clearTimeout(showTimer); clearTimeout(hideTimer);
    restoreTitle();
    anchor = null; pinned = false; pinnedFor = null;
    if(tipEl) tipEl.classList.remove('show');
  }
  function tipTarget(e){
    const t = e.target;
    return (t && t.closest) ? t.closest('[data-item-tip]') : null;
  }

  document.addEventListener('pointerdown', function(e){ lastPointerType = e.pointerType || 'mouse'; }, true);
  document.addEventListener('pointerover', function(e){
    if(pinned || e.pointerType === 'touch') return;
    const t = tipTarget(e);
    if(!t || t === anchor) return;
    clearTimeout(showTimer);
    showTimer = setTimeout(function(){ show(t, false); }, SHOW_MS);
  });
  document.addEventListener('pointerout', function(e){
    if(pinned || e.pointerType === 'touch') return;
    const t = tipTarget(e);
    if(!t) return;
    if(e.relatedTarget && t.contains(e.relatedTarget)) return;
    clearTimeout(showTimer);
    if(anchor === t){
      clearTimeout(hideTimer);
      hideTimer = setTimeout(function(){ if(!pinned) hide(); }, HIDE_MS);
    }
  });
  document.addEventListener('focusin', function(e){
    if(pinned) return;
    const t = tipTarget(e);
    if(t && t !== anchor) show(t, false);
  });
  document.addEventListener('focusout', function(e){
    if(!pinned && anchor && tipTarget(e) === anchor) hide();
  });
  document.addEventListener('click', function(e){
    const t = tipTarget(e);
    if(lastPointerType === 'mouse'){
      if(pinned && !t) hide();
      return;
    }
    if(t){
      if(pinnedFor === t) hide();   /* second tap on the pinned card: act + dismiss */
      else show(t, true);           /* first tap: pin (the card's own action still runs) */
    } else if(pinned) hide();
  });
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape') hide(); });
  window.addEventListener('resize', function(){ if(anchor && tipEl && tipEl.classList.contains('show')) place(anchor); });
  document.addEventListener('scroll', function(){
    if(!anchor) return;
    if(!anchor.isConnected){ hide(); return; }
    if(pinned) place(anchor); else hide();
  }, true);
})();

/* ===== Ability Progression Simulator (Prompt 31) =====
   Interactive AP sandbox next to the static track: spend unlocks and AP
   exactly the way a match grants them. Economy = window.AP_MODEL
   (scripts/ap-model.json — game level_info data cross-checked against
   deadlock.wiki/Boons): level-ups at fixed gathered-souls thresholds grant
   an ability unlock (600 / 1,100 / 2,000 / 3,800) or +1 AP; tiers cost
   1 / 2 / 5 AP; the ultimate takes the 4th unlock. Illegal moves are
   impossible: the button is disabled and the reason is printed under it.
   State is keyed per hero+build; switching builds re-seeds, re-renders of
   the same build (checklist clicks) keep the sandbox state. */
const _simStates = {};
let _simViewKey = null;
function xEsc(s){ return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
function simModel(){ return window.AP_MODEL || { levels: [], tierAt: [1, 3, 8], ults: {} }; }
function simFresh(heroName, mode, arch){
  const so = arch.skill_order || {};
  return {
    key: heroName + '|' + mode, hero: heroName, mode,
    boon: 0, tokens: 1, apPool: 0,
    unlocked: {}, apIn: {}, history: [],
    adjusted: false, loaded: false,
    track: (so.track || []).slice(),
    unlockOrder: (so.unlock || []).slice(),
    ult: (simModel().ults || {})[heroName] || null
  };
}
function simStateFor(h, arch){
  const mode = archModeSlug(arch, arch && arch.label);
  const key = h.hero + '|' + mode;
  if(_simViewKey !== key){ _simViewKey = key; _simStates[key] = simFresh(h.hero, mode, arch); }
  if(!_simStates[key]) _simStates[key] = simFresh(h.hero, mode, arch);
  return _simStates[key];
}
function simLevels(){ return simModel().levels || []; }
function simSouls(st){ const L = simLevels(); return L.length ? L[Math.min(st.boon, L.length - 1)][0] : 0; }
function simNext(st, kind){
  const L = simLevels();
  for(let i = st.boon + 1; i < L.length; i++) if(L[i][1] === kind) return L[i][0];
  return null;
}
function simTierOf(ap){ const T = simModel().tierAt || [1, 3, 8]; return ap >= T[2] ? 3 : ap >= T[1] ? 2 : ap >= T[0] ? 1 : 0; }
function simWhy(st, name){
  const unlockedCount = Object.keys(st.unlocked).length;
  if(!st.unlocked[name]){
    if(st.ult && name === st.ult && unlockedCount < 3)
      return 'Ultimate unlocks last — it takes the 4th unlock (3,800 souls)';
    if(st.tokens <= 0){
      const nx = simNext(st, 'U');
      return nx ? `No unlock available yet — next unlock at ${nx.toLocaleString('en-US')} souls (gather souls below)` : 'No unlocks left';
    }
    return '';
  }
  if((st.apIn[name] || 0) >= 8) return 'Maxed — tiers cost 1 + 2 + 5 AP';
  if(st.apPool <= 0){
    const nx = simNext(st, 'A');
    return nx ? `Not enough AP yet — next AP at ${nx.toLocaleString('en-US')} souls (gather souls below)` : 'No AP left to earn';
  }
  return '';
}
function simApply(st, name){
  if(!st.unlocked[name]){ st.tokens -= 1; st.unlocked[name] = true; st.apIn[name] = 0; st.history.push({ name, kind: 'unlock' }); }
  else { st.apPool -= 1; st.apIn[name] = (st.apIn[name] || 0) + 1; st.history.push({ name, kind: 'ap' }); }
}
function simAdvance(st){
  const L = simLevels();
  if(st.boon >= L.length - 1) return false;
  st.boon += 1;
  if(L[st.boon][1] === 'U') st.tokens += 1; else st.apPool += 1;
  return true;
}
function simFundFor(st, name){
  // Advance level-ups until the resource this spend needs exists (or max).
  let guard = 0;
  while(guard++ < 40){
    const needUnlock = !st.unlocked[name];
    if(needUnlock && st.tokens > 0) return;
    if(!needUnlock && st.apPool > 0) return;
    if(!simAdvance(st)) return;
  }
}
function simLoadRecommended(st, arch){
  const fresh = simFresh(st.hero, st.mode, arch);
  Object.keys(fresh).forEach(k => { st[k] = fresh[k]; });
  const pending = st.track.slice();
  let adjusted = false, guard = 0;
  while(pending.length && guard++ < 500){
    let progressed = false;
    for(let i = 0; i < pending.length; i++){
      const nm = pending[i];
      // Structural legality (the ultimate rule) cannot be fixed by gathering
      // souls — defer that step until the other abilities are unlocked.
      if(!st.unlocked[nm] && st.ult && nm === st.ult && Object.keys(st.unlocked).length < 3) continue;
      simFundFor(st, nm);
      if(simWhy(st, nm) === ''){
        simApply(st, nm);
        if(i !== 0) adjusted = true;
        pending.splice(i, 1); progressed = true; break;
      }
    }
    if(!progressed && !simAdvance(st)) break;
  }
  st.adjusted = adjusted;
  st.loaded = true;
}
function simUndo(st){
  const last = st.history.pop();
  if(!last) return;
  if(last.kind === 'unlock'){ delete st.unlocked[last.name]; delete st.apIn[last.name]; st.tokens += 1; }
  else { st.apIn[last.name] -= 1; st.apPool += 1; }
}
function simPanelHtml(st){
  const L = simLevels();
  const souls = simSouls(st);
  const next = st.boon + 1 < L.length ? L[st.boon + 1] : null;
  const btns = st.unlockOrder.map(name => {
    const isUlt = st.ult && name === st.ult;
    const isOpen = !!st.unlocked[name];
    const ap = st.apIn[name] || 0;
    const tier = simTierOf(ap);
    const T = simModel().tierAt || [1, 3, 8];
    const pips = [0, 1, 2].map(i => {
      const lo = i === 0 ? 0 : T[i - 1], hi = T[i];
      const frac = !isOpen ? 0 : Math.max(0, Math.min(1, (ap - lo) / (hi - lo)));
      return `<span class="sim-pip"><span class="sim-pip-fill" style="width:${Math.round(frac * 100)}%"></span></span>`;
    }).join('');
    let action;
    if(!isOpen) action = 'Unlock';
    else if(ap >= 8) action = 'Tier 3 · MAXED';
    else {
      const need = T[tier];
      action = ap === (tier === 0 ? 0 : T[tier - 1])
        ? `+1 AP → Tier ${tier + 1} (${(simModel().tierCosts || [1, 2, 5])[tier]} AP)`
        : `+1 AP (${ap}/${need} toward Tier ${tier + 1})`;
    }
    const why = simWhy(st, name);
    const status = !isOpen ? 'Locked' : `Tier ${tier} · ${ap} AP`;
    return `<div class="sim-ab">
      <button type="button" class="sim-ab-btn" data-sim-act="ability" data-sim-name="${xEsc(name)}" ${why ? 'disabled' : ''}>
        ${imageOrFallback(abilityIcons[st.hero]?.[name], name + ' ability icon', 'ability-priority-icon', 'ability-priority-fallback', name.charAt(0))}
        <span class="sim-ab-name">${xEsc(name)}${isUlt ? ' <span class="sim-ult">ULT</span>' : ''}</span>
        <span class="sim-ab-status">${status}</span>
        <span class="sim-pips">${pips}</span>
        <span class="sim-ab-action">${action}</span>
      </button>
      ${why ? `<p class="sim-why">${xEsc(why)}</p>` : ''}
    </div>`;
  }).join('');
  const chips = st.track.map((nm, i) =>
    `<span class="sim-step${st.loaded && i < st.history.length ? ' done' : ''}">${i + 1}. ${xEsc(nm)}</span>`).join('');
  return `<div class="sim-head">
      <h4>⚗ Ability progression simulator</h4>
      <span>Test custom leveling orders against the real AP economy — illegal moves are blocked, with the reason</span>
    </div>
    <div class="sim-status">
      <span class="sim-stat"><span class="sim-stat-label">Souls gathered</span><b>${souls.toLocaleString('en-US')}</b></span>
      <span class="sim-stat"><span class="sim-stat-label">Level</span><b>${st.boon + 1} / ${L.length}</b></span>
      <span class="sim-stat"><span class="sim-stat-label">AP available</span><b data-sim-ap>${st.apPool}</b></span>
      <span class="sim-stat"><span class="sim-stat-label">Unlocks available</span><b data-sim-tokens>${st.tokens}</b></span>
      <span class="sim-stat"><span class="sim-stat-label">AP spent</span><b>${st.history.filter(x => x.kind === 'ap').length} / ${(simModel().totalAp || 32)}</b></span>
    </div>
    <div class="sim-abilities">${btns}</div>
    <div class="sim-controls">
      <button type="button" class="sim-btn sim-btn-boon" data-sim-act="boon" ${next ? '' : 'disabled'}>${next ? `Gather souls → ${next[0].toLocaleString('en-US')} (${next[1] === 'U' ? '+1 Unlock' : '+1 AP'})` : 'Max level — every boon earned'}</button>
      <button type="button" class="sim-btn" data-sim-act="load">Load recommended</button>
      <button type="button" class="sim-btn" data-sim-act="undo" ${st.history.length ? '' : 'disabled'}>Undo</button>
      <button type="button" class="sim-btn" data-sim-act="reset">Reset</button>
    </div>
    ${st.adjusted ? '<p class="sim-note">ℹ This build\u2019s written track spends on the ultimate before the game allows it (the ultimate needs the 4th unlock, 3,800 souls). The simulator applied the same 16 spends in the nearest legal order.</p>' : ''}
    <div class="sim-track"><span class="sim-track-label">Recommended 16-step track${st.loaded ? ' — highlighted = applied' : ''}</span><div class="sim-steps">${chips}</div></div>
    <p class="sim-source">AP economy from the game\u2019s boon table (deadlock.wiki/Boons, cross-checked with the assets API): unlocks at 600 / 1,100 / 2,000 / 3,800 gathered souls, +1 AP at every other level-up (32 AP total), tiers cost 1 / 2 / 5 AP.</p>`;
}
function simSectionHtml(h, arch){
  const st = simStateFor(h, arch);
  return `<div class="sim-panel" data-sim-root data-sim-hero="${xEsc(h.hero)}" data-sim-mode="${xEsc(st.mode)}">${simPanelHtml(st)}</div>`;
}
document.addEventListener('click', e => {
  const btn = e.target.closest('[data-sim-act]');
  if(!btn || btn.disabled) return;
  const root = btn.closest('[data-sim-root]');
  if(!root) return;
  const hero = root.dataset.simHero, mode = root.dataset.simMode;
  const ad = archDataFor(hero);
  const arch = ad && ad.archetypes[mode];
  if(!arch) return;
  let st = _simStates[hero + '|' + mode];
  if(!st){ st = simFresh(hero, mode, arch); _simStates[hero + '|' + mode] = st; }
  const act = btn.dataset.simAct;
  if(act === 'ability'){
    const nm = btn.dataset.simName;
    if(simWhy(st, nm) === ''){ simApply(st, nm); st.loaded = false; }
  } else if(act === 'boon'){ simAdvance(st); }
  else if(act === 'undo'){ simUndo(st); st.loaded = false; }
  else if(act === 'reset'){ const f = simFresh(hero, mode, arch); Object.keys(f).forEach(k => { st[k] = f[k]; }); }
  else if(act === 'load'){ simLoadRecommended(st, arch); }
  root.innerHTML = simPanelHtml(st);
});

/* ===== Build Creator + Base64 share links (Prompt 33) =====
   A flat 12-slot sandbox: pick a hero, click shop items in/out, watch the
   soul total / category counts / active count live (>4 actives warns — the
   game has 4 active slots — but is allowed here). "Copy share link" encodes
   {v, h(ero slug), n(ame), i(tems)} as Base64url in ?b=.
   IMPORT IS FAIL-CLOSED (see SCHEMA.md): alphabet + size caps before decode,
   JSON.parse in try/catch, key whitelist (any extra key — __proto__,
   constructor, anything — rejects the whole import), hero checked against
   the exact 44-slug whitelist, items against the exact buyable itemdb name
   set, <=12 and unique, name truncated to 60 chars and only ever rendered
   as text (input value / textContent — never innerHTML). Any failure opens
   the creator empty with a plain notice; nothing is partially applied. */
const CR_MAX_ITEMS = 12, CR_MAX_NAME = 60, CR_MAX_PAYLOAD = 4096, CR_MAX_B64 = 5462;
let crState = null, crCat = 'All', crQuery = '', crDomReady = false;
function crDb(){ return window.ARCHETYPE_ITEMDB || {}; }
function crItemNames(){
  if(!crItemNames._set){
    crItemNames._set = new Set(Object.keys(crDb()).filter(n => [800, 1600, 3200, 6400].includes((crDb()[n] || {}).cost)));
  }
  return crItemNames._set;
}
function crBuyableSorted(){
  return [...crItemNames()].sort((a, b) => (crDb()[a].cost - crDb()[b].cost) || a.localeCompare(b));
}
function crHeroList(){ return (typeof heroes !== 'undefined' && Array.isArray(heroes)) ? heroes : []; }
function crHeroSlugs(){
  if(!crHeroSlugs._set) crHeroSlugs._set = new Set(crHeroList().map(h => toSlug(h.hero)));
  return crHeroSlugs._set;
}
function crHeroName(slug){ const h = crHeroList().find(x => toSlug(x.hero) === slug); return h ? h.hero : ''; }
function crB64UrlEncode(str){
  const bytes = new TextEncoder().encode(str);
  let bin = '';
  bytes.forEach(b => { bin += String.fromCharCode(b); });
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function crParseShare(raw){
  const fail = why => ({ ok: false, why });
  if(typeof raw !== 'string' || !raw) return fail('empty');
  if(raw.length > CR_MAX_B64) return fail('link too long');
  if(!/^[A-Za-z0-9_-]+$/.test(raw)) return fail('not base64url');
  let text;
  try {
    const b64 = raw.replace(/-/g, '+').replace(/_/g, '/');
    const bin = atob(b64 + '='.repeat((4 - b64.length % 4) % 4));
    const bytes = new Uint8Array(bin.length);
    for(let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  } catch(e){ return fail('undecodable'); }
  if(text.length > CR_MAX_PAYLOAD) return fail('payload too large');
  let obj;
  try { obj = JSON.parse(text); } catch(e){ return fail('not json'); }
  if(!obj || typeof obj !== 'object' || Array.isArray(obj)) return fail('not an object');
  if(Object.keys(obj).some(k => !['v', 'h', 'n', 'i'].includes(k))) return fail('unexpected key');
  if(obj.v !== 1) return fail('bad version');
  if(typeof obj.h !== 'string' || !crHeroSlugs().has(obj.h)) return fail('unknown hero');
  if(!Array.isArray(obj.i) || obj.i.length > CR_MAX_ITEMS) return fail('bad items');
  const names = crItemNames(), seen = new Set();
  for(const it of obj.i){
    if(typeof it !== 'string' || !names.has(it)) return fail('unknown item');
    if(seen.has(it)) return fail('duplicate item');
    seen.add(it);
  }
  let nm = '';
  if(obj.n !== undefined){
    if(typeof obj.n !== 'string') return fail('bad name');
    nm = obj.n.slice(0, CR_MAX_NAME);
  }
  return { ok: true, heroSlug: obj.h, name: nm, items: obj.i.slice() };
}
function crShareUrl(){
  const payload = { v: 1, h: crState.heroSlug, n: crState.name, i: crState.items.slice() };
  return location.href.split('?')[0].split('#')[0] + '?b=' + crB64UrlEncode(JSON.stringify(payload));
}
function crNotice(msg, isError){
  const el = document.getElementById('crNotice');
  if(!el) return;
  el.hidden = !msg;
  el.textContent = msg || '';
  el.classList.toggle('cr-notice-error', !!isError);
}
function crStatus(msg){
  const el = document.getElementById('crStatus');
  if(el) el.textContent = msg || '';
}
function crEnsureDom(){
  const layout = document.getElementById('hero-builds');
  if(!layout) return;
  const tools = document.querySelector('.picker-tools');
  if(tools && !document.getElementById('creatorOpenBtn')){
    const b = document.createElement('button');
    b.type = 'button'; b.id = 'creatorOpenBtn'; b.className = 'creator-open-btn';
    b.textContent = '✦ Build Creator';
    b.addEventListener('click', () => crToggle(true));
    tools.insertBefore(b, tools.firstChild);
  }
  if(document.getElementById('buildCreator')){ crDomReady = true; return; }
  const sec = document.createElement('section');
  sec.id = 'buildCreator'; sec.className = 'build-creator'; sec.hidden = true;
  sec.setAttribute('aria-label', 'Build Creator — custom 12-slot builds with share links');
  sec.innerHTML = `
    <div class="cr-head">
      <div><h2>✦ Build Creator</h2><p class="cr-sub">Your own 12-slot loadout for any hero — then share it with one link. Sandbox rules: 12 unique items max; more than 4 actives warns (the game has 4 active slots) but is allowed here.</p></div>
      <button type="button" class="cr-btn" data-cr-act="close">← Back to builds</button>
    </div>
    <p class="cr-notice" id="crNotice" role="status" hidden></p>
    <div class="cr-top">
      <label class="cr-field"><span>Hero</span><select id="crHeroSel"></select></label>
      <label class="cr-field cr-grow"><span>Build name</span><input id="crName" type="text" maxlength="${CR_MAX_NAME}" placeholder="e.g. Lane Bully" autocomplete="off"></label>
    </div>
    <div class="cr-totals" role="region" aria-label="Build totals">
      <span class="tot"><span class="tot-label">Items</span><b id="crCount">0 / 12</b></span>
      <span class="tot"><span class="tot-label">Total souls</span><b id="crSouls">0</b></span>
      <span class="tot"><span class="tot-label">Weapon</span><b id="crCatW">0</b></span>
      <span class="tot"><span class="tot-label">Vitality</span><b id="crCatV">0</b></span>
      <span class="tot"><span class="tot-label">Spirit</span><b id="crCatS">0</b></span>
      <span class="tot"><span class="tot-label">Actives</span><b id="crActives">0</b></span>
      <span class="cr-active-warn" id="crActiveWarn" hidden>⚠ More than 4 actives — in game only 4 active slots (Z/X/C/V) exist.</span>
    </div>
    <div class="cr-slots" id="crSlots" aria-label="Your 12 slots"></div>
    <label class="cr-field"><span>Note (optional — stays on this device, not in the share link)</span><textarea id="crNote" rows="2" maxlength="280" placeholder="e.g. Swap slot 9 for Warp Stone vs Lash"></textarea></label>
    <div class="cr-actions">
      <button type="button" class="cr-btn cr-btn-primary" data-cr-act="share">Copy share link</button>
      <button type="button" class="cr-btn" data-cr-act="clear">Clear build</button>
      <input id="crLink" class="cr-link" type="text" readonly placeholder="Your share link appears here" aria-label="Share link">
    </div>
    <p class="cr-status" id="crStatus" role="status"></p>
    <div class="cr-browser">
      <div class="cr-browser-head">
        <input id="crSearch" type="search" placeholder="Search items" autocomplete="off" aria-label="Search items">
        <div class="cr-cats" role="group" aria-label="Filter by category">
          ${['All', 'Weapon', 'Vitality', 'Spirit'].map(c => `<button type="button" class="cr-cat${c === 'All' ? ' is-active' : ''}" data-cr-cat="${c}">${c}</button>`).join('')}
        </div>
      </div>
      <div class="cr-grid" id="crGrid"></div>
    </div>`;
  layout.parentNode.insertBefore(sec, layout.nextSibling);
  crState = crState || { heroSlug: '', name: '', items: [], note: '' };
  // hero options — built with DOM APIs; names are text, never markup
  const sel = sec.querySelector('#crHeroSel');
  const ph = document.createElement('option');
  ph.value = ''; ph.textContent = 'Choose a hero…';
  sel.appendChild(ph);
  crHeroList().slice().sort((a, b) => a.hero.localeCompare(b.hero)).forEach(h => {
    const o = document.createElement('option');
    o.value = toSlug(h.hero); o.textContent = h.hero;
    sel.appendChild(o);
  });
  sel.addEventListener('change', () => { crState.heroSlug = sel.value; crStatus(''); });
  sec.querySelector('#crName').addEventListener('input', e => { crState.name = e.target.value; });
  sec.querySelector('#crNote').addEventListener('input', e => { crState.note = e.target.value; });
  sec.querySelector('#crSearch').addEventListener('input', e => { crQuery = e.target.value.toLowerCase(); crFilterGrid(); });
  sec.querySelectorAll('[data-cr-cat]').forEach(b => b.addEventListener('click', () => {
    crCat = b.dataset.crCat;
    sec.querySelectorAll('[data-cr-cat]').forEach(x => x.classList.toggle('is-active', x === b));
    crFilterGrid();
  }));
  sec.querySelectorAll('[data-cr-act]').forEach(b => b.addEventListener('click', () => crAction(b.dataset.crAct)));
  crBuildGrid(sec);
  crRenderBuild();
  crDomReady = true;
}
function crBuildGrid(sec){
  const grid = sec.querySelector('#crGrid');
  crBuyableSorted().forEach(name => {
    const rec = crDb()[name] || {};
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'cr-item ' + safeClass(rec.cat || '');
    b.dataset.crItem = name;
    b.setAttribute('data-item-tip', name);
    const icon = document.createElement('span');
    icon.innerHTML = imageOrFallback(itemIcons[name], name + ' icon', 'item-icon', 'item-fallback', name.charAt(0));
    const nm = document.createElement('span'); nm.className = 'cr-item-name'; nm.textContent = name;
    const cost = document.createElement('span'); cost.className = 'cr-item-cost';
    cost.textContent = (rec.cost || 0).toLocaleString('en-US') + ' souls' + (rec.active ? ' · ACTIVE' : '');
    b.append(icon, nm, cost);
    b.addEventListener('click', () => crToggleItem(name));
    grid.appendChild(b);
  });
}
function crFilterGrid(){
  document.querySelectorAll('#crGrid [data-cr-item]').forEach(b => {
    const name = b.dataset.crItem;
    const rec = crDb()[name] || {};
    const okCat = crCat === 'All' || rec.cat === crCat;
    const okQ = !crQuery || name.toLowerCase().includes(crQuery);
    b.style.display = (okCat && okQ) ? '' : 'none';
  });
}
function crToggleItem(name){
  const i = crState.items.indexOf(name);
  if(i !== -1) crState.items.splice(i, 1);
  else {
    if(crState.items.length >= CR_MAX_ITEMS){ crStatus('All 12 slots are full — remove an item first.'); return; }
    crState.items.push(name);
  }
  crStatus('');
  crRenderBuild();
}
function crRenderBuild(){
  if(!crDomReady && !document.getElementById('buildCreator')) return;
  const db = crDb();
  // slots
  const slots = document.getElementById('crSlots');
  if(slots){
    slots.textContent = '';
    for(let i = 0; i < CR_MAX_ITEMS; i++){
      const name = crState.items[i];
      const d = document.createElement('div');
      d.className = 'cr-slot' + (name ? ' filled ' + safeClass((db[name] || {}).cat || '') : '');
      if(name){
        d.setAttribute('data-item-tip', name);
        const num = document.createElement('span'); num.className = 'cr-slot-num'; num.textContent = String(i + 1);
        const nm = document.createElement('span'); nm.className = 'cr-slot-name'; nm.textContent = name;
        const cost = document.createElement('span'); cost.className = 'cr-slot-cost';
        cost.textContent = (db[name].cost || 0).toLocaleString('en-US');
        const rm = document.createElement('button');
        rm.type = 'button'; rm.className = 'cr-slot-x'; rm.textContent = '×';
        rm.setAttribute('aria-label', 'Remove ' + name);
        rm.addEventListener('click', () => crToggleItem(name));
        d.append(num, nm, cost, rm);
      } else {
        const num = document.createElement('span'); num.className = 'cr-slot-num'; num.textContent = String(i + 1);
        const nm = document.createElement('span'); nm.className = 'cr-slot-name cr-empty'; nm.textContent = 'Empty slot';
        d.append(num, nm);
      }
      slots.appendChild(d);
    }
  }
  // totals
  let souls = 0, actives = 0; const cats = { Weapon: 0, Vitality: 0, Spirit: 0 };
  crState.items.forEach(n => { const r = db[n] || {}; souls += r.cost || 0; if(r.active) actives += 1; if(cats[r.cat] !== undefined) cats[r.cat] += 1; });
  const set = (id, v) => { const el = document.getElementById(id); if(el) el.textContent = v; };
  set('crCount', crState.items.length + ' / 12');
  set('crSouls', souls.toLocaleString('en-US'));
  set('crCatW', String(cats.Weapon)); set('crCatV', String(cats.Vitality)); set('crCatS', String(cats.Spirit));
  set('crActives', String(actives));
  const warn = document.getElementById('crActiveWarn');
  if(warn) warn.hidden = actives <= 4;
  // grid states
  document.querySelectorAll('#crGrid [data-cr-item]').forEach(b => {
    const inBuild = crState.items.includes(b.dataset.crItem);
    b.classList.toggle('in-build', inBuild);
    b.disabled = !inBuild && crState.items.length >= CR_MAX_ITEMS;
  });
}
function crAction(act){
  if(act === 'close'){ crToggle(false); return; }
  if(act === 'clear'){
    crState = { heroSlug: '', name: '', items: [], note: '' };
    const sel = document.getElementById('crHeroSel'); if(sel) sel.value = '';
    const nm = document.getElementById('crName'); if(nm) nm.value = '';
    const nt = document.getElementById('crNote'); if(nt) nt.value = '';
    const lk = document.getElementById('crLink'); if(lk) lk.value = '';
    crNotice(''); crStatus('Cleared.');
    crRenderBuild();
    return;
  }
  if(act === 'share'){
    if(!crState.heroSlug){ crStatus('Pick a hero first — a share link needs its hero.'); return; }
    if(!crState.items.length){ crStatus('Add at least one item first.'); return; }
    crState.name = (document.getElementById('crName').value || '').slice(0, CR_MAX_NAME);
    const url = crShareUrl();
    const lk = document.getElementById('crLink');
    if(lk) lk.value = url;
    const done = () => crStatus('Share link ready — anyone opening it gets this exact build in the creator.');
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(url).then(done, () => { if(lk){ lk.select(); } crStatus('Share link is in the box — copy it manually.'); });
    } else { if(lk) lk.select(); crStatus('Share link is in the box — copy it manually.'); }
  }
}
function crToggle(open){
  crEnsureDom();
  const sec = document.getElementById('buildCreator');
  const layout = document.getElementById('hero-builds');
  if(!sec || !layout) return;
  sec.hidden = !open;
  layout.style.display = open ? 'none' : '';
  const btn = document.getElementById('creatorOpenBtn');
  if(btn) btn.textContent = open ? '✦ Build Creator (open)' : '✦ Build Creator';
  if(open) sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function crInitFromUrl(){
  crEnsureDom();
  let raw = null;
  try { raw = new URLSearchParams(location.search).get('b'); } catch(e){ raw = null; }
  if(raw === null) return;
  crToggle(true);
  const r = crParseShare(raw);
  if(r.ok){
    crState = { heroSlug: r.heroSlug, name: r.name, items: r.items.slice(), note: '' };
    const sel = document.getElementById('crHeroSel'); if(sel) sel.value = r.heroSlug;
    const nm = document.getElementById('crName'); if(nm) nm.value = r.name;
    const lk = document.getElementById('crLink'); if(lk) lk.value = crShareUrl();
    crRenderBuild();
    crNotice('Loaded a shared build' + (r.name ? ': ' + r.name : '') + ' for ' + crHeroName(r.heroSlug) + '. Tweak it and copy a fresh link any time.', false);
  } else {
    crState = { heroSlug: '', name: '', items: [], note: '' };
    crRenderBuild();
    crNotice('That share link wasn\u2019t valid, so the creator opened empty. Nothing from it was applied.', true);
  }
}
if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', crInitFromUrl);
else crInitFromUrl();
