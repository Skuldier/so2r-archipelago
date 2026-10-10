"""World-map terrain chest option coverage.

The EXPEL/NEDE rows remain in the immutable public catalog for old rooms, but new
conservative seeds must not contain a location or reward from either fieldmap.
"""
from collections import Counter
import unittest

from . import SO2RTestBase
from .. import SO2RWorld
from ..items import CHAPTER_KEYS_ENABLED
from ..locations import BOSS_LOCATION_TABLE, CHEST_LOCATION_TABLE


WORLD_MAP_FIELDMAPS = {"EXPEL", "NEDE"}


def _active_main_chests(world_map_chests: bool) -> dict:
    return {
        name: data for name, data in CHEST_LOCATION_TABLE.items()
        if data.group != "maze" and not data.postgame
        and (world_map_chests or data.fieldmap not in WORLD_MAP_FIELDMAPS)
    }


class TestWorldMapChestCatalog(unittest.TestCase):
    def test_expel_and_nede_rows_and_public_ids_remain_stable(self):
        by_fieldmap = {
            fieldmap: {name: data for name, data in CHEST_LOCATION_TABLE.items()
                       if data.fieldmap == fieldmap}
            for fieldmap in WORLD_MAP_FIELDMAPS
        }
        self.assertEqual({"EXPEL", "NEDE"}, set(by_fieldmap))
        self.assertTrue(by_fieldmap["EXPEL"])
        self.assertTrue(by_fieldmap["NEDE"])
        for name, data in {name: data for rows in by_fieldmap.values() for name, data in rows.items()}.items():
            self.assertEqual(data.address, SO2RWorld.location_name_to_id[name], msg=name)


class TestWorldMapChestsOff(SO2RTestBase):
    options = {"resource_packs": False, "boss_checks": False}

    def test_default_removes_every_expel_and_nede_location_and_reward(self):
        expected = _active_main_chests(world_map_chests=False)
        location_names = {location.name for location in self.multiworld.get_locations(self.player)}
        self.assertEqual(set(expected), location_names)
        self.assertFalse(location_names & {
            name for name, data in CHEST_LOCATION_TABLE.items()
            if data.fieldmap in WORLD_MAP_FIELDMAPS
        })
        self.assertEqual(Counter(data.vanilla_item_name for data in expected.values()),
                         Counter(item.name for item in self.multiworld.itempool))

    def test_pool_and_location_counts_match(self):
        self.assertEqual(len(self.multiworld.get_locations(self.player)), len(self.multiworld.itempool))

    def test_slot_data_marks_the_conservative_pool(self):
        self.assertEqual(0, self.world.fill_slot_data()["world_map_chests"])


class TestWorldMapChestsOn(SO2RTestBase):
    options = {"resource_packs": False, "boss_checks": False, "world_map_chests": True}

    def test_opt_in_restores_exact_catalog_subset_and_rewards(self):
        expected = _active_main_chests(world_map_chests=True)
        location_names = {location.name for location in self.multiworld.get_locations(self.player)}
        self.assertEqual(set(expected), location_names)
        self.assertEqual(Counter(data.vanilla_item_name for data in expected.values()),
                         Counter(item.name for item in self.multiworld.itempool))

    def test_pool_and_location_counts_match(self):
        self.assertEqual(len(self.multiworld.get_locations(self.player)), len(self.multiworld.itempool))

    def test_slot_data_marks_the_opt_in_pool(self):
        self.assertEqual(1, self.world.fill_slot_data()["world_map_chests"])


class TestConservativeCharacterSeed(SO2RTestBase):
    """The approved fresh-seed profile: no terrain chests or region-key bypasses."""
    options = {
        "boss_checks": True,
        "optional_bosses": False,
        "raid_bosses": False,
        "recruitment_bosses": "none",
        "maze_chests": False,
        "world_map_chests": False,
        "guild_missions": False,
        "chapter_keys": True,
        "region_keys": False,
        "character_items": True,
        "early_partner_recruit": True,
        "route": "claude",
        "starting_character": "bowman",
    }

    def test_playable_pool_has_one_early_partner_and_six_local_chest_rewards(self):
        locations = self.multiworld.get_locations(self.player)
        location_names = {location.name for location in locations}
        early = self.multiworld.get_location("Recruitment: Rena", self.player)
        self.assertTrue(early.locked)
        self.assertIn("Boss: Snow Ogre", location_names)
        self.assertFalse(location_names & {
            name for name, data in CHEST_LOCATION_TABLE.items()
            if data.fieldmap in WORLD_MAP_FIELDMAPS
        })
        character_items = [item for item in self.multiworld.itempool if item.name.startswith("Character: ")]
        self.assertEqual(6, len(character_items))
        self.assertEqual({item.name for item in character_items},
                         self.world.options.local_items.value & {item.name for item in character_items})
        self.assertEqual(len(locations), len(self.multiworld.itempool) + 1)
        for location in locations:
            for item in character_items:
                self.assertEqual(location.name in CHEST_LOCATION_TABLE, location.item_rule(item),
                                 msg=f"{location.name}: {item.name}")


class TestChapterOnlyNedeSafety(SO2RTestBase):
    options = {"chapter_keys": True, "region_keys": False, "raid_bosses": True}

    def test_no_nede_check_or_boss_can_supply_royal_audience_before_that_key(self):
        location_names = {location.name for location in self.multiworld.get_locations(self.player)}
        nede_chests = {name for name, data in CHEST_LOCATION_TABLE.items() if data.fieldmap == "NEDE"}
        self.assertFalse(nede_chests & location_names)

        nede_bosses = {name for name, data in BOSS_LOCATION_TABLE.items() if data.region == "NEDE"}
        self.assertTrue(nede_bosses <= location_names)
        royal_audience = next(key.name for key in CHAPTER_KEYS_ENABLED if key.n == 1)
        for name in nede_bosses:
            location = self.multiworld.get_location(name, self.player)
            self.assertFalse(self.can_reach_location(name), msg=name)
            self.assertFalse(location.can_fill(
                self.multiworld.state, self.world.create_item(royal_audience), check_access=True), msg=name)
