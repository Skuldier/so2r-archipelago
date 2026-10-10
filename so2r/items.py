"""Item table for the SO2R Archipelago world.

Ids follow ArchipelagoIds.cs / docs/APWORLD.md exactly:
  - game item x1:      5_000_000 + item id
  - game item xN (2..10): 5_000_000 + 10_000 * (N - 1) + item id
  - Fol:                5_100_000 + amount / 10   (amount is always a multiple of 10)
  - filler placeholder ids reuse the same bands above (they are ordinary game items/Fol)

Only data/items.json and data/chests.json are read (both checked in); no dependency on
the predecessor dumps at import time.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

from BaseClasses import Item, ItemClassification
from .characters import CHARACTERS
from .descent import DEPTH_SEAL_ID, DEPTH_SEAL_NAME
from .gear_pool import FOL_AMOUNTS as GEAR_FOL_AMOUNTS, GEAR
from .open_world import AREA_KEYS
from .resources import read_json

ITEM_ID_BASE = 5_000_000
BUNDLE_BAND_STEP = 10_000
FOL_ID_BASE = 5_100_000
# Progressive weapons (docs/GEAR_POOL.md): 5_860_000 + PlayerID, one item per character; the n-th copy received is
# that character's n-th rung in slot_data.gear.progressive_weapons (ArchipelagoIds.ProgressiveWeaponItemBase).
PROGRESSIVE_WEAPON_BASE = 5_860_000
# Traps: 5_910_001..5_910_011 (band 5_910_000-5_910_099). Junk items with ItemClassification.trap; the plugin (0.72.0+)
# applies each as a short, harmless setback. Ids and names are shared with the plugin; do not change them.
TRAP_ID_BASE = 5_910_000
TRAPS: List[tuple] = [  # (item id, name, kind)
    (5_910_001, "Ambush Trap", "field"),
    (5_910_002, "Monster Magnet Trap", "field"),
    (5_910_003, "Chain Trap", "field"),
    (5_910_004, "Lost Trap", "field"),
    (5_910_005, "Heavy Boots Trap", "field"),
    (5_910_006, "Oracle Trap", "field"),
    (5_910_007, "Muzak Trap", "field"),
    (5_910_008, "Empowered Foes Trap", "battle"),
    (5_910_009, "Back Attack Trap", "battle"),
    (5_910_010, "Status Trap", "battle"),
    (5_910_011, "Fatigue Trap", "battle"),
    # 5_910_012 is retired (2026-10-01; plugin applies it with no effect). Never reuse the id.
]
TRAP_NAMES: List[str] = [name for _id, name, _kind in TRAPS]

GAME_NAME = "Star Ocean: The Second Story R"


# Filler placeholders granted for boss locations: (game item id, count).
FILLER_ITEM_SPECS: List[tuple] = [
    (756, 3),   # Blackberries x3
    (757, 3),   # Blueberries x3
    (277, 1),   # Resurrection Elixir x1
]
FILLER_FOL_AMOUNT = 5000


@dataclass(frozen=True)
class ItemData:
    code: int
    classification: ItemClassification
    category: str
    game_item_id: int  # 0 for Fol
    count: int          # bundle count (1 for a single item, 0 for Fol)
    is_fol: bool
    fol_amount: int      # 0 for non-Fol


class SO2RItem(Item):
    game = GAME_NAME


# BOOK is Leon's weapon type (all 18 BOOK items carry the weapon type bit).
WEAPON_CATEGORIES = {
    "SWORD", "KNUCKLE", "TWIN_SWORD", "WAND", "WHIP", "STUNGUN", "GUN_AND_DISK", "ROD", "PUNCH", "BOOK",
}
ARMOR_CATEGORIES = {"ARMOR", "HELMET", "GREEVE", "SHIELD"}
ACCESSORY_CATEGORIES = {"ACCESSORY"}
EQUIPMENT_CATEGORIES = WEAPON_CATEGORIES | ARMOR_CATEGORIES | ACCESSORY_CATEGORIES


def _classify(category: str, rarity: str) -> ItemClassification:
    """Chest loot never gates logic, so it is useful or filler. Every weapon, armor
    piece and accessory is useful whatever its rarity, as is any other rare (SR/SSR)
    item; common consumables, materials, unidentified items and the like are filler.
    Useful items never land on an excluded (missable or post-game) location."""
    if category in EQUIPMENT_CATEGORIES or rarity in ("SR", "SSR"):
        return ItemClassification.useful
    return ItemClassification.filler


def fol_item_code(amount: int) -> int:
    assert amount % 10 == 0, f"Fol amount {amount} is not a multiple of 10"
    return FOL_ID_BASE + amount // 10


def fol_item_name(amount: int) -> str:
    return f"{amount} Fol"


def bundle_item_code(game_item_id: int, count: int) -> int:
    assert 1 <= count <= 10, f"bundle count {count} out of range"
    return ITEM_ID_BASE + BUNDLE_BAND_STEP * (count - 1) + game_item_id


def bundle_item_name(base_name: str, count: int) -> str:
    if count <= 1:
        return base_name
    return f"{base_name} ×{count}"


def progressive_weapon_name(player_id: int) -> str:
    return f"Progressive Weapon: {CHARACTERS[player_id].label}"


def progressive_weapon_code(player_id: int) -> int:
    return PROGRESSIVE_WEAPON_BASE + player_id


def _load_base_items() -> Dict[int, dict]:
    raw = read_json("items.json")
    return {entry["id"]: entry for entry in raw}


def _load_chests() -> List[dict]:
    return read_json("chests.json")


def _load_region_keys() -> List[dict]:
    return read_json("region_keys.json")


def _load_chapter_keys() -> List[dict]:
    return read_json("chapter_keys.json")


def _load_resource_packs() -> List[dict]:
    return read_json("resource_packs.json")


def _load_key_items() -> List[dict]:
    return read_json("key_items.json")


def _load_guild_missions() -> List[dict]:
    return read_json("guild_missions.json")["missions"]


@dataclass(frozen=True)
class RegionKeyData:
    item_id: int
    name: str
    region: str  # locality id
    region_name: str
    fast_travel_id: int
    fieldmap: str
    arrival: str  # "Position" | "Mapjump"
    available_from: int | None  # the destination row's story window start; the Guide
    # Map does not list the destination earlier (docs/LOGIC_AUDIT.md)
    barrier_progress: int | None  # an in-region story barrier the key cannot bypass
    # (Forest of Symbols, Eluria Tower, Field of Love, Minae Cave; docs/KEY_ITEMS.md)


REGION_KEYS: List[RegionKeyData] = [
    RegionKeyData(
        item_id=k["item_id"],
        name=k["name"],
        region=k["region"],
        region_name=k["region_name"],
        fast_travel_id=k["fast_travel_id"],
        fieldmap=k["fieldmap"],
        arrival=k["arrival"],
        available_from=k["available_from"],
        barrier_progress=k["barrier_progress"],
    )
    for k in _load_region_keys()
]
REGION_KEY_BY_NAME: Dict[str, RegionKeyData] = {k.name: k for k in REGION_KEYS}
REGION_KEY_BY_REGION: Dict[str, RegionKeyData] = {k.region: k for k in REGION_KEYS}


@dataclass(frozen=True)
class ChapterKeyData:
    item_id: int
    n: int
    label: str  # short name, e.g. "Royal Audience"
    name: str  # display item name, "Chapter Key: <label>"
    events: List[str]
    unlocks_progress: int
    enabled: bool


# Every chapter key candidate (docs/LOGIC_DESIGN.md "Chapter gate candidates"), including
# ones not yet live-verified (enabled=False). item_name_to_id must stay static regardless
# of `enabled`, so every entry here is always added to ITEM_TABLE below; only
# CHAPTER_KEYS_ENABLED (and everything downstream of it) is option-visible.
CHAPTER_KEYS: List[ChapterKeyData] = [
    ChapterKeyData(
        item_id=k["item_id"],
        n=k["n"],
        label=k["label"],
        name=k["name"],
        events=list(k["events"]),
        unlocks_progress=k["unlocks_progress"],
        enabled=k["enabled"],
    )
    for k in _load_chapter_keys()
]
CHAPTER_KEY_BY_NAME: Dict[str, ChapterKeyData] = {k.name: k for k in CHAPTER_KEYS}

# The subset the world actually pools, rules, and reports in slot_data (rules.py,
# __init__.py). Never widen this by anything other than flipping an entry's `enabled` in
# tools/apworld/data/chapter_keys.json.
CHAPTER_KEYS_ENABLED: List[ChapterKeyData] = [k for k in CHAPTER_KEYS if k.enabled]


@dataclass(frozen=True)
class KeyItemData:
    """A story key item that holds its own scene (docs/KEY_ITEMS.md). The AP item is the
    ordinary game item id, delivered to the inventory under slot_data.story_keys; the
    plugin refuses `events` until it is received, exactly like a chapter key."""
    item_id: int
    native_id: int
    name: str
    events: List[str]
    route: str | None  # "claude" / "rena" when only that route has the scene
    unlocks_progress: int
    replaces_chapter_key: int | None  # chapter key n whose event this key already holds
    gated_bosses: List[int]  # battles inside the region that need this key's scene
    gated_regions: List[str]  # regions whose chests conservatively need this key


KEY_ITEMS: List[KeyItemData] = [
    KeyItemData(
        item_id=k["item_id"],
        native_id=k["native_id"],
        name=k["name"],
        events=list(k["events"]),
        route=k["route"],
        unlocks_progress=k["unlocks_progress"],
        replaces_chapter_key=k["replaces_chapter_key"],
        gated_bosses=list(k["gated_bosses"]),
        gated_regions=list(k["gated_regions"]),
    )
    for k in _load_key_items()
]
KEY_ITEM_BY_NAME: Dict[str, KeyItemData] = {k.name: k for k in KEY_ITEMS}


@dataclass(frozen=True)
class ResourcePackData:
    """One resource pack (docs/RESOURCE_PACKS.md): several ordinary items granted at
    once. The plugin reads the contents from slot_data.resource_packs."""
    item_id: int
    name: str
    pack: str  # "Restorative", "Cooking", ...
    size: str  # "small" (filler) | "large" (useful)
    weight: int
    contents: List[tuple]  # (native item id, count)


RESOURCE_PACKS: List[ResourcePackData] = [
    ResourcePackData(
        item_id=p["item_id"],
        name=p["name"],
        pack=p["pack"],
        size=p["size"],
        weight=p["weight"],
        contents=[(c["item_id"], c["count"]) for c in p["contents"]],
    )
    for p in _load_resource_packs()
]
SMALL_PACKS: List[ResourcePackData] = [p for p in RESOURCE_PACKS if p.size == "small"]
LARGE_PACKS: List[ResourcePackData] = [p for p in RESOURCE_PACKS if p.size == "large"]
# With resource packs on, a chest keeps its own content only when that is equipment, a
# book (the skill guidebooks and the symbology books) or Fol. Everything else becomes a
# pack: consumables, cooked dishes, materials, fish, unidentified "?" items and curios.
KEPT_CHEST_CATEGORIES = EQUIPMENT_CATEGORIES | {"BOOK"}


def keeps_chest_content(name: str) -> bool:
    data = ITEM_TABLE[name]
    if data.is_fol or data.category in KEPT_CHEST_CATEGORIES:
        return True
    return data.category == "OTHER" and bool(ITEM_META_BY_GAME_ID[data.game_item_id].get("skill_book"))


def _build_table():
    base_items = _load_base_items()
    chests = _load_chests()

    table: Dict[str, ItemData] = {}
    # game item id -> (base name, category, rarity), used by locations.py to name chests.
    item_meta_by_id: Dict[int, dict] = base_items

    def add_game_item(game_item_id: int, count: int) -> str:
        entry = base_items[game_item_id]
        name = bundle_item_name(entry["name"], count)
        if name not in table:
            table[name] = ItemData(
                code=bundle_item_code(game_item_id, count),
                classification=_classify(entry["category"], entry["rarity"]),
                category=entry["category"],
                game_item_id=game_item_id,
                count=count,
                is_fol=False,
                fol_amount=0,
            )
        return name

    def add_fol(amount: int) -> str:
        name = fol_item_name(amount)
        if name not in table:
            table[name] = ItemData(
                code=fol_item_code(amount),
                classification=ItemClassification.filler,
                category="FOL",
                game_item_id=0,
                count=0,
                is_fol=True,
                fol_amount=amount,
            )
        return name

    # Vanilla chest contents (every chest in data/chests.json, regardless of options --
    # id tables are static; option gating only affects which locations/items are active).
    for chest in chests:
        if chest["rewardType"] == "ITEM":
            add_game_item(chest["value"], chest["count"])
        elif chest["rewardType"] == "FOL":
            add_fol(chest["value"])

    # Filler pool for boss locations.
    for game_item_id, count in FILLER_ITEM_SPECS:
        add_game_item(game_item_id, count)
    add_fol(FILLER_FOL_AMOUNT)

    # Every weapon, armor piece and accessory (data/gear.json), for the generated pool (docs/GEAR_POOL.md). The
    # names follow the same full-dump uniqueness rule as data/items.json, so a piece already present is the same item.
    for gear in GEAR:
        name = gear.name
        code = bundle_item_code(gear.id, 1)
        if name in table:
            assert table[name].code == code, f"gear name {name!r} collides with another item"
            continue
        table[name] = ItemData(code, _classify(gear.category, gear.rarity), gear.category, gear.id, 1, False, 0)
    for amount in GEAR_FOL_AMOUNTS:
        add_fol(amount)

    # Guild mission pool items (docs/MISSIONS.md "World data (guild_missions option)"):
    # every location's resolved pool item is always added here, independent of the
    # guild_missions option, the same always-present-in-the-table split used by region
    # and chapter keys above -- pool membership (create_items()) is what the option
    # actually gates. A "filler" kind needs no table entry: SO2RWorld picks one of the
    # already-present FILLER_ITEM_NAMES at create_items() time.
    for quest in _load_guild_missions():
        pool_item = quest["pool_item"]
        if pool_item["kind"] == "item":
            add_game_item(pool_item["game_item_id"], pool_item["count"])
        elif pool_item["kind"] == "fol":
            add_fol(pool_item["amount"])

    # Region keys (docs/PROGRESSION_DESIGN.md §4, region_keys option). item_name_to_id
    # must be static: every key is always in ITEM_TABLE regardless of the option; only
    # pool membership (create_items()) depends on region_keys being on.
    for key in _load_region_keys():
        name = key["name"]
        assert name not in table, f"region key name collides with an existing item name {name!r}"
        table[name] = ItemData(
            code=key["item_id"],
            classification=ItemClassification.progression,
            category="REGION_KEY",
            game_item_id=0,
            count=0,
            is_fol=False,
            fol_amount=0,
        )

    # Chapter keys (family A, docs/PROGRESSION_DESIGN.md §4, chapter_keys option). Same
    # always-present-in-the-table / option-gated-pool split as region keys above.
    for key in _load_chapter_keys():
        name = key["name"]
        assert name not in table, f"chapter key name collides with an existing item name {name!r}"
        table[name] = ItemData(
            code=key["item_id"],
            classification=ItemClassification.progression,
            category="CHAPTER_KEY",
            game_item_id=0,
            count=0,
            is_fol=False,
            fol_amount=0,
        )

    # Key items (key_items option): the game item itself, so the id is the ordinary
    # single-item id. Same always-present-in-the-table / option-gated-pool split.
    for key in _load_key_items():
        name = key["name"]
        assert name not in table, f"key item name collides with an existing item name {name!r}"
        assert key["item_id"] == bundle_item_code(key["native_id"], 1)
        table[name] = ItemData(
            code=key["item_id"],
            classification=ItemClassification.progression,
            category="KEY_ITEM",
            game_item_id=key["native_id"],
            count=1,
            is_fol=False,
            fol_amount=0,
        )

    # Resource packs (resource_packs option): small packs are filler, large ones useful.
    for pack in _load_resource_packs():
        name = pack["name"]
        assert name not in table, f"resource pack name collides with an existing item name {name!r}"
        table[name] = ItemData(
            code=pack["item_id"],
            classification=(ItemClassification.useful if pack["size"] == "large"
                            else ItemClassification.filler),
            category="PACK",
            game_item_id=0,
            count=0,
            is_fol=False,
            fol_amount=0,
        )

    for trap_id, trap_name, _kind in TRAPS:
        assert trap_name not in table, f"trap name collides with an existing item name {trap_name!r}"
        table[trap_name] = ItemData(trap_id, ItemClassification.trap, "TRAP", 0, 0, False, 0)

    for character in CHARACTERS.values():
        table[character.name] = ItemData(character.item_id, ItemClassification.useful,
                                         "CHARACTER", 0, 0, False, 0)
        name = progressive_weapon_name(character.player_id)
        assert name not in table, f"progressive weapon name collides with an existing item name {name!r}"
        table[name] = ItemData(progressive_weapon_code(character.player_id), ItemClassification.useful,
                               "PROGRESSIVE_WEAPON", 0, 0, False, 0)

    # Open-world area keys (game_mode: open_world; docs/OPEN_WORLD_PLAN.md §7.3). Same always-present-in-the-table /
    # option-gated-pool split as the region and chapter keys.
    for key in AREA_KEYS:
        assert key.name not in table, f"area key name collides with an existing item name {key.name!r}"
        table[key.name] = ItemData(key.item_id, ItemClassification.progression, "AREA_KEY", 0, 0, False, 0)

    # Descent mode's one progression item: copy k opens the portal out of floor k (docs/descent/DESIGN_V1.md section 4).
    assert DEPTH_SEAL_NAME not in table, "depth seal name collides with an existing item name"
    table[DEPTH_SEAL_NAME] = ItemData(DEPTH_SEAL_ID, ItemClassification.progression, "DEPTH_SEAL", 0, 0, False, 0)
    return table, item_meta_by_id


ITEM_TABLE: Dict[str, ItemData] = {}
ITEM_META_BY_GAME_ID: Dict[int, dict] = {}
ITEM_TABLE, ITEM_META_BY_GAME_ID = _build_table()

FILLER_ITEM_NAMES: List[str] = [
    bundle_item_name(ITEM_META_BY_GAME_ID[game_item_id]["name"], count)
    for game_item_id, count in FILLER_ITEM_SPECS
] + [fol_item_name(FILLER_FOL_AMOUNT)]


def build_item_name_groups() -> Dict[str, set]:
    groups: Dict[str, set] = {"Fol": set(), "Bundles": set(), "Consumables": set(), "Equipment": set(),
                             "Characters": {character.name for character in CHARACTERS.values()},
                             "Progressive Weapons": {progressive_weapon_name(pid) for pid in CHARACTERS},
                             "Key Items": {key.name for key in KEY_ITEMS},
                             "Area Keys": {key.name for key in AREA_KEYS},
                             "Depth Seals": {DEPTH_SEAL_NAME},
                             "Resource Packs": {pack.name for pack in RESOURCE_PACKS},
                             "Traps": set(TRAP_NAMES)}
    for name, data in ITEM_TABLE.items():
        if data.is_fol:
            groups["Fol"].add(name)
            continue
        if data.count > 1:
            groups["Bundles"].add(name)
        if data.category == "BATTLE":
            groups["Consumables"].add(name)
        if data.category in EQUIPMENT_CATEGORIES:
            groups["Equipment"].add(name)
    return {k: v for k, v in groups.items() if v}


def vanilla_content_name(chest: dict) -> str:
    """Name of the AP item that occupies this chest's vanilla content."""
    if chest["rewardType"] == "ITEM":
        return bundle_item_name(
            ITEM_META_BY_GAME_ID[chest["value"]]["name"], chest["count"])
    if chest["rewardType"] == "FOL":
        return fol_item_name(chest["value"])
    raise ValueError(f"unexpected chest rewardType {chest['rewardType']!r}")
