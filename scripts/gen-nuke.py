#!/usr/bin/env python3
"""Generate the NUKE (4th) archetype block for every hero.

NUKE = signature-ability supercharge build: an imbue item template that all
targets ONE named ability. Research basis (2026-10-22):
- deadlock.wiki ability pages (base damage + spirit scaling) — PRIMARY source
- scripts/abilityscaling.json (assets API) — cross-check; NOTE: the API file
  misattributes some properties (Warden Flask/Word scalings are swapped vs
  the wiki; Grey Talon's Owl scaling sits under Spirit Snare; Bebop's Hyper
  Beam DPS sits under Exploding Uppercut). Wiki numbers win where they clash.
- Mobalytics / deadlockhandbook / community guides for meta confirmation.

Writes archetypes.nuke into each data/archetypes/<slug>.json. The other
three archetypes are not touched. Idempotent: re-running replaces .nuke.
"""
import json, glob, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMDB = json.load(open(os.path.join(BASE, 'scripts', 'itemdb.json')))
ITEMSTATS = json.load(open(os.path.join(BASE, 'scripts', 'itemstats.json')))
COMPONENTS = json.load(open(os.path.join(BASE, 'scripts', 'components.json')))
ITEM_IDS = json.load(open(os.path.join(BASE, 'scripts', 'items_map.json')))

IMBUE_ALLOWED = {'Mystic Expansion', 'Compress Cooldown', 'Duration Extender',
                 'Quicksilver Reload', 'Ballistic Enchantment', 'Surge of Power',
                 'Echo Shard', 'Mercurial Magnum', 'Mystic Reverb',
                 'Extra Charge', 'Rapid Recharge'}

# ---------------------------------------------------------------- specs ----
# flavor: burst | spam | dot | ult | charge | weapon
# stack: ordered imbue items assigned to the signature ability
STACKS = {
    'burst':  ['Mystic Expansion', 'Surge of Power', 'Compress Cooldown', 'Mystic Reverb', 'Echo Shard'],
    'spam':   ['Mystic Expansion', 'Compress Cooldown', 'Surge of Power', 'Echo Shard', 'Mystic Reverb'],
    'dot':    ['Mystic Expansion', 'Duration Extender', 'Surge of Power', 'Mystic Reverb', 'Echo Shard'],
    'ult':    ['Compress Cooldown', 'Mystic Expansion', 'Surge of Power', 'Mercurial Magnum'],
    'charge': ['Extra Charge', 'Rapid Recharge', 'Compress Cooldown', 'Surge of Power', 'Echo Shard'],
    'weapon': ['Mystic Expansion', 'Ballistic Enchantment', 'Compress Cooldown', 'Mercurial Magnum'],
}

SPECS = {
# slug: sig, scale, why, alts[(name, when)], flavor, tagline, kit, win
'abrams': dict(
    sig='Seismic Impact', scale='100 base damage · ×2.325 per Spirit Power',
    why='The highest spirit scaling in Abrams\' kit by a mile — every point of Spirit Power lands as slam damage, and the leap itself is the engage, so the nuke and the initiation are the same button.',
    alts=[('Shoulder Charge', 'Spam pick: 30 base but ×1.4 scaling on a short cooldown — pick it when fights are constant brawls and the ult is always down.'),
          ('Siphon Life', 'Sustain pick: the drain aura (22 DPS, ×0.6) keeps you alive mid-teamfight when you\'re getting focused after the dive.')],
    flavor='ult',
    tagline='NUKE — Seismic Impact supercharge: one slam, fight over.',
    kit='Every imbue goes on Seismic Impact. Cooldown compression (Superior + Transcendent) plus Refresher means the slam that starts the fight can also end it, and the Spirit Power stack makes each landing a genuine execute threat instead of a wet noodle.',
    win='Win by deleting the first target of every fight with a max-scaled Seismic Impact, then slamming again off Refresher before the enemy resets. If the first slam doesn\'t kill, the build has failed the fight — pick targets at 60% HP or below.'),

'apollo': dict(
    sig='Disengaging Sigil', scale='Delayed Damage 200 base · ×2.6 per Spirit Power',
    why='The single biggest scaling number on any non-ult ability in Apollo\'s kit: the sigil\'s delayed detonation converts Spirit Power at ×2.6. Plant it where the fight has to happen and it out-damages everything else he owns.',
    alts=[('Flawless Advance', 'Reliability pick: 85 base, ×1.3 — a dash-slash that cannot be dodged like a planted trap; pick it against mobile comps that never stand on the sigil.'),
          ('Itani Lo Sahn', 'Duelist pick: Perfect Damage 65 base, ×1.55 when you can land the perfect-release timing consistently.')],
    flavor='burst',
    tagline='NUKE — Disengaging Sigil supercharge: the trap IS the burst.',
    kit='Every imbue goes on Disengaging Sigil. Expansion grows the blast, Surge of Power feeds the ×2.6 scaling, and Echo Shard lets you plant a second sigil before the first detonates — a corridor of ×2.6 explosions no push can walk through.',
    win='Win by pre-planting sigils on objectives and chokes: the enemy either gives up the ground or eats a 700+ delayed detonation. Never chase — zone, detonate, duel the survivors.'),

'baba': dict(
    sig='Granny Long Legs', scale='450 base damage · ×1.6 per Spirit Power',
    why='A 450 base with ×1.6 scaling is the biggest single-cast number in Baba\'s kit — the spider form turns a full spirit stack into a teamfight delete button, and duration imbues stretch every second of it.',
    alts=[('Threadsap', 'Sustain pick: her per-bullet spirit damage (×0.26) plus power steal snowballs long trades — pick it when fights drag and Granny gets focused down.'),
          ("Baba's Brew", 'Brawl pick: the empowered heavy melee (75 base, ×0.6) for close-range chaos when the ult is a liability.')],
    flavor='ult',
    tagline='NUKE — Granny Long Legs supercharge: grandmother goes nuclear.',
    kit='Every imbue goes on Granny Long Legs. Duration and cooldown stacking means more spider uptime per game, and the full Spirit Power engine (Boundless + Exposure) feeds the ×1.6 scaling on a 450 base — this is a raid boss, not a transformation.',
    win='Win teamfights by ulting second: let the enemy spend their CC, then walk the spider through the whole team. If Granny gets chain-stunned out, the build has nothing — timing is the entire skill.'),

'bebop': dict(
    sig='Sticky Bomb', scale='110 base damage · ×1.5 per Spirit Power · stacks +1% per hero hit, +2.5% per kill (permanent)',
    why='Confirmed by the wiki\'s own damage formula — ((Base + Upgrade + SP×1.5) × stack multiplier) — Sticky Bomb is the only ability in the game whose damage grows permanently all match while scaling at ×1.5. Every bomb makes the next one worse. His spirit build imbues the hook; the NUKE imbues the bomb itself.',
    alts=[('Hyper Beam', 'Channel pick: 160 DPS at ×2.51 scaling — the better imbue when the enemy team clumps and you can channel safely behind your frontline.'),
          ('Grapple Arm', 'Playmaker pick: the hook deals 85 base at ×1.5 itself — pick it when your team needs picks more than raw detonation damage.')],
    flavor='spam',
    tagline='NUKE — Sticky Bomb supercharge: every bomb makes the next one worse.',
    kit='Every imbue goes on Sticky Bomb. Rapid Recharge and cooldown compression keep a bomb on someone at all times, Echo Shard double-plants, and Mystic Reverb echoes the detonation — while the permanent stack multiplier compounds quietly until bombs are deleting carries outright.',
    win='Win by accumulation: never stop sticking bombs, even into tanks — stacks are forever. By the third item spike your bombs out-damage most ults on a fraction of the cooldown; close by double-bombing the carry off Echo Shard.',
    damage='bebop'),

'billy': dict(
    sig='Blasted', scale='40 base damage · ×1.9 per Spirit Power',
    why='The highest scaling in Billy\'s kit (×1.9) on a point-blank shotgun blast — low base, but at full Spirit Power the scaling does all the talking, and the cooldown is short enough to blast twice in one brawl.',
    alts=[('Rising Ram', 'Gap-close pick: 120 base, ×0.7 — the ram is how you GET to Blasted range; pick it when you\'re being kited and never reach shotgun distance.'),
          ('Bashdown', 'Combo pick: 35 base, ×1.1 — weave it between Blasted casts in extended melee brawls.')],
    flavor='burst',
    tagline='NUKE — Blasted supercharge: point-blank spirit cannon.',
    kit='Every imbue goes on Blasted. Surge of Power feeds the ×1.9 scaling, cooldown compression keeps the blast cycling, and Echo Shard gives you the second blast that finishes what the first one started.',
    win='Win by deleting whoever you touch first: ram in, Blasted twice, walk out. You are a melee-range burst mage now — if you\'re shooting from mid-range, you\'re playing the wrong build.'),

'calico': dict(
    sig='Gloom Bombs', scale='45 base damage per bomb · ×0.644 per Spirit Power · multiple bombs per cast',
    why='One cast throws several bombs, and every bomb scales — the per-cast total beats Ava\'s single hit while the cooldown is a fraction of an ult\'s. Spam, area denial and burst in one imbue target.',
    alts=[('Ava', 'Ult pick: 150 base, ×0.609 — the single biggest lump Calico can drop; pick it when your team needs one guaranteed delete per fight.'),
          ('Leaping Slash', 'Assassin pick: the slash is your dive and its heal scales ×1.4 with spirit — pick it when you\'re the one being bursted first.')],
    flavor='spam',
    tagline='NUKE — Gloom Bombs supercharge: the whole lane is explosives.',
    kit='Every imbue goes on Gloom Bombs. Expansion widens the carpet, cooldown stacking means the carpet never lifts, and Echo Shard overlaps two casts into a bomb field that deletes anyone crossing it.',
    win='Win by carpeting every choke and objective with scaling bombs, then Leaping Slash onto whoever the carpet softens. Fights in open ground waste the build — drag them into your field.'),

'celeste': dict(
    sig='Dazzling Trick', scale='140 base damage · ×0.6 per Spirit Power',
    why='The biggest base number in her kit on a reliable, spammable cast — Shining Wonder scales similarly (×0.63) off less than half the base. Trick converts a spirit stack into instant, unmissable burst.',
    alts=[('Shining Wonder', 'AoE pick: 55 base, ×0.63 — pick it when fights clump and the wonder\'s bounce hits three targets instead of one.'),
          ('Radiant Daggers', 'Sustain pick: the barrier scales ×0.8 — pick it when you\'re the dive target and dead Celestes cast nothing.')],
    flavor='spam',
    tagline='NUKE — Dazzling Trick supercharge: burst on a hair trigger.',
    kit='Every imbue goes on Dazzling Trick. Cooldown compression turns a 140-base nuke into a rhythm — trick, dagger, trick — while the spirit engine (Boundless + Exposure) keeps each cast climbing all game.',
    win='Win trades by casting Trick on cooldown and never letting the enemy play a fair fight: they\'re either eating scaling burst or giving up the lane. Close fights with Echo Shard double-Tricks.'),

'deadman-danny': dict(
    sig='Chimera Mk1', scale='Explosion Damage 70 base · ×1.5 per Spirit Power',
    why='The Chimera\'s explosion is Danny\'s hardest-scaling spirit hit (×1.5) — his spirit build already cycles it on a 25s loop; the NUKE compresses that loop until the grenade is simply always exploding.',
    alts=[('Close The Deal', 'Finisher pick: 70 base, ×1.0 — pick it when targets keep escaping the Chimera blast at low HP.'),
          ('Strix Salvo', 'Poke pick: the salvo\'s marked damage scales ×1.1 — pick it for long sightline lanes where the Chimera can\'t reach.')],
    flavor='spam',
    tagline='NUKE — Chimera Mk1 supercharge: the grenade never stops.',
    kit='Every imbue goes on Chimera Mk1. Rapid cooldown stacking plus Echo Shard means two explosions per rotation, and the ÷1.5 scaling turns each one into real carry damage instead of a zoning tool.',
    win='Win by tempo: Chimera on cooldown, every cooldown, until the enemy can\'t hold any position for 20 seconds straight. The build loses long silent fights — keep the explosions coming.'),

'drifter': dict(
    sig='Eternal Night', scale='40 base damage · ×1.4 per Spirit Power (plus the darkness itself)',
    why='Drifter is a gun-and-fang carry, but Eternal Night is his one real spirit-scaling damage button (×1.4) — supercharging it means the ult that isolates your victim also opens with a real burst, on a compressed cooldown.',
    alts=[('Rend', 'Bleed pick: the rend stacks are his sustained damage — pick it when fights are long brawls where the ult burst doesn\'t close.'),
          ("Stalker's Mark", 'Hunt pick: the mark is the pick tool — pick it when your team plays for single-target deletion over teamfight burst.')],
    flavor='ult',
    tagline='NUKE — Eternal Night supercharge: the dark hits back.',
    kit='Every imbue goes on Eternal Night. Cooldown compression plus Refresher gives you darkness on demand, and the spirit stack makes the opening burst punish anyone caught alone in it.',
    win='Win by picking the map apart: ult the isolated carry, burst them inside their own blindness, reset with Refresher for the next pick. In fair 5v5s this build is average — never take one.'),

'dynamo': dict(
    sig='Kinetic Pulse', scale='115 base damage · ×1.55 per Spirit Power',
    why='The classic Dynamo nuke: 115 base at ×1.55 scaling on a knock-up that sets up itself. Singularity controls fights, but Pulse is where his spirit damage actually lives — and it charges, so the charge items print value.',
    alts=[('Singularity', 'Teamfight pick: the black hole wins objectives by existing — pick it when your team has the AoE to capitalize and Pulse alone can\'t carry the fight.'),
          ('Rejuvenating Aurora', 'Support pick: when you\'re playing second support and your team needs the heal engine more than your burst.')],
    flavor='charge',
    tagline='NUKE — Kinetic Pulse supercharge: pulse, pulse, black hole.',
    kit='Every imbue goes on Kinetic Pulse. Extra Charge + Rapid Recharge bank a second pulse, Surge of Power feeds the ×1.55 scaling, and Echo Shard turns one knock-up into a juggle combo.',
    win='Win by chaining pulses: knock-up, echo pulse, Singularity on the landing. A team that spends three seconds airborne takes the whole rotation — that\'s the fight.'),

'graves': dict(
    sig='Jar of Dead', scale='90 base damage · ×1.6 per Spirit Power',
    why='The hardest-scaling cast in her kit (×1.6) and the one that defines her lanes — the jar bursts, walls and zones at once. Grasping Hands hits hard too, but the jar is the repeatable nuke.',
    alts=[('Grasping Hands', 'Burst pick: 115 base, ×1.27 — pick it when you need the damage NOW rather than on the jar\'s terms.'),
          ('Borrowed Decree', 'Army pick: the deadhead summons scale with boons — pick it for push/siege games where the army, not the burst, wins.')],
    flavor='burst',
    tagline='NUKE — Jar of Dead supercharge: artillery from beyond.',
    kit='Every imbue goes on Jar of Dead. Expansion grows the zone, Surge feeds the ×1.6, and Echo Shard double-jars a choke so nobody crosses without eating both detonations.',
    win='Win by making ground uninhabitable: jar every choke and objective on cooldown and let the summons mop up. If fights happen in the open, drag them to your jars.'),

'grey-talon': dict(
    sig='Charged Shot', scale='80 base damage · ×1.0 per Spirit Power · +54 damage at Tier 2 · improved scaling at Tier 3',
    why='The signature sniper shot — piercing, holdable forever, and the only ability in his kit that turns a spirit build into a one-shot threat (deadlock.wiki + API agree: 80 base, ×1.0 scaling, +54 at Tier 2, better scaling at Tier 3).',
    alts=[('Guided Owl', 'Snowball pick: 230 base, ×0.937, and +8 permanent Spirit Power per kill — pick it when you\'re fed; the owl literally funds future Charged Shots.'),
          ('Spirit Snare', 'Safety pick: the curse trap (silence + disarm) — pick it into dive comps where landing one more shot matters more than a bigger one.')],
    flavor='burst',
    tagline='NUKE — Charged Shot supercharge: one arrow, deleted.',
    kit='Every imbue goes on Charged Shot. Expansion and Surge of Power feed the shot, cooldown compression keeps a charged arrow ready for every peek, and Echo Shard + Mystic Reverb mean the shot they dodge is followed by the one they don\'t.',
    win='Win from range nobody else can play at: hold angles, delete the first hero who peeks at 60%, and let Guided Owl stacks compound your Spirit Power until shots are executes. Never brawl — you are artillery.',
    damage='talon', final='talon'),

'haze': dict(
    sig='Sleep Dagger', scale='No spirit damage scaling — this is a COOLDOWN build, not a damage nuke',
    why='Honest pick: Haze has no spirit-scaling damage ability worth imbuing — Fixation is a gun passive and Bullet Dance is her weapon. So the NUKE supercharges her pick tool instead: Sleep Dagger, with charge and cooldown items, so a slept target is a dead target every single rotation.',
    alts=[('Bullet Dance', 'Ult-uptime pick: cooldown items also mean more Bullet Dances per game — pick it when teamfights, not picks, decide your matches.'),
          ('Smoke Bomb', 'Escape pick: more smoke uptime when you\'re the one getting hunted and daggers never get to start a fight.')],
    flavor='charge', cooldown_build=True,
    tagline='NUKE (cooldown) — Sleep Dagger supercharge: sleep, delete, repeat.',
    kit='Every imbue goes on Sleep Dagger — but read the label: this is a cooldown build, not a damage nuke. Extra Charge + Rapid Recharge bank daggers, Transcendent Cooldown keeps them flowing, and the spirit stack exists to make the dagger rotation permanent. Your gun still does the killing; the dagger decides who dies.',
    win='Win by pick volume: a slept carry every rotation means your team always fights 5v4. If your daggers aren\'t starting fights, swap to the Weapon build — this one prints picks, not damage.'),

'holliday': dict(
    sig='Crackshot', scale='55 base damage · ×1.116 per Spirit Power (scale_function_tech_damage)',
    why='Crackshot\'s empowered shot is the only Holliday ability whose damage scales with spirit at better than ×1.1 — imbuing it turns every Crackshot proc into a genuine chunk instead of a gun footnote.',
    alts=[('Spirit Lasso', 'Playmaker pick: 80 base, ×0.93, and it drags people into your team — pick it when picks matter more than poke.'),
          ('Powder Keg', 'Combo pick: the keg chain (40 impact + burn) — pick it when you\'re landing Bounce Pad stomp combos reliably.')],
    flavor='spam',
    tagline='NUKE — Crackshot supercharge: every proc is a chunk.',
    kit='Every imbue goes on Crackshot. Cooldown compression means the empowered shot is always up, Surge of Power feeds the scaling, and Echo Shard resets the rotation for back-to-back procs.',
    win='Win the poke war permanently: Crackshot on cooldown from max range until someone is low enough to Lasso. You lose extended brawls — keep every fight at proc distance.'),

'infernus': dict(
    sig='Napalm', scale='125 base damage · ×0.975 per Spirit Power',
    why='Napalm carries the biggest base damage in his kit at near-×1 scaling, and it\'s spammable — his spirit build already treats it as artillery. The NUKE makes the artillery the whole personality.',
    alts=[('Concussive Combustion', 'Ult pick: the detonation wins teamfights outright — pick it when fights are decided by one big 5v5 per ult cycle.'),
          ('Flame Dash', 'Mobility pick: 40 base, ×0.6 — pick it when you\'re being kited and napalm never lands at range.')],
    flavor='spam',
    tagline='NUKE — Napalm supercharge: the map is on fire, permanently.',
    kit='Every imbue goes on Napalm. Expansion grows the burn zone, cooldown stacking means it never lifts, and Echo Shard double-coats a choke so crossing it costs a third of a health bar.',
    win='Win by zoning entire objectives with scaling fire, then detonating Combustion on whoever the flames herd together. Open-field fights waste you — burn the ground they need.'),

'ivy': dict(
    sig='Air Drop', scale='Bomb damage 115 base · ×0.7 per Spirit Power',
    why='The Air Drop bomb is Ivy\'s biggest single spirit hit and it arrives with a stun — imbuing it means the delivery service drops a real nuke, and cooldown stacking means deliveries never stop.',
    alts=[('Entangling Thorns', 'DoT pick: 40 DPS, ×0.55 — pick it when fights are long and the bomb keeps getting dodged.'),
          ('Stone Form', 'Engage pick: 75 base, ×0.6 plus the slam CC — pick it when you\'re the team\'s initiator and the bomb is just the follow-up.')],
    flavor='ult',
    tagline='NUKE — Air Drop supercharge: special delivery.',
    kit='Every imbue goes on Air Drop. Cooldown compression plus Refresher doubles the delivery schedule, Expansion grows the blast, and the spirit stack makes each drop a genuine kill threat instead of a taxi ride with confetti.',
    win='Win by dropping on the backline every fight: bomb, stun, delete, fly out. If the enemy saves CC for your landing, bait it with Stone Form first — then deliver.'),

'kelvin': dict(
    sig='Frost Grenade', scale='Explosion spirit scaling ×0.8 (assets API; base value not published there)',
    why='The grenade is Kelvin\'s burst — the beam sustains and the dome defends, but the grenade is the cast that chunks. Imbuing it with cooldown and expansion turns his poke into a fragmentation problem the enemy can\'t lane against.',
    alts=[('Arctic Beam', 'Sustain pick: the beam\'s damage (60 base, ×0.6) and healing both scale — pick it for long brawl games where grenades alone don\'t close.'),
          ('Frozen Shelter', 'Objective pick: the dome wins urn and mid-boss fights by existing — pick it when your team plays around shelter timings.')],
    flavor='spam',
    tagline='NUKE — Frost Grenade supercharge: fragmentation weather.',
    kit='Every imbue goes on Frost Grenade. Expansion widens the freeze, cooldown stacking keeps grenades raining, and Echo Shard double-taps a frozen target before the ice breaks.',
    win='Win the poke war with grenade volume, then dome the objective your grenades cleared. You don\'t win fair brawls — you win the 30 seconds of chip damage before them.'),

'lady-geist': dict(
    sig='Malice', scale='90 base damage · ×1.22 per Spirit Power',
    why='Malice is the reliable scaling engine: 90 base at ×1.22, thrown in shards, on a short cooldown. Essence Bomb\'s published base is just the uncharged tick (23) — Malice is the number you can actually build a nuke on.',
    alts=[('Essence Bomb', 'Charged-bomb pick: a fully charged bomb is her biggest single pop — pick it when you can play slow poke and charge safely.'),
          ('Life Drain', 'Sustain pick: the drain keeps you casting — pick it when you\'re being bursted before Malice stacks matter.')],
    flavor='spam',
    tagline='NUKE — Malice supercharge: shards all the way down.',
    kit='Every imbue goes on Malice. Cooldown compression turns shards into a stream, Surge feeds the ×1.22, and Echo Shard double-throws the volley that finishes a trade.',
    win='Win by shard volume: Malice on cooldown, every cooldown, trading health you can drain back. The build starves in long silent fights — force trades constantly.'),

'lash': dict(
    sig='Flog', scale='105 base damage · ×0.975 per Spirit Power',
    why='Flog is Lash\'s repeatable spirit hit: 105 base at essentially ×1 scaling on a whip crack that also sets up everything else. Death Slam is the highlight reel, but Flog is the nuke you cast ten times a fight.',
    alts=[('Ground Strike', 'Dive pick: 65 base, ×0.85, and it scales with fall height — pick it when you\'re playing the full dive pattern and striking from altitude.'),
          ('Death Slam', 'Highlight pick: the slam itself has no published damage scaling (the damage is the follow-up) — pick it when your team needs the grab, not the number.')],
    flavor='spam',
    tagline='NUKE — Flog supercharge: the whip cracks harder.',
    kit='Every imbue goes on Flog. Cooldown stacking means the whip never rests, Surge feeds the near-×1 scaling, and Echo Shard gives you the second crack that catches the dash-out.',
    win='Win by whip tempo: Flog, grapple, Flog, slam. Short violent rotations where the second Flog lands before they reset. Long poke wars starve this build — stay in their face.'),
}

SPECS.update({
'mcginnis': dict(
    sig='Heavy Barrage', scale='60 base damage per barrage · ×0.731 per Spirit Power · multi-rocket',
    why='Barrage fires a stream of rockets and every rocket scales — the per-cast total is the biggest spirit number McGinnis owns, and cooldown stacking means the rocket weather never clears.',
    alts=[('Mini Turret', 'Siege pick: turret DPS scales ×0.42 forever once placed — pick it for push/objective games where barrages get wasted on waves.'),
          ('Spectral Wall', 'Zone pick: the wall decides where fights happen — pick it when your team plays around wall timings.')],
    flavor='spam',
    tagline='NUKE — Heavy Barrage supercharge: rocket weather, permanent.',
    kit='Every imbue goes on Heavy Barrage. Cooldown compression plus Echo Shard overlaps barrages into a continuous rocket stream, and the spirit engine feeds every rocket in it.',
    win='Win by sieging from behind your wall: barrage on cooldown until their frontline melts, then walk the turrets up. Open-field fights waste the barrage — fight from your fortress.'),

'mina': dict(
    sig='Nox Nostra', scale='Bonus Damage 45 base · ×1.85 per Spirit Power',
    why='The bat swarm\'s bonus damage scales at ×1.85 — the highest rate in Mina\'s kit — turning her ult-window into a genuine delete instead of a light show. The spirit build treats Nox as a finisher; the NUKE builds the whole kit around feeding it.',
    alts=[('Love Bites', 'Assassin pick: the bite is her dive-and-delete tool — pick it when games are pick-based and Nox windows are rare.'),
          ('Sanguine Retreat', 'Survival pick: 60 base, ×1.0 on the retreat hit — pick it when you\'re the focus target and living matters more than bursting.')],
    flavor='burst',
    tagline='NUKE — Nox Nostra supercharge: the swarm eats carries.',
    kit='Every imbue goes on Nox Nostra. Surge of Power feeds the ×1.85 bonus scaling, cooldown compression shortens the wait between swarms, and Echo Shard extends the burst pattern your dives set up.',
    win='Win in windows: farm quietly, then every Nox window deletes a carry. Outside the window you\'re fragile — the build is a timer, play on it.'),

'mirage': dict(
    sig="Djinn's Mark", scale='65 base damage · ×0.3 per Spirit Power — honest note: Mirage\'s scaling is weak everywhere; this is a mark-SPAM build',
    why='Straight talk: Mirage is a gun carry and his spirit scaling is poor (best is the mark\'s ×0.3). The NUKE doesn\'t pretend otherwise — it supercharges mark uptime with cooldown and charge items so detonations, slows and Traveler plays chain nonstop. The gun still kills; the mark decides when.',
    alts=[('Traveler', 'Roam pick: the teleport is his real superpower — pick it when the game is about map plays, not mark damage.'),
          ('Fire Scarabs', 'Shred pick: the scarabs eat health over time — pick it into tank stacks where marks pop too slowly.')],
    flavor='charge', cooldown_build=True,
    tagline='NUKE (cooldown) — Djinn\'s Mark supercharge: marks forever.',
    kit='Every imbue goes on Djinn\'s Mark — a cooldown build wearing a nuke\'s coat, and the label says so. Charge and cooldown items keep a mark on every target, every fight, while your gun does gun things to marked targets.',
    win='Win by never letting a mark lapse: marked targets take your gunfire worse and die to detonation chains. If you wanted a damage nuke, play the Weapon build — this one prints uptime.'),

'mo-krill': dict(
    sig='Scorn', scale='75 DPS · ×1.488 per Spirit Power',
    why='Scorn\'s shout drains at the highest scaling rate in their kit (×1.488 per second of channel) — point-blank spirit damage that also fuels the combo. Burrow initiates, but Scorn is where the spirit damage lives.',
    alts=[('Burrow', 'Engage pick: 50 base, ×0.75 plus the knock-up — pick it when you\'re the primary initiator and Scorn uptime is secondary.'),
          ('Sand Blast', 'Poke pick: 40 DPS, ×0.6 at range — pick it when you can\'t stay in Scorn range without dying.')],
    flavor='dot',
    tagline='NUKE — Scorn supercharge: screamed to death.',
    kit='Every imbue goes on Scorn. Duration stacking stretches every shout, cooldown compression shortens the breath between them, and the spirit engine feeds the ×1.488 drain until standing near you is a death sentence.',
    win='Win by standing on people: burrow in, shout the full duration, combo the runner. Every second they spend in Scorn range is scaling damage they can\'t trade with.'),

'nurse-harrow': dict(
    sig='Lurking Terrors', scale='60 DPS · ×0.3 per Spirit Power — honest note: Harrow\'s damage scaling is the weakest in this guide; this NUKE leans duration/cooldown',
    why='Harrow is a healer first — her damage scaling is genuinely poor everywhere (best DPS property: Terrors at ×0.3). The NUKE supercharges her ult anyway: duration and cooldown stacking keep the terror pressure near-permanent, and the build is honest that you\'re buying uptime and fear, not a 1,000-damage bomb.',
    alts=[('Leech Therapy', 'Sustain-engine pick: the leeches are her real kit — pick it when your team needs the drain/heal engine more than ult pressure.'),
          ('Healing Needles', 'Support pick: heal output scales ×0.2 per shot — pick it when you\'re playing dedicated healer and damage is a rumor.')],
    flavor='dot', cooldown_build=True,
    tagline='NUKE (uptime) — Lurking Terrors supercharge: fear, forever.',
    kit='Every imbue goes on Lurking Terrors. Duration Extender stretches each cast, cooldown stacking overlaps the next, and the spirit stack quietly lifts both the terrors and everything else she casts.',
    win='Win by attrition: permanent terror coverage while your leeches drain and your needles heal. You will not top the damage chart — you will make the enemy team play scared for 40 minutes.'),

'paige': dict(
    sig='Captivating Read', scale='90 base damage · ×1.3 per Spirit Power',
    why='The Read is Paige\'s nuke: 90 base at ×1.3 scaling with a stun attached. Rallying Charge hits a bigger base (125) but scales at ×1.0 — at full spirit the Read wins outright, and it stops the target from leaving.',
    alts=[('Rallying Charge', 'Engage pick: 125 base, ×1.0, and its heal scales ×1.6 — pick it when you\'re the team\'s initiator and the charge IS the play.'),
          ('Plot Armor', 'Sustain pick: the armor\'s damage (60, ×1.3) ticks while you live — pick it in long brawl games.')],
    flavor='burst',
    tagline='NUKE — Captivating Read supercharge: storytime is lethal.',
    kit='Every imbue goes on Captivating Read. Surge feeds the ×1.3, Expansion widens the story\'s reach, and Echo Shard gives you the second chapter — read, stun, read again.',
    win='Win by reading the carry every fight: stun-lock into your team\'s damage, then charge the cleanup. Missed reads waste the build — hold it for targets that matter.'),

'paradox': dict(
    sig='Paradoxical Swap', scale='Swap Damage 150 base · ×1.1 per Spirit Power',
    why='The swap itself deals the biggest spirit-scaling hit in her kit (150 base, ×1.1) — and it relocates the victim into your team while it lands. Kinetic Carbine is her gun-scaled poke; the spirit NUKE lives on the swap. Cooldown stacking means the swap is always a threat.',
    alts=[('Kinetic Carbine', 'Poke pick: the carbine is weapon-scaled, so imbues don\'t feed it directly — pick it when you\'re playing the poke pattern and swaps are rare. (Honestly: that\'s the Weapon build.)'),
          ('Pulse Grenade', 'Waveclear pick: 35 base, ×0.3 — pick it when you need lane pressure more than playmaking.')],
    flavor='spam',
    tagline='NUKE — Paradoxical Swap supercharge: you\'re coming with me.',
    kit='Every imbue goes on Paradoxical Swap. Cooldown compression (Superior + Transcendent) plus Echo Shard turns the swap from a once-a-fight trick into a constant relocation threat, and the spirit stack makes the landing damage a real chunk.',
    win='Win by swapping the carry every single rotation — the threat alone zones their backline off every fight. A Paradox who never swaps is just a worse gun; swap on cooldown.'),

'pocket': dict(
    sig='Affliction', scale='60 base damage · ×1.3 per Spirit Power · damage-over-time curse (total far exceeds the base over its duration)',
    why='Affliction is a DoT, and that\'s exactly why it\'s the nuke: ×1.3 scaling applied over a long duration, stretched further by Duration Extender, on a target that can\'t cleanse your whole rotation. The satchel pops; Affliction executes.',
    alts=[("Enchanter's Satchel", 'Burst pick: 65 base, ×1.1 instantly — pick it when fights are too short for the curse to tick out.'),
          ('Barrage', 'Spam pick: 32 per projectile, ×0.465 across a fan of projectiles — pick it for waveclear and close-range melts.')],
    flavor='dot',
    tagline='NUKE — Affliction supercharge: cursed, cloaked, gone.',
    kit='Every imbue goes on Affliction. Duration stacking stretches the curse, Surge feeds the ×1.3, and Echo Shard double-curses — by the time they notice the ticks, the math is already done.',
    win='Win by cursing the carry and leaving: cloak in, Affliction + satchel, cloak out, let the ticks finish. Standing around to watch wastes the build — trust the curse.'),

'rat-king': dict(
    sig='Scrap Grenade', scale='200 base damage · ×1.2 per WEAPON damage (EBaseWeaponDamageIncrease) — the one weapon-flavored NUKE in the guide',
    why='The exception that proves the rule: Scrap Grenade doesn\'t scale with Spirit Power at all — it scales with Weapon Damage (×1.2). So this NUKE stacks weapon damage and leads its 4,800 spike with Weapon items, with Ballistic Enchantment as the imbue core. Same template, different fuel — and the build says so on the label.',
    alts=[('Rat Swarm', 'Army pick: the swarm\'s detonation (70 base) also scales with weapon damage — pick it when the rats, not the grenade, are your win condition.'),
          ('Royal Pestments', 'Shred pick: the pestments chew armor in long fights — pick it into tank stacks.')],
    flavor='weapon', weapon_build=True,
    tagline='NUKE — Scrap Grenade supercharge: weapon-fed explosives.',
    kit='The imbue core is Ballistic Enchantment on Scrap Grenade — the one NUKE in the guide fed by Weapon Damage instead of Spirit Power, because that\'s what the grenade actually scales with (×1.2 per weapon damage). Everything else is weapon-damage stacking and cooldown so grenades keep coming.',
    win='Win by grenade tempo: a 200-base explosive every rotation, fed by a full weapon stack. Your rats screen, your gun pressures, the grenade deletes. If you wanted spirit scaling, you picked the wrong king.'),

'rem': dict(
    sig='Pillow Toss', scale='Wake Damage 120 base · ×1.6 per Spirit Power',
    why='The pillow is a sleep that ends in the hardest-scaling hit in Rem\'s kit: waking damage at 120 base, ×1.6. Tag Along scales the same rate off a smaller base (75) — the pillow is the nuke, the nap is just the delivery.',
    alts=[('Tag Along', 'Mobility pick: 75 base, ×1.6 on the dash — pick it when you\'re playing pocket-roam and the pillow keeps missing sleep windows.'),
          ('Naptime', 'Control pick: the sleep itself wins fights — pick it when your team converts sleeps better than you convert wake damage.')],
    flavor='burst',
    tagline='NUKE — Pillow Toss supercharge: nap time is over.',
    kit='Every imbue goes on Pillow Toss. Surge feeds the ×1.6 wake hit, Expansion grows the pillow\'s threat zone, and Echo Shard tosses a second pillow before the first nap ends.',
    win='Win by sleeping the carry and detonating the wake on your terms: pillow, position, wake-nuke. A pillow tossed on cooldown at randoms is just bedding — aim the nap.'),

'seven': dict(
    sig='Lightning Ball', scale='35 base damage · ×0.79 per Spirit Power · very low cooldown, huge area',
    why='Per cast it looks small — that\'s the trap. Lightning Ball is nearly spammable, covers a huge area, and every cast scales: at full cooldown compression the DPS out-nukes everything else Seven owns. His spirit build pokes with it; the NUKE makes it a permanent storm front.',
    alts=[('Static Charge', 'Zone pick: 95 DPS in the charge zone — pick it when fights stand still and the zone ticks at full value.'),
          ('Storm Cloud', 'Ult pick: the cloud is his teamfight ceiling — pick it when games hinge on one big 5v5 per ult.')],
    flavor='spam',
    tagline='NUKE — Lightning Ball supercharge: the storm never breaks.',
    kit='Every imbue goes on Lightning Ball. Cooldown compression plus Echo Shard means two balls in the air at once, and the spirit engine makes each one sting more than the last build\'s.',
    win='Win by ball volume: poke lanes nobody can stand in, then Storm Cloud the retreat. You win the war of a thousand cuts — never coin-flip a single cast.'),

'shiv': dict(
    sig='Slice and Dice', scale='75 base damage · ×1.2 per Spirit Power',
    why='The dash-slash is Shiv\'s one clean spirit-scaling burst (75 base, ×1.2) — and it\'s the ability his whole engage pattern already revolves around. Imbue it and every dive opens with a real nuke instead of a love tap.',
    alts=[('Serrated Knives', 'Bleed pick: the knives stack bleed for execute thresholds — pick it in long brawl games where dice windows are rare.'),
          ('Killing Blow', 'Execute pick: the ult finishes what rage starts — pick it when your team needs guaranteed closes on tanks.')],
    flavor='spam',
    tagline='NUKE — Slice and Dice supercharge: in, out, bleeding.',
    kit='Every imbue goes on Slice and Dice. Cooldown compression keeps the dash cycling, Surge feeds the ×1.2, and Echo Shard gives you the second slash — in, out, and back in.',
    win='Win by dive tempo: slash in on cooldown, bleed them, execute the panic. You\'re a burst assassin now — long fair trades are for the Vitality build.'),

'silver': dict(
    sig='Entangling Bola', scale='Bonus Damage 25 base · ×2.0 per Spirit Power',
    why='The bola\'s bonus damage carries a ×2.0 scaling rate — the highest in Silver\'s kit — and the bola already starts every one of his plays. Supercharge it and the setup IS the damage.',
    alts=[('Boot Kick', 'Burst pick: 40 base, ×1.6 — a reliable kick when the bola keeps getting dodged or cleansed.'),
          ('Lycan Curse', 'Transform pick: the curse window is his DPS ceiling — pick it when teamfights, not picks, decide the game.')],
    flavor='burst',
    tagline='NUKE — Entangling Bola supercharge: tied up and blown up.',
    kit='Every imbue goes on Entangling Bola. Surge feeds the ×2.0 bonus damage, cooldown stacking keeps a bola flying every rotation, and Echo Shard double-bolas the carry who cleansed the first.',
    win='Win by bola-ing the carry every fight and converting the root into the bonus-damage burst. A missed bola is a wasted rotation — hold it for real targets.'),

'sinclair': dict(
    sig='Vexing Bolt', scale='Max Damage 120 base · ×1.86 per Spirit Power (at max range/charge)',
    why='A ×1.86 scaling rate on a 120-base bolt is elite — Vexing Bolt at full distance out-scales most ultimates. Sinclair\'s spirit build spams it; the NUKE feeds it until one bolt is a fight-starter.',
    alts=[('Rabbit Hex', 'Amp pick: the hex amplifies ALL damage the target takes — pick it when your team\'s damage matters more than yours.'),
          ('Audience Participation', 'Chaos pick: stolen-ability games are unpredictable — pick it when the enemy ult is better than anything you own.')],
    flavor='spam',
    tagline='NUKE — Vexing Bolt supercharge: long-distance deletion.',
    kit='Every imbue goes on Vexing Bolt. Cooldown compression keeps bolts flying, Surge feeds the ×1.86, and Echo Shard double-taps the target who stepped up to the first one.',
    win='Win the range war: max-distance bolts on cooldown until someone is in execute range of your team. Close-range brawls waste the scaling — stay at bolt distance.'),

'solomon': dict(
    sig='Setup Bishop', scale='Impact Damage 70 base · ×2.0 per Spirit Power',
    why='×2.0 scaling on the bishop\'s impact — the best rate in Solomon\'s kit — on the piece that starts his whole chess pattern. Set the bishop, and the opening move already hits like a finisher.',
    alts=[('Develop Queen', 'Ult pick: 120 base, ×1.4 on the queen — pick it when the game needs the full-board play rather than opening burst.'),
          ('Rook Battery', 'Zone pick: 50 base, ×1.3 from the rook line — pick it for siege games where the battery fires forever.')],
    flavor='burst',
    tagline='NUKE — Setup Bishop supercharge: the opening move kills.',
    kit='Every imbue goes on Setup Bishop. Surge feeds the ×2.0 impact, Expansion widens the diagonal, and Echo Shard sets a second bishop before the first one\'s threat expires.',
    win='Win by setting the board early and punishing every step onto it: bishop impact starts fights your pieces finish. Playing reactively wastes the setup — dictate the board.'),

'the-doorman': dict(
    sig='Doorway', scale='125 base damage · ×1.5 per Spirit Power',
    why='The Doorway\'s slam is the biggest scaling hit in his kit (125 base, ×1.5) — the doors aren\'t just service entrances, they\'re the nuke. Call Bell starts the show; the Doorway ends it.',
    alts=[('Call Bell', 'Spam pick: 55 explosion base, ×1.2 on a short cooldown — pick it when fights are constant and doorways are too slow.'),
          ('Luggage Cart', 'Chaos pick: 60 base, ×0.75 and a runaway cart — pick it for corridor maps where the cart always connects.')],
    flavor='burst',
    tagline='NUKE — Doorway supercharge: mind the doors. Or don\'t.',
    kit='Every imbue goes on Doorway. Expansion grows the doorway\'s threat, Surge feeds the ×1.5 slam, and Echo Shard opens a second door before the first one closes.',
    win='Win by delivering enemies through doors they didn\'t choose: bell to gather, doorway to delete. Fights in doorless open ground halve the build — host every fight at a door.'),

'venator': dict(
    sig='Hex-Lined Snap Trap', scale='80 base damage · ×2.2 per Spirit Power (tech damage scaling)',
    why='A ×2.2 spirit scaling rate hiding in a trap — the best rate in Venator\'s kit, better than his ult\'s weapon-based scaling. Plant the trap where fights must happen and it deletes whoever steps up.',
    alts=[('Ira Domini', 'Finisher pick: 120 base but weapon-scaled (×1.5 per weapon damage) — pick it when you\'re playing execute duty and the imbue value is really the cooldown.'),
          ('Consecrating Grenade', 'Zone pick: the grenade sanctifies ground — pick it for objective games where the trap gets played around.')],
    flavor='burst',
    tagline='NUKE — Hex-Lined Snap Trap supercharge: watch your step.',
    kit='Every imbue goes on Hex-Lined Snap Trap. Expansion widens the snap zone, Surge feeds the ×2.2, and Echo Shard plants a second trap to cover the escape route from the first.',
    win='Win by trapping the map: objectives, chokes and retreat paths all snap for scaling damage. If the enemy won\'t walk anywhere, you\'ve already won the space — take the objective.'),

'victor': dict(
    sig='Pain Battery', scale='100 base damage · ×1.6 per Spirit Power',
    why='The Battery is Victor\'s engine: 100 base at ×1.6, charged by the damage he soaks and discharged on demand. Shocking Reanimation scales harder (×2.0) but only fires when he dies — the Battery is the nuke he actually casts.',
    alts=[('Shocking Reanimation', 'Revive-bomb pick: 200 base, ×2.0 when he comes back — pick it when you\'re playing deliberate death-bait in teamfights.'),
          ('Aura of Suffering', 'Aura pick: the DPS aura ticks forever in brawls — pick it when fights never end and discharges are rare.')],
    flavor='spam',
    tagline='NUKE — Pain Battery supercharge: hurt him and he\'ll return it.',
    kit='Every imbue goes on Pain Battery. Cooldown compression keeps discharges cycling, Surge feeds the ×1.6, and Echo Shard double-discharges on the carry who thought one battery was the whole threat.',
    win='Win by soaking and discharging: take the poke, bank it, discharge it into their carry at ×1.6. Dying with a full battery is the only real mistake.'),

'vindicta': dict(
    sig='Stake', scale='Max Bonus Damage 90 base · ×2.3 per Spirit Power',
    why='Honest framing: Vindicta\'s rifle does the killing — but Stake\'s bonus damage scales at ×2.3, the best rate in her kit, and a staked target is a dead target. The NUKE turns her setup tool into a scaling execute enabler, with cooldown stacking so the stake is always out.',
    alts=[('Assassinate', 'Execute pick: the shot is weapon-scaled in game (API lists only its 40-base impact) — pick it when you\'re playing pure sniper and the imbue value is cooldown for more executes.'),
          ('Crow Familiar', 'Harass pick: the crow\'s per-bullet spirit damage (×0.18) adds up across a lane — pick it for long lane-domination games.')],
    flavor='charge', cooldown_build=True,
    tagline='NUKE — Stake supercharge: pinned, then deleted.',
    kit='Every imbue goes on Stake. Charge and cooldown items keep a stake ready every rotation, Surge feeds the ×2.3 bonus damage, and the rifle converts every pin into a kill — the nuke is the setup, the shot is the signature.',
    win='Win by staking priority targets on cooldown and executing the pin before help arrives. You\'re still a sniper — this build just makes sure the sniper always has a target nailed down.'),

'violet': dict(
    sig='Flow State', scale='Max Damage 100 base · ×1.8 per Spirit Power',
    why='Flow State at full charge scales ×1.8 off a 100 base — the hardest-hitting repeatable cast in Violet\'s kit, on the ability her whole ink game already flows through. The ult zones; Flow State deletes.',
    alts=[('Abstract Landscape', 'Ult pick: 100 base, ×1.4 across a wall of terrain — pick it when the fight is about space, not single targets.'),
          ('Still Life', 'Trap pick: 60 base, ×1.4 — pick it when enemies keep diving you and the portrait punishes the dive.')],
    flavor='burst',
    tagline='NUKE — Flow State supercharge: art in motion, lethal.',
    kit='Every imbue goes on Flow State. Surge feeds the ×1.8, Expansion stretches the canvas, and Echo Shard double-casts so the second flow hits before the first one\'s paint dries.',
    win='Win by flowing through fights at full charge: every max Flow State is a carry deleted or a fight conceded. Half-charged casts waste the scaling — patience is damage.'),

'viscous': dict(
    sig='Goo Ball', scale='110 base damage · ×1.0 per Spirit Power',
    why='The ball is Viscous\' identity and his biggest spirit-scaling hit (110 base, ×1.0) — and it\'s a duration ability, so duration imbues stretch the damage window while cooldown stacking keeps him rolling.',
    alts=[('Splatter', 'Spam pick: 55 base, ×0.7 on a short cooldown — pick it when the ball keeps getting interrupted and you need reliable poke.'),
          ('Puddle Punch', 'Brawl pick: the punch is melee-scaled — pick it in permanent melee brawls where rolling is impossible.')],
    flavor='ult',
    tagline='NUKE — Goo Ball supercharge: the ball does not stop.',
    kit='Every imbue goes on Goo Ball. Duration stacking stretches every roll, cooldown compression plus Refresher means a second ball per fight, and the spirit stack makes each bounce a real hit instead of a nuisance.',
    win='Win by rolling through the whole fight, twice: ball in, bounce the backline, Refresher, ball again. If you\'re standing still in goo form, you\'re a puddle — keep moving.'),

'vyper': dict(
    sig='Screwjab Dagger', scale='Max Venom Damage 140 base · ×2.79 per Spirit Power (at max venom stacks)',
    why='×2.79 — the highest scaling rate in Vyper\'s kit and one of the highest in the game — on the venom that defines her. At max stacks the dagger out-scales ultimates; the NUKE exists to get her there and keep her there.',
    alts=[('Slither', 'Petrify pick: 180 base, ×2.046 on the petrify — pick it when the petrify setup is landing and you want the guaranteed burst.'),
          ('Lethal Venom', 'Stack pick: the venom stacks themselves (50 base, ×0.8) — pick it in long trades where daggers get cleansed.')],
    flavor='spam',
    tagline='NUKE — Screwjab Dagger supercharge: venom at ×2.79.',
    kit='Every imbue goes on Screwjab Dagger. Cooldown compression keeps stacks from ever falling off, Surge feeds the ×2.79 max-venom hit, and Echo Shard double-jabs the target who cleansed.',
    win='Win by never letting venom lapse: at max stacks every dagger is an ult-grade hit. The build is a ramp — play patient early, homicidal late.'),

'warden': dict(
    sig='Binding Word', scale='110 base damage · ×2.44 per Spirit Power (deadlock.wiki — the assets API lists these scalings swapped with Alchemical Flask)',
    why='The numbers decide it: Binding Word\'s ×2.44 scaling is the highest in Warden\'s kit by a factor of four over the flask (60 base, ×0.63 — wiki values; the API\'s scaling file has the two abilities\' numbers swapped, the wiki and Mobalytics agree with each other). It also immobilizes for 1.75s and silences at Tier 3 — the nuke CCs its own target.',
    alts=[('Alchemical Flask', 'Spam pick: 60 base, ×0.63, but it also cuts enemy weapon damage 25% and slows — pick it when you\'re playing lane bully and words are too slow.'),
          ('Last Stand', 'Teamfight pick: the channel pulses spirit damage with lifesteal (≈70 DPS, ×1.3 by the API\'s figures) — pick it when fights are stationary brawls around you.')],
    flavor='burst',
    tagline='NUKE — Binding Word supercharge: speak, and they break.',
    kit='Every imbue goes on Binding Word. Surge of Power feeds the ×2.44 scaling, cooldown compression (Superior + Transcendent) drops the word’s cooldown toward spam territory, and Echo Shard lets you curse a second hero before the first one’s chains break. Mystic Burst in the opener is deliberate: it procs on the word’s cast, taxing every curse further.',
    win='Win by cursing the carry on cooldown: a max-scaled Binding Word chunks, roots and (at T3) silences — your team executes inside the root. Flask to slow their escape first; never word a target with a cleanse off cooldown unless yours is the bait.',
    damage='warden'),

'wraith': dict(
    sig='Telekinesis', scale='100 base damage · ×1.0 per Spirit Power (the slam) — the lift is the point; read the note',
    why='Wraith is a gun carry: Card Trick\'s spirit damage is a rounding error (×0.045 per bullet). Her one real spirit-scaling hit is Telekinesis — 100 base, ×1.0 on the slam — and the lift itself is the best pick tool in her kit. So this NUKE supercharges the lift: cooldown stacking and Refresher for double lifts, with enough spirit that the slam genuinely hurts. It is a playmaker build, not a damage nuke — her gun still does the killing.',
    alts=[('Project Mind', 'Roam pick: the teleport repositions fights — pick it when the game is about map plays and lifts are getting cleansed.'),
          ('Card Trick', 'Spam pick: honest note — the trick\'s damage is gun-driven; imbue value here is only cooldown for more trick cycles in farm games.')],
    flavor='ult', cooldown_build=True, final='wraith',
    tagline='NUKE (playmaker) — Telekinesis supercharge: two lifts per fight.',
    kit='Every imbue goes on Telekinesis. Cooldown compression plus Refresher means two lifts a fight, Echo Shard covers your other casts while it\'s down, and the spirit stack makes the slam a real 250+ hit instead of a formality. The lift decides fights; this build makes sure it\'s always ready.',
    win='Win by lifting the carry every fight — twice. First lift forces the cleanse, second lift is the kill. If lifts aren\'t starting your fights, the Weapon build is right there.'),

'yamato': dict(
    sig='Shadow Transformation', scale='Full Charge Damage 145 base · ×1.85 per Spirit Power',
    why='The transformed slash scales at ×1.85 off a 145 base — Yamato\'s hardest spirit number by far. Her other slashes are melee/weapon-flavored; the transformation is the nuke, and cooldown stacking means she\'s never out of it for long.',
    alts=[('Crimson Slash', 'Sustain pick: the slash\'s heal scales ×1.036 with spirit — pick it when you\'re being bursted out of transform windows.'),
          ('Flying Slash', 'Mobility pick: melee-scaled damage — pick it when the game is about chase, not transformation burst.')],
    flavor='ult',
    tagline='NUKE — Shadow Transformation supercharge: the shadow falls.',
    kit='Every imbue goes on Shadow Transformation. Cooldown compression plus Refresher doubles transformation uptime per fight, and the spirit engine feeds the ×1.85 full-charge slash until it deletes backlines.',
    win='Win inside the transformation: charge the slash fully, delete a priority target, Refresher for the second window. Outside the transform you\'re farming — inside it, you\'re the win condition.'),

})

# ------------------------------------------------------------ templates ----
P1 = {
    'spirit': ['Extra Spirit', 'Mystic Burst', 'Mystic Expansion', 'Extra Charge', 'Mystic Vulnerability'],
    'dot':    ['Extra Spirit', 'Mystic Burst', 'Mystic Expansion', 'Extra Charge', 'Duration Extender'],
    'charge': ['Extra Charge', 'Extra Spirit', 'Mystic Burst', 'Mystic Expansion', 'Compress Cooldown'],
    'weapon': ['Close Quarters', 'Headshot Booster', 'Long Range', 'Swift Striker'],
}
P2 = {
    'spirit': ['Improved Spirit', 'Compress Cooldown', 'Quicksilver Reload', 'Surge of Power', 'Superior Cooldown', 'Duration Extender', 'Rapid Recharge', 'Tankbuster'],
    'dot':    ['Improved Spirit', 'Compress Cooldown', 'Quicksilver Reload', 'Surge of Power', 'Superior Cooldown', 'Superior Duration', 'Mystic Vulnerability', 'Tankbuster'],
    'charge': ['Improved Spirit', 'Quicksilver Reload', 'Surge of Power', 'Superior Cooldown', 'Rapid Recharge', 'Mystic Vulnerability', 'Tankbuster', 'Duration Extender'],
    'talon':  ['Improved Spirit', 'Compress Cooldown', 'Quicksilver Reload', 'Surge of Power', 'Superior Cooldown', 'Spirit Lifesteal', 'Rapid Recharge', 'Tankbuster'],
    'weapon': ['Rapid Rounds', 'High-Velocity Rounds', 'Mystic Expansion', 'Point Blank', 'Intensifying Magazine', 'Compress Cooldown', 'Quicksilver Reload', 'Tesla Bullets'],
}
FINALS = {
    'burst':  ['Boundless Spirit', 'Escalating Exposure', 'Mystic Reverb', 'Echo Shard', 'Surge of Power', 'Tankbuster', 'Superior Cooldown', 'Mercurial Magnum', "Diviner's Kevlar", 'Transcendent Cooldown', "Enchanter's Emblem", 'Counterspell'],
    'spam':   ['Boundless Spirit', 'Escalating Exposure', 'Mystic Reverb', 'Echo Shard', 'Surge of Power', 'Rapid Recharge', 'Superior Cooldown', 'Transcendent Cooldown', 'Mercurial Magnum', "Diviner's Kevlar", "Enchanter's Emblem", 'Tankbuster'],
    'dot':    ['Boundless Spirit', 'Escalating Exposure', 'Mystic Reverb', 'Echo Shard', 'Surge of Power', 'Superior Duration', 'Greater Expansion', 'Superior Cooldown', 'Mercurial Magnum', "Diviner's Kevlar", "Enchanter's Emblem", 'Tankbuster'],
    'ult':    ['Boundless Spirit', 'Escalating Exposure', 'Mystic Reverb', 'Refresher', 'Surge of Power', 'Transcendent Cooldown', 'Superior Cooldown', 'Mercurial Magnum', "Diviner's Kevlar", 'Echo Shard', "Enchanter's Emblem", 'Tankbuster'],
    'charge': ['Boundless Spirit', 'Escalating Exposure', 'Rapid Recharge', 'Surge of Power', 'Superior Cooldown', 'Transcendent Cooldown', 'Echo Shard', 'Mercurial Magnum', "Diviner's Kevlar", 'Mystic Reverb', "Enchanter's Emblem", 'Tankbuster'],
    'talon':  ['Boundless Spirit', 'Escalating Exposure', 'Mystic Reverb', 'Echo Shard', 'Surge of Power', 'Tankbuster', 'Superior Cooldown', 'Mercurial Magnum', "Diviner's Kevlar", 'Spiritual Overflow', 'Counterspell', "Enchanter's Emblem"],
    'wraith': ['Boundless Spirit', 'Escalating Exposure', 'Mystic Reverb', 'Refresher', 'Surge of Power', 'Superior Cooldown', 'Transcendent Cooldown', 'Mercurial Magnum', "Diviner's Kevlar", 'Ethereal Shift', "Enchanter's Emblem", 'Tankbuster'],
    'weapon': ['Ballistic Enchantment', 'Glass Cannon', 'Sharpshooter', 'Point Blank', 'Headhunter', 'Armor Piercer', 'Mercurial Magnum', 'Superior Cooldown', 'Transcendent Cooldown', 'Mystic Expansion', 'Long Range', 'Swift Striker'],
}
P3_NAMES = {'burst': 'Late-Game Detonation', 'spam': 'Late-Game Perma-Cycle', 'dot': 'Late-Game Meltdown',
            'ult': 'Late-Game Double Ult', 'charge': 'Late-Game Charge Engine', 'weapon': 'Late-Game Grenade Works'}

WHY = {
    'Extra Spirit': 'Cheapest Spirit Power in the shop — every point feeds {sig} directly.',
    'Mystic Burst': 'Bonus spirit damage procs on {sig} casts — a free tax on every hit. Component into Tankbuster.',
    'Mystic Expansion': 'Imbue {sig}: bigger radius/area so the nuke connects more often.',
    'Extra Charge': 'Imbue {sig}: bank an extra charge for back-to-back casts. Component into Rapid Recharge.',
    'Mystic Vulnerability': 'Spirit resist shred on your hits — {sig} lands harder. Component into Escalating Exposure.',
    'Duration Extender': 'Imbue {sig}: longer effect duration, more value per cast. Component into Superior Duration.',
    'Compress Cooldown': 'Imbue {sig}: −18% cooldown — the spam engine starts here. Component into Superior Cooldown.',
    'Close Quarters': '+20% weapon damage up close — grenade range is shotgun range. Component into Point Blank.',
    'Headshot Booster': 'Cheap weapon damage; component into Headhunter.',
    'Long Range': 'Weapon damage at range while the grenade is in the air; component into Sharpshooter.',
    'Swift Striker': 'Fire rate between grenades; component (Rapid Rounds) is bought mid.',
    'Improved Spirit': 'The big early Spirit Power chunk; component into Boundless Spirit.',
    'Quicksilver Reload': 'Fire rate and reload for the gaps between {sig} casts; component into Mercurial Magnum.',
    'Surge of Power': 'Imbue {sig}: +28 Spirit Power scoped to your signature — the core of the whole build.',
    'Superior Cooldown': 'Upgraded from Compress Cooldown — {sig} cycles permanently.',
    'Rapid Recharge': 'Upgraded from Extra Charge — faster charge regen and +14 Spirit Power for {sig}.',
    'Tankbuster': 'Upgraded from Mystic Burst — max-HP spirit shred so {sig} hurts frontlines too.',
    'Superior Duration': 'Upgraded from Duration Extender — {sig} lasts even longer.',
    'Spirit Lifesteal': 'Sustain off your own spirit damage; component into Spiritual Overflow.',
    'Rapid Rounds': 'Fire rate filler; component into Swift Striker.',
    'High-Velocity Rounds': 'Weapon damage; component into Sharpshooter and Armor Piercer.',
    'Point Blank': 'Upgraded from Close Quarters — point-blank weapon damage for grenade range.',
    'Intensifying Magazine': 'Sustained-fire ramp while grenades cycle.',
    'Slowing Bullets': 'Your shots slow — running from the next grenade gets harder.',
    'Mystic Shot': 'Spirit procs on the gun between grenade casts.',
    'Tesla Bullets': 'Chain lightning on the gun — wave pressure between nukes.',
}
SELL_PAIRS = [
    ('Extra Spirit', 'Surge of Power', 'Component — Surge scopes the power onto {sig}.'),
    ('Mystic Burst', 'Tankbuster', 'Upgraded into max-HP shred.'),
    ('Mystic Vulnerability', 'Escalating Exposure', 'Upgraded into the stacking spirit amp.'),
    ('Improved Spirit', 'Boundless Spirit', 'Upgraded into the T4 spirit engine.'),
    ('Compress Cooldown', 'Superior Cooldown', 'Upgraded — the cooldown engine matures.'),
    ('Superior Cooldown', 'Transcendent Cooldown', 'Upgraded — peak cooldown compression.'),
    ('Extra Charge', 'Rapid Recharge', 'Upgraded — charges return faster.'),
    ('Duration Extender', 'Superior Duration', 'Upgraded — longer effects.'),
    ('Mystic Expansion', 'Greater Expansion', 'Upgraded — even bigger {sig}.'),
    ('Quicksilver Reload', 'Mercurial Magnum', 'Upgraded — the fire-rate imbue capstone.'),
    ('Mystic Expansion', 'Ballistic Enchantment', 'Component — the weapon imbue grows out of it.'),
    ('Spirit Lifesteal', 'Spiritual Overflow', 'Component — overflow feeds the shot cycle.'),
    ('Close Quarters', 'Point Blank', 'Upgraded — point-blank cannon.'),
    ('Headshot Booster', 'Headhunter', 'Upgraded — headshot engine.'),
    ('Long Range', 'Sharpshooter', 'Upgraded — range cannon.'),
]
SWAP_POOL = [
    dict(vs='Baba (spirit drain)', out='Mystic Reverb', into='Dispel Magic', why='Cleanse Threadsap stacks before she steals the Spirit Power this whole build runs on.'),
    dict(vs='Heavy spirit burst (Seven, Violet)', out='Echo Shard', into='Counterspell', why='Auto-block their opener — a double cast is worthless if you die in the first one.'),
    dict(vs='Hard dive (Lash, Danny)', out='Mercurial Magnum', into='Metal Skin', why='Survive the dive window; your damage is back-loaded, theirs is not.'),
    dict(vs='Healing cores (Ivy, Dynamo)', out='Tankbuster', into='Decay', why='Healing cut beats max-HP shred when they out-sustain the burst.'),
    dict(vs='Kiting carries (Vindicta, Grey Talon)', out="Diviner's Kevlar", into='Knockdown', why='Ground the kite — a rooted carry eats the full rotation.'),
    dict(vs='Long brawls', out='Transcendent Cooldown', into='Leech', why='Double lifesteal out-trades the last slice of cooldown in fights that will not end.'),
    dict(vs='CC chains', out="Enchanter's Emblem", into='Unstoppable', why='Debuff immunity for the one rotation that has to land.'),
]
SWAP_POOL_WEAPON = [
    dict(vs='Armor stacking', out='Long Range', into='Toxic Bullets', why='Bleed ticks ignore the armor math your grenade cannot.'),
    dict(vs='Hard dive (Lash, Danny)', out='Glass Cannon', into='Metal Skin', why='You are the grenade — dying first throws the whole build away.'),
    dict(vs='Healing cores (Ivy, Dynamo)', out='Headhunter', into='Healbane', why='Cut the healing your burst has to chew through.'),
    dict(vs='Baba (spirit drain)', out='Mystic Expansion', into='Dispel Magic', why='Cleanse the drain — even a weapon build hates losing stats.'),
]

def sp_totals(final):
    flat = pct = 0.0
    for nm in final:
        s = ITEMSTATS.get(nm) or {}
        flat += s.get('sp', 0) or 0
        pct += s.get('spPct', 0) or 0
    eff = round(flat * (1 + pct / 100)) if pct else int(flat)
    return int(flat), int(pct), eff

def damage_math(kind, final):
    flat, pct, eff = sp_totals(final)
    src = f"final loadout Spirit Power from items: {flat} flat" + (f" + {pct}% (Boundless Spirit) ≈ {eff} effective" if pct else f" = {eff}")
    if kind == 'talon':
        d10 = 134 + eff
        d23 = 134 + round(2.3 * eff)
        return (f"Charged Shot, maxed: (80 base + 54 Tier-2 upgrade = 134) + ×1.0 scaling × {eff} SP "
                f"({src}) = ~{d10} damage per shot on the API/wiki published scaling. Tier 3 improves the "
                f"scaling further — an older patch note pegged the T3 bonus at +1.3 (×2.3 total), which would "
                f"make it ~{d23}. Surge of Power's Spirit Power is already inside the {eff}. "
                f"Verdict on the '~1,000 damage per shot' claim: not from the item build alone. Four figures "
                f"needs a fed game stacked on top — Guided Owl's +8 permanent Spirit Power per kill, level "
                f"boons, and Mystic Reverb's echo on the same shot. The honest build-only number is ~{d10}–{d23}.")
    if kind == 'bebop':
        b0 = 195 + round(1.5 * eff)
        b15 = round(b0 * 1.15)
        return (f"Sticky Bomb, maxed: (110 base + 85 Tier-2 upgrade = 195) + ×1.5 scaling × {eff} SP "
                f"({src}) = ~{b0} per bomb at zero stacks. The permanent stack multiplier is the real story: "
                f"at a modest +15% mid-game stack that is ~{b15} per bomb, Echo Shard plants two of them "
                f"(~{b15 * 2} burst on one area), and Mystic Reverb's echo plus Escalating Exposure's amp "
                f"push real fights past that. Damage uses Spirit Power at cast time — cast fat, not early.")
    if kind == 'warden':
        w = 110 + round(2.44 * eff)
        return (f"Binding Word: 110 base + ×2.44 scaling × {eff} Spirit Power ({src}) = ~{w} damage on a "
                f"target that also eats a 1.75s immobilize (silence at Tier 3) — before Mystic Burst's proc, "
                f"Escalating Exposure's stacking amp, and the +20% bullet damage Warden deals to trapped "
                f"targets at Tier 1. For comparison, Alchemical Flask at the same Spirit Power: "
                f"60 + ×0.63 × {eff} ≈ {60 + round(0.63 * eff)}. That gap is why the word is the nuke.")
    return None

def build_block(slug, spec, hero_data, ability_names):
    flavor = spec['flavor']
    sig = spec['sig']
    primary = 'Weapon' if flavor == 'weapon' else 'Spirit'
    p1key = 'weapon' if flavor == 'weapon' else ('dot' if flavor == 'dot' else 'charge' if flavor == 'charge' else 'spirit')
    p2key = 'weapon' if flavor == 'weapon' else p1key
    if flavor in ('burst', 'spam', 'ult'): p2key = 'spirit'
    if flavor == 'dot': p2key = 'dot'
    if flavor == 'charge': p2key = 'charge'
    if spec.get('final') == 'talon': p2key = 'talon'
    fkey = spec.get('final') or flavor
    final = FINALS[fkey]
    p1_items = [{'name': n, 'why': WHY[n].format(sig=sig)} for n in P1[p1key]]
    p2_items = [{'name': n, 'why': WHY[n].format(sig=sig)} for n in P2[p2key]]
    early = {i['name'] for i in p1_items + p2_items}
    sell = [{'from': f, 'to': t, 'why': w.format(sig=sig)}
            for f, t, w in SELL_PAIRS if f in early and t in final]
    # skill order
    U = hero_data['archetypes']['spirit']['skill_order']['unlock']
    alts = [a for a, _ in spec['alts']]
    rest = [a for a in ability_names if a not in [sig] + alts]
    P = [sig] + alts + rest
    if sig == U[-1]:  # ult signature: unlocked last, maxed first after unlock
        B = [x for x in P if x != sig]
        track = [B[0], B[1], B[0], B[2], B[0], sig, sig, sig, B[0], sig, B[1], B[1], B[1], B[2], B[2], sig]
        unlock = [B[0], B[1], B[2], sig]
    else:
        track = [P[0], P[1], P[0], P[2], P[0], P[3], P[0], P[0], P[1], P[3], P[1], P[1], P[1], P[2], P[2], P[3]]
        unlock = [P[0], P[1], P[2], P[3]]
    skill_order = {
        'unlock': unlock,
        'max_priority': {
            '1': f"{sig} — the NUKE target; max first, no debate",
            '2': f"{P[1]} — max second; it covers what {sig} can't",
            '5': f"{P[2]} — max last of the three; the build is already online",
        },
        'track': track,
    }
    pool = SWAP_POOL_WEAPON if flavor == 'weapon' else SWAP_POOL
    swaps = []
    for s in pool:
        if s['out'] in final and s['into'] not in final:
            swaps.append({'vs': s['vs'], 'out': s['out'], 'in': s['into'], 'why': s['why']})
        if len(swaps) == 4: break
    assert len(swaps) >= 3, f'{slug}: only {len(swaps)} valid swaps'
    spike = (f"4800 Weapon — Ballistic Enchantment online; the grenade is the build"
             if flavor == 'weapon' else
             f"4800 Spirit — the {sig} engine comes online")
    block = {
        'label': '✦ NUKE',
        'is_meta': False,
        'primary_category': primary,
        'tagline': spec['tagline'],
        'kit_synergy': spec['kit'],
        'best_ability': {
            'name': sig,
            'scaling': spec['scale'],
            'why': spec['why'],
            'alternates': [{'name': n, 'when': w} for n, w in spec['alts']],
        },
        'imbue_stack': spec.get('stack') or STACKS[flavor],
        'skill_order': skill_order,
        'phases': {
            'p1': {'name': 'Laning & 4.8k Spike Rush', 'spike': spike, 'items': p1_items},
            'p2': {'name': 'Mid-Game Power Spike', 'items': p2_items},
            'p3': {'name': P3_NAMES[flavor], 'final_loadout': final,
                   'sell_upgrade': sell, 'win_condition': spec['win']},
        },
        'counters': {'swaps': swaps},
    }
    if spec.get('damage'):
        block['damage_math'] = damage_math(spec['damage'], final)
    if spec.get('cooldown_build'):
        block['cooldown_build'] = True
    return block

def audit(slug, block, ability_names):
    errs = []
    db = ITEMDB
    prim = block['primary_category']
    s = sum(db[i['name']]['cost'] for i in block['phases']['p1']['items'] if db[i['name']]['cat'] == prim)
    if s != 4800: errs.append(f'p1 {prim} spend {s} != 4800')
    lo = block['phases']['p3']['final_loadout']
    if len(lo) != 12 or len(set(lo)) != 12: errs.append('final not 12 unique')
    if sum(1 for n in lo if db[n]['active']) > 4: errs.append('>4 actives')
    early = {i['name'] for ph in ('p1', 'p2') for i in block['phases'][ph]['items']}
    for n in lo:
        for c in COMPONENTS.get(n, []):
            if c not in early and c not in lo: errs.append(f'component {c} for {n} never bought')
    allitems = [i['name'] for ph in ('p1', 'p2') for i in block['phases'][ph]['items']] + lo
    for n in allitems:
        if n not in db: errs.append(f'{n} not in itemdb')
        if n not in ITEM_IDS: errs.append(f'{n} not in items_map')
    for n in block['imbue_stack']:
        if n not in IMBUE_ALLOWED: errs.append(f'imbue stack item {n} not in allowed list')
    if block['best_ability']['name'] not in ability_names: errs.append('sig not a real ability')
    for a in block['best_ability']['alternates']:
        if a['name'] not in ability_names: errs.append(f"alt {a['name']} not a real ability")
    if len(block['skill_order']['track']) != 16: errs.append('track != 16')
    for n in block['skill_order']['track'] + block['skill_order']['unlock']:
        if n not in ability_names: errs.append(f'track/unlock name {n} not a real ability')
    return errs

def main():
    names = json.load(open(os.path.join(BASE, 'scripts', 'ability-names.json')))
    files = sorted(glob.glob(os.path.join(BASE, 'data', 'archetypes', '*.json')))
    assert len(files) == 44, len(files)
    all_errs = []
    for fp in files:
        slug = os.path.basename(fp)[:-5]
        d = json.load(open(fp))
        spec = SPECS.get(slug)
        if not spec:
            all_errs.append(f'{slug}: NO SPEC'); continue
        block = build_block(slug, spec, d, names[d['name']])
        errs = audit(slug, block, names[d['name']])
        if errs:
            all_errs += [f'{slug}: {e}' for e in errs]; continue
        d['archetypes']['nuke'] = block
        with open(fp, 'w') as f:
            f.write(json.dumps(d, separators=(',', ':'), sort_keys=True))
        print(f'{slug}: OK  sig={spec["sig"]}  flavor={spec["flavor"]}')
    if all_errs:
        print('\nFAILURES:'); [print(' ', e) for e in all_errs]; sys.exit(1)
    print('\nAll 44 NUKE blocks generated + self-audited clean.')

if __name__ == '__main__':
    main()
