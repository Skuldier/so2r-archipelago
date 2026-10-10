"""Monster drops (docs/LOOT_TIERS_IDEAS.md, "Monster drops (implemented)"): the table slot_data["drops"] hands the plugin so
won battles can drop world-level-scaled equipment on the client. Drops are local, never Archipelago items.

Every non-gag piece of gear in data/gear.json gets a band 0-9 (higher = stronger):
  - weapons: attack deciles across all weapons (sorted by power, then id);
  - armor-type gear: deciles within each of ARMOR, SHIELD, HELMET and GREEVE, so each category spans 0-9;
  - accessories: power is mostly 0, so band by rarity: N 0-2, R 3-5, SR 6-7, SSR 8-9, spread evenly within the
    range by item id order.
`band_levels[b]` is the world level at which band b becomes the normal drop band; the plugin drops around it. The list is computed per seed by `band_levels_for`: ten even steps from the seed's
`world_level_start` to `world_level_max`, forced strictly ascending (falls back to BAND_LEVELS without options).
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .gear_pool import GEAR
from .loot import (BONUS_BAND_SCALE, BONUS_COUNTS, FACTORS, LOOT_TIER_NAMES, SLOT_ACCESSORY, SLOT_ARMOR, SLOT_WEAPON, UNIQUE_LISTED_MULTIPLIER,
                   UNIQUES, bonus_pool_data, cursed_pool_data, signature_pool_data, stat_pool_data)

SLOT_DATA_VERSION = 1
BANDS = 10
ACCESSORY_BANDS = {"N": (0, 2), "R": (3, 5), "SR": (6, 7), "SSR": (8, 9)}
# Fallback when the world level options are absent (hand-built test namespaces); real seeds use band_levels_for().
BAND_LEVELS: List[int] = [1, 8, 16, 25, 33, 41, 50, 58, 66, 75]
FACTOR_RARITY = {"N": 1, "R": 2}


def band_levels_for(options=None) -> List[int]:
    """Per-seed band_levels: round(start + i * (max - start) / 9), strictly ascending, band 0 at start (min 1)."""
    try:
        start = int(options.world_level_start.value)
        top = int(options.world_level_max.value)
    except AttributeError:
        return list(BAND_LEVELS)
    levels = [max(1, start)]
    for i in range(1, BANDS):
        levels.append(max(round(start + i * (top - start) / (BANDS - 1)), levels[-1] + 1))
    return levels


def _deciles(rows: list) -> Dict[int, int]:
    """Gear id -> band 0..9 by position in (power, id) order."""
    ordered = sorted(rows, key=lambda gear: (gear.power, gear.id))
    return {gear.id: index * BANDS // len(ordered) for index, gear in enumerate(ordered)}


def _accessory_bands(rows: list) -> Dict[int, int]:
    bands: Dict[int, int] = {}
    for rarity, (low, high) in ACCESSORY_BANDS.items():
        ordered = sorted((gear for gear in rows if gear.rarity == rarity), key=lambda gear: gear.id)
        span = high - low + 1
        for index, gear in enumerate(ordered):
            bands[gear.id] = low + index * span // len(ordered)
    return bands


def build_table() -> List[List[int]]:
    """[[item_id, slot (1 weapon, 2 armor, 4 accessory), equip_mask, band], ...] in item id order."""
    usable = [gear for gear in GEAR if not gear.gag]
    bands: Dict[int, int] = {}
    bands.update(_deciles([gear for gear in usable if gear.slot == "weapon"]))
    for category in sorted({gear.category for gear in usable if gear.slot == "armor"}):
        bands.update(_deciles([gear for gear in usable if gear.slot == "armor" and gear.category == category]))
    bands.update(_accessory_bands([gear for gear in usable if gear.slot == "accessory"]))
    slots = {"weapon": SLOT_WEAPON, "armor": SLOT_ARMOR, "accessory": SLOT_ACCESSORY}
    return [[gear.id, slots[gear.slot], gear.equip, bands[gear.id]] for gear in sorted(usable, key=lambda g: g.id)]


def slot_data(chance: int, chain_bonus: int, boss_always: bool, tier_weights: Dict[str, int],
              options=None, bonus_effects: bool = False, enabled: bool = True,
              cursed_weight: Optional[int] = None, stat_bonuses: bool = False, signature: bool = False) -> dict:
    """enabled False = table only (Feats without Monster Drops): no random drops, the plugin only rolls feat rewards."""
    data = {
        "version": SLOT_DATA_VERSION,
        "enabled": bool(enabled),
        "chance": int(chance) if enabled else 0,
        "chain_bonus": int(chain_bonus) if enabled else 0,
        "boss_always": bool(boss_always) if enabled else False,
        "tier_weights": {name: int(tier_weights.get(name, 0)) for name in LOOT_TIER_NAMES},
        "unique_multiplier": UNIQUE_LISTED_MULTIPLIER,
        "band_levels": band_levels_for(options),
        "table": build_table(),
        "factors": [[row["id"], row["mask"], FACTOR_RARITY[row["rarity"]], row["weight"]] for row in FACTORS],
        "uniques": [[row["item_id"], row["factor"]] for row in UNIQUES],
    }
    if bonus_effects:  # Loot Bonus Effects: the plugin rolls the same bonuses on drops (band groups 0-3, 4-6, 7-9 -> scale)
        data["bonus_pool"] = bonus_pool_data()
        data["bonus_band_scale"] = list(BONUS_BAND_SCALE)
        data["bonus_counts"] = dict(BONUS_COUNTS)
    if stat_bonuses:  # Loot Stat Bonuses: Magic drops get one stat, Rare/Unique draw from bonus_pool + stat_pool
        data["stat_pool"] = stat_pool_data()
    if signature:  # Unique Signature Effects: a Unique drop appends one row fitting its slot and equip mask
        data["signature_pool"] = signature_pool_data()
    if cursed_weight is not None:  # Cursed Loot: the plugin rolls Cursed drops from this block
        data["cursed"] = {"weight": int(cursed_weight), **cursed_pool_data()}
    return data
