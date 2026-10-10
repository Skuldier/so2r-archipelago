"""slot_data.chest_logic (docs/GUIDE_MAP_CHESTS.md): the plugin's "in logic" count must
agree with the generator's own rules. For random sets of held progression items, every
chest's exported requirement sets are compared with Archipelago's reachability."""
import random

from . import SO2RTestBase
from .. import CHEST_LOGIC_GOAL
from ..items import ITEM_TABLE
from ..locations import CHEST_LOCATION_TABLE
from BaseClasses import CollectionState


class ChestLogicMatchesRules:
    samples = 60
    has_progression = True

    def test_exported_requirements_match_reachability(self):
        requirements = self.world._chest_requirements()
        chests = {data.flag: name for name, data in self.world._active_chest_locations()}
        self.assertEqual(set(chests), set(requirements))
        progression = sorted({item.name for item in self.multiworld.itempool if item.advancement})
        self.assertEqual(self.has_progression, bool(progression))
        rng = random.Random(20260922)
        for sample in range(self.samples):
            held = {name for name in progression if rng.random() < sample / self.samples}
            state = CollectionState(self.multiworld)
            for name in sorted(held):
                state.collect(self.world.create_item(name), True)
            for flag, name in chests.items():
                if CHEST_LOCATION_TABLE[name].postgame:
                    continue
                expected = self.multiworld.get_location(name, self.player).can_reach(state)
                exported = any(alt <= held for alt in requirements[flag])
                self.assertEqual(expected, exported, msg=f"{name} with {sorted(held)}")

    def test_slot_data_shape(self):
        data = self.world.fill_slot_data()["chest_logic"]
        self.assertEqual(1, data["version"])
        self.assertEqual({str(data.flag) for _, data in self.world._active_chest_locations()}, set(data["chests"]))
        codes = {item.code for item in ITEM_TABLE.values()}
        for requirement in data["requirements"]:
            for item_id in requirement:
                self.assertTrue(item_id == CHEST_LOGIC_GOAL or item_id in codes)
        for refs in data["chests"].values():
            self.assertTrue(refs)
            for ref in refs:
                self.assertTrue(0 <= ref < len(data["requirements"]))


class TestChestLogicDefault(ChestLogicMatchesRules, SO2RTestBase):
    options = {}
    has_progression = False

    def test_everything_is_free_without_locks(self):
        data = self.world.fill_slot_data()["chest_logic"]
        self.assertEqual([[]], data["requirements"])


class TestChestLogicKeys(ChestLogicMatchesRules, SO2RTestBase):
    options = {"chapter_keys": True, "key_items": True}


class TestChestLogicRegionKeys(ChestLogicMatchesRules, SO2RTestBase):
    options = {"chapter_keys": True, "key_items": True, "region_keys": True, "world_map_chests": True}


class TestChestLogicRena(ChestLogicMatchesRules, SO2RTestBase):
    options = {"route": "rena", "key_items": True, "region_keys": True}


class TestChestLogicMaze(ChestLogicMatchesRules, SO2RTestBase):
    options = {"chapter_keys": True, "maze_chests": True}

    def test_maze_chests_need_the_goal(self):
        requirements = self.world._chest_requirements()
        maze = [data.flag for _, data in self.world._active_chest_locations() if data.postgame]
        self.assertEqual(100, len(maze))
        for flag in maze:
            self.assertEqual([frozenset({CHEST_LOGIC_GOAL})], requirements[flag])
