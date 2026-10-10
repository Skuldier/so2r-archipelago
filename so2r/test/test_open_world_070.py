"""Open world 0.70.0: Nede world-map chests on a Nede start, dungeon area keys that open their Guide Map point."""
import json
import unittest
from pathlib import Path

from . import SO2RTestBase
from ..locations import CHEST_LOCATION_TABLE
from ..open_world import (AREA_KEY_BY_LOCALITY, AREA_KEYS, DUNGEON_TRAVEL, MAZE_REGION_ID, OPEN_WORLD_AREAS,
                          OPEN_WORLD_GEAR_MAPPING_VERSION, OPEN_WORLD_MAPPING_VERSION)

ARLIA_KEY = "Fast Travel: Arlia"
LAQUA_KEY = "Fast Travel: L'Aqua"
EXPECTED_TRAVEL = {"MF_0002": 1, "MF_0005": 4, "MF_0008": 9, "MF_0011": 14, "MF_0013": 16, "MF_0014": 19,
                   "MF_0020": 26, "MF_0022": 29, "MF_0027": 34, "MF_0033": 43, "MF_0036": 46, "MF_0037": 47,
                   "MF_0038": 49, "MF_0039": 52, "MF_0042": 55}
NEDE_WORLD_MAP = {name for name, data in CHEST_LOCATION_TABLE.items() if data.fieldmap == "NEDE"}
EXPEL_WORLD_MAP = {name for name, data in CHEST_LOCATION_TABLE.items() if data.fieldmap == "EXPEL"}


def _names(test) -> set:
    return {location.name for location in test.multiworld.get_locations(test.player)}


def _chest_name(flag: int) -> str:
    return next(name for name, data in CHEST_LOCATION_TABLE.items() if data.flag == flag)


class TestDungeonTravelTable(unittest.TestCase):
    def test_every_area_key_but_the_maze_and_phynal_has_an_entry(self):
        keyed = {k.locality for k in AREA_KEYS} - {MAZE_REGION_ID, "MF_0048"}
        self.assertEqual(keyed, set(DUNGEON_TRAVEL))
        self.assertEqual(EXPECTED_TRAVEL, DUNGEON_TRAVEL)
        self.assertTrue(all(OPEN_WORLD_AREAS[locality].dungeon for locality in DUNGEON_TRAVEL))

    def test_rows_are_enter_rows_on_the_dungeons_maps(self):
        path = Path(__file__).resolve().parents[3] / "tools" / "apworld" / "data" / "fast_travel.json"
        if not path.exists():  # an installed world has no tools/ next to it
            self.skipTest("fast_travel.json not found")
        rows = {r["fast_travel_id"]: r for r in json.loads(path.read_text(encoding="utf-8"))["fast_travel"]}
        for locality, row_id in DUNGEON_TRAVEL.items():
            self.assertEqual("ENTER", rows[row_id]["release_type"], locality)
            self.assertTrue(rows[row_id]["fieldmap"].startswith(locality + "_"), locality)

    def test_mapping_versions(self):
        self.assertEqual("so2r-ids-v1-open-world-v3", OPEN_WORLD_MAPPING_VERSION)
        self.assertEqual("so2r-ids-v1-open-world-v4", OPEN_WORLD_GEAR_MAPPING_VERSION)


class TestNedeStartWorldMap(SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "nede", "maze_chests": True, "item_pool": "vanilla"}

    def test_nede_world_map_chests_are_sphere_one_and_expel_has_none(self):
        names = _names(self)
        self.assertEqual(20, len(NEDE_WORLD_MAP))
        self.assertTrue(NEDE_WORLD_MAP <= names)
        self.assertFalse(names & EXPEL_WORLD_MAP)
        self.assertTrue(all(self.can_reach_location(name) for name in NEDE_WORLD_MAP))
        self.assertEqual(len(names), len(self.multiworld.itempool))

    def test_an_expel_dungeon_needs_only_its_key_and_the_maze_needs_both(self):
        salva = _chest_name(OPEN_WORLD_AREAS["MF_0005"].chests[0])
        maze = _chest_name(OPEN_WORLD_AREAS[MAZE_REGION_ID].chests[0])
        self.assertFalse(self.can_reach_location(salva))
        self.collect_by_name(AREA_KEY_BY_LOCALITY["MF_0005"].name)
        self.assertTrue(self.can_reach_location(salva))
        self.assertTrue(self.can_reach_location("Boss: Allen Tucks"))
        self.collect_by_name(AREA_KEY_BY_LOCALITY[MAZE_REGION_ID].name)
        self.assertFalse(self.can_reach_location(maze))
        self.collect_by_name(ARLIA_KEY)
        self.assertTrue(self.can_reach_location(maze))

    def test_slot_data(self):
        slot = self.world.fill_slot_data()
        self.assertEqual(OPEN_WORLD_MAPPING_VERSION, slot["mapping_version"])
        travel = slot["open_world"]["dungeon_travel"]
        self.assertEqual(EXPECTED_TRAVEL, travel)
        self.assertNotIn(MAZE_REGION_ID, travel)
        self.assertEqual(0, slot["world_map_chests"])  # the option itself stays off


class TestNedeStartGeneratedPool(SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "nede"}

    def test_gear_mapping_version_and_travel(self):
        slot = self.world.fill_slot_data()
        self.assertEqual(OPEN_WORLD_GEAR_MAPPING_VERSION, slot["mapping_version"])
        self.assertEqual(EXPECTED_TRAVEL, slot["open_world"]["dungeon_travel"])
        self.assertTrue(NEDE_WORLD_MAP <= _names(self))


class TestExpelStartWorldMap(SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "expel"}

    def test_no_world_map_chests_with_the_option_off(self):
        self.assertFalse(_names(self) & (NEDE_WORLD_MAP | EXPEL_WORLD_MAP))


class TestExpelStartWorldMapOn(SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "expel", "world_map_chests": True}

    def test_nede_ones_need_laqua(self):
        self.assertTrue(NEDE_WORLD_MAP <= _names(self))
        self.assertTrue(all(self.can_reach_location(name) for name in EXPEL_WORLD_MAP))
        self.assertFalse(any(self.can_reach_location(name) for name in NEDE_WORLD_MAP))
        self.collect_by_name(LAQUA_KEY)
        self.assertTrue(all(self.can_reach_location(name) for name in NEDE_WORLD_MAP))


class TestNedeStartWorldMapOn(SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "nede", "world_map_chests": True}

    def test_expel_ones_still_need_arlia(self):
        self.assertTrue(all(self.can_reach_location(name) for name in NEDE_WORLD_MAP))
        self.assertFalse(any(self.can_reach_location(name) for name in EXPEL_WORLD_MAP))
        self.collect_by_name(ARLIA_KEY)
        self.assertTrue(all(self.can_reach_location(name) for name in EXPEL_WORLD_MAP))


class TestBunnyMountChest(SO2RTestBase):
    """Chests 606 (bunny mount) and 607 (barrier closed at the hub), live 2026-10-01: never hold progression."""
    options = {"game_mode": "open_world", "starting_planet": "nede"}

    def test_no_progression_chests_exist_and_reject_progression_only(self):
        for flag in (606, 607):
            with self.subTest(flag=flag):
                name = _chest_name(flag)
                self.assertTrue(name.startswith(f"Nede World Map Chest {flag}"), name)
                self.assertIn(name, _names(self))
                rule = self.multiworld.get_location(name, self.player).item_rule
                for key in (ARLIA_KEY, AREA_KEY_BY_LOCALITY["MF_0005"].name):
                    self.assertFalse(rule(self.world.create_item(key)), key)
                self.assertTrue(rule(self.world.create_item(self.world.get_filler_item_name())))

    def test_another_world_map_chest_still_takes_progression(self):
        rule = self.multiworld.get_location(_chest_name(605), self.player).item_rule
        self.assertTrue(rule(self.world.create_item(ARLIA_KEY)))

    def test_never_hold_progression_after_fill(self):
        from test.general import setup_multiworld
        from Fill import distribute_items_restrictive
        for seed in range(1, 6):
            multiworld = setup_multiworld(type(self.world), seed=seed, options=self.options)
            distribute_items_restrictive(multiworld)
            for flag in (606, 607):
                item = multiworld.get_location(_chest_name(flag), 1).item
                self.assertIsNotNone(item)
                self.assertFalse(item.advancement, f"seed {seed} chest {flag}: {item.name}")
