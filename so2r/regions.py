"""Region table for the SO2R Archipelago world (Milestone 8 step 1: a data-driven
story-progress region model, no access rules yet).

Loads apworld/so2r/data/regions.json, built by tools/apworld/build_data.py from the
game's own story-progress event spine plus a handful of authored estimates for
localities the spine never names. See docs/LOGIC_DESIGN.md for the full derivation.

Every region is created and chained linearly from Menu in ascending story_index order
with no access rules -- everything stays reachable exactly as it was before this
model existed. This only changes location->region assignment (and therefore spoiler
log region names); nothing about generation output changes for players yet.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .resources import read_json


@dataclass(frozen=True)
class RegionData:
    id: str
    name: str
    continent: str
    story_progress: int | None
    missable: bool
    note: str
    story_index: int
    key_item_id: int | None  # region_keys.json item id, or None if this region has no key
    fast_travel_id: int | None  # the key's fast-travel destination id, or None


def _load_regions() -> List[dict]:
    return read_json("regions.json")


def _build_region_table() -> Dict[str, RegionData]:
    table: Dict[str, RegionData] = {}
    for region in _load_regions():
        table[region["id"]] = RegionData(
            id=region["id"],
            name=region["name"],
            continent=region["continent"],
            story_progress=region["story_progress"],
            missable=region["missable"],
            note=region["note"],
            story_index=region["story_index"],
            key_item_id=region.get("key_item_id"),
            fast_travel_id=region.get("fast_travel_id"),
        )
    return table


REGION_TABLE: Dict[str, RegionData] = _build_region_table()

# Regions in ascending story_index order (the linear chain order used by create_regions()).
REGIONS_IN_STORY_ORDER: List[RegionData] = sorted(
    REGION_TABLE.values(), key=lambda r: r.story_index
)

UNPLACED_BOSSES_REGION_NAME = "Unplaced Bosses"


def ap_region_name(region_id: str) -> str:
    """The AP Region display name for a locality/overworld id."""
    return REGION_TABLE[region_id].name


__all__ = [
    "RegionData",
    "REGION_TABLE",
    "REGIONS_IN_STORY_ORDER",
    "UNPLACED_BOSSES_REGION_NAME",
    "ap_region_name",
]
