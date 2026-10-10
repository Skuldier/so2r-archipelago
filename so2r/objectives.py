"""Bucket List objectives (docs/OBJECTIVES_V1.md; v2 = world 0.87.0): the 74-row table, the tier apportionment, the
slot-by-slot selection (named objectives and Random categories) and the drawing algorithm.

Open world only. data/objectives.json is hand-authored (not derived from game data, so there is no generator): ids are
stable and never reused. Every drawn objective is a location `Objective: <name>` at 5_840_000 + id; the plugin completes it
from its own counters. This module is pure (no Archipelago imports besides the data loader) so the draw is easy to test.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .resources import read_json

OBJECTIVE_LOCATION_ID_BASE = 5_840_000
OBJECTIVE_NAME_PREFIX = "Objective: "
# Rooms that carry slot_data.objectives append this to their mapping version (after "-cm1"), so a plugin without the
# feature refuses the room instead of playing locations it can never check.
OBJECTIVE_MAPPING_SUFFIX = "-ob1"

GOAL_ORBS = "orbs"
GOAL_OBJECTIVES = "objectives"
GOAL_ORBS_AND_OBJECTIVES = "orbs_and_objectives"

TIER_NAMES = {1: "Easy", 2: "Medium", 3: "Hard"}
TIER_BY_NAME = {name: tier for tier, name in TIER_NAMES.items()}
# Largest-remainder ties go to the scarcest tier first, so a tiny draw keeps its Hard.
_TIER_PRIORITY = (3, 2, 1)
# The cap on how much of the seed's chest checks an "open N chests" objective may ask for.
CHEST_CAP_FRACTION = 0.7
FIELD_LOCALITIES = ("MF_0036", "MF_0037", "MF_0038", "MF_0039")
# Towns per planet (locality ids the plugin reads with GetVisitedFieldmapFlag). Expel: Arlia, Salva, Krosse Castle,
# Kurik, Marze, Harley, Lacuer Castle. Nede: Centropolis, North City, Noel's Home, Princebridge, L'Aqua, Armlock, Fun City.
TOWNS: Dict[str, Tuple[str, ...]] = {
    "EXPEL": ("MF_0003", "MF_0004", "MF_0007", "MF_0009", "MF_0010", "MF_0012", "MF_0017"),
    "NEDE": ("MF_0030", "MF_0031", "MF_0032", "MF_0034", "MF_0046", "MF_0040", "MF_0043"),
}


@dataclass(frozen=True)
class ObjectiveRow:
    id: int
    name: str  # location name without the prefix; static and variant-free
    text: str  # in-game text, "{variant}" filled at draw time
    tier: int  # 1..3
    family: str
    kind: str
    params: dict
    exclusive: Tuple[int, ...]
    requires: dict
    no_progression: bool
    goal_only: Optional[str]
    tier_override: Optional[dict]
    # v2: the exclusivity group (defaults to the family) and whether the row is reachable only through objective_slots.
    # Slot-only rows never join the tier-mix draw, so a seed without slots draws exactly what 0.86.0 drew.
    group: Optional[str] = None
    slot_only: bool = False

    @property
    def address(self) -> int:
        return OBJECTIVE_LOCATION_ID_BASE + self.id

    @property
    def location_name(self) -> str:
        return OBJECTIVE_NAME_PREFIX + self.name

    @property
    def logic(self) -> str:
        return self.requires["logic"]


def _load() -> Tuple[ObjectiveRow, ...]:
    data = read_json("objectives.json")
    assert data["location_base"] == OBJECTIVE_LOCATION_ID_BASE and data["name_prefix"] == OBJECTIVE_NAME_PREFIX
    rows = tuple(ObjectiveRow(r["id"], r["name"], r["text"], r["tier"], r["family"], r["kind"], r["params"],
                              tuple(r["exclusive"]), r["requires"], r["no_progression"], r["goal_only"],
                              r["tier_override"], r.get("group"), bool(r.get("slot_only", False)))
                 for r in data["objectives"])
    assert len({r.id for r in rows}) == len(rows), "duplicate objective id"
    assert len({r.name for r in rows}) == len(rows), "duplicate objective name"
    assert all(1 <= r.id <= 199 for r in rows)
    return rows


@dataclass(frozen=True)
class Category:
    """A "Random ..." entry for objective_slots. Membership is by tier and/or family (None = no restriction); `weighted`
    (plain "Random") rolls the tier from the Objective Tier Mix first."""
    name: str
    description: str
    tiers: Optional[Tuple[int, ...]]
    families: Optional[Tuple[str, ...]]
    weighted: bool

    def contains(self, row: ObjectiveRow, tier: Optional[int] = None) -> bool:
        return ((self.tiers is None or (row.tier if tier is None else tier) in self.tiers)
                and (self.families is None or row.family in self.families))


def _load_categories() -> Tuple[Category, ...]:
    return tuple(Category(c["name"], c["description"], tuple(c["tiers"]) if c["tiers"] else None,
                          tuple(c["families"]) if c["families"] else None, bool(c["weighted"]))
                 for c in read_json("objectives.json")["categories"])


OBJECTIVE_ROWS: Tuple[ObjectiveRow, ...] = _load()
OBJECTIVE_BY_ID: Dict[int, ObjectiveRow] = {r.id: r for r in OBJECTIVE_ROWS}
OBJECTIVE_LOCATION_TABLE: Dict[str, ObjectiveRow] = {r.location_name: r for r in OBJECTIVE_ROWS}
CATEGORIES: Tuple[Category, ...] = _load_categories()
CATEGORY_BY_NAME: Dict[str, Category] = {c.name: c for c in CATEGORIES}
CATEGORY_NAMES: Tuple[str, ...] = tuple(c.name for c in CATEGORIES)
# Every valid objective_slots entry: the objectives' exact names and the category names.
SLOT_KEYS: Tuple[str, ...] = tuple(r.name for r in OBJECTIVE_ROWS) + CATEGORY_NAMES
assert not set(CATEGORY_NAMES) & {r.name for r in OBJECTIVE_ROWS}, "category name collides with an objective name"


def category_members(category: Category) -> List[ObjectiveRow]:
    return [r for r in OBJECTIVE_ROWS if category.contains(r)]


def location_name_groups() -> Dict[str, set]:
    groups: Dict[str, set] = {"Objectives": set()}
    for row in OBJECTIVE_ROWS:
        groups["Objectives"].add(row.location_name)
        groups.setdefault(f"Objectives: {TIER_NAMES[row.tier]}", set()).add(row.location_name)
        groups.setdefault(f"Objectives: {row.family}", set()).add(row.location_name)
    return groups


@dataclass(frozen=True)
class DrawContext:
    """What the draw needs to know about the final seed (the caps of docs/OBJECTIVES_V1.md section 2.3)."""
    goal: str
    start_planet: str
    other_planet_open: bool
    chest_count: int  # non-maze, non-Phynal chest checks
    boss_party_ids: frozenset  # active boss-spot party ids
    area_key_count: int  # non-maze Area Keys in the seed
    town_count: int  # towns on the start planet
    fields_ok: bool  # all four Field keys exist
    chest_areas: frozenset  # localities with at least one active chest check
    character_count: int = 0  # character items in the seed's pool (the roster less the starter)

    def spot_count(self) -> int:
        return len(self.boss_party_ids)


@dataclass(frozen=True)
class Drawn:
    row: ObjectiveRow
    variant: Optional[dict]
    tier: int  # effective tier (after tier_override)
    how: str = ""  # how a slot-driven draw chose it: "picked", "category: <name>", "replaced <name>", "tier mix"

    @property
    def text(self) -> str:
        label = self.variant["label"] if self.variant else ""
        return self.row.text.format(variant=label)


def effective_tier(row: ObjectiveRow, ctx: DrawContext) -> int:
    if row.tier_override and ctx.other_planet_open and "other_planet_open" in row.tier_override:
        return row.tier_override["other_planet_open"]
    return row.tier


def active_variants(row: ObjectiveRow, ctx: DrawContext) -> List[dict]:
    """The row's variants that exist in this seed (row 20: a boss whose spot is active; row 28: every skill)."""
    variants = row.requires.get("variants")
    if not variants:
        return []
    return [v for v in variants if "boss" not in v or v["boss"] in ctx.boss_party_ids]


def eligible(row: ObjectiveRow, ctx: DrawContext) -> bool:
    """The seed-pool caps (section 2.3): an ineligible row is simply not in the pool."""
    if row.goal_only is not None and row.goal_only != ctx.goal:
        return False
    logic, n = row.logic, row.requires.get("n")
    if logic == "chests":
        return n <= int(CHEST_CAP_FRACTION * ctx.chest_count)
    if logic == "spots":
        return ctx.spot_count() > 0 and n <= ctx.spot_count() - 1
    if logic == "keys":
        return n <= ctx.area_key_count
    if logic == "towns":
        return n <= ctx.town_count
    if logic == "fields":
        return ctx.fields_ok
    if logic == "dungeon":
        # v1 rows name the boss that completes the clear; v2 rows list the area's bosses, which count when they are spots.
        return ("boss" not in row.requires or row.requires["boss"] in ctx.boss_party_ids)             and row.requires["area"] in ctx.chest_areas
    if logic == "named":
        return bool(active_variants(row, ctx))
    if logic == "boss":
        return row.requires["boss"] in ctx.boss_party_ids  # needs boss_checks: no spots, no row
    if logic == "party":
        return n <= ctx.character_count
    return True


def _group(row: ObjectiveRow, legacy: bool) -> str:
    return row.group if row.group and not legacy else row.family


def conflicts(a: ObjectiveRow, b: ObjectiveRow, ctx: DrawContext, legacy: bool = True) -> bool:
    """The exclusivity rules plus the planets objective against any row on the other planet. `legacy` is the v1 rule, one
    row per family; a slot-driven draw uses each row's exclusivity group instead (the family unless the row names one), so
    several bosses or dungeons can coexist while two thresholds of the same thing never do."""
    if _group(a, legacy) == _group(b, legacy) or b.id in a.exclusive or a.id in b.exclusive:
        return True
    for planets, other in ((a, b), (b, a)):
        if planets.logic == "planets":
            planet = other.requires.get("planet")
            if planet is not None and planet != ctx.start_planet:
                return True
    return False


def apportion(count: int, weights: Dict[str, int]) -> Dict[int, int]:
    """Largest remainder over the tier-mix weights; ties go Hard, then Medium, then Easy."""
    w = {tier: max(0, int(weights.get(name, 0))) for tier, name in TIER_NAMES.items()}
    total = sum(w.values())
    if total <= 0:
        raise ValueError("objective_tier_mix has every weight at 0")
    quota = {tier: count * w[tier] / total for tier in w}
    result = {tier: int(quota[tier]) for tier in w}
    left = count - sum(result.values())
    order = sorted(w, key=lambda t: (-(quota[t] - result[t]), _TIER_PRIORITY.index(t)))
    for tier in order[:left]:
        result[tier] += 1
    return result


def _mix_pool(ctx: DrawContext) -> Dict[int, List[ObjectiveRow]]:
    """The tier-mix pool: every eligible row except the slot-only ones (those are reachable through objective_slots)."""
    pool: Dict[int, List[ObjectiveRow]] = {1: [], 2: [], 3: []}
    for row in OBJECTIVE_ROWS:
        if not row.slot_only and eligible(row, ctx):
            pool[effective_tier(row, ctx)].append(row)
    return pool


def _fill_mix(random, ctx: DrawContext, drawn: List[Drawn], wanted: Dict[int, int], legacy: bool, how: str) -> None:
    """docs/OBJECTIVES_V1.md section 2.2 steps 3-5: per tier, scarcest first, shuffled by id, borrowing on a shortfall."""
    pool = _mix_pool(ctx)

    def take(tier: int, want: int) -> int:
        candidates = sorted(pool[tier], key=lambda r: r.id)
        random.shuffle(candidates)
        got = 0
        for row in candidates:
            if got >= want:
                break
            if any(d.row.id == row.id or conflicts(d.row, row, ctx, legacy) for d in drawn):
                continue
            variants = active_variants(row, ctx)
            drawn.append(Drawn(row, random.choice(variants) if variants else None, tier, how))
            got += 1
        return got

    carry = 0
    for tier in (3, 2, 1):  # scarcest first; a shortfall borrows from the nearest tier below
        want = wanted[tier] + carry
        carry = want - take(tier, want)
    for tier in (2, 1, 3):  # Easy's shortfall goes back to Medium, then anywhere left
        if carry <= 0:
            break
        carry -= take(tier, carry)


def _remaining_wanted(count: int, drawn: List[Drawn], weights: Dict[str, int]) -> Dict[int, int]:
    """Tier counts for the slots the explicit and category picks left open: the full apportionment less what is drawn,
    trimmed (Easy first) or topped up (by the weights) to exactly the open slot count."""
    left = count - len(drawn)
    target = apportion(count, weights)
    wanted = {t: max(0, target[t] - sum(1 for d in drawn if d.tier == t)) for t in target}
    for tier in (1, 2, 3):
        while sum(wanted.values()) > left and wanted[tier] > 0:
            wanted[tier] -= 1
    if sum(wanted.values()) < left:
        for tier, extra in apportion(left - sum(wanted.values()), weights).items():
            wanted[tier] += extra
    return wanted


def draw(random, ctx: DrawContext, count: int, weights: Dict[str, int],
         player_name: str = "", slots: Iterable[str] = ()) -> List[Drawn]:
    """docs/OBJECTIVES_V1.md section 2.2 and the v2 slot rules. Draws nothing, and consumes no randomness, when `count` is 0.

    With no slot entries this is exactly the 0.86.0 draw (slot-only rows stay out of the pool, one row per family).
    With entries, in order: (1) the exact objective names, if eligible and not conflicting; (2) the Random categories,
    from their eligible members; the picks that could not be honoured are replaced by a random pick of the same tier;
    (3) every slot still open is filled from the tier mix."""
    if count <= 0:
        return []
    entries = [str(s).strip() for s in slots]
    if len(entries) > count and any(entries[count:]):
        logging.warning("SO2R player %s: objective_slots has %d entries but only %d objectives are drawn; the extra "
                        "entries are ignored.", player_name, len([e for e in entries[count:] if e]), count)
    entries = entries[:count]
    legacy = not any(entries)
    wanted = apportion(count, weights)
    drawn: List[Drawn] = []
    if legacy:
        _fill_mix(random, ctx, drawn, wanted, True, "")
    else:
        _draw_slots(random, ctx, count, weights, player_name, entries, drawn)
    if len(drawn) < count:
        logging.warning("SO2R player %s: only %d of %d objectives could be drawn for this seed.",
                        player_name, len(drawn), count)
    elif legacy and any(sum(1 for d in drawn if d.tier == t) != wanted[t] for t in wanted):
        logging.warning("SO2R player %s: the objective tier mix could not be met exactly; borrowed from a nearby tier.",
                        player_name)
    drawn.sort(key=lambda d: (d.tier, d.row.id))
    return drawn


def _draw_slots(random, ctx: DrawContext, count: int, weights: Dict[str, int], player_name: str,
                entries: List[str], drawn: List[Drawn]) -> None:
    by_name = {r.name.casefold(): r for r in OBJECTIVE_ROWS}
    by_category = {c.name.casefold(): c for c in CATEGORIES}
    tag = f"SO2R player {player_name}: objective_slots"

    def blocked(row: ObjectiveRow) -> bool:
        return any(d.row.id == row.id or conflicts(d.row, row, ctx, False) for d in drawn)

    def add(row: ObjectiveRow, how: str) -> None:
        variants = active_variants(row, ctx)
        drawn.append(Drawn(row, random.choice(variants) if variants else None, effective_tier(row, ctx), how))

    replacements: List[Tuple[int, str]] = []  # (tier, the entry that could not be honoured)
    # (1) the exact names
    for entry in entries:
        if not entry or entry.casefold() in by_category:
            continue
        row = by_name.get(entry.casefold())
        if row is None:
            logging.warning("%s: '%s' is not an objective or category; the slot is drawn from the tier mix.", tag, entry)
        elif not eligible(row, ctx):
            logging.warning("%s: '%s' is not available in this seed; replaced by a random %s objective.", tag, row.name,
                            TIER_NAMES[effective_tier(row, ctx)])
            replacements.append((effective_tier(row, ctx), row.name))
        elif blocked(row):
            logging.warning("%s: '%s' conflicts with an objective already chosen (the first is kept); replaced by a "
                            "random %s objective.", tag, row.name, TIER_NAMES[effective_tier(row, ctx)])
            replacements.append((effective_tier(row, ctx), row.name))
        else:
            add(row, "picked")
    # (2) the categories, in slot order
    for entry in entries:
        category = by_category.get(entry.casefold()) if entry else None
        if category is None:
            continue
        members = [r for r in OBJECTIVE_ROWS
                   if category.contains(r, effective_tier(r, ctx)) and eligible(r, ctx) and not blocked(r)]
        if not members:
            logging.warning("%s: '%s' has no eligible objective left in this seed; the slot is drawn from the tier mix.",
                            tag, category.name)
            continue
        if category.weighted:
            tiers = sorted({effective_tier(r, ctx) for r in members})
            w = [max(0, int(weights.get(TIER_NAMES[t], 0))) for t in tiers]
            tier = random.choices(tiers, weights=w)[0] if sum(w) > 0 else random.choice(tiers)
            members = [r for r in members if effective_tier(r, ctx) == tier]
        add(random.choice(sorted(members, key=lambda r: r.id)), f"category: {category.name}")
    # the picks that could not be honoured: a random objective of the same tier
    for tier, name in replacements:
        members = [r for r in OBJECTIVE_ROWS if effective_tier(r, ctx) == tier and eligible(r, ctx) and not blocked(r)]
        if members:
            add(random.choice(sorted(members, key=lambda r: r.id)), f"replaced {name}")
        else:
            logging.warning("%s: no eligible %s objective is left to replace '%s'.", tag, TIER_NAMES[tier], name)
    # (3) everything still open comes from the tier mix
    if len(drawn) < count:
        _fill_mix(random, ctx, drawn, _remaining_wanted(count, drawn, weights), False, "tier mix")
