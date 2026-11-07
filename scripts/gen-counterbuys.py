#!/usr/bin/env python3
"""Generate the `situational` counter-buy array for every archetype build.

The "in case this, buy that" system: each build gets 5-7 conditional rules
{when, buy, sell, note} produced from the rule table below — NOT hand-written
per build. Rules are tuned to the build's own damage type (weapon / spirit /
vitality; NUKE uses its declared primary_category) plus hero traits
(melee-range / sniper).

Hard guarantees (the validator re-proves all of them):
  * every `buy` is a real buyable item in scripts/itemdb.json — this script
    hard-fails on any name not in the DB, and on any buy missing from
    scripts/itemtooltips.json (the on-site plaque needs it);
  * `buy` is never already in the final 12 — if the natural answer IS owned,
    the rule becomes the "already in this build" variant (sell = null, the
    note carries the buy-it-earlier instruction);
  * `sell` is always a flex item from the final 12: never the build's core
    (top upgrade-target / 6400 anchor), never a NUKE imbue-stack item, never
    a component of the buy item, and never sold twice in the same build;
  * after the swap the final 12 still has <= 4 actives.

Usage: python3 scripts/gen-counterbuys.py [--dry-run]
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMDB = json.load(open(os.path.join(BASE, 'scripts', 'itemdb.json')))
COMPONENTS = json.load(open(os.path.join(BASE, 'scripts', 'components.json')))
TOOLTIPS = json.load(open(os.path.join(BASE, 'scripts', 'itemtooltips.json')))
BUYABLE = {n for n, v in ITEMDB.items()
           if not n.startswith('upgrade_') and v['cost'] in (800, 1600, 3200, 6400)}

MELEE = {'abrams', 'billy', 'calico', 'lash', 'mo-krill', 'shiv', 'yamato'}
SNIPER = {'grey-talon', 'vindicta'}

# ---------------------------------------------------------------------------
# Rule table. Each rule: (when, [(buy, note), ...]) — options are tried in
# order; the first option that is a fresh, legal swap wins. Notes carry the
# item's real mechanics (from the API tooltip data).
# ---------------------------------------------------------------------------

def anti_heal(dtype):
    if dtype == 'weapon':
        opts = [
            ("Toxic Bullets", "Your bullets bleed them for 1.9% max-HP DPS and cut their incoming healing 35% for 4s — a sustain comp can't out-heal a bleed your whole mag re-applies."),
            ("Healbane", "Your spirit damage cuts their incoming healing 35%, and a kill under the effect heals you 275 — cheap anti-heal that pays you back."),
        ]
    elif dtype == 'spirit':
        opts = [
            ("Decay", "-50% incoming healing plus a current-HP bleed for 12s — cast it on their sustain core a breath before your burst lands."),
            ("Healbane", "Your spirit damage cuts their incoming healing 35%, and a kill under the effect heals you 275 — anti-heal that also keeps you alive."),
        ]
    else:  # vitality
        opts = [
            ("Healbane", "Your spirit damage cuts their incoming healing 35%, and a kill under the effect heals you 275 — your attrition finally wins the war."),
            ("Decay", "-50% incoming healing plus a current-HP bleed for 12s — point it at the hero their whole comp heals around."),
        ]
    return ("Lifesteal / heal comp — they out-sustain every trade", opts)


def cc_chain(dtype):
    tail = [
        ("Debuff Reducer", "Passively cuts every debuff's duration by 25% and adds 90 HP — the cheap answer when Unstoppable's slot is too rich; it also builds INTO Unstoppable later."),
    ]
    if dtype == 'spirit':
        opts = [
            ("Ethereal Shift", "4s invulnerable void state on a 37s cooldown dodges the entire chain — and you exit with +20 Spirit Power and +30% spirit resist."),
            ("Unstoppable", "5.5s immune to stun, silence, sleep, root and disarm — pop it as the chain STARTS, not after the second link lands."),
        ] + tail
    elif dtype == 'vitality':
        opts = [
            ("Unstoppable", "5.5s immune to stun, silence, sleep, root and disarm — as the frontline you eat the chain opener; this makes it whiff."),
            ("Reactive Barrier", "A 325 barrier pops automatically the instant you're stunned, chained, immobilized, slept or silenced — insurance you never have to press."),
        ] + tail
    else:
        opts = [
            ("Unstoppable", "5.5s immune to stun, silence, sleep, root and disarm — pop it as the chain STARTS, not after the second link lands."),
        ] + tail
    return ("Heavy CC chain — hooks, stuns and swaps lock you down", opts)


def hp_stack(dtype):
    if dtype == 'spirit':
        opts = [
            ("Tankbuster", "Big ability hits add bonus spirit damage equal to 7.5% of their CURRENT health, and it ignores spirit resist — HP stacking stops working."),
            ("Spirit Burn", "Spirit damage past the threshold explodes and burns: damage over time plus reduced healing while it ticks — tanks burn from the inside."),
        ]
    elif dtype == 'weapon':
        opts = [
            ("Armor Piercer", "55% of your bullets ignore bullet resist entirely and pierce through — resist-stacked tanks take near-full DPS."),
            ("Crippling Headshot", "Headshots strip 16% bullet AND spirit resist for 12s — your whole team hits the tank harder, not just you."),
        ]
    else:
        opts = [
            ("Tankbuster", "Big ability hits add bonus spirit damage equal to 7.5% of their CURRENT health, ignoring spirit resist — your abilities chunk the HP stack."),
            ("Inhibitor", "Your bullets build up a 30% outgoing-damage penalty and 40% healing cut on them — the frontline stops being a threat AND stops being healed."),
        ]
    return ("Tanks stacking HP on the frontline", opts)


def fed_spirit(dtype):
    if dtype == 'spirit':
        opts = [
            ("Enchanter's Emblem", "+18% spirit resist that also feeds YOUR build — +15 Spirit Power and 5% cooldown reduction while you're above 65% HP."),
            ("Spirit Resilience", "+30% spirit resist, and another +15% below half HP — their burst window closes exactly when it matters."),
        ]
    else:
        opts = [
            ("Spirit Resilience", "+30% spirit resist, and another +15% below half HP — their one-shot combo stops one-shotting."),
            ("Counterspell", "Parry their big ability: it negates the damage and effects, heals you 150 and refunds +20 Spirit Power."),
        ]
    return ("Enemy spirit carry is fed — their burst deletes you", opts)


def fed_gun(dtype):
    if dtype == 'spirit':
        opts = [
            ("Metal Skin", "5 full seconds of bullet immunity on a 24s cooldown — their entire engage window does literally nothing."),
            ("Bullet Resilience", "+30% bullet resist, and another +15% below half HP — you survive the mag dump and answer back."),
        ]
    elif dtype == 'weapon':
        opts = [
            ("Bullet Resilience", "+30% bullet resist, and another +15% below half HP — you duel the fed carry on your terms and win the trade."),
            ("Return Fire", "Returns 65% of their bullet damage (and 25% of spirit damage) for 6.5s — a fed carry nearly kills themselves shooting you."),
        ]
    else:
        opts = [
            ("Bullet Resilience", "+30% bullet resist, and another +15% below half HP — the fed carry's mag stops being a death sentence."),
            ("Return Fire", "Returns 65% of their bullet damage for 6.5s — park in their face and let the fed carry shoot themselves."),
            ("Plated Armor", "30% chance to deflect a bullet completely, negating its on-hit effects too — raw probability armor against a firehose."),
        ]
    return ("Enemy gun carry is fed — their bullets delete you", opts)


def own_resist(dtype):
    if dtype == 'spirit':
        return ("Enemy stacking spirit resist — your damage falls off", [
            ("Escalating Exposure", "Every spirit hit strips 8% of their spirit resist and stacks +4.5% spirit amp, up to 12 stacks — resist stacking becomes a countdown timer."),
            ("Spirit Snatch", "Melee hits steal 12% of their spirit resist and 25 Spirit Power for 10s — take their defense and their damage in one swing."),
        ])
    if dtype == 'weapon':
        return ("Enemy stacking bullet resist — your damage falls off", [
            ("Crippling Headshot", "Headshots strip 16% bullet AND spirit resist for 12s — one clip from you opens the target up for everyone."),
            ("Armor Piercer", "55% of your bullets ignore bullet resist entirely and pierce through — their resist purchase simply doesn't apply."),
        ])
    return ("Enemies stacking resists against your mixed damage", [
        ("Inhibitor", "Your bullets build up a 30% outgoing-damage penalty and 40% healing cut — resists don't matter when their damage and healing both shrink."),
        ("Tankbuster", "Bonus spirit damage equal to 7.5% of their current HP on big ability hits, ignoring spirit resist — a second damage type they didn't itemize against."),
    ])


def flavor(slug, atype, dtype):
    if slug in MELEE:
        if dtype == 'spirit':
            opts = [
                ("Mystic Slow", "Your spirit damage slows them 24% for 2s — every ability hit re-applies it, so touching them once means touching them forever."),
                ("Cold Front", "A 48% move-slow blast on a 25s cooldown, point-blank — your engage tool and your anti-kite tool in one slot."),
            ]
        elif dtype == 'vitality':
            opts = [
                ("Cold Front", "A 48% move-slow blast on a 25s cooldown, point-blank — your engage tool and your anti-kite tool in one slot."),
                ("Mystic Slow", "Your spirit damage slows them 24% for 2s — every ability hit re-applies it, so touching them once means touching them forever."),
            ]
        else:
            opts = [
                ("Slowing Bullets", "Your bullets build up to a 24% move slow — once your gun touches them, they don't get away."),
                ("Mystic Slow", "Your spirit damage slows them 24% for 2s — even your ability poke helps you close the last metres."),
            ]
        return ("You're getting kited — you can't stick to targets", opts)
    if slug in SNIPER:
        opts = [
            ("Warp Stone", "11m blink on a 16s cooldown, plus 30% bullet resist for 6s after — re-perch before they can re-engage."),
            ("Metal Skin", "5 full seconds of bullet immunity on a 24s cooldown — dive in, it does nothing, then take your shot."),
        ]
        return ("Dive assassins keep jumping your perch", opts)
    if atype == 'vitality':
        return ("Your team needs a save, not more damage", [
            ("Rescue Beam", "Heals an ally for 20% of max HP and can pull them out of the fight mid-channel — the save your carry remembers."),
            ("Healing Nova", "325 HP to every ally within 18m — flat-out turns one teamfight per minute."),
            ("Divine Barrier", "600 barrier plus a full debuff cleanse for an ally — and the cooldown halves when you cast it on someone else."),
        ])
    return ("Long-range poke you can't reach", [
        ("Warp Stone", "11m blink straight through their sightline on a 16s cooldown — you arrive inside their range instead of dying outside it."),
        ("Majestic Leap", "Leap in with a 200 barrier banked — it's an engage and a disengage in a single slot."),
    ])


def behind(dtype):
    return ("You're behind early — you need cheap souls back", [
        ("Trophy Collector", "Kills and assists stack PERMANENT soul generation (16 souls/min per stack) plus sprint speed — the comeback engine that pays for itself."),
        ("Reactive Barrier", "A 325 barrier pops automatically when you're stunned, chained or slept — 1,600 souls that stop the snowball kill from landing."),
    ])


OWNED_SUFFIX = " Already in this build — buy it a phase earlier instead of waiting for the full build."


def build_rules(slug, atype, arch):
    """Assemble the situational rules for one archetype build."""
    if atype == 'nuke':
        dtype = arch.get('primary_category', 'Spirit').lower()
    else:
        dtype = atype
    p3 = arch['phases']['p3']
    final = list(p3['final_loadout'])
    final_set = set(final)
    final_actives = sum(1 for n in final if ITEMDB[n]['active'])

    # --- protected (never sold): the build's core items + NUKE imbue stack.
    # Centrality = upgrade-target frequency, boosted when the build's own
    # copy names the item (kit_synergy / tagline) — cost alone misleads
    # (Sharpshooter is a 3,200 build-defining core, not a 6,400). Top 2.
    to_count = {}
    for s in p3.get('sell_upgrade', []):
        to_count[s.get('to')] = to_count.get(s.get('to'), 0) + 1
    text_hay = (arch.get('kit_synergy', '') + ' ' + arch.get('tagline', '')).lower()
    p2_names = {it['name'] for it in arch['phases']['p2']['items']}
    scored = []
    for n in final:
        score = (3 * to_count.get(n, 0)
                 + (2 if n.lower() in text_hay else 0)
                 + (2 if ITEMDB[n]['cost'] == 6400 else 0)
                 + (1 if n in p2_names else 0))
        if score > 0:
            scored.append((score, ITEMDB[n]['cost'], -final.index(n), n))
    scored.sort(reverse=True)
    protected = {n for *_k, n in scored[:2]}
    if atype == 'nuke':
        protected |= {n for n in arch.get('imbue_stack', []) if n in final_set}

    candidates = [anti_heal(dtype), cc_chain(dtype), hp_stack(dtype),
                  fed_spirit(dtype), fed_gun(dtype), own_resist(dtype),
                  flavor(slug, atype, dtype), behind(dtype)]

    # Pre-protect every rule's PRIMARY answer that this build already owns:
    # that rule will endorse the item ("already in this build — buy it
    # earlier"), so no other rule may turn around and sell it. Fallbacks are
    # not protected (the pool is only 12 deep), but the owned-fallback path
    # below refuses to endorse an item an earlier rule already sold.
    for _when, _opts in candidates:
        if _opts[0][0] in final_set:
            protected.add(_opts[0][0])
    # Natural flex slots: items that appear ONLY in the final loadout —
    # never bought in p1/p2 and not an upgrade target. Sells prefer these.
    early_names = {it['name'] for it in arch['phases']['p1']['items']} | p2_names
    flex_first = {n for n in final
                  if n not in early_names and to_count.get(n, 0) == 0}

    used_buys, used_sells, rules = set(), set(), []
    dropped = []
    for when, options in candidates:
        if len(rules) >= 7:
            break
        for buy, _ in options:  # hard-fail on any bad name, placed or not
            if buy not in ITEMDB or buy not in BUYABLE:
                raise SystemExit(f"FATAL: rule buy '{buy}' not a buyable itemdb item")
            if buy not in TOOLTIPS:
                raise SystemExit(f"FATAL: rule buy '{buy}' missing tooltip data")
        placed = False
        # The natural answer is already in the build -> say so, don't fall
        # through to a weaker substitute (e.g. Toxic Bullets owned by a gun
        # build must not degrade into a spirit-scaling Healbane swap).
        # Exception: vitality builds, whose finals pre-slot most defensive
        # answers — there the fall-through options are same-class defensive
        # items (Counterspell, Return Fire, Reactive Barrier), so a fresh
        # swap beats a panel full of "already in this build".
        primary_buy, primary_note = options[0]
        if atype != 'vitality' and primary_buy in final_set and primary_buy not in used_buys:
            rules.append({'when': when, 'buy': primary_buy, 'sell': None,
                          'note': primary_note + OWNED_SUFFIX})
            used_buys.add(primary_buy)
            placed = True
        owned_fallback = None
        if not placed:
            for buy, note in options:
                if buy in used_buys:
                    continue
                if buy in final_set:
                    if owned_fallback is None:
                        owned_fallback = (buy, note)
                    continue
                # pick a flex sell
                buy_rec = ITEMDB[buy]
                comps = set(COMPONENTS.get(buy, []))
                pool = [n for n in final
                        if n not in protected and n not in used_sells
                        and n != buy and n not in comps]
                legal = []
                for n in pool:
                    after = final_actives - (1 if ITEMDB[n]['active'] else 0) \
                        + (1 if buy_rec['active'] else 0)
                    if after <= 4:
                        legal.append(n)
                if not legal:
                    continue
                # Prefer selling a passive flex; sell an active only when
                # the <=4-active cap forces it (buy is active at 4 actives).
                # Natural flex slots (final-loadout-only items) go first.
                must_sell_active = buy_rec['active'] and final_actives >= 4

                def sell_key(n, _msa=must_sell_active):
                    if _msa:
                        pref = 0 if ITEMDB[n]['active'] else 1
                    else:
                        pref = 0 if not ITEMDB[n]['active'] else 1
                    return (0 if n in flex_first else 1, pref,
                            ITEMDB[n]['cost'], -final.index(n))

                legal.sort(key=sell_key)
                sell = legal[0]
                rules.append({'when': when, 'buy': buy, 'sell': sell, 'note': note})
                used_buys.add(buy)
                used_sells.add(sell)
                placed = True
                break
        if not placed and owned_fallback is not None:
            buy, note = owned_fallback
            if buy not in used_buys and buy not in used_sells:
                rules.append({'when': when, 'buy': buy, 'sell': None,
                              'note': note + OWNED_SUFFIX})
                used_buys.add(buy)
                placed = True
        if not placed:
            dropped.append(when)
    # Final consistency: no rule may sell an item another rule tells you to buy.
    buys = {r['buy'] for r in rules}
    for r in rules:
        assert r['sell'] is None or r['sell'] not in buys, \
            f"rule sells endorsed buy {r['sell']!r}"
    return rules, dropped


def main():
    dry = '--dry-run' in sys.argv
    import glob
    files = sorted(glob.glob(os.path.join(BASE, 'data', 'archetypes', '*.json')))
    assert len(files) == 44, f'expected 44 hero files, got {len(files)}'
    total, owned_ct, all_dropped = 0, 0, []
    counts = {}
    for fp in files:
        d = json.load(open(fp))
        slug = d['hero']
        for atype, arch in d['archetypes'].items():
            rules, dropped = build_rules(slug, atype, arch)
            assert 5 <= len(rules) <= 7, \
                f'{slug}/{atype}: {len(rules)} rules (need 5-7); dropped={dropped}'
            counts[len(rules)] = counts.get(len(rules), 0) + 1
            total += len(rules)
            owned_ct += sum(1 for r in rules if r['sell'] is None)
            if dropped:
                all_dropped.append((f'{slug}/{atype}', dropped))
            arch['situational'] = rules
        if not dry:
            with open(fp, 'w') as f:
                f.write(json.dumps(d, separators=(',', ':')) + '\n')
    print(f'builds: 176 | rules total: {total} | avg {total/176:.2f}/build')
    print(f'rule-count distribution: {dict(sorted(counts.items()))}')
    print(f'owned-variant rules (buy already in final 12): {owned_ct}')
    if all_dropped:
        print('dropped candidate conditions (no legal swap / cap reached):')
        for b, ds in all_dropped:
            print(f'  {b}: {ds}')
    print('DRY RUN — no files written' if dry else 'WROTE situational into all 44 hero files')


if __name__ == '__main__':
    main()
