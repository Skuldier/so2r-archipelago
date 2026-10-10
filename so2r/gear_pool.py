"""The generated open-world item pool (docs/GEAR_POOL.md). Vanilla chest contents play no part.

The pool is sized to the free locations (locations minus keys, Orbs and characters) and split:
  - equipment, `equipment_share` percent of it, made of
      - weapons (42 %): per roster character a ladder of Progressive Weapon copies (the n-th copy received is the
        character's n-th rung, weakest first), plus random individual weapons for the rest;
      - armor (32 %) and accessories (the rest), drawn at random;
    every piece is one some roster character can equip, drawn without repeats and weighted by rarity, with jackpots
    (superboss / Maze / Legend SSR) rare and gag weapons rarer;
  - everything else resource packs (small and large) and Fol, or the plain filler list with packs off.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence

from .resources import read_json


WEAPON_SHARE = 0.42
ARMOR_SHARE = 0.32
MAX_TIERS = 4
MIN_TIERS = 2
LADDER_SKIP = 0.15  # the weakest weapons of a character never become a rung
RARITY_WEIGHT = {"N": 3.0, "R": 4.0, "SR": 3.0, "SSR": 1.5}
JACKPOT_WEIGHT = 0.6
GAG_WEIGHT = 0.5
FOL_SHARE = 0.2
LARGE_PACK_SHARE = 0.3
FOL_AMOUNTS = (1000, 2000, 3000, 5000, 8000, 10000)
FOL_WEIGHTS = (4, 4, 3, 3, 2, 1)


@dataclass(frozen=True)
class Gear:
    id: int
    name: str
    category: str
    slot: str
    rarity: str
    equip: int
    power: int
    sourced: bool
    jackpot: bool
    gag: bool

    def usable_by(self, player_id: int) -> bool:
        return bool(self.equip & (1 << (player_id - 1)))


_RAW = read_json("gear.json")
GEAR: List[Gear] = [Gear(**row) for row in _RAW["gear"]]
GEAR_BY_ID: Dict[int, Gear] = {gear.id: gear for gear in GEAR}
# The weapon each character already holds when it arrives: the plugin's basic weapon as the seed's starter
# (CharacterStarterSetup.BasicWeapons), its native join weapon when received later (0 = none).
STARTER_WEAPON: Dict[int, int] = {int(pid): row["starter"] for pid, row in _RAW["start_weapons"].items()}
RECRUIT_WEAPON: Dict[int, int] = {int(pid): row["recruit"] for pid, row in _RAW["start_weapons"].items()}


def arrival_power(player_id: int, starter: bool) -> int:
    """The attack of the weapon this character arrives with (0 when it has none)."""
    weapon = (STARTER_WEAPON if starter else RECRUIT_WEAPON).get(player_id, 0)
    return GEAR_BY_ID[weapon].power if weapon in GEAR_BY_ID else 0


@dataclass
class GearPool:
    """Item names for the pool (one entry per copy) and the ladders slot_data carries."""
    names: List[str] = field(default_factory=list)
    ladders: Dict[int, List[int]] = field(default_factory=dict)  # player id -> game item ids, weakest first


def roster_mask(roster: Sequence[int]) -> int:
    mask = 0
    for player_id in roster:
        mask |= 1 << (player_id - 1)
    return mask


def weight(gear: Gear) -> float:
    value = RARITY_WEIGHT[gear.rarity]
    if gear.jackpot:
        value *= JACKPOT_WEIGHT / RARITY_WEIGHT["SSR"]
    if gear.gag:
        value *= GAG_WEIGHT
    return value


def ladder_for(random, player_id: int, tiers: int, taken: set, floor: int = 0) -> List[int]:
    """`tiers` rungs for one character, weakest first: the character's own weapons (no jackpot or gag) stronger than
    the one it arrives with (`floor`, its attack), sorted by attack and split into `tiers` bands with one pick from
    each, so every rung is an upgrade (room 051, 2026-09-24: Leon's first rung was his starting Reference Book). With
    no weapon to beat, the weakest LADDER_SKIP is left out instead. A weapon another ladder already took is avoided
    when its band has anything else."""
    candidates = sorted((gear for gear in GEAR if gear.slot == "weapon" and gear.usable_by(player_id)
                         and not gear.jackpot and not gear.gag and gear.power > floor),
                        key=lambda gear: (gear.power, gear.id))
    if not candidates:
        return []
    usable = candidates if floor > 0 else candidates[int(len(candidates) * LADDER_SKIP):] or candidates
    tiers = min(tiers, len(usable))
    rungs: List[int] = []
    last = floor
    for band in range(tiers):
        start = band * len(usable) // tiers
        end = (band + 1) * len(usable) // tiers
        # Each rung strictly beats the one before (equal-attack weapons would make a copy a sidegrade); when its band
        # has nothing stronger, the next stronger weapon above it stands in, and a ladder that runs out stops short.
        choices = [gear for gear in usable[start:end] if gear.power > last] or \
            [gear for gear in usable[start:] if gear.power > last][:1]
        if not choices:
            break
        fresh = [gear for gear in choices if gear.id not in taken] or choices
        pick = random.choice(fresh)
        taken.add(pick.id)
        rungs.append(pick.id)
        last = pick.power
    return rungs


def draw(random, candidates: List[Gear], count: int) -> List[Gear]:
    """`count` distinct pieces, weighted; repeats only once every candidate has been drawn."""
    picks: List[Gear] = []
    remaining = list(candidates)
    while len(picks) < count and candidates:
        if not remaining:
            remaining = list(candidates)
        index = random.choices(range(len(remaining)), weights=[weight(gear) for gear in remaining])[0]
        picks.append(remaining.pop(index))
    return picks


def build(random, roster: Sequence[int], slots: int, equipment_share: int, progressive_name, gear_name,
          small_packs: Sequence[str], large_packs: Sequence[str], small_weights: Sequence[int],
          large_weights: Sequence[int], filler_names: Sequence[str], fol_name, progressive: bool = True,
          fol_share: float = FOL_SHARE) -> GearPool:
    """The pool for `slots` free locations. Names come back through the callbacks so this module stays free of the
    item table: progressive_name(player id), gear_name(gear), fol_name(amount). With `progressive` False the ladders
    are still sized (so the random draws and the weapon share match) but dropped: their slots become filler (packs
    and Fol), `pool.ladders` stays empty and the item count is unchanged."""
    pool = GearPool()
    if slots <= 0:
        return pool
    mask = roster_mask(roster)
    equipment = min(slots, round(slots * equipment_share / 100))
    weapons = round(equipment * WEAPON_SHARE)
    armor = round(equipment * ARMOR_SHARE)
    accessories = equipment - weapons - armor

    # Most weapons are ladder rungs; a reserve of about 15 % (at least 4) stays individual weapons.
    reserve = max(4, round(weapons * 0.15))
    tiers = max(MIN_TIERS, min(MAX_TIERS, (weapons - reserve) // max(1, len(roster))))
    if tiers * len(roster) > weapons:
        tiers = weapons // max(1, len(roster))
    taken: set = set()
    for index, player_id in enumerate(roster):
        # roster[0] is the seed's starter (characters.choose_roster); the others arrive as items.
        floor = arrival_power(player_id, starter=index == 0)
        rungs = ladder_for(random, player_id, tiers, taken, floor) if tiers > 0 else []
        if rungs:
            pool.ladders[player_id] = rungs
            pool.names.extend(progressive_name(player_id) for _ in rungs)
    individual = weapons - sum(len(rungs) for rungs in pool.ladders.values())
    if not progressive:
        pool.ladders.clear()
        pool.names.clear()
        taken.clear()

    def usable(slot: str) -> List[Gear]:
        return [gear for gear in GEAR if gear.slot == slot and gear.equip & mask and gear.id not in taken]

    for slot, count in (("weapon", individual), ("armor", armor), ("accessory", accessories)):
        pool.names.extend(gear_name(gear) for gear in draw(random, usable(slot), count))

    rest = slots - len(pool.names)
    fol = round(rest * fol_share)
    for _ in range(fol):
        pool.names.append(fol_name(random.choices(FOL_AMOUNTS, weights=FOL_WEIGHTS)[0]))
    for _ in range(rest - fol):
        if small_packs:
            if large_packs and random.random() < LARGE_PACK_SHARE:
                pool.names.append(random.choices(list(large_packs), weights=list(large_weights))[0])
            else:
                pool.names.append(random.choices(list(small_packs), weights=list(small_weights))[0])
        else:
            pool.names.append(random.choice(list(filler_names)))
    return pool
