"""Descent game mode (docs/descent/DESIGN_V1.md).

A solo start in floor 1 (a dungeon); every floor is one existing dungeon whose chests are checks. A guardian drawn from a
depth pool stands at the dungeon's zone; killing it opens a portal to the next floor once enough Progressive Depth Seals are
held. The goal is the last floor's guardian. data/descent.json is written by tools/apworld/build_descent.py.

Everything here is a pure function of `random` and plain values, so it is unit-testable without a multiworld.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .resources import read_json

_DATA = read_json("descent.json")

# Rooms in descent mode; older clients must refuse them (ArchipelagoIds.DescentMappingVersion). No -cm1 suffix:
# challenge missions never exist in this mode.
DESCENT_MAPPING_VERSION = "so2r-ids-v1-descent-v1"
SLOT_DATA_VERSION = 1
HUB_PROGRESS: int = _DATA["hub_progress"]

DEPTH_SEAL_ID = 5_920_000
DEPTH_SEAL_NAME = "Progressive Depth Seal"
GUARDIAN_LOCATION_BASE = 5_830_000
# Names for 1..15 are static (location_name_to_id is class-level); the option allows 3..13 floors today.
GUARDIAN_NAME_COUNT = 15
MIN_FLOORS = 3
MAX_FLOORS = 13
MIN_FIRST_FLOOR_CHESTS = 6
LOCK_MESSAGE = "The way out is sealed. Face the guardian."

# Chest-count floor for the Treasure modifier, and the dungeon Ambush cannot run in (native symbols only).
TREASURE_MIN_CHESTS = 3
FIELD_OF_MIGHT = "MF_0037"

# Restorative packs weigh this much more in a descent pool, and Fol's share of the filler drops (no shops).
RESTORATIVE_WEIGHT_FACTOR = 2
FOL_SHARE = 0.05

# Runtime parameters the plugin reads (slot_data.descent.modifiers); balance changes need no plugin update.
MODIFIER_PARAMS: Dict[str, dict] = {
    "empowered_foes": {"world_level_bonus": 5},
    "heavy_boots": {},
    "back_attack": {},
    "silence": {"status_id": 5},
    "ambush": {"rate_factor": 2.0},
    "treasure": {},
    "bounty": {"drop_chance_factor": 2.0},
    "blessed": {"exp_factor": 2.0, "fol_factor": 2.0},
    "cursed": {"cursed_weight_factor": 3.0},
}
TREASURE_BOOST = 2.0  # Rare and Unique weights x2, Normal x0.5, for the chests of a Treasure floor (loot.roll_item)


@dataclass(frozen=True)
class Dungeon:
    locality: str
    id: str
    name: str
    tier: int
    planet: str  # EXPEL | NEDE
    entrance_row: int
    entrance_map: str
    maps: Tuple[str, ...]
    chests: Tuple[int, ...]
    zone: Optional[dict]
    verified: bool


@dataclass(frozen=True)
class Guardian:
    party_id: int
    name: str
    group: object  # 1..4 | "final"
    level: Optional[int]
    vetted: bool


@dataclass(frozen=True)
class Modifier:
    key: str
    name: str
    weight: int
    kind: str
    needs: Optional[str]


@dataclass(frozen=True)
class Floor:
    index: int  # 1-based
    dungeon: Dungeon
    guardian: Guardian
    world_level: int
    guardian_level: int
    modifier: Optional[str]  # modifier key
    seals_to_descend: Optional[int]  # None on the goal floor
    goal: bool

    @property
    def location_id(self) -> int:
        return GUARDIAN_LOCATION_BASE + self.index


DUNGEONS: List[Dungeon] = [
    Dungeon(d["locality"], d["id"], d["name"], d["tier"], d["planet"], d["entrance_row"], d["entrance_map"],
            tuple(d["maps"]), tuple(d["chests"]), d["zone"], d["verified"])
    for d in _DATA["dungeons"]
]
DUNGEON_BY_LOCALITY: Dict[str, Dungeon] = {d.locality: d for d in DUNGEONS}
GUARDIANS: List[Guardian] = [Guardian(g["party_id"], g["name"], g["group"], g["level"], g["vetted"])
                             for g in _DATA["guardians"]]
GUARDIAN_BY_PARTY: Dict[int, Guardian] = {g.party_id: g for g in GUARDIANS}
MODIFIERS: List[Modifier] = [Modifier(m["key"], m["name"], m["weight"], m["kind"], m["needs"]) for m in _DATA["modifiers"]]
MODIFIER_BY_KEY: Dict[str, Modifier] = {m.key: m for m in MODIFIERS}
MODIFIER_NAMES: List[str] = [m.name for m in MODIFIERS]
MODIFIER_DEFAULT_WEIGHTS: Dict[str, int] = {m.name: m.weight for m in MODIFIERS}
GUARDIAN_LOCATIONS: Dict[str, int] = {f"Floor {n} Guardian": GUARDIAN_LOCATION_BASE + n
                                      for n in range(1, GUARDIAN_NAME_COUNT + 1)}
PLANET_ORDER = {"EXPEL": 0, "NEDE": 1}
FINAL_GUARDIAN = 539


def guardian_location_name(floor: int) -> str:
    return f"Floor {floor} Guardian"


def eligible(unverified: bool) -> List[Dungeon]:
    """The dungeons a seed may draw: verified ones with a guardian zone, plus the unverified ones with the toggle.
    A dungeon with zone null (Krosse Cave until its zone is authored, Sacred Forest) is never eligible."""
    return [d for d in DUNGEONS if d.zone is not None and (d.verified or unverified)]


def _allocate(random, sizes: Dict[int, int], count: int) -> Dict[int, int]:
    """Stratified allocation: round(count * size / total) per tier by largest remainder, random tie-break."""
    total = sum(sizes.values())
    quota = {tier: count * size // total for tier, size in sizes.items()}
    remainders = {tier: (count * size) % total for tier, size in sizes.items()}
    tiers = sorted(sizes)
    random.shuffle(tiers)  # the tie-break
    order = sorted(tiers, key=lambda tier: -remainders[tier])
    left = count - sum(quota.values())
    for tier in order:
        if left <= 0:
            break
        if quota[tier] < sizes[tier]:
            quota[tier] += 1
            left -= 1
    return quota


def choose_dungeons(random, count: int, unverified: bool) -> List[Dungeon]:
    """`count` distinct dungeons, stratified by tier, ordered by (tier, planet, random): Expel before Nede inside a tier.
    Floor 1 has at least MIN_FIRST_FLOOR_CHESTS chests."""
    pool = eligible(unverified)
    if count > len(pool):
        raise ValueError(f"Descent has {len(pool)} eligible dungeons with the current options; "
                         f"descent_floors {count} is too many.")
    by_tier: Dict[int, List[Dungeon]] = {}
    for dungeon in pool:
        by_tier.setdefault(dungeon.tier, []).append(dungeon)
    quota = _allocate(random, {tier: len(rows) for tier, rows in by_tier.items()}, count)
    first_tier = min(tier for tier, n in quota.items() if n > 0)
    picked: List[Dungeon] = []
    for tier in sorted(by_tier):
        if quota[tier] == 0:
            continue
        rows = random.sample(by_tier[tier], quota[tier])
        if tier == first_tier and not any(len(d.chests) >= MIN_FIRST_FLOOR_CHESTS for d in rows):
            # Floor 1 needs room for the first seal and character: swap a small pick for a big dungeon of the tier.
            big = [d for d in by_tier[tier] if len(d.chests) >= MIN_FIRST_FLOOR_CHESTS and d not in rows]
            rows[random.randrange(len(rows))] = random.choice(big)
        keyed = [(PLANET_ORDER[d.planet], random.random(), d) for d in rows]
        keyed.sort(key=lambda row: (row[0], row[1]))
        ordered = [row[2] for row in keyed]
        if tier == first_tier and len(ordered[0].chests) < MIN_FIRST_FLOOR_CHESTS:
            # Swap with a big dungeon of the same planet so the planet order holds.
            for index, dungeon in enumerate(ordered):
                if dungeon.planet == ordered[0].planet and len(dungeon.chests) >= MIN_FIRST_FLOOR_CHESTS:
                    ordered[0], ordered[index] = ordered[index], ordered[0]
                    break
        picked.extend(ordered)
    return picked


def _group_for(depth: float) -> int:
    return 1 if depth < 0.25 else 2 if depth < 0.5 else 3 if depth < 0.8 else 4


def choose_guardians(random, count: int, final_mode: str = "gabriel") -> List[Guardian]:
    """One guardian per floor, no repeats. Floor i draws from the group its depth d = (i - 1) / (count - 1) falls in
    (an empty group falls back to the nearest one with vetted guardians left, lower groups first); the last floor is
    Gabriel, or with final_mode "random_top" a draw from the top group (vetted or not)."""
    remaining = {group: [g for g in GUARDIANS if g.group == group and g.vetted] for group in (1, 2, 3, 4)}
    result: List[Guardian] = []
    for floor in range(1, count + 1):
        if floor == count:
            if final_mode == "random_top":
                result.append(random.choice([g for g in GUARDIANS if g.group == 4]))
            else:
                result.append(GUARDIAN_BY_PARTY[FINAL_GUARDIAN])
            continue
        want = _group_for((floor - 1) / (count - 1))
        for group in sorted(remaining, key=lambda g: (abs(g - want), g)):
            if remaining[group]:
                result.append(remaining[group].pop(random.randrange(len(remaining[group]))))
                break
        else:
            raise ValueError("Descent ran out of guardians.")
    return result


def world_level(floor: int, count: int, start: int, maximum: int) -> int:
    """round(start + (max - start) * (i - 1) / (N - 1))."""
    return round(start + (maximum - start) * (floor - 1) / (count - 1))


def modifier_allowed(modifier: Modifier, dungeon: Dungeon, scaling_on: bool, loot_tiers: bool, cursed_loot: bool,
                     monster_drops: bool) -> bool:
    """The dependency of design 1.3: a modifier whose need is unmet is out of this seed's pool for this floor."""
    needs = modifier.needs
    if needs == "scaling":
        return scaling_on
    if needs == "not_might":
        return dungeon.locality != FIELD_OF_MIGHT
    if needs == "cursed_loot":
        return loot_tiers and cursed_loot
    if needs == "loot_tiers_3_chests":
        return loot_tiers and len(dungeon.chests) >= TREASURE_MIN_CHESTS
    if needs == "monster_drops":
        return monster_drops
    return True


def choose_modifiers(random, dungeons: Sequence[Dungeon], chance: int, weights: Dict[str, int], scaling_on: bool,
                     loot_tiers: bool, cursed_loot: bool, monster_drops: bool) -> List[Optional[str]]:
    """Floor 1 never has one; floors 2..N-1 roll `chance` percent; the last floor always rolls. At most one per floor, never
    the same key twice in a row; weights by name (0 removes a modifier)."""
    result: List[Optional[str]] = [None]
    count = len(dungeons)
    for index in range(1, count):
        previous = result[-1]
        if index != count - 1 and random.random() * 100 >= chance:
            result.append(None)
            continue
        options = [m for m in MODIFIERS if weights.get(m.name, 0) > 0 and m.key != previous
                   and modifier_allowed(m, dungeons[index], scaling_on, loot_tiers, cursed_loot, monster_drops)]
        if not options:
            result.append(None)
            continue
        result.append(random.choices(options, weights=[weights[m.name] for m in options])[0].key)
    return result


def build_floors(random, count: int, unverified: bool, modifier_chance: int, modifier_weights: Dict[str, int],
                 scaling_on: bool, loot_tiers: bool, cursed_loot: bool, monster_drops: bool, wl_start: int, wl_max: int,
                 boss_offset: int, final_mode: str = "gabriel") -> List[Floor]:
    dungeons = choose_dungeons(random, count, unverified)
    guardians = choose_guardians(random, count, final_mode)
    modifiers = choose_modifiers(random, dungeons, modifier_chance, modifier_weights, scaling_on, loot_tiers,
                                 cursed_loot, monster_drops)
    floors = []
    for index, (dungeon, guardian, modifier) in enumerate(zip(dungeons, guardians, modifiers), start=1):
        level = world_level(index, count, wl_start, wl_max)
        floors.append(Floor(index, dungeon, guardian, level, level + boss_offset, modifier,
                            None if index == count else index, index == count))
    return floors


def chars_needed(floor: int, count: int, joinable: int) -> int:
    """Character items held (the starter is not counted) before floor `floor`'s guardian is in logic."""
    return round((floor - 1) / (count - 1) * joinable)


def weapons_needed(floor: int, count: int, joinable: int, total_rungs: int) -> int:
    return min(total_rungs, (floor - 1) * (joinable + 1) // (count - 1))


def packs_weights(packs: Sequence) -> List[int]:
    """Pack weights for a descent pool: Restorative x2."""
    return [p.weight * RESTORATIVE_WEIGHT_FACTOR if p.pack == "Restorative" else p.weight for p in packs]


def slot_data(floors: Sequence[Floor], heal_on_descent: bool) -> dict:
    """slot_data.descent, contract version 1 (DESIGN_V1.md section 6)."""
    count = len(floors)
    return {
        "version": SLOT_DATA_VERSION,
        "hub_progress": HUB_PROGRESS,
        "floor_count": count,
        "goal_floor": count,
        "seal": {"item_id": DEPTH_SEAL_ID, "name": DEPTH_SEAL_NAME},
        "guardian_location_base": GUARDIAN_LOCATION_BASE,
        "heal_on_descent": bool(heal_on_descent),
        "lock_message": LOCK_MESSAGE,
        "modifiers": {key: dict(params) for key, params in MODIFIER_PARAMS.items()},
        "floors": [{
            "index": floor.index,
            "dungeon": floor.dungeon.locality,
            "name": floor.dungeon.name,
            "tier": floor.dungeon.tier,
            "planet": floor.dungeon.planet,
            "entrance_row": floor.dungeon.entrance_row,
            "entrance_map": floor.dungeon.entrance_map,
            "maps": list(floor.dungeon.maps),
            "zone": dict(floor.dungeon.zone),
            "guardian_party": floor.guardian.party_id,
            "guardian_name": floor.guardian.name,
            "guardian_level": floor.guardian_level,
            "world_level": floor.world_level,
            "guardian_location": floor.location_id,
            "modifier": floor.modifier,
            "chests": sorted(floor.dungeon.chests),
            "seals_to_descend": floor.seals_to_descend,
            "next": [] if floor.goal else [floor.index + 1],
        } for floor in floors],
    }


def spoiler_lines(floors: Sequence[Floor]) -> List[str]:
    lines = []
    for floor in floors:
        modifier = MODIFIER_BY_KEY[floor.modifier].name if floor.modifier else "-"
        tail = "(goal)" if floor.goal else f"seals to descend: {floor.seals_to_descend}"
        lines.append(f"{floor.index:>2}  {floor.dungeon.name:<26} T{floor.dungeon.tier} {floor.dungeon.planet.title():<6} "
                     f"WL {floor.world_level:<3} chests {len(floor.dungeon.chests):<3} "
                     f"Guardian: {floor.guardian.name} ({floor.guardian.party_id}, Lv{floor.guardian_level})  "
                     f"Modifier: {modifier}  {tail}")
    return lines
