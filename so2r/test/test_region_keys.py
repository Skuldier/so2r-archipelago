"""region_keys option assertions (docs/PROGRESSION_DESIGN.md §4, brief-confirmed id band
and slot_data shape)."""
import unittest

from . import SO2RTestBase
from ..items import ITEM_TABLE, REGION_KEY_BY_REGION, REGION_KEYS
from ..locations import CHEST_LOCATION_TABLE


class TestRegionKeyTable(unittest.TestCase):
    def test_ids_unique_and_in_band(self):
        ids = [k.item_id for k in REGION_KEYS]
        self.assertEqual(len(ids), len(set(ids)))
        for item_id in ids:
            self.assertTrue(5_700_000 <= item_id < 5_750_000, msg=item_id)

    def test_names_unique(self):
        names = [k.name for k in REGION_KEYS]
        self.assertEqual(len(names), len(set(names)))

    def test_item_name_to_id_has_every_key_regardless_of_option(self):
        # items.py's ITEM_TABLE (and therefore SO2RWorld.item_name_to_id) is built once,
        # independent of any option -- every key must be present even if a given seed
        # never turns region_keys on.
        for key in REGION_KEYS:
            self.assertIn(key.name, ITEM_TABLE, msg=key.name)
            self.assertEqual(key.item_id, ITEM_TABLE[key.name].code, msg=key.name)

    def test_lacuer_city_spot_check(self):
        key = REGION_KEY_BY_REGION["MF_0016"]
        self.assertEqual(5700016, key.item_id)
        self.assertEqual(23, key.fast_travel_id)
        self.assertEqual("MF_0016_01A", key.fieldmap)
        self.assertEqual("Mapjump", key.arrival)

    def test_hoffman_ruins_spot_check(self):
        # docs/PROGRESSION_DESIGN.md §4 / APWORLD.md: Hoffman Ruins (MF_0022) has no
        # field row whose nameID equals the locality id, so its key falls back to the
        # lowest-id ENTER row of any map in the locality -- FAST_TRAVEL_029, MF_0022_03A.
        key = REGION_KEY_BY_REGION["MF_0022"]
        self.assertEqual(29, key.fast_travel_id)
        self.assertEqual("MF_0022_03A", key.fieldmap)

    def test_excluded_regions_have_no_key(self):
        for excluded in ("EXPEL", "NEDE", "MF_0001", "MF_0028", "MF_0029", "MF_0049"):
            self.assertNotIn(excluded, REGION_KEY_BY_REGION)

    def test_no_enter_row_regions_have_no_key(self):
        for excluded in ("MF_0041", "MF_0044"):
            self.assertNotIn(excluded, REGION_KEY_BY_REGION)

    def test_maze_region_has_a_key(self):
        # Kept for stable ids; never pooled (the maze only exists after the ending).
        self.assertIn("MF_0051", REGION_KEY_BY_REGION)

    def test_destination_windows(self):
        # A key cannot work before the Guide Map lists its destination.
        self.assertEqual(6000500, REGION_KEY_BY_REGION["MF_0048"].available_from)
        self.assertEqual(6000500, REGION_KEY_BY_REGION["MF_0047"].available_from)
        self.assertEqual(4000000, REGION_KEY_BY_REGION["MF_0032"].available_from)
        # Lacuer City's row 23 has two consecutive variants: no window overall.
        self.assertIsNone(REGION_KEY_BY_REGION["MF_0016"].available_from)


class TestChestStoryGate(unittest.TestCase):
    def test_chest_72_carries_its_story_gate(self):
        by_flag = {d.flag: d for d in CHEST_LOCATION_TABLE.values()}
        self.assertEqual(1900000, by_flag[72].story_progress_required)

    def test_field_of_wisdom_labyrinth_carries_its_story_gate(self):
        # MAPJUMP_327/331/333 (the labyrinth doors) are gated by
        # FLAG_WISDOM_FIRSTTIME_MIRROR and disable rows 4200000-4700000 with the crystal
        # flags; the flag is set by the Field of Wisdom story arc, so an early
        # fast-travel visit cannot enter the labyrinth (docs/LOGIC_DESIGN.md).
        by_flag = {d.flag: d for d in CHEST_LOCATION_TABLE.values()}
        for flag in range(310, 317):
            self.assertEqual(4200000, by_flag[flag].story_progress_required, msg=flag)

    def test_most_chests_have_no_story_gate(self):
        # 134, 139-146: Salva Mines past the rock, which Ashton's Harley side quest lifts (docs/ACCESS_AUDIT.md).
        gated = [d for d in CHEST_LOCATION_TABLE.values() if d.story_progress_required is not None]
        self.assertEqual([72, 134, 139, 140, 141, 142, 143, 144, 145, 146, 310, 311, 312, 313, 314, 315, 316],
                         sorted(d.flag for d in gated))


class TestRegionKeysOffUnchanged(SO2RTestBase):
    options = {"region_keys": False}

    def test_no_region_keys_in_pool(self):
        item_names = {item.name for item in self.multiworld.itempool}
        key_names = {k.name for k in REGION_KEYS}
        self.assertEqual(set(), item_names & key_names)

    def test_empty_slot_data_region_keys(self):
        slot_data = self.world.fill_slot_data()
        self.assertEqual({}, slot_data["region_keys"])
        self.assertEqual(0, slot_data["progression"]["region_keys"])


class TestRegionKeysOnDefault(SO2RTestBase):
    options = {"region_keys": True}

    def test_pool_size_matches_location_count(self):
        self.assertEqual(
            len(self.multiworld.get_locations(self.player)),
            len(self.multiworld.itempool) + len(self.multiworld.precollected_items.get(self.player, [])),
        )

    def test_every_active_key_in_pool(self):
        item_names = {item.name for item in self.multiworld.itempool}
        active_key_names = {k.name for k in self.world._active_region_keys()}
        self.assertTrue(active_key_names <= item_names, msg=active_key_names - item_names)

    def test_maze_key_excluded_when_maze_chests_off(self):
        item_names = {item.name for item in self.multiworld.itempool}
        maze_key_name = REGION_KEY_BY_REGION["MF_0051"].name
        self.assertNotIn(maze_key_name, item_names)

    def test_slot_data_region_keys_populated(self):
        slot_data = self.world.fill_slot_data()
        self.assertEqual(1, slot_data["progression"]["region_keys"])
        self.assertGreater(len(slot_data["region_keys"]), 0)
        lacuer = slot_data["region_keys"][str(5700016)]
        self.assertEqual("MF_0016", lacuer["region"])
        self.assertEqual("Lacuer City", lacuer["name"])
        self.assertEqual(23, lacuer["fast_travel_id"])
        self.assertEqual("MF_0016_01A", lacuer["fieldmap"])


class TestRegionKeysWithMaze(SO2RTestBase):
    options = {"region_keys": True, "maze_chests": True}

    def test_maze_key_never_pooled(self):
        # The maze is post-game (VR Expel from a clear save): a travel key cannot open
        # it before the goal, so it is not an item even with maze_chests on.
        item_names = {item.name for item in self.multiworld.itempool}
        maze_key_name = REGION_KEY_BY_REGION["MF_0051"].name
        self.assertNotIn(maze_key_name, item_names)

    def test_pool_size_matches_location_count(self):
        self.assertEqual(
            len(self.multiworld.get_locations(self.player)),
            len(self.multiworld.itempool) + len(self.multiworld.precollected_items.get(self.player, [])),
        )


class TestRegionKeysAllOptionsPoolSize(SO2RTestBase):
    options = {
        "boss_checks": True,
        "optional_bosses": True,
        "raid_bosses": True,
        "maze_chests": True,
        "world_map_chests": True,
        "route": "claude",
        "recruitment_bosses": "opera_and_ernest",
        "region_keys": True,
    }

    def test_pool_size_matches_location_count(self):
        self.assertEqual(
            len(self.multiworld.get_locations(self.player)),
            len(self.multiworld.itempool) + len(self.multiworld.precollected_items.get(self.player, [])),
        )


class TestRegionKeysNoBossChecksPoolSize(SO2RTestBase):
    options = {"boss_checks": False, "region_keys": True}

    def test_pool_size_matches_location_count(self):
        self.assertEqual(
            len(self.multiworld.get_locations(self.player)),
            len(self.multiworld.itempool) + len(self.multiworld.precollected_items.get(self.player, [])),
        )
