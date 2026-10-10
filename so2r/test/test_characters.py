import random
import unittest

from . import SO2RTestBase
from ..characters import CHARACTERS, choose_roster, shuffle_recruitment_rewards
from ..items import ITEM_TABLE


class TestCharacterCatalog(unittest.TestCase):
    def test_stable_native_ids_include_both_protagonists(self):
        self.assertEqual(set(range(1, 14)), set(CHARACTERS))
        for pid, row in CHARACTERS.items():
            self.assertEqual(5850000 + pid, ITEM_TABLE[row.name].code)
        self.assertEqual("Character: Claude", CHARACTERS[1].name)
        self.assertEqual("Character: Rena", CHARACTERS[2].name)

    def test_eight_slots_and_incompatible_pairs_are_supported(self):
        observed = set()
        for seed in range(100):
            starter = seed % 13 + 1
            roster = choose_roster(random.Random(seed), starter)
            ids = {row.player_id for row in roster}
            self.assertEqual(8, len(ids))
            self.assertEqual(starter, roster[0].player_id)
            observed.update((a, b) for a in ids for b in ids)
            self.assertEqual(roster, choose_roster(random.Random(seed), starter))
        for pair in ((1, 2), (5, 8), (4, 6), (7, 9), (7, 10)):
            self.assertIn(pair, observed)


class TestRecruitmentRewardAssignment(unittest.TestCase):
    def test_every_starter_keeps_seven_unique_rewards_at_seven_sites(self):
        for starter in CHARACTERS:
            for seed in range(40):
                roster = choose_roster(random.Random(seed), starter)
                sites = random.Random(seed + 900).sample(list(CHARACTERS), 7)
                assigned = shuffle_recruitment_rewards(random.Random(seed), sites, roster)
                self.assertEqual(set(sites), set(assigned))
                self.assertEqual({r.player_id for r in roster[1:]}, {r.player_id for r in assigned.values()})
                self.assertTrue(all(source != reward.player_id for source, reward in assigned.items()))
                self.assertNotIn(starter, {r.player_id for r in assigned.values()})

    def test_identical_site_and_reward_sets_have_no_self_rewards(self):
        roster = [CHARACTERS[i] for i in range(1, 9)]
        for seed in range(100):
            assigned = shuffle_recruitment_rewards(random.Random(seed), list(range(2, 9)), roster)
            self.assertEqual(set(range(2, 9)), {r.player_id for r in assigned.values()})
            self.assertTrue(all(source != reward.player_id for source, reward in assigned.items()))

    def test_starters_own_site_is_still_a_check(self):
        roster = [CHARACTERS[i] for i in range(1, 9)]
        assigned = shuffle_recruitment_rewards(random.Random(1), list(range(1, 8)), roster)
        self.assertIn(1, assigned)
        self.assertNotEqual(1, assigned[1].player_id)

    def test_assignment_is_deterministic_and_input_order_independent(self):
        roster = choose_roster(random.Random(50), 4)
        sites = [3, 4, 6, 7, 9, 10, 13]
        expected = shuffle_recruitment_rewards(random.Random(100), sites, roster)
        self.assertEqual(expected, shuffle_recruitment_rewards(random.Random(100), sites, roster))
        self.assertEqual(expected, shuffle_recruitment_rewards(random.Random(100), sites[::-1],
                                                               roster[:1] + roster[1:][::-1]))
        self.assertEqual(sites, [3, 4, 6, 7, 9, 10, 13])

    def test_bad_source_set_is_rejected(self):
        roster = choose_roster(random.Random(0), 1)
        for sites in ([1, 2, 3], list(range(1, 9)), [1, 1, 2, 3, 4, 5, 6],
                      [0, 2, 3, 4, 5, 6, 7], [14, 2, 3, 4, 5, 6, 7], [True, 2, 3, 4, 5, 6, 7]):
            with self.assertRaises(ValueError):
                shuffle_recruitment_rewards(random.Random(0), sites, roster)

    def test_bad_roster_is_rejected(self):
        from ..characters import CharacterData
        valid = [CHARACTERS[i] for i in range(1, 9)]
        for roster in (valid[:7], valid + [CHARACTERS[9]], valid[:7] + [valid[0]],
                       valid[:7] + [CharacterData(99, 'Unknown')]):
            with self.assertRaises(ValueError):
                shuffle_recruitment_rewards(random.Random(0), list(range(1, 8)), roster)


class CharacterWorldChecks:
    def test_items_and_starter_contract(self):
        self.assertEqual("so2r-ids-v1-characters-v1", self.world.fill_slot_data()["mapping_version"])
        data = self.world.fill_slot_data()["characters"]
        joinable = self.world.options.joinable_characters.value  # default 3
        self.assertEqual(joinable + 1, len(set(data["roster"])))
        self.assertIn(data["starter"], data["roster"])
        self.assertEqual(joinable, len(data["items"]))
        pool = [item for item in self.multiworld.itempool if item.name.startswith("Character: ")]
        self.assertEqual(joinable, len(pool))
        self.assertEqual(joinable, len({item.name for item in pool}))
        self.assertNotIn(CHARACTERS[data["starter"]].name, {item.name for item in pool})
        for item in pool:
            row = data["items"][str(item.code)]
            self.assertEqual(item.code, 5850000 + row["player_id"])
            self.assertEqual(item.name, "Character: " + row["name"])
        self.assertEqual(len(self.multiworld.get_locations(self.player)), len(self.multiworld.itempool))

    def test_items_do_not_add_a_collect_all_goal(self):
        self.collect_all_but([character.name for character in CHARACTERS.values()])
        self.assertTrue(self.multiworld.completion_condition[self.player](self.multiworld.state))


class TestClaudeCharacters(CharacterWorldChecks, SO2RTestBase):
    options = {"resource_packs": False, "character_items": True, "starting_character": "rena", "route": "claude",
               "chapter_keys": True, "region_keys": True}

    def test_starter_does_not_change_story_route(self):
        data = self.world.fill_slot_data()
        self.assertEqual("claude", data["route"])
        self.assertEqual(2, data["characters"]["starter"])


class TestRenaCharacters(CharacterWorldChecks, SO2RTestBase):
    options = {"resource_packs": False, "character_items": True, "starting_character": "claude", "route": "rena",
               "chapter_keys": True, "region_keys": True}


class TestCharacterChestOnly(CharacterWorldChecks, SO2RTestBase):
    # Legacy full-pool replacement-budget fixture; conservative character seeds are
    # covered separately with world-map terrain checks disabled.
    options = {"resource_packs": False, "character_items": True, "chapter_keys": True, "region_keys": True,
               "boss_checks": False, "world_map_chests": True}


class TestCharacterMaze(CharacterWorldChecks, SO2RTestBase):
    # The full seven-joiner roster still works.
    options = {"resource_packs": False, "character_items": True, "chapter_keys": True, "region_keys": True, "maze_chests": True,
               "joinable_characters": 7}


class TestCharacterDefaultRoster(SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "expel"}

    def test_default_is_three_joiners_one_early(self):
        data = self.world.fill_slot_data()["characters"]
        self.assertEqual(4, len(data["roster"]))  # the starter plus joinable_characters (default 3)
        self.assertEqual(3, len(data["items"]))
        self.assertEqual(1, len(self.multiworld.local_early_items[self.player]))  # early_characters: 1 of the 3

    def test_roster_function_bounds(self):
        import random as rng
        self.assertEqual(2, len(choose_roster(rng.Random(1), 3, 1)))
        with self.assertRaises(ValueError):
            choose_roster(rng.Random(1), 3, 0)
        with self.assertRaises(ValueError):
            choose_roster(rng.Random(1), 3, 8)


class TestCharacterFixedSitesKeepSeven(SO2RTestBase):
    # The early partner places characters at fixed encounters, so joinable_characters does not shrink it.
    options = {"resource_packs": False, "character_items": True, "early_partner_recruit": True, "route": "claude",
               "starting_character": "bowman", "chapter_keys": True, "joinable_characters": 2}

    def test_early_partner_keeps_all_seven(self):
        self.assertEqual(7, len(self.world.fill_slot_data()["characters"]["items"]))


class EarlyCharacterChecks:
    """early_characters: that many roster characters (never the starter) land in the slot's own sphere 1."""
    expected_early = 1

    def test_early_characters_are_marked_and_placed_in_sphere_one(self):
        from Fill import distribute_items_restrictive

        early = self.multiworld.local_early_items[self.player]
        roster_items = {character.name for character in self.world.character_roster[1:]}
        self.assertEqual(self.expected_early, len(early))
        self.assertTrue(set(early) <= roster_items)
        distribute_items_restrictive(self.multiworld)
        start = self.multiworld.state.copy()
        start.sweep_for_advancements(locations=(location for location in self.multiworld.get_filled_locations()
                                                if location.address is None))
        placed = [location for location in self.multiworld.get_filled_locations()
                  if location.item.player == self.player and location.item.name in early]
        self.assertEqual(self.expected_early, len(placed))
        for location in placed:
            self.assertEqual(self.player, location.player)
            self.assertTrue(location.can_reach(start), f"{location.item.name} at {location.name} is not sphere 1")


class TestEarlyCharacterStory(EarlyCharacterChecks, SO2RTestBase):
    options = {"resource_packs": False, "character_items": True, "chapter_keys": True, "region_keys": True}


class TestEarlyCharactersThree(EarlyCharacterChecks, SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "expel", "early_characters": 3}
    expected_early = 3


class TestEarlyCharactersOff(SO2RTestBase):
    options = {"game_mode": "open_world", "early_characters": 0}

    def test_no_character_is_forced_early(self):
        self.assertFalse(self.multiworld.local_early_items[self.player])


class TestEarlyCharactersWithEarlyPartner(SO2RTestBase):
    options = {"resource_packs": False, "character_items": True, "early_partner_recruit": True, "route": "claude",
               "starting_character": "bowman", "chapter_keys": True}

    def test_the_early_partner_is_the_guarantee(self):
        self.assertFalse(self.multiworld.local_early_items[self.player])


class TestCharactersOff(SO2RTestBase):
    def test_no_character_contract_or_items_when_off(self):
        self.assertIsNone(self.world.fill_slot_data()["characters"])
        self.assertFalse(any(item.name.startswith("Character: ") for item in self.multiworld.itempool))
