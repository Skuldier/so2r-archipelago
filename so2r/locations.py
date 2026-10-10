"""Location table for the SO2R Archipelago world (chests and bosses).

Ids follow ArchipelagoIds.cs / docs/APWORLD.md exactly:
  - chest location:         5_500_000 + chest flag
  - boss location:          5_600_000 + enemy party id
  - guild mission location: 5_800_000 + quest id (docs/MISSIONS.md "World data
    (guild_missions option)"; the plugin does not send this check yet)
  - challenge mission location: 5_820_000 + native MissionID (docs/MISSIONS.md "Challenge Missions as checks")
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List

from BaseClasses import Location, LocationProgressType

from .items import vanilla_content_name
from .resources import read_json

CHEST_LOCATION_ID_BASE = 5_500_000
BOSS_LOCATION_ID_BASE = 5_600_000
GUILD_MISSION_LOCATION_ID_BASE = 5_800_000
CHALLENGE_MISSION_LOCATION_ID_BASE = 5_820_000

GAME_NAME = "Star Ocean: The Second Story R"


class SO2RLocation(Location):
    game = GAME_NAME


@dataclass(frozen=True)
class ChestLocationData:
    address: int
    flag: int
    fieldmap: str
    area: str
    reward_type: str
    value: int
    count: int
    excluded_progress: bool
    group: str  # "main" | "maze"
    vanilla_item_name: str
    region: str  # locality id ("EXPEL"/"NEDE" for the overworlds)
    story_progress_required: int | None  # authored in-region story gate, see
    # tools/apworld/data/chest_story_gates.json / docs/LOGIC_DESIGN.md
    postgame: bool  # only exists after the ending (maze, VR Expel); docs/LOGIC_AUDIT.md
    access_progress: int | None = None  # audited physical access point (docs/ACCESS_AUDIT.md);
    # never later than the region's first touch or earlier than the authored gate


@dataclass(frozen=True)
class BossLocationData:
    address: int
    party_id: int
    boss_name: str
    group: str  # "story" | "optional" | "raid" (never "scripted"; see _build_boss_table())
    goal: bool
    region: str | None  # locality id, or None if not yet placed (see boss_regions.json)
    condition: str | None  # None | "claude_route" | "rena_route" | "opera_recruitment" |
    # "ashton_recruitment" | "ernest_recruitment" | "private_action" -- gates this party's
    # existence in a given playthrough; see SO2RWorld._active_boss_locations().
    story_progress: int | None  # window start of the battle event that starts the fight
    missable: bool  # the fight can be permanently skipped; the check is EXCLUDED
    postgame: bool  # only exists after the ending (clear save); docs/LOGIC_AUDIT.md


@dataclass(frozen=True)
class GuildMissionLocationData:
    address: int
    quest_id: int
    quest_key: str  # "QUEST_048"
    category: str  # ITEM_GET | LEARNING | APPRAISAL | FACTOR_MATERIAL
    start_progress: int
    region: str  # locality id, the latest region <= start_progress
    story_progress_required: int  # == start_progress; gated via chest_story_gate_rule()
    skill: str | None  # special_skill or super_special_skill, whichever is set
    target: dict | None  # {"item_id", "item", "count"} or None (LEARNING rows)
    pool_item_kind: str  # "item" | "fol" | "filler" (see build_guild_missions())
    pool_item_name: str | None  # the AP item this location grants; None when kind is
    # "filler" -- SO2RWorld picks a random filler name at create_items() time instead
    vanilla_rewards: List[dict]  # informational only, every reward row (doc/tracker)


@dataclass(frozen=True)
class ChallengeMissionLocationData:
    address: int
    mission_id: int
    tab: str  # Beginner | Expert | Specialist | Legend
    text: str  # the in-game text, thousands separators included
    mission_type: str  # BT_* | OT_* | SK_*
    value: int
    tier: int  # 1..4, see data/challenge_missions.json tier_rules
    previous: int | None
    start_progress: int
    requires: dict  # {"chests": N, "nede": True, "story_progress": P}
    no_progression: bool  # a grind: the location refuses progression items


def _load_chests() -> List[dict]:
    return read_json("chests.json")


def _load_bosses() -> List[dict]:
    return read_json("bosses.json")


def _load_guild_missions() -> dict:
    return read_json("guild_missions.json")


_ITEM_ID_SUFFIX = re.compile(r" \(#\d+\)")


def _display_item_name(item_name: str) -> str:
    """The vanilla item name as shown inside a chest location name.

    Item names carry a " (#id)" suffix when several game items share a display name (every
    unidentified "?WEAPON"/"?ARMOR" placeholder, for instance). The chest flag already makes the
    location name unique, so the suffix is dropped here; the pool still uses the full item name."""
    return _ITEM_ID_SUFFIX.sub("", item_name)


def _build_chest_table() -> Dict[str, ChestLocationData]:
    table: Dict[str, ChestLocationData] = {}
    for chest in _load_chests():
        vanilla_name = vanilla_content_name(chest)
        loc_name = f"{chest['area']} Chest {chest['flag']} ({_display_item_name(vanilla_name)})"
        assert loc_name not in table, f"duplicate chest location name {loc_name!r}"
        table[loc_name] = ChestLocationData(
            address=CHEST_LOCATION_ID_BASE + chest["flag"],
            flag=chest["flag"],
            fieldmap=chest["fieldmap"],
            area=chest["area"],
            reward_type=chest["rewardType"],
            value=chest["value"],
            count=chest["count"],
            excluded_progress=chest["excluded_progress"],
            group=chest["group"],
            vanilla_item_name=vanilla_name,
            region=chest["region"],
            story_progress_required=chest.get("story_progress_required"),
            postgame=chest["postgame"],
            access_progress=chest.get("access_progress"),
        )
    return table


def _build_boss_table() -> Dict[str, BossLocationData]:
    table: Dict[str, BossLocationData] = {}
    for boss in _load_bosses():
        if boss["group"] == "scripted":
            # The game ends this fight without a normal win (see boss_regions.json's
            # `scripted` flag); it stays documented in bosses.json but must never become
            # an Archipelago location, so no seed can ever contain an uncompletable check.
            continue
        loc_name = f"Boss: {boss['name']}"
        assert loc_name not in table, f"duplicate boss location name {loc_name!r}"
        table[loc_name] = BossLocationData(
            address=BOSS_LOCATION_ID_BASE + boss["id"],
            party_id=boss["id"],
            boss_name=boss["name"],
            group=boss["group"],
            goal=boss["goal"],
            region=boss["region"],
            condition=boss.get("condition"),
            story_progress=boss["story_progress"],
            missable=boss["missable"],
            postgame=boss["postgame"],
        )
    return table


def _build_guild_mission_table() -> Dict[str, GuildMissionLocationData]:
    table: Dict[str, GuildMissionLocationData] = {}
    for quest in _load_guild_missions()["missions"]:
        loc_name = f"Guild Mission: {quest['name']}"
        assert loc_name not in table, f"duplicate guild mission location name {loc_name!r}"
        table[loc_name] = GuildMissionLocationData(
            address=GUILD_MISSION_LOCATION_ID_BASE + quest["id"],
            quest_id=quest["id"],
            quest_key=quest["quest_id"],
            category=quest["category"],
            start_progress=quest["start_progress"],
            region=quest["region"],
            story_progress_required=quest["story_progress_required"],
            skill=quest["skill"],
            target=quest["target"],
            pool_item_kind=quest["pool_item"]["kind"],
            pool_item_name=quest["pool_item"]["name"],
            vanilla_rewards=quest["vanilla_rewards"],
        )
    return table


def _load_challenge_missions() -> dict:
    return read_json("challenge_missions.json")


def _build_challenge_mission_table() -> Dict[str, ChallengeMissionLocationData]:
    data = _load_challenge_missions()
    assert data["location_base"] == CHALLENGE_MISSION_LOCATION_ID_BASE
    table: Dict[str, ChallengeMissionLocationData] = {}
    for row in data["missions"]:
        assert row["name"] not in table, f"duplicate challenge mission location name {row['name']!r}"
        table[row["name"]] = ChallengeMissionLocationData(
            address=CHALLENGE_MISSION_LOCATION_ID_BASE + row["id"],
            mission_id=row["id"],
            tab=row["tab"],
            text=row["text"],
            mission_type=row["type"],
            value=row["value"],
            tier=row["tier"],
            previous=row["previous"],
            start_progress=row["start_progress"],
            requires=row["requires"],
            no_progression=row["no_progression"],
        )
    return table


CHEST_LOCATION_TABLE: Dict[str, ChestLocationData] = _build_chest_table()
BOSS_LOCATION_TABLE: Dict[str, BossLocationData] = _build_boss_table()
GUILD_MISSION_LOCATION_TABLE: Dict[str, GuildMissionLocationData] = _build_guild_mission_table()
CHALLENGE_MISSION_LOCATION_TABLE: Dict[str, ChallengeMissionLocationData] = _build_challenge_mission_table()
CHALLENGE_MISSION_TIER_RULES: dict = _load_challenge_missions()["tier_rules"]

_CHALLENGE_FAMILIES = {"BT": "Battle", "OT": "Exploration", "SK": "Skills"}


def location_name_groups() -> Dict[str, set]:
    groups: Dict[str, set] = {
        "Chests": set(),
        "Bosses": set(),
        "Story Bosses": set(),
        "Optional Bosses": set(),
        "Raid Bosses": set(),
        "Maze Chests": set(),
        "Guild Missions": set(),
    }
    for name, data in CHEST_LOCATION_TABLE.items():
        groups["Chests"].add(name)
        groups.setdefault(data.fieldmap, set()).add(name)
        groups.setdefault(data.area, set()).add(name)
        if data.group == "maze":
            groups["Maze Chests"].add(name)
    for name, data in BOSS_LOCATION_TABLE.items():
        groups["Bosses"].add(name)
        if data.group == "story":
            groups["Story Bosses"].add(name)
        elif data.group == "optional":
            groups["Optional Bosses"].add(name)
        elif data.group == "raid":
            groups["Raid Bosses"].add(name)
    for name in GUILD_MISSION_LOCATION_TABLE:
        groups["Guild Missions"].add(name)
    for name, data in CHALLENGE_MISSION_LOCATION_TABLE.items():
        groups.setdefault("Challenge Missions", set()).add(name)
        groups.setdefault(f"Challenge Missions: {data.tab}", set()).add(name)
        groups.setdefault(f"Challenge Missions: Tier {data.tier}", set()).add(name)
        family = _CHALLENGE_FAMILIES[data.mission_type.split("_", 1)[0]]
        groups.setdefault(f"Challenge Missions: {family}", set()).add(name)
    return {k: v for k, v in groups.items() if v}


__all__ = [
    "CHEST_LOCATION_ID_BASE",
    "BOSS_LOCATION_ID_BASE",
    "GUILD_MISSION_LOCATION_ID_BASE",
    "CHALLENGE_MISSION_LOCATION_ID_BASE",
    "SO2RLocation",
    "ChestLocationData",
    "BossLocationData",
    "GuildMissionLocationData",
    "ChallengeMissionLocationData",
    "CHEST_LOCATION_TABLE",
    "BOSS_LOCATION_TABLE",
    "GUILD_MISSION_LOCATION_TABLE",
    "CHALLENGE_MISSION_LOCATION_TABLE",
    "CHALLENGE_MISSION_TIER_RULES",
    "location_name_groups",
    "LocationProgressType",
]
