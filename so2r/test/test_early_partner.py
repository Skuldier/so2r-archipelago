"""Coverage for the one verified, early partner recruitment mode."""
import random
import unittest
from types import SimpleNamespace

from . import SO2RTestBase
from .. import SO2RWorld
from .. import early_partner
from ..characters import CHARACTERS, choose_roster
from ..locations import CHEST_LOCATION_TABLE


class TestEarlyPartnerSelection(unittest.TestCase):
    def test_all_starters_produce_a_deterministic_distinct_non_rena_reward(self):
        for starter in CHARACTERS:
            for seed in range(10):
                roster = choose_roster(random.Random(seed), starter)
                reward = early_partner.prepare_reward(random.Random(seed + 100), roster, "claude")
                self.assertIn(reward, roster[1:])
                self.assertNotEqual(early_partner.EARLY_PARTNER_SOURCE_PLAYER_ID, reward.player_id)
                self.assertEqual(reward, early_partner.prepare_reward(
                    random.Random(seed + 100), roster, "claude"))

    def test_rena_route_and_invalid_catalog_candidate_refuse_generation(self):
        roster = choose_roster(random.Random(0), 1)
        with self.assertRaisesRegex(ValueError, "verified Claude-route"):
            early_partner.prepare_reward(random.Random(0), roster, "rena")
        bad_site = dict(early_partner.EARLY_PARTNER_SITE, VerifiedRoutes=[])
        with self.assertRaisesRegex(ValueError, "verified Claude-route"):
            early_partner.require_ready("claude", bad_site)

    def test_contract_has_only_the_single_v2_placement(self):
        reward = CHARACTERS[4]
        self.assertEqual({
            "version": 2,
            "mode": "early_partner",
            "catalog_sha256": early_partner.CATALOG_SHA256,
            "placements": {"5950002": {"source_player_id": 2, "reward_item_id": reward.item_id}},
        }, early_partner.slot_contract(reward))

    def test_full_and_early_modes_are_mutually_exclusive_before_roster_selection(self):
        world = object.__new__(SO2RWorld)
        world.options = SimpleNamespace(
            recruitment_checks=SimpleNamespace(value=True),
            early_partner_recruit=SimpleNamespace(value=True),
            character_items=SimpleNamespace(value=True),
        )
        with self.assertRaisesRegex(ValueError, "mutually exclusive"):
            world.generate_early()


class EarlyPartnerWorldChecks:
    def test_one_locked_local_early_check_and_six_general_character_items(self):
        locations = self.multiworld.get_locations(self.player)
        early_locations = [location for location in locations
                           if location.address == early_partner.EARLY_PARTNER_LOCATION_ID]
        self.assertEqual(1, len(early_locations))
        early_location = early_locations[0]
        self.assertEqual("Recruitment: Rena", early_location.name)
        self.assertTrue(early_location.locked)
        self.assertEqual(self.player, early_location.item.player)
        self.assertNotEqual("Character: Rena", early_location.item.name)

        general_characters = [item for item in self.multiworld.itempool
                              if item.name.startswith("Character: ")]
        self.assertEqual(6, len(general_characters))
        self.assertEqual(6, len({item.name for item in general_characters}))
        self.assertNotIn(early_location.item.name, {item.name for item in general_characters})
        self.assertEqual(len(self.multiworld.get_unfilled_locations(self.player)),
                         len(self.multiworld.itempool))
        self.assertEqual(len(locations), len(self.multiworld.itempool) + 1)

    def test_remaining_character_items_are_local_and_chest_only(self):
        names = {item.name for item in self.multiworld.itempool if item.name.startswith("Character: ")}
        self.assertEqual(names, self.world.options.local_items.value & names)
        for location in self.multiworld.get_locations(self.player):
            for name in names:
                item = self.world.create_item(name)
                if location.name in CHEST_LOCATION_TABLE:
                    self.assertTrue(location.item_rule(item), location.name)
                else:
                    self.assertFalse(location.item_rule(item), location.name)

    def test_slot_contract_and_roster_remain_the_standard_eight_seven_contract(self):
        slot = self.world.fill_slot_data()
        self.assertEqual(early_partner.EARLY_PARTNER_MAPPING_VERSION, slot["mapping_version"])
        plan = slot["recruitment_checks"]
        locked_item = self.multiworld.get_location("Recruitment: Rena", self.player).item
        self.assertEqual(early_partner.slot_contract(
            CHARACTERS[locked_item.code - 5_850_000]), plan)
        roster = slot["characters"]
        self.assertEqual(8, len(roster["roster"]))
        self.assertEqual(7, len(roster["items"]))
        reward_id = plan["placements"]["5950002"]["reward_item_id"] - 5_850_000
        self.assertIn(reward_id, roster["roster"])
        self.assertNotEqual(2, reward_id)
        self.assertNotEqual(roster["starter"], reward_id)


class TestEarlyPartnerBosses(EarlyPartnerWorldChecks, SO2RTestBase):
    options = {"resource_packs": False, "character_items": True, "early_partner_recruit": True, "route": "claude",
               "starting_character": "bowman", "chapter_keys": True}


class TestEarlyPartnerChestOnly(EarlyPartnerWorldChecks, SO2RTestBase):
    options = {"resource_packs": False, "character_items": True, "early_partner_recruit": True, "route": "claude",
               "starting_character": "bowman", "chapter_keys": True, "boss_checks": False}
