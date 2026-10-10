"""Chapter-key generation and access rules for the eight traced story gates.
Event/threshold evidence is recorded in docs/CHAPTER_LOCKS.md; native lock/unlock
coverage is tracked separately from these managed generation checks.
"""
import unittest

from . import SO2RTestBase
from ..items import CHAPTER_KEYS, CHAPTER_KEYS_ENABLED, ITEM_TABLE
from ..locations import CHEST_LOCATION_TABLE


def _location_name_for_flag(flag: int) -> str:
    for name, data in CHEST_LOCATION_TABLE.items():
        if data.flag == flag:
            return name
    raise KeyError(flag)


class TestChapterKeyTable(unittest.TestCase):
    def test_ids_unique_and_in_band(self):
        ids = [k.item_id for k in CHAPTER_KEYS]
        self.assertEqual(len(ids), len(set(ids)))
        for item_id in ids:
            self.assertTrue(5_750_000 <= item_id < 5_800_000, msg=item_id)

    def test_names_unique(self):
        names = [k.name for k in CHAPTER_KEYS]
        self.assertEqual(len(names), len(set(names)))

    def test_item_name_to_id_has_every_key_regardless_of_option(self):
        for key in CHAPTER_KEYS:
            self.assertIn(key.name, ITEM_TABLE, msg=key.name)
            self.assertEqual(key.item_id, ITEM_TABLE[key.name].code, msg=key.name)

    def test_royal_audience_spot_check(self):
        by_n = {k.n: k for k in CHAPTER_KEYS}
        key = by_n[1]
        self.assertEqual(5750001, key.item_id)
        self.assertEqual("Chapter Key: Royal Audience", key.name)
        self.assertEqual(["ev_1000000"], key.events)
        self.assertEqual(1001000, key.unlocks_progress)

    def test_lacuer_ferry_spot_check(self):
        by_n = {k.n: k for k in CHAPTER_KEYS}
        key = by_n[2]
        self.assertEqual(5750002, key.item_id)
        self.assertEqual("Chapter Key: Lacuer Ferry", key.name)
        self.assertEqual(["ev_1600000"], key.events)
        self.assertEqual(1800000, key.unlocks_progress)

    def test_hoffman_passage_spot_check(self):
        key = {k.n: k for k in CHAPTER_KEYS}[3]
        self.assertEqual(5750003, key.item_id)
        self.assertEqual("Chapter Key: Hoffman Passage", key.name)
        self.assertEqual(["ev_2302500"], key.events)
        self.assertEqual(2400000, key.unlocks_progress)
        self.assertTrue(key.enabled)

    def test_eluria_voyage_spot_check(self):
        key = {k.n: k for k in CHAPTER_KEYS}[4]
        self.assertEqual(5750004, key.item_id)
        self.assertEqual("Chapter Key: Eluria Voyage", key.name)
        self.assertEqual(["ev_2800500"], key.events)
        self.assertEqual(2900000, key.unlocks_progress)
        self.assertTrue(key.enabled)

    def test_four_fields_spot_check(self):
        key = {k.n: k for k in CHAPTER_KEYS}[5]
        self.assertEqual(5750005, key.item_id)
        self.assertEqual("Chapter Key: The Four Fields", key.name)
        self.assertEqual(["ev_4100000"], key.events)
        self.assertEqual(4200000, key.unlocks_progress)
        self.assertTrue(key.enabled)

    def test_all_eight_traced_gates_enabled(self):
        self.assertEqual(8, len(CHAPTER_KEYS_ENABLED))
        self.assertEqual(set(range(1, 9)), {k.n for k in CHAPTER_KEYS_ENABLED})

    def test_late_gates_match_recorded_events_and_thresholds(self):
        by_n = {k.n: k for k in CHAPTER_KEYS}
        for n, label, event, threshold in (
            (6, "Phynal Expedition", "ev_4600000", 4700000),
            (7, "Armlock", "ev_5100000", 5200000),
            (8, "Final Voyage", "ev_5900200", 5900500),
        ):
            with self.subTest(key=label):
                key = by_n[n]
                self.assertTrue(key.enabled)
                self.assertEqual(5750000 + n, key.item_id)
                self.assertEqual("Chapter Key: " + label, key.name)
                self.assertEqual([event], key.events)
                self.assertEqual(threshold, key.unlocks_progress)

    def test_candidate_unlocks_progress_strictly_increasing(self):
        ordered = sorted(CHAPTER_KEYS, key=lambda k: k.n)
        for previous, current in zip(ordered, ordered[1:]):
            self.assertGreater(
                current.unlocks_progress, previous.unlocks_progress,
                msg=f"n={current.n} unlocks_progress must exceed n={previous.n}'s",
            )


class TestChapterKeysOffUnchanged(SO2RTestBase):
    options = {"chapter_keys": False}

    def test_no_chapter_keys_in_pool(self):
        item_names = {item.name for item in self.multiworld.itempool}
        key_names = {k.name for k in CHAPTER_KEYS}
        self.assertEqual(set(), item_names & key_names)

    def test_empty_slot_data_chapter_keys(self):
        slot_data = self.world.fill_slot_data()
        self.assertEqual({}, slot_data["chapter_keys"])
        self.assertEqual(0, slot_data["progression"]["chapter_keys"])


class TestChapterKeysOnDefault(SO2RTestBase):
    # Retain the legacy Cross-overworld reachability assertion below; conservative
    # seeds now intentionally omit terrain chests until their access audit is done.
    options = {"chapter_keys": True, "world_map_chests": True}

    def test_pool_size_matches_location_count(self):
        self.assertEqual(
            len(self.multiworld.get_locations(self.player)),
            len(self.multiworld.itempool) + len(self.multiworld.precollected_items.get(self.player, [])),
        )

    def test_every_key_in_pool(self):
        item_names = {item.name for item in self.multiworld.itempool}
        key_names = {k.name for k in CHAPTER_KEYS_ENABLED}
        self.assertTrue(key_names <= item_names, msg=key_names - item_names)

    def test_disabled_candidates_never_in_pool(self):
        item_names = {item.name for item in self.multiworld.itempool}
        disabled_names = {k.name for k in CHAPTER_KEYS if not k.enabled}
        self.assertEqual(set(), item_names & disabled_names)

    def test_slot_data_chapter_keys_populated(self):
        slot_data = self.world.fill_slot_data()
        self.assertEqual(1, slot_data["progression"]["chapter_keys"])
        self.assertEqual(len(CHAPTER_KEYS_ENABLED), len(slot_data["chapter_keys"]))
        four_fields = slot_data["chapter_keys"][str(5750005)]
        self.assertEqual("The Four Fields", four_fields["name"])
        self.assertEqual(["ev_4100000"], four_fields["events"])
        self.assertEqual(4200000, four_fields["unlocks_progress"])
        eluria = slot_data["chapter_keys"][str(5750004)]
        self.assertEqual("Eluria Voyage", eluria["name"])
        self.assertEqual(["ev_2800500"], eluria["events"])
        self.assertEqual(2900000, eluria["unlocks_progress"])
        hoffman = slot_data["chapter_keys"][str(5750003)]
        self.assertEqual("Hoffman Passage", hoffman["name"])
        self.assertEqual(["ev_2302500"], hoffman["events"])
        self.assertEqual(2400000, hoffman["unlocks_progress"])
        audience = slot_data["chapter_keys"][str(5750001)]
        self.assertEqual("Royal Audience", audience["name"])
        self.assertEqual(["ev_1000000"], audience["events"])
        self.assertEqual(1001000, audience["unlocks_progress"])

    def test_slot_data_lists_exactly_the_enabled_keys(self):
        slot_data = self.world.fill_slot_data()
        expected_ids = {str(k.item_id) for k in CHAPTER_KEYS_ENABLED}
        self.assertEqual(expected_ids, set(slot_data["chapter_keys"].keys()))

    def test_gated_chest_not_reachable_without_keys(self):
        # Krosse Castle (MF_0007, story_progress 1001000) is exactly the Royal Audience
        # chokepoint -- unreachable with no chapter keys collected.
        name = _location_name_for_flag(30)
        self.assertFalse(self.can_reach_location(name))

    def test_arlia_salva_and_cross_overworld_reachable_without_keys(self):
        # All below chapter key 1's unlocks_progress (1001000): must stay reachable
        # exactly as with chapter_keys off.
        for flag in (1,):  # Arlia
            self.assertTrue(self.can_reach_location(_location_name_for_flag(flag)))
        for flag in (20,):  # Salva - Allen's Mansion
            self.assertTrue(self.can_reach_location(_location_name_for_flag(flag)))
        for flag in (130,):  # Salva Mines
            self.assertTrue(self.can_reach_location(_location_name_for_flag(flag)))
        for flag in (501,):  # Expel World Map (Cross)
            self.assertTrue(self.can_reach_location(_location_name_for_flag(flag)))

    def test_gated_chest_reachable_after_both_keys_collected(self):
        name = _location_name_for_flag(30)
        self.assertFalse(self.can_reach_location(name))
        self.collect_by_name([k.name for k in CHAPTER_KEYS_ENABLED])
        self.assertTrue(self.can_reach_location(name))

    def test_everything_reachable_once_both_keys_collected(self):
        self.collect_by_name([k.name for k in CHAPTER_KEYS_ENABLED])
        for location in self.multiworld.get_locations(self.player):
            self.assertTrue(self.can_reach_location(location.name), msg=location.name)


class LateChapterChecks:
    """Exercise the newly promoted keys in both protagonist routes."""

    def test_late_story_thresholds_wait_for_their_own_key(self):
        from ..rules import story_reaches_progress

        self.collect_by_name([k.name for k in CHAPTER_KEYS_ENABLED if k.n <= 5])
        for label, threshold in (
            ("Phynal Expedition", 4700000),
            ("Armlock", 5200000),
            ("Final Voyage", 5900500),
        ):
            with self.subTest(key=label):
                self.assertTrue(story_reaches_progress(threshold - 1, self.player, True)(self.multiworld.state))
                self.assertFalse(story_reaches_progress(threshold, self.player, True)(self.multiworld.state))
                self.collect_by_name("Chapter Key: " + label)
                self.assertTrue(story_reaches_progress(threshold, self.player, True)(self.multiworld.state))

    def test_late_keys_are_single_items_and_reach_the_client(self):
        slot_data = self.world.fill_slot_data()
        for n, label, event, threshold in (
            (6, "Phynal Expedition", "ev_4600000", 4700000),
            (7, "Armlock", "ev_5100000", 5200000),
            (8, "Final Voyage", "ev_5900200", 5900500),
        ):
            with self.subTest(key=label):
                self.assertEqual(1, sum(item.name == "Chapter Key: " + label for item in self.multiworld.itempool))
                row = slot_data["chapter_keys"][str(5750000 + n)]
                self.assertEqual(label, row["name"])
                self.assertEqual([event], row["events"])
                self.assertEqual(threshold, row["unlocks_progress"])


class TestChapterKeysWithRegionKeys(LateChapterChecks, SO2RTestBase):
    options = {"chapter_keys": True, "region_keys": True}

    def test_pool_size_matches_location_count(self):
        self.assertEqual(
            len(self.multiworld.get_locations(self.player)),
            len(self.multiworld.itempool) + len(self.multiworld.precollected_items.get(self.player, [])),
        )

    def test_both_key_families_in_pool(self):
        from ..items import REGION_KEYS
        item_names = {item.name for item in self.multiworld.itempool}
        self.assertTrue({k.name for k in CHAPTER_KEYS_ENABLED} <= item_names)
        self.assertTrue({k.name for k in REGION_KEYS if k.region != "MF_0051"} <= item_names)

    def test_region_key_bypasses_chapter_gate(self):
        # A region key for a region past the Royal Audience gate (e.g. Krosse Castle
        # itself, MF_0007) grants access on its own, without any chapter key.
        from ..items import REGION_KEY_BY_REGION
        name = _location_name_for_flag(30)
        self.assertFalse(self.can_reach_location(name))
        self.collect_by_name(REGION_KEY_BY_REGION["MF_0007"].name)
        self.assertTrue(self.can_reach_location(name))

    def test_phynal_key_does_not_complete_the_story(self):
        # The Phynal destination row only exists from 6000500 (the final voyage), so the
        # key alone does not open the region, let alone complete the story.
        self.collect_by_name("Fast Travel: Phynal")
        self.assertFalse(self.can_reach_region("Phynal"))
        self.assertFalse(self.multiworld.completion_condition[self.player](self.multiworld.state))
        self.assertFalse(self.can_reach_location("Boss: Gabriel"))

    def test_phynal_key_waits_for_its_destination_window(self):
        self.collect_by_name("Fast Travel: Phynal")
        self.collect_by_name([k.name for k in CHAPTER_KEYS_ENABLED if k.n <= 7])
        self.assertFalse(self.can_reach_region("Phynal"))
        self.collect_by_name("Chapter Key: Final Voyage")
        self.assertTrue(self.can_reach_region("Phynal"))

    def test_goal_requires_each_enabled_chapter_key(self):
        self.collect_by_name("Fast Travel: Phynal")
        self.collect_by_name([key.name for key in CHAPTER_KEYS_ENABLED])
        for key in CHAPTER_KEYS_ENABLED:
            with self.subTest(key=key.name):
                removed = self.remove_by_name(key.name)
                self.assertFalse(self.multiworld.completion_condition[self.player](self.multiworld.state))
                self.assertFalse(self.can_reach_location("Boss: Gabriel"))
                self.collect(removed)
        self.assertTrue(self.multiworld.completion_condition[self.player](self.multiworld.state))
        self.assertTrue(self.can_reach_location("Boss: Gabriel"))

    def test_fast_travel_does_not_bypass_the_forest_blocker(self):
        # The key reaches the forest map, but ev_sub_012000 turns the party back until the
        # story reaches 1502000 (region_key_barriers.json), which needs the audience. Only
        # the entrance chest (170) lies before the turn-back points (docs/ACCESS_AUDIT.md).
        past_turn_back = next(name for name, data in CHEST_LOCATION_TABLE.items() if data.flag == 171)
        self.collect_by_name("Fast Travel: Forest of Symbols")
        self.assertFalse(self.can_reach_location(past_turn_back))
        self.assertFalse(self.can_reach_location("Boss: Snow Ogre"))
        self.collect_by_name("Chapter Key: Royal Audience")
        self.assertTrue(self.can_reach_location(past_turn_back))
        self.assertTrue(self.can_reach_location("Boss: Snow Ogre"))

    def test_zaphkiel_is_placed_in_fun_city(self):
        # Formerly unplaced; the winnable fight is ev_5701000 in the Fun City Arena at
        # 5701000, which needs the Armlock key but not the Final Voyage.
        from BaseClasses import LocationProgressType
        location = self.multiworld.get_location("Boss: Zaphkiel", self.player)
        self.assertEqual("Fun City", location.parent_region.name)
        self.assertEqual(LocationProgressType.DEFAULT, location.progress_type)
        self.collect_by_name([k.name for k in CHAPTER_KEYS_ENABLED if k.n <= 6])
        self.assertFalse(self.can_reach_location(location.name))
        self.collect_by_name("Chapter Key: Armlock")
        self.assertTrue(self.can_reach_location(location.name))


class TestChapterKeysWithMaze(SO2RTestBase):
    options = {"chapter_keys": True, "region_keys": True, "maze_chests": True}

    def test_pool_size_matches_location_count(self):
        self.assertEqual(
            len(self.multiworld.get_locations(self.player)),
            len(self.multiworld.itempool) + len(self.multiworld.precollected_items.get(self.player, [])),
        )


class TestChapterGoalWithoutBossLocations(SO2RTestBase):
    # This retains the pre-toggle full chest-pool budget fixture. The conservative
    # profile is separately covered by TestChapterOnlyNedeSafety.
    options = {"chapter_keys": True, "region_keys": True, "boss_checks": False,
               "world_map_chests": True}

    def test_all_eight_chapters_fit_the_chest_only_pool(self):
        # 272 main chests minus the post-game-only Eluria Tower chest 286.
        self.assertEqual(271, len(self.multiworld.itempool))
        self.assertEqual(len(self.multiworld.get_locations(self.player)), len(self.multiworld.itempool))
        for key in CHAPTER_KEYS_ENABLED:
            self.assertEqual(1, sum(item.name == key.name for item in self.multiworld.itempool))

    def test_key_replacement_preserves_unique_equipment(self):
        equipment = {
            data.vanilla_item_name for data in CHEST_LOCATION_TABLE.values()
            if data.group == "main" and ITEM_TABLE[data.vanilla_item_name].category in {
                "SWORD", "TWIN_SWORD", "ROD", "WAND", "WHIP", "GUN_AND_DISK",
                "KNUCKLE", "PUNCH", "STUNGUN", "ARMOR", "SHIELD", "HELMET", "GREEVE", "ACCESSORY",
            }
        }
        self.assertTrue(equipment)
        self.assertTrue(equipment <= {item.name for item in self.multiworld.itempool})

    def test_impossible_key_replacement_leaves_pool_unchanged(self):
        name = next(name for name, data in ITEM_TABLE.items() if data.category == "SWORD")
        pool = [self.world.create_item(name)]
        original = list(pool)
        with self.assertRaisesRegex(ValueError, "Cannot replace"):
            self.world._replace_pool_items_with_keys(pool, CHAPTER_KEYS_ENABLED)
        self.assertEqual(original, pool)

    def test_chest_only_goal_still_requires_chapter_completion(self):
        self.assertFalse(any(loc.name.startswith("Boss:") for loc in self.multiworld.get_locations(self.player)))
        self.assertEqual([539, 540], self.world.fill_slot_data()["goal_parties"])
        self.collect_by_name("Fast Travel: Phynal")
        self.assertFalse(self.multiworld.completion_condition[self.player](self.multiworld.state))
        self.collect_by_name([key.name for key in CHAPTER_KEYS_ENABLED])
        self.assertTrue(self.multiworld.completion_condition[self.player](self.multiworld.state))


class TestRenaStoryBossWithKeys(LateChapterChecks, SO2RTestBase):
    options = {"route": "rena", "chapter_keys": True, "region_keys": True}

    def test_travel_does_not_bypass_renas_story_boss_gate(self):
        self.collect_by_name("Fast Travel: Forest of Symbols")
        self.assertFalse(self.can_reach_location("Boss: Azam Gille"))
        self.collect_by_name("Chapter Key: Royal Audience")
        self.assertTrue(self.can_reach_location("Boss: Azam Gille"))


class TestChapterKeysAllOptionsPoolSize(SO2RTestBase):
    options = {
        "boss_checks": True,
        "optional_bosses": True,
        "raid_bosses": True,
        "maze_chests": True,
        "world_map_chests": True,
        "route": "claude",
        "recruitment_bosses": "opera_and_ernest",
        "region_keys": True,
        "chapter_keys": True,
    }

    def test_pool_size_matches_location_count(self):
        self.assertEqual(
            len(self.multiworld.get_locations(self.player)),
            len(self.multiworld.itempool) + len(self.multiworld.precollected_items.get(self.player, [])),
        )
