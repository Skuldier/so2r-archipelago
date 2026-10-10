"""Open-world game mode data (docs/OPEN_WORLD_PLAN.md).

The open world runs at the Final Voyage hold (story progress 5900200) with the hub profile's flags, the Psynard over
both planets, towns open and one area key per dungeon (§7.3 option (a)). data/open_world.json is written by
tools/apworld/build_open_world_areas.py from the physical access model at the hub (docs/OPEN_WORLD_AREAS.md): each
area's chests that are there and reachable for both heroes, and the area keys with their stable ids
(5_770_000 + the area's MF_00NN number).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .resources import read_json

_DATA = read_json("open_world.json")

# Rooms in open-world mode; older clients must refuse them (ArchipelagoIds.OpenWorldMappingVersion).
# v3 = v1 plus slot_data.open_world.dungeon_travel (plugin 0.70.0).
OPEN_WORLD_MAPPING_VERSION = "so2r-ids-v1-open-world-v3"
# Open-world rooms with the generated item pool (slot_data.gear, Progressive Weapon items; docs/GEAR_POOL.md). A plugin
# before 0.62.0 cannot apply a progressive weapon, so it must refuse these (ArchipelagoIds.OpenWorldGearMappingVersion). v4 = v2 plus dungeon_travel.
OPEN_WORLD_GEAR_MAPPING_VERSION = "so2r-ids-v1-open-world-v4"
HUB_PROGRESS: int = _DATA["hub_progress"]
# Phynal: reached by the Final Voyage, which the four Orbs release (§7.4); its area needs the Orbs, not a key.
GOAL_REGION_ID: str = _DATA["goal_region"]
START_DESTINATIONS: Dict[str, int] = dict(_DATA["start_destinations"])
PLANETS: Tuple[str, ...] = ("EXPEL", "NEDE")
FINAL_VOYAGE_EVENT = "ev_5900200"
FINAL_VOYAGE_NEXT_PROGRESS = 5900500
ORB_NAMES: Tuple[str, ...] = ("Orb of Wisdom", "Orb of Might", "Orb of Courage", "Orb of Love")
MAZE_REGION_ID = "MF_0051"
# Dungeon -> FastTravel row id of its entrance (the ENTER row at its first map), read from the live game. Its area key
# also opens that Guide Map point, so on a locked planet the key alone puts the dungeon in logic. The maze (the Guide
# Map is off there) and Phynal (no key) are not listed.
DUNGEON_TRAVEL: Dict[str, int] = {
    "MF_0002": 1, "MF_0005": 4, "MF_0008": 9, "MF_0011": 14, "MF_0013": 16, "MF_0014": 19, "MF_0020": 26,
    "MF_0022": 29, "MF_0027": 34, "MF_0033": 43, "MF_0036": 46, "MF_0037": 47, "MF_0038": 49, "MF_0039": 52,
    "MF_0042": 55,
}


@dataclass(frozen=True)
class AreaKeyData:
    item_id: int
    name: str
    locality: str


@dataclass(frozen=True)
class OpenWorldArea:
    locality: str
    name: str
    planet: str
    dungeon: bool
    chests: Tuple[int, ...]


AREA_KEYS: List[AreaKeyData] = [AreaKeyData(k["item_id"], k["name"], k["locality"]) for k in _DATA["area_keys"]]
AREA_KEY_BY_LOCALITY: Dict[str, AreaKeyData] = {k.locality: k for k in AREA_KEYS}
OPEN_WORLD_AREAS: Dict[str, OpenWorldArea] = {
    a["locality"]: OpenWorldArea(a["locality"], a["name"], a["planet"], a["dungeon"], tuple(a["chests"]))
    for a in _DATA["areas"]
}
# Chest flag -> its area, for every town and dungeon chest that is there and reachable at the hub.
OPEN_WORLD_CHEST_AREA: Dict[int, str] = {flag: a.locality for a in OPEN_WORLD_AREAS.values() for flag in a.chests}
# Kurik's early maps are gone at the hub and the Symbological Weapons Lab is only ever entered by a story scene.
LOST_CHESTS: Tuple[int, ...] = tuple(_DATA["lost_chests"])


@dataclass(frozen=True)
class BossSpot:
    """A story boss restaged where its scene would have started it (OPEN_WORLD_PLAN.md Phase 2): the boss scene's own
    trigger, an event collision on `map` named `event`, or entering `map` when `event` is None."""
    party_id: int
    name: str
    locality: str
    map: str
    event: Optional[str]
    condition: Optional[str]


BOSS_SPOTS: List[BossSpot] = [
    BossSpot(s["party_id"], s["name"], s["locality"], s["map"], s["event"], s.get("condition"))
    for s in _DATA.get("boss_spots", [])
]

