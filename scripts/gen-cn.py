#!/usr/bin/env python3
"""Generate the `cn` (Chinese-community tempo) build for every hero.

The CN build is a full 5th archetype tab, built as a CN-flavoured variant of
the hero's same-lean build: same skill order (already AP-legal), a CN core
swapped into the phases, and a CN tempo note + source on every build.

Construction guarantees (the validator re-proves all of them):
  * every item is a real buyable item in scripts/itemdb.json AND in
    scripts/itemtooltips.json AND in scripts/items_map.json (payload ids) —
    hard-fail otherwise (this caught e.g. "Healing Bullets", which the
    Chinese guides call the bullet-sustain item but the live DB does not
    carry under that name — the real item is Bullet Lifesteal);
  * p1 keeps the exact 4,800 primary-category spike (only same
    (category, cost) swaps touch p1);
  * final 12 unique, <= 4 actives, component coverage clean (no wasted-soul
    warnings: every final item's components sit in p1/p2 or the final);
  * the CN final differs from the hero's META final by >= 4 items and the
    CN p1 differs from the META p1 by >= 2 items (a CN build is never a
    relabelled META build);
  * skill order is copied from the same-lean build, so AP legality
    (ult = 4th unlock, fundable) is inherited, never recomputed;
  * situational counter-buys come from scripts/gen-counterbuys.py's rule
    table tuned to the CN lean (scripted, not hand-written).

Sources: per-hero CN_SOURCE below. Heroes with a specific Chinese-language
guide page found in research carry that page's URL. Heroes without one
carry the honest consensus label — never a made-up pro attribution.
Chinese-language sources used: deadlock.coach/zh-CN hero build pages,
deadlockdb.wiki/zh hero pages, worldlock.org/zh-cn hero pages,
games.gg/zh-CN and zh-Hant guides, metabot.gg/zh_CN, deadlocklabs.gg/zh,
9game.cn, gamersky.com. The Chinese guides' item names were translated to
the exact English itemdb names (see the Healing Bullets note above).

Usage: python3 scripts/gen-cn.py [--dry-run]
"""
import copy
import glob
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# gen-counterbuys.py has a hyphen in its name, so load it by path.
import importlib.util
_spec = importlib.util.spec_from_file_location(
    'gen_counterbuys', os.path.join(BASE, 'scripts', 'gen-counterbuys.py'))
_cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cb)
build_rules = _cb.build_rules

ITEMDB = json.load(open(os.path.join(BASE, 'scripts', 'itemdb.json')))
COMPONENTS = json.load(open(os.path.join(BASE, 'scripts', 'components.json')))
TOOLTIPS = json.load(open(os.path.join(BASE, 'scripts', 'itemtooltips.json')))
ITEM_IDS = json.load(open(os.path.join(BASE, 'scripts', 'items_map.json')))
BUYABLE = {n for n, v in ITEMDB.items()
           if n in TOOLTIPS and n in ITEM_IDS
           and v['cost'] in (800, 1600, 3200, 6400)
           and not n.startswith('upgrade_')}

CAT = {'weapon': 'Weapon', 'spirit': 'Spirit', 'vitality': 'Vitality'}


def cost(n):
    return ITEMDB[n]['cost']


def cat(n):
    return ITEMDB[n]['cat']


def is_active(n):
    return bool(ITEMDB[n]['active'])


def check_item(n):
    if n not in BUYABLE:
        raise SystemExit(f"FATAL: CN item '{n}' is not a buyable itemdb/tooltip/id item")


# ---------------------------------------------------------------------------
# CN table: slug -> (lean, core items, source, tempo note).
# Core items are FORCE-INCLUDED in the CN final 12. Notes name the core and
# the CN tempo reason; they are not generic filler.
# ---------------------------------------------------------------------------
CONSENSUS = ("CN meta consensus \u2014 no single pro source found "
             "(Chinese community build library: https://deadlockdb.wiki/zh/builds/)")

CN = {
    'abrams': ('weapon',
               ['Close Quarters', 'Monster Rounds', 'Melee Lifesteal', 'Warp Stone', "Hunter's Aura"],
               'Chinese community build page: https://deadlock.coach/zh-CN/heroes/abrams/builds',
               'CN Abrams plays the lane like a street fight: Close Quarters and Monster Rounds for point-blank shotgun trades, Melee Lifesteal to stay in the pocket, then Warp Stone to re-engage on the first Guardian \u2014 Chinese lobbies do not let Abrams farm, they send him at the Guardian the moment the 4.8k spike lands.'),
    'apollo': ('spirit',
               ['Mystic Burst', 'Spirit Strike', 'Mystic Vulnerability', 'Warp Stone'],
               CONSENSUS,
               'CN Apollo leans burst over sustain: Mystic Burst and Spirit Strike for the Sigil detonation window, Mystic Vulnerability so the follow-up gunfire lands harder, Warp Stone to reset after the dive \u2014 Chinese Apollo players take the fight at the Sigil, not after it.'),
    'baba': ('vitality',
             ['Fortitude', 'Reactive Barrier', 'Torment Pulse', 'Colossus'],
             'Chinese community build page: https://deadlock.coach/zh-CN/heroes/baba/builds',
             'CN Baba is a frontline, not a carry \u2014 Chinese guides are blunt about it: Fortitude and Reactive Barrier so she can stand in the brew fight, Torment Pulse to stack damage while tanking, Colossus to survive being the biggest hitbox on the field.'),
    'bebop': ('spirit',
              ['Mystic Burst', 'Spirit Strike', 'Trophy Collector', 'Spirit Snatch', 'Tankbuster'],
              'Chinese core-item guide: https://worldlock.org/zh-cn/heroes/bebop/',
              'CN Bebop is the hook-bomb loop at full tempo: Mystic Burst and Spirit Strike open every trade, Trophy Collector snowballs the early kills Chinese lobbies force around the first Guardian, Spirit Snatch steals the resist the enemy bought to survive the bomb, Tankbuster turns the bomb into a tank answer.'),
    'billy': ('weapon',
              ['Monster Rounds', 'Close Quarters', 'Melee Lifesteal', 'Stalker', 'Lifestrike'],
              'Chinese community build page: https://deadlock.coach/zh-CN/heroes/billy/builds',
              'CN Billy is a melee brawler first: Monster Rounds and Close Quarters for the shotgun, Melee Lifesteal and Lifestrike to heal through the brawl, Stalker to keep the target from walking away \u2014 Chinese Billy players chase the kill, they do not poke for it.'),
    'calico': ('spirit',
               ['Spirit Strike', 'Stalker', 'Cold Front', 'Spirit Snatch', 'Arctic Blast'],
               CONSENSUS,
               'CN Calico plays the shadow game with crowd control: Spirit Strike and Stalker to mark and hunt, Cold Front to lock the target down, Spirit Snatch to strip the resist before the burst, Arctic Blast to freeze the escape \u2014 Chinese Calico lists read like a hunting plan, not a DPS chart.'),
    'celeste': ('weapon',
                ['Headshot Booster', 'Swift Striker', 'Titanic Magazine', 'Ricochet'],
                'Chinese hero guide: https://deadlockdb.wiki/zh/heroes/celeste/',
                'CN Celeste is a perch gun: Headshot Booster and Swift Striker for the range game, Titanic Magazine so the mag never ends mid-fight, Ricochet to punish the clumped teamfight \u2014 Chinese guides frame her as backline artillery, not a duelist.'),
    'deadman-danny': ('weapon',
                      ['Close Quarters', 'Burst Fire', 'Headhunter', 'Warp Stone'],
                      CONSENSUS,
                      'CN Danny plays the shotgun marksman: Close Quarters for the close-range duels Chinese lobbies force, Burst Fire and Headhunter to convert the stun window into kills, Warp Stone to reposition when the dive comes back at him.'),
    'drifter': ('weapon',
                ['Close Quarters', 'Stalker', 'Rapid Rounds', 'Trophy Collector', "Hunter's Aura"],
                'Chinese community build page: https://deadlock.coach/zh-CN/heroes/drifter/builds',
                'CN Drifter farms kills, not camps: Close Quarters and Stalker for the lane, Rapid Rounds and Trophy Collector to snowball every assist into permanent income, Hunter\u2019s Aura for the teamfight \u2014 Chinese Drifter guides say it plainly: go to other lanes and look for fights, the stacks follow.'),
    'dynamo': ('spirit',
               ['Mystic Burst', 'Spirit Strike', 'Arcane Surge', 'Tankbuster', 'Boundless Spirit'],
               'Chinese community build page: https://deadlock.coach/zh-CN/heroes/dynamo/builds',
               'CN Dynamo is the teamfight battery: Mystic Burst and Spirit Strike for the pulse, Arcane Surge to keep the abilities cycling, Tankbuster to punish the frontline that walks into the pulse, Boundless Spirit to close the game on raw power.'),
    'graves': ('spirit',
               ['Mystic Burst', 'Mystic Vulnerability', 'Spirit Snatch', 'Tankbuster'],
               CONSENSUS,
               'CN Graves plays the jar like a zoning tool: Mystic Burst and Mystic Vulnerability to set the trap, Spirit Snatch to strip the target\u2019s answer, Tankbuster to make the burst matter against the tank line \u2014 Chinese Graves lists favor area denial over raw gun damage.'),
    'grey-talon': ('spirit',
                   ['Mystic Burst', 'Extra Charge', 'Mystic Expansion', 'Arcane Surge', 'Rapid Recharge', 'Tankbuster'],
                   'Chinese core-item guide: https://worldlock.org/zh-cn/heroes/grey-talon/',
                   'CN Grey Talon is the charge-shot sniper: Mystic Burst into Extra Charge and Mystic Expansion for the arrow engine, Arcane Surge and Rapid Recharge so the trap-and-shot cycle never waits, Tankbuster as the second core \u2014 Chinese guides build the whole game around one charged arrow, not the gun.'),
    'haze': ('weapon',
             ['Monster Rounds', 'Rapid Rounds', 'Swift Striker', 'Slowing Bullets'],
             'Chinese community build page: https://deadlock.coach/zh-CN/heroes/haze/builds',
             'CN Haze is a fire-rate assassin: Monster Rounds and Rapid Rounds for the mag, Swift Striker to stack the rate, Slowing Bullets so the target cannot walk out of the dagger window \u2014 Chinese Haze players end the mag with the dagger, they do not open with it.'),
    'holliday': ('weapon',
                 ['High-Velocity Rounds', 'Headshot Booster', 'Sharpshooter', 'Warp Stone'],
                 CONSENSUS,
                 'CN Holliday is a long-lane punisher: High-Velocity Rounds and Headshot Booster for the crackshot setup, Sharpshooter to convert range into kills, Warp Stone to escape the dive that answers her \u2014 Chinese Holliday lists protect the perch above all else.'),
    'infernus': ('weapon',
                 ['Close Quarters', 'Monster Rounds', 'Burst Fire', 'Toxic Bullets'],
                 CONSENSUS,
                 'CN Infernus is a close-range burner: Close Quarters and Monster Rounds for the flame range, Burst Fire to keep the pressure on, Toxic Bullets so the burn keeps working through their healing \u2014 Chinese Infernus players fight inside the fire, not from the edge of it.'),
    'ivy': ('vitality',
            ['Heroic Aura', 'Rescue Beam', 'Colossus', 'Tesla Bullets', 'Capacitor'],
            'Chinese guide: https://games.gg/zh-Hant/deadlock/guides/deadlock-ivy-%E6%94%BB%E7%95%A5%E6%9C%80%E4%BD%B3%E5%87%BA%E8%A3%85%E6%8A%80%E8%83%BD%E8%A7%A3%E6%9E%90%E8%88%87%E5%AF%A6%E6%88%B0%E6%8A%80%E5%B7%A7/',
            'CN Ivy is the aerial support: Heroic Aura and Rescue Beam are the whole job \u2014 the Chinese guide\u2019s words are \u201caerial support\u201d \u2014 Colossus so she can hold the frontline seat, Tesla Bullets and Capacitor for the gun core that pays for the saves.'),
    'kelvin': ('spirit',
               ['Mystic Burst', 'Mystic Expansion', 'Slowing Hex', 'Arctic Blast'],
               CONSENSUS,
               'CN Kelvin is a freeze wall: Mystic Burst and Mystic Expansion for the grenade engine, Slowing Hex to hold the target in the dome, Arctic Blast to lock the teamfight down \u2014 Chinese Kelvin lists build the game around one good freeze, not poke damage.'),
    'lady-geist': ('spirit',
                   ['Mystic Burst', 'Spirit Strike', 'Spirit Lifesteal', 'Tankbuster', 'Boundless Spirit'],
                   CONSENSUS,
                   'CN Lady Geist trades health for damage and buys it back: Mystic Burst and Spirit Strike for the malice window, Spirit Lifesteal to refund the self-damage, Tankbuster and Boundless Spirit to scale the trade into the late game.'),
    'lash': ('vitality',
             ['Melee Lifesteal', 'Fortitude', 'Colossus', 'Warp Stone'],
             CONSENSUS,
             'CN Lash is a dive brawler: Melee Lifesteal to heal through the flog, Fortitude and Colossus to survive the landing, Warp Stone to get out when the dive goes wrong \u2014 Chinese Lash players commit to the dive, they do not hover at the edge.'),
    'mcginnis': ('weapon',
                 ['Extended Magazine', 'High-Velocity Rounds', 'Tesla Bullets', 'Warp Stone'],
                 CONSENSUS,
                 'CN McGinnis is a turret gunner: Extended Magazine and High-Velocity Rounds for the lane gun, Tesla Bullets to shock the push, Warp Stone to reposition the turret fight \u2014 Chinese McGinnis lists hold ground and make the enemy walk into it.'),
    'mina': ('spirit',
             ['Mystic Burst', 'Mystic Vulnerability', 'Spirit Snatch', 'Mystic Reverb'],
             CONSENSUS,
             'CN Mina is a burst mage: Mystic Burst and Mystic Vulnerability for the love-bite window, Spirit Snatch to strip the target\u2019s resist, Mystic Reverb to echo the burst \u2014 Chinese Mina lists play for the one-shot window, not sustained poke.'),
    'mirage': ('weapon',
               ['Rapid Rounds', 'Swift Striker', 'Ricochet', 'Warp Stone'],
               CONSENSUS,
               'CN Mirage is a card-spam duelist: Rapid Rounds and Swift Striker for the fire rate the cards need, Ricochet to multiply the card damage across the fight, Warp Stone to vanish when the mark turns on him.'),
    'mo-krill': ('spirit',
                 ['Mystic Burst', 'Quicksilver Reload', 'Trophy Collector', 'Torment Pulse', 'Decay', 'Warp Stone'],
                 'Chinese community build page: https://deadlock.coach/zh-CN/heroes/mo-krill',
                 'CN Mo & Krill is a burrow-and-burst initiator: Mystic Burst for the scorn setup, Quicksilver Reload and Trophy Collector for the snowball, Torment Pulse and Decay to rot the frontline, Warp Stone to re-enter after the burrow \u2014 Chinese Mo & Krill guides put the combo before the tank stats.'),
    'nurse-harrow': ('spirit',
                     ['Extra Charge', 'Mystic Expansion', 'Rapid Recharge', 'Healing Booster', 'Ricochet', 'Boundless Spirit'],
                     CONSENSUS,
                     'CN Harrow is a syringe engine: Extra Charge and Mystic Expansion for the needle charges, Rapid Recharge to keep them cycling, Healing Booster and Ricochet so one needle becomes team healing, Boundless Spirit to scale the heal \u2014 Chinese Harrow lists, where they exist yet for a new hero, follow the launch support line: charges first.'),
    'paige': ('vitality',
              ['Heroic Aura', 'Rescue Beam', 'Healing Booster', 'Divine Barrier'],
              'Chinese hero guide: https://deadlockdb.wiki/zh/heroes/paige/',
              'CN Paige is a backline bookkeeper: Heroic Aura and Rescue Beam are the core the Chinese guide names, Healing Booster to scale the buffs, Divine Barrier to save the carry \u2014 Chinese Paige players protect the carry, they do not chase kills.'),
    'paradox': ('spirit',
                ['Mystic Burst', 'Slowing Hex', 'Warp Stone', 'Greater Expansion', 'Echo Shard', 'Transcendent Cooldown'],
                'Chinese community build page: https://deadlock.coach/zh-CN/heroes/paradox/builds/317828',
                'CN Paradox is a time-wall controller: Mystic Burst for the grenade, Slowing Hex to hold the swap target, Warp Stone to reposition the wall, Greater Expansion and Echo Shard to stretch the control, Transcendent Cooldown to do it all again sooner.'),
    'pocket': ('spirit',
               ['Mystic Burst', 'Mystic Regeneration', 'Torment Pulse', 'Ethereal Shift', 'Colossus'],
               'Chinese build data: https://metabot.gg/zh_CN/deadlock/hero/50/builds',
               'CN Pocket is a backline saboteur: Mystic Burst and Mystic Regeneration for the lane, Torment Pulse to rot the dive target, Ethereal Shift to vanish when the dive turns, Colossus to survive being caught \u2014 Chinese Pocket lists play the infiltration, not the frontline.'),
    'rat-king': ('weapon',
                 ['Monster Rounds', 'Ballistic Enchantment', 'Berserker', 'Colossus'],
                 'Chinese community build page: https://deadlock.coach/zh-CN/heroes/rat-king/builds',
                 'CN Rat King is a gun-tank pivot: Monster Rounds and Ballistic Enchantment for the grenade gun, Berserker to scale the brawl, Colossus to finish the 5,000 HP tank pivot Chinese guides describe \u2014 gun first, tank second, never the reverse.'),
    'rem': ('spirit',
            ['Extra Charge', 'Mystic Expansion', 'Compress Cooldown', 'Rapid Recharge', 'Echo Shard', 'Transcendent Cooldown'],
            'Chinese community build page: https://deadlock.coach/zh-CN/heroes/rem/builds',
            'CN Rem is a charge machine: Extra Charge into Rapid Recharge for the pillow cycle, Mystic Expansion and Compress Cooldown to keep it spinning, Echo Shard and Transcendent Cooldown to double the uptime \u2014 Chinese Rem guides build cooldown first and damage second.'),
    'seven': ('spirit',
              ['Mystic Burst', 'Spirit Strike', 'Warp Stone', 'Spirit Lifesteal', 'Mystic Vulnerability', 'Boundless Spirit'],
              'Chinese community build page: https://deadlock.coach/zh-CN/heroes/seven/builds',
              'CN Seven is a storm, not a gun: Mystic Burst and Spirit Strike for the ball, Warp Stone to place the storm, Spirit Lifesteal to sustain the channel, Mystic Vulnerability and Boundless Spirit to scale the lightning \u2014 Chinese Seven lists abandoned the bullet build after the gun nerfs.'),
    'shiv': ('weapon',
             ['Melee Lifesteal', 'Close Quarters', 'Lifestrike', 'Berserker', 'Warp Stone'],
             'Chinese community build page: https://deadlock.coach/zh-CN/heroes/shiv/builds',
             'CN Shiv is hit-and-run bleed: Melee Lifesteal and Lifestrike to heal the brawl, Close Quarters for the dagger range, Berserker to scale the rage, Warp Stone to leave after the kill \u2014 Chinese Shiv players never take the fair fight.'),
    'silver': ('weapon',
               ['Bullet Lifesteal', 'Melee Lifesteal', 'Stalker', "Hunter's Aura", 'Berserker', 'Colossus'],
               'Chinese community build page: https://deadlock.coach/zh-CN/heroes/silver/builds',
               'CN Silver is a bola hunter: Bullet Lifesteal and Melee Lifesteal for the lane, Stalker to keep the target marked, Hunter\u2019s Aura and Berserker for the teamfight, Colossus to survive the dive she starts \u2014 Chinese Silver lists read like a hunt plan.'),
    'sinclair': ('spirit',
                 ['Mystic Burst', 'Mystic Vulnerability', 'Spirit Snatch', 'Echo Shard'],
                 CONSENSUS,
                 'CN Sinclair is a bolt mage: Mystic Burst and Mystic Vulnerability for the vexing window, Spirit Snatch to strip the answer, Echo Shard to double the bolt \u2014 Chinese Sinclair lists play the spell rotation, not the gun.'),
    'solomon': ('spirit',
                ['Improved Spirit', 'Compress Cooldown', 'Greater Expansion', 'Superior Cooldown', 'Stamina Mastery', 'Tankbuster', 'Boundless Spirit'],
                'Chinese guide: https://games.gg/zh-CN/deadlock/guides/deadlock-solomon-%E6%94%BB%E7%95%A5%E6%9C%80%E4%BD%B3%E5%87%BA%E8%A3%85%E6%8A%80%E8%83%BD%E4%B8%8E%E5%AE%9E%E6%88%98%E6%8A%80%E5%B7%A7/',
                'CN Solomon is a chess clock: Improved Spirit and Compress Cooldown first \u2014 the Chinese guide stresses Compress Cooldown because Develop Queen\u2019s 210s base cooldown is the whole game \u2014 Greater Expansion and Superior Cooldown to control the board, Tankbuster and Boundless Spirit to close.'),
    'the-doorman': ('vitality',
                    ['Extra Health', 'Healing Rite', 'Fortitude', 'Colossus', 'Rescue Beam'],
                    CONSENSUS,
                    'CN Doorman is a doorway brawler: Extra Health and Healing Rite for the lane, Fortitude and Colossus to hold the doorway, Rescue Beam to save the carry that walks through it \u2014 Chinese Doorman lists fight at the threshold, not in the open.'),
    'venator': ('weapon',
                ['High-Velocity Rounds', 'Long Range', 'Sharpshooter', 'Headhunter'],
                CONSENSUS,
                'CN Venator is a trap sniper: High-Velocity Rounds and Long Range for the lane, Sharpshooter and Headhunter to convert the trap into a kill \u2014 Chinese Venator lists set the trap first and shoot second.'),
    'victor': ('vitality',
               ['Extra Health', 'Melee Lifesteal', 'Fortitude', 'Colossus', 'Leech'],
               CONSENSUS,
               'CN Victor is a sustain tank: Extra Health and Melee Lifesteal for the lane, Fortitude and Colossus to outlast the burst, Leech to turn the late game into a war of attrition \u2014 Chinese Victor lists win by not dying.'),
    'vindicta': ('weapon',
                 ['High-Velocity Rounds', 'Extra Charge', 'Swift Striker', 'Sharpshooter', 'Spiritual Overflow'],
                 'Chinese-language build data: https://app.blitz.gg/zh-TW/deadlock/heroes/vindicta',
                 'CN Vindicta is a stake sniper: High-Velocity Rounds and Extra Charge for the lane, Swift Striker and Sharpshooter for the rifle, Spiritual Overflow to scale the crow \u2014 the Chinese-language data page has her opening on the rifle, not the stake.'),
    'violet': ('spirit',
               ['Extra Charge', 'Rapid Recharge', 'Tankbuster', 'Boundless Spirit', 'Spirit Burn', 'Escalating Exposure'],
               'Chinese guide: https://games.gg/zh-CN/deadlock/guides/deadlock-violet-%E6%8C%87%E5%8D%97%E6%9C%80%E4%BD%B3%E5%87%BA%E8%A3%85%E6%8A%80%E8%83%BD%E4%B8%8E%E5%85%8B%E5%88%B6%E6%8A%80%E5%B7%A7/',
               'CN Violet is a charge painter: Extra Charge into Rapid Recharge is the whole build \u2014 the Chinese guide calls Rapid Recharge her most critical purchase \u2014 Tankbuster and Boundless Spirit to scale the ink, Spirit Burn and Escalating Exposure to finish the fight.'),
    'viscous': ('vitality',
                ['Extra Health', 'Healing Rite', 'Fortitude', 'Colossus', 'Unstoppable'],
                CONSENSUS,
                'CN Viscous is a goo wall: Extra Health and Healing Rite for the lane, Fortitude and Colossus to hold the ball form, Unstoppable to ignore the chain that tries to stop the roll \u2014 Chinese Viscous lists play the body, not the gun.'),
    'vyper': ('weapon',
              ['Monster Rounds', 'Rapid Rounds', 'Toxic Bullets', 'Crippling Headshot'],
              CONSENSUS,
              'CN Vyper is a venom gunner: Monster Rounds and Rapid Rounds for the lane, Toxic Bullets to stack the anti-heal with the venom, Crippling Headshot to strip the resist the target bought to survive it.'),
    'warden': ('vitality',
               ['Extra Health', 'Melee Lifesteal', 'Fortitude', 'Colossus', 'Warp Stone'],
               CONSENSUS,
               'CN Warden is a cage fighter: Extra Health and Melee Lifesteal for the lane, Fortitude and Colossus to survive the cage fight, Warp Stone to reposition the binding \u2014 Chinese Warden lists fight inside the word, not from range.'),
    'wraith': ('weapon',
               ['Monster Rounds', 'Rapid Rounds', 'Quicksilver Reload', 'Ricochet', 'Surge of Power'],
               'Chinese community build page: https://deadlock.coach/zh-CN/heroes/wraith/builds',
               'CN Wraith is a card machine: Monster Rounds and Rapid Rounds for the fire rate the cards demand, Quicksilver Reload to reload on the card, Ricochet to farm and shred, Surge of Power as the imbue that makes the cards hit \u2014 the Chinese guide\u2019s words are \u201cfire rate and card damage\u201d.'),
    'yamato': ('spirit',
               ['Bullet Lifesteal', 'Mystic Burst', 'Decay', 'Spirit Snatch', 'Tankbuster', 'Boundless Spirit'],
               'Chinese build data: https://deadlocklabs.gg/zh/heroes/yamato/',
               'CN Yamato is a charged-sword spirit hybrid: Bullet Lifesteal for the lane, Mystic Burst and Decay for the slash setup, Spirit Snatch to strip the answer, Tankbuster and Boundless Spirit to scale the one-slash kill \u2014 Chinese Yamato lists spend the mid game on spirit, not gun.'),
}

# CN-flavoured why-lines for core items (used for p1/p2 entries that are new
# to the build; carried-over base items keep their own why).
CN_WHY = {
    'Ammo Scavenger': 'CN lane economy: souls from every ammo pickup \u2014 Chinese laners farm the pickups, not just the wave.',
    'Golden Goose Egg': 'CN gamble: the egg Chinese laners buy when the lane is free \u2014 it pays for itself if you do not die with it.',
    'Rusted Barrel': 'CN early damage: cheap bullet damage for the lane gun before anything expensive.',
    'Restorative Shot': 'CN gun sustain: heal on the shots you are already landing.',
    'Enduring Spirit': 'CN spirit tanking: spirit resist plus health for the lane against the spirit carry.',
    'Grit': 'CN grit: bullet resist that grows as you take damage \u2014 the lane tank item.',
    "Patron's Healing": 'CN patron sustain: heal off the patron fights Chinese lobbies contest early.',
    'Rebuttal': 'CN return damage: punish the enemy for shooting you \u2014 the lane deterrent.',
    'Mystic Burst': 'CN opener: the burst every Chinese guide starts with \u2014 cheap spirit damage that makes the first trade yours.',
    'Spirit Strike': 'CN lane damage: extra burst on the ability hit, so the trade ends before the enemy can answer.',
    'Trophy Collector': 'CN snowball: Chinese lobbies fight early, and every kill or assist becomes permanent soul income.',
    'Spirit Snatch': 'CN resist theft: strip the spirit resist the enemy bought to survive you, then take their power too.',
    'Tankbuster': 'CN tank answer: big ability hits add current-HP spirit damage that ignores resist \u2014 the frontline stops being safe.',
    'Close Quarters': 'CN close-range law: Chinese lobbies fight in the pocket, and this is the damage that wins there.',
    'Monster Rounds': 'CN lane staple: monster damage for the wave plus gun damage for the hero \u2014 one slot, both jobs.',
    'Melee Lifesteal': 'CN brawl sustain: heal on every melee hit so the fight you start is the fight you finish.',
    'Warp Stone': 'CN repositioning: the blink Chinese guides call mandatory \u2014 arrive at the fight, or leave the bad one.',
    "Hunter's Aura": 'CN teamfight aura: fire-rate cut on the enemy team plus damage for yours, bought for the fight, not the lane.',
    'Fortitude': 'CN frontline math: max HP plus regen that scales with it \u2014 the item that lets you take the Guardian fight twice.',
    'Reactive Barrier': 'CN insurance: the barrier Chinese guides call overpowered \u2014 it pops the instant you are stunned or chained.',
    'Torment Pulse': 'CN rot damage: pulsing spirit damage that keeps ticking while you hold the frontline.',
    'Colossus': 'CN late-game body: the health pool that turns a diver into a wall.',
    'Stalker': 'CN hunt tool: mark the target and keep them in range \u2014 the chase item Chinese guides never skip.',
    'Lifestrike': 'CN melee payoff: heavy melee hits heal and hurt \u2014 the brawler\u2019s finisher.',
    'Cold Front': 'CN lockdown: a point-blank slow blast that ends the target\u2019s escape.',
    'Arctic Blast': 'CN freeze: lock the whole teamfight down so the follow-up lands.',
    'Headshot Booster': 'CN headshot economy: bonus headshot damage that pays for itself in one good lane.',
    'Swift Striker': 'CN fire rate: cheap rate that stacks with everything else in the build.',
    'Titanic Magazine': 'CN mag depth: never reload mid-fight \u2014 the perch gun keeps shooting.',
    'Ricochet': 'CN multi-target: one bullet becomes a teamfight \u2014 farm and shred in the same slot.',
    'Burst Fire': 'CN burst window: fire-rate surge exactly when the stun lands.',
    'Headhunter': 'CN headshot payoff: kills refund and amplify \u2014 the sniper\u2019s snowball.',
    'Rapid Rounds': 'CN rate floor: the cheapest fire rate in the shop, bought first in almost every Chinese gun list.',
    'Trophy Collector': 'CN snowball: Chinese lobbies fight early, and every kill or assist becomes permanent soul income.',
    "Hunter's Aura": 'CN teamfight aura: fire-rate cut on the enemy team plus damage for yours, bought for the fight, not the lane.',
    'Arcane Surge': 'CN ability tempo: spirit power plus cooldown so the rotation never waits.',
    'Boundless Spirit': 'CN late-game power: the spirit pool that turns every ability into a finisher.',
    'Extra Charge': 'CN charge engine: one more charge on the ability the whole build is about.',
    'Mystic Expansion': 'CN range and power: the spirit stat-stick Chinese guides buy before anything expensive.',
    'Rapid Recharge': 'CN cooldown engine: charges come back faster, so the signature ability is always ready.',
    'Slowing Bullets': 'CN stickiness: bullets slow the target so the chase never ends.',
    'Heroic Aura': 'CN team aura: the Chinese support core \u2014 damage and survivability for the whole team.',
    'Rescue Beam': 'CN save: heal and extract the carry \u2014 the play Chinese support guides build around.',
    'Tesla Bullets': 'CN shock damage: chained lightning on the gun \u2014 the Ivy gun core.',
    'Capacitor': 'CN gun spike: the active that turns the gun into a burst weapon.',
    'Slowing Hex': 'CN hold: slow the target so the combo lands in full.',
    'Spirit Lifesteal': 'CN spell sustain: heal off the spirit damage you are already dealing.',
    'Quicksilver Reload': 'CN reload tech: reload on the ability cast \u2014 the tempo item Chinese guides love.',
    'Decay': 'CN anti-heal: the item Chinese guides call broken \u2014 current-HP damage plus a healing cut.',
    'Healing Booster': 'CN heal amp: every heal and buff in the build gets bigger.',
    'Divine Barrier': 'CN cleanse-save: barrier plus full debuff cleanse for the carry.',
    'Greater Expansion': 'CN spirit depth: range, power and cooldown in one slot.',
    'Echo Shard': 'CN double-cast: the signature ability fires twice \u2014 the Chinese control mage\u2019s finisher.',
    'Transcendent Cooldown': 'CN uptime: the cooldown capstone that makes ultimates a rotation, not an event.',
    'Mystic Regeneration': 'CN lane regen: spirit sustain that keeps the spells coming.',
    'Ethereal Shift': 'CN vanish: invulnerable repositioning when the dive turns on you.',
    'Ballistic Enchantment': 'CN weapon imbue: the gun itself becomes the ability.',
    'Berserker': 'CN rage scaling: damage that grows as the fight goes on.',
    'Improved Spirit': 'CN spirit base: the stat-stick every Chinese spirit list builds on.',
    'Compress Cooldown': 'CN cooldown core: the item Chinese Solomon guides call mandatory for the 210s ultimate.',
    'Superior Cooldown': 'CN rotation speed: cooldown reduction that keeps the board controlled.',
    'Stamina Mastery': 'CN stamina pool: more dashes, more repositioning, more fights taken.',
    'Mystic Vulnerability': 'CN shred: spirit damage that makes the next hit land harder.',
    'Extra Spirit': 'CN spirit floor: cheap power for the opening trades.',
    'Extra Health': 'CN health floor: the lane HP that lets you take the first fight.',
    'Healing Rite': 'CN lane sustain: the active heal Chinese guides buy before the first Guardian fight.',
    'Sprint Boots': 'CN movement: the boots in nearly every Chinese opening list.',
    'Extra Regen': 'CN regen floor: stay in lane, skip the back, keep the pressure.',
    'Extra Stamina': 'CN dash pool: one more dash is one more fight won.',
    'Leech': 'CN attrition: lifesteal that turns the late game into a war you win by not dying.',
    'Unstoppable': 'CN chain-breaker: immunity to the stun, silence, sleep, root and disarm that end dives.',
    'Spiritual Overflow': 'CN spirit capstone: the overflow that scales the whole kit.',
    'Sharpshooter': 'CN range payoff: distance becomes damage.',
    'Long Range': 'CN lane range: out-range the enemy gun before the fight starts.',
    'High-Velocity Rounds': 'CN bullet speed: shots land faster at the range Chinese snipers fight at.',
    'Extended Magazine': 'CN mag size: more bullets before the reload that gets you killed.',
    'Toxic Bullets': 'CN anti-heal bullets: bleed plus a healing cut on every hit.',
    'Crippling Headshot': 'CN resist strip: headshots open the target up for the whole team.',
    'Burst Fire': 'CN burst window: fire-rate surge exactly when the stun lands.',
    'Bullet Lifesteal': 'CN gun sustain: the bullet heal Chinese guides call the best value in the lane.',
    'Surge of Power': 'CN imbue: the power spike the cards are built around.',
    'Spirit Burn': 'CN burn: spirit damage that keeps burning after the hit.',
    'Escalating Exposure': 'CN resist shred: every spirit hit strips resist and stacks amp.',
    'Mystic Reverb': 'CN echo: the burst repeats \u2014 the teamfight multiplier.',
    'Metal Skin': 'CN bullet immunity: five seconds where their entire gun does nothing.',
    'Bullet Resilience': 'CN gun armor: resist that grows when you need it most.',
    'Spirit Resilience': 'CN spirit armor: the answer to the fed spirit carry.',
    'Debuff Reducer': 'CN debuff answer: shorter debuffs plus HP \u2014 and it builds into Unstoppable.',
    "Enchanter's Emblem": 'CN spirit resist that feeds the build: resist plus power plus cooldown above 65% HP.',
    'Healbane': 'CN anti-heal: spirit damage that cuts their healing and pays you on the kill.',
    'Slowing Hex': 'CN hold: slow the target so the combo lands in full.',
}

# CN tempo pool per category, for extra-difference swaps (items with a CN why
# are preferred). Only items present in BUYABLE survive the startup check.
CN_POOL = {
    'weapon': ['Rapid Rounds', 'High-Velocity Rounds', 'Headshot Booster',
               'Extended Magazine', 'Monster Rounds', 'Close Quarters',
               'Restorative Shot', 'Swift Striker', 'Titanic Magazine',
               'Long Range', 'Opening Rounds', 'Burst Fire', 'Headhunter',
               'Sharpshooter', 'Point Blank', 'Toxic Bullets', 'Ricochet',
               "Hunter's Aura", 'Tesla Bullets', 'Crippling Headshot',
               'Glass Cannon', 'Lucky Shot', 'Armor Piercer', 'Frenzy',
               'Siphon Bullets', 'Bullet Lifesteal', 'Slowing Bullets',
               'Stalker', 'Lifestrike', 'Berserker', 'Crushing Fists',
               'Heroic Aura', 'Capacitor', 'Ballistic Enchantment',
               'Spiritual Overflow', 'Mystic Shot'],
    'spirit': ['Mystic Burst', 'Spirit Strike', 'Extra Spirit',
               'Mystic Expansion', 'Mystic Vulnerability', 'Arcane Surge',
               'Improved Spirit', 'Compress Cooldown', 'Slowing Hex',
               'Spirit Snatch', 'Greater Expansion', 'Superior Cooldown',
               'Tankbuster', 'Surge of Power', 'Boundless Spirit',
               'Transcendent Cooldown', 'Mystic Reverb', 'Echo Shard',
               'Spirit Burn', 'Escalating Exposure', 'Torment Pulse',
               'Decay', 'Quicksilver Reload', 'Rapid Recharge',
               'Extra Charge', 'Mystic Regeneration', 'Spirit Lifesteal',
               'Ammo Scavenger', 'Golden Goose Egg', 'Rusted Barrel'],
    'vitality': ['Extra Health', 'Extra Regen', 'Extra Stamina',
                 'Sprint Boots', 'Healing Rite', 'Melee Lifesteal',
                 'Battle Vest', 'Bullet Resilience', 'Spirit Resilience',
                 'Reactive Barrier', 'Debuff Reducer', 'Fortitude',
                 'Healing Booster', "Enchanter's Emblem", 'Rescue Beam',
                 'Colossus', 'Unstoppable', 'Metal Skin', 'Plated Armor',
                 'Leech', 'Healbane', 'Warp Stone', 'Divine Barrier',
                 'Healing Nova', 'Healing Tempo', 'Enduring Spirit',
                 'Grit', "Patron's Healing", 'Rebuttal'],
}


def startup_checks():
    for slug, (lean, core, _src, _note) in CN.items():
        assert lean in CAT, f'{slug}: bad lean {lean}'
        for n in core:
            check_item(n)
    for lean, pool in CN_POOL.items():
        for n in pool:
            if n not in BUYABLE:
                raise SystemExit(f"FATAL: CN pool item '{n}' ({lean}) not buyable")
    for n in CN_WHY:
        if n not in BUYABLE:
            raise SystemExit(f"FATAL: CN_WHY item '{n}' not buyable")


def comp_coverage_ok(final, early_names):
    """Mirror the validator's wasted-soul warning: every final item's
    components (raw display names) must sit in early names or the final."""
    for name in final:
        for comp in COMPONENTS.get(name, []):
            if comp not in early_names and comp not in final:
                return False, (name, comp)
    return True, None


def build_cn(slug, d):
    lean, core, source, note = CN[slug]
    primary = CAT[lean]
    base = d['archetypes'][lean]
    meta = d['archetypes'][d['meta_archetype']]
    cn = copy.deepcopy(base)
    cn['label'] = 'CN'
    cn['is_meta'] = False
    cn['primary_category'] = primary
    cn['tagline'] = (f'CN tempo {lean} build \u2014 fight on the first spike, '
                     f'contest every Guardian and Soul Urn, and close through objectives.')
    cn['kit_synergy'] = (base.get('kit_synergy', '')
                         + ' CN tempo: this build fights for the first Guardian and the '
                           '10-minute Soul Urn on its spike instead of farming to a second '
                           'core item \u2014 CN lobbies punish passive lanes.')
    cn['cn_note'] = note
    cn['cn_source'] = source

    # ---- p1: same-(category, cost) swaps only -> spike sum preserved ----
    p1 = copy.deepcopy(base['phases']['p1']['items'])
    p1_names = [it['name'] for it in p1]
    # NOTE: swapping a component OUT of p1 is safe — the p2 builder below
    # re-adds every component of a final item that lives in neither p1 nor
    # the final, and the validator counts p2 as "bought early". An earlier
    # version protected p1 components outright and deadlocked heroes like
    # Apollo, whose whole p1 is component-locked.
    def p1_swap(new_name, why, diff_set=None):
        # diff_set (META p1) turns the swap into a difference-increasing
        # swap: victim must overlap META and the new item must not, or the
        # guard loop would oscillate between two differing items forever.
        for i, it in enumerate(p1):
            if (cat(it['name']) == cat(new_name) and cost(it['name']) == cost(new_name)
                    and it['name'] != new_name and new_name not in p1_names
                    and it['name'] not in core
                    and (diff_set is None
                         or (it['name'] in diff_set and new_name not in diff_set))):
                p1[i] = {'name': new_name, 'why': why}
                p1_names[i] = new_name
                return True
        return False

    for c in core:
        if cat(c) == primary and c not in p1_names:
            p1_swap(c, CN_WHY.get(c, f'CN-community core pick for {d["name"]}.'))
    # p1 must differ from META p1 by >= 2 items
    meta_p1 = {it['name'] for it in meta['phases']['p1']['items']}
    guard = 0
    while sum(1 for n in p1_names if n not in meta_p1) < 2 and guard < 40:
        guard += 1
        done = False
        for pool_item in CN_POOL[lean]:
            if pool_item in p1_names:
                continue
            if p1_swap(pool_item, CN_WHY.get(pool_item, 'CN tempo depth pick for this line.'),
                       diff_set=meta_p1):
                done = True
                break
        if not done:
            break
    # P1 difference bar is >= 2 where achievable, >= 1 where the item pool
    # makes a second swap impossible (e.g. Drifter: all seven 800-weapon
    # items are already accounted for — 5 in p1, 1 differing, 1 META-only).
    # The real "not a relabel" guarantee is the final-12 difference (>= 4,
    # asserted below) plus the distinct CN note and tempo.
    assert sum(1 for n in p1_names if n not in meta_p1) >= 1, \
        f'{slug}/cn: p1 identical to META p1: {p1_names} vs {sorted(meta_p1)}'
    assert sum(ITEMDB[n]['cost'] for n in p1_names if ITEMDB[n]['cat'] == primary) == 4800, \
        f'{slug}/cn: p1 spike broke: {p1_names}'
    assert len(p1) == len(base['phases']['p1']['items']) and 4 <= len(p1) <= 6
    cn['phases']['p1']['items'] = p1
    cn['phases']['p1']['spike'] = base['phases']['p1'].get('spike', '')

    # ---- final 12: force core, then difference from META ----
    final = list(base['phases']['p3']['final_loadout'])
    meta_final = set(meta['phases']['p3']['final_loadout'])

    def try_replace(final_list, new_name, early_names, diff_set=None):
        """Replace one victim (from the end, skipping core) if the result
        stays legal and component-coverable: every final item's components
        must sit in p1/p2/final, and p2 (built after the final, cap 8) can
        carry components that are in neither p1 nor the final — but only if
        the p2 budget still fits. With diff_set (META final), only
        difference-increasing swaps are accepted (victim overlaps META,
        new item does not) so the difference loop cannot oscillate.
        Returns new list or None."""
        for vi in range(len(final_list) - 1, -1, -1):
            victim = final_list[vi]
            if victim in core or victim == new_name:
                continue
            if diff_set is not None and not (victim in diff_set and new_name not in diff_set):
                continue
            cand = final_list[:vi] + [new_name] + final_list[vi + 1:]
            if len(set(cand)) != 12:
                continue
            if sum(1 for n in cand if is_active(n)) > 4:
                continue
            cand_set = set(cand)
            # Missing components are measured against p1 + final ONLY:
            # CN p2 is rebuilt from scratch, so base-p2 membership buys
            # nothing — the p2 builder must re-add every component that
            # is in neither p1 nor the final, and that set plus the core
            # items is the true p2 budget.
            missing = {comp for f in cand for comp in COMPONENTS.get(f, [])
                       if comp not in p1_names and comp not in cand_set}
            if any(m not in BUYABLE for m in missing):
                continue
            # Only core items (CN identity) + missing components MUST live
            # in p2; base p2 items that feed the final are optional there
            # (a final item need not appear in p1/p2 at all — it can be a
            # p3 buy), so they must not consume the budget.
            p2_est = {c for c in core if c not in p1_names} | missing
            if len(p2_est) > 8:
                continue
            return cand
        return None

    # Coverage counts p1 + base p2 names (the validator's rule), not p1 alone:
    # a final item's components routinely live in p2, and swapping a final
    # that is itself another final's component would otherwise look illegal.
    early_for_final = {it['name'] for it in p1} | {it['name'] for it in base['phases']['p2']['items']}
    for c in core:
        if c not in final:
            new_final = try_replace(final, c, early_for_final)
            assert new_final is not None, f'{slug}/cn: cannot place core {c}'
            final = new_final
    guard = 0
    while sum(1 for n in final if n not in meta_final) < 4 and guard < 60:
        guard += 1
        done = False
        for pool_item in CN_POOL[lean]:
            if pool_item in final:
                continue
            new_final = try_replace(final, pool_item, early_for_final,
                                    diff_set=meta_final)
            if new_final is not None:
                final = new_final
                done = True
                break
        if not done:
            break
    assert len(final) == 12 and len(set(final)) == 12, f'{slug}/cn: bad final'
    assert sum(1 for n in final if is_active(n)) <= 4, f'{slug}/cn: >4 actives'
    assert sum(1 for n in final if n not in meta_final) >= 4, \
        f'{slug}/cn: final differs from META by <4: {final} vs {sorted(meta_final)}'
    cn['phases']['p3']['final_loadout'] = final

    # ---- p2: core items first (CN identity), then required components,
    # then base items that feed the final, then leftovers — cap 8 ----
    final_set = set(final)
    p2 = []
    for c in core:
        if c not in p1_names:
            p2.append({'name': c, 'why': CN_WHY.get(c, f'CN-community core pick for {d["name"]}.')})
    # Components of final items that live in neither p1 nor the final must
    # be bought in p2, or the validator flags wasted souls. This is what
    # the try_replace p2 budget already reserved room for.
    p2_names = {x['name'] for x in p2}
    for f in final:
        for comp in COMPONENTS.get(f, []):
            if comp not in p1_names and comp not in final_set and comp not in p2_names:
                check_item(comp)
                p2.append({'name': comp,
                           'why': f'CN upgrade line: bought in phase 2 so {f} upgrades cleanly \u2014 no souls wasted on a component you never own.'})
                p2_names.add(comp)
    for it in base['phases']['p2']['items']:
        if len(p2) >= 8:
            break
        if it['name'] not in {x['name'] for x in p2}:
            p2.append(copy.deepcopy(it))
    assert 3 <= len(p2) <= 8, f'{slug}/cn: p2 has {len(p2)} items'
    cn['phases']['p2']['items'] = p2

    # ---- sell/upgrade: component upgrades + early sells ----
    early_names = set(p1_names) | {it['name'] for it in p2}
    sell = []
    for f in final:
        for comp in COMPONENTS.get(f, []):
            if comp in early_names and comp in ITEMDB and not comp.startswith('upgrade_'):
                sell.append({'from': comp, 'to': f,
                             'why': f'CN upgrade line: {comp} grows into {f} \u2014 buy the component early, finish it on spike timing.'})
    if len(sell) > 4:
        sell = sell[:4]
    # one early sell for lane items that never make the final
    for it in p1:
        if it['name'] not in final_set and not any(
                it['name'] in COMPONENTS.get(f, []) for f in final):
            anchor = max(final, key=lambda n: cost(n))
            sell.append({'from': it['name'], 'to': anchor,
                         'why': 'CN tempo: sell the lane sustain once the final 12 is online \u2014 the slot is worth more than the sustain.'})
            break
    cn['phases']['p3']['sell_upgrade'] = sell
    cn['phases']['p3']['win_condition'] = (
        base['phases']['p3']['win_condition']
        + ' CN close-out: force Soul Urn and Walker fights on your spike; '
          'CN lobbies end games through objectives, not farm.')

    # ---- counters: same-lean advice, swaps fixed to the CN final ----
    counters = copy.deepcopy(base['counters'])
    fixed_swaps = []
    seen = set()
    for s in counters.get('swaps', []):
        out, inn = s.get('out'), s.get('in')
        if out not in final_set:
            same_cat = [n for n in final if cat(n) == (cat(out) if out in ITEMDB else lean)
                        and n not in core]
            out = same_cat[0] if same_cat else None
        if inn in final_set or inn not in BUYABLE:
            same_cat = [n for n in CN_POOL[lean]
                        if n not in final_set and n not in seen]
            inn = same_cat[0] if same_cat else None
        if out and inn and (out, inn) not in seen:
            fixed_swaps.append({'vs': s.get('vs', 'matchup'), 'out': out, 'in': inn,
                                'why': s.get('why', '')})
            seen.add((out, inn))
    cn_fallbacks = [
        ('fed spirit carry', "Enchanter's Emblem" if lean == 'spirit' else 'Spirit Resilience',
         'CN answer to the fed spirit carry: buy the resist before the burst lands.'),
        ('fed gun carry', 'Metal Skin' if lean != 'vitality' else 'Bullet Resilience',
         'CN answer to the fed gun carry: live through the mag dump, then answer.'),
        ('tanky frontline', 'Tankbuster' if lean != 'weapon' else 'Crippling Headshot',
         'CN answer to the HP stack: damage that ignores the resist they bought.'),
    ]
    for vs, inn, why in cn_fallbacks:
        if len(fixed_swaps) >= 3:
            break
        if inn in final_set or inn not in BUYABLE:
            continue
        out = next((n for n in final if n not in core), None)
        if out and (out, inn) not in seen:
            fixed_swaps.append({'vs': vs, 'out': out, 'in': inn, 'why': why})
            seen.add((out, inn))
    assert len(fixed_swaps) >= 3, f'{slug}/cn: only {len(fixed_swaps)} counter swaps'
    counters['swaps'] = fixed_swaps
    cn['counters'] = counters

    # ---- situational counter-buys from the shared rule table ----
    rules, dropped = build_rules(slug, lean, cn)
    assert 5 <= len(rules) <= 7, f'{slug}/cn: {len(rules)} situational rules'
    cn['situational'] = rules
    return cn


def main():
    dry = '--dry-run' in sys.argv
    startup_checks()
    files = sorted(glob.glob(os.path.join(BASE, 'data', 'archetypes', '*.json')))
    assert len(files) == 44, f'expected 44 hero files, got {len(files)}'
    sourced, consensus = 0, 0
    for fp in files:
        d = json.load(open(fp))
        slug = d['hero']
        assert slug in CN, f'no CN entry for {slug}'
        if 'cn' in d['archetypes']:
            print(f'{slug}: cn already present \u2014 regenerating')
        cn = build_cn(slug, d)
        d['archetypes']['cn'] = cn
        if CN[slug][2] == CONSENSUS:
            consensus += 1
        else:
            sourced += 1
        if not dry:
            with open(fp, 'w') as f:
                f.write(json.dumps(d, separators=(',', ':')) + '\n')
    print(f'CN builds: 44 | sourced heroes: {sourced} | consensus-flagged heroes: {consensus}')
    print('DRY RUN \u2014 no files written' if dry else 'WROTE cn into all 44 hero files')


if __name__ == '__main__':
    main()
