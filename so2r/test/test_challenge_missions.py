"""challenge_missions option (docs/MISSIONS.md "Challenge Missions as checks"): the 58-row table, the tier and
prerequisite rules in both game modes, the pool balance, slot data and fill behaviour."""
import statistics
import unittest

from BaseClasses import CollectionState

from . import SO2RTestBase
from .test_loot import _fill
from .. import SO2RWorld
from ..items import ITEM_TABLE
from ..locations import (BOSS_LOCATION_TABLE, CHALLENGE_MISSION_LOCATION_ID_BASE, CHALLENGE_MISSION_LOCATION_TABLE,
                         CHALLENGE_MISSION_TIER_RULES, CHEST_LOCATION_TABLE, GUILD_MISSION_LOCATION_TABLE,
                         location_name_groups)
from ..open_world import HUB_PROGRESS, MAZE_REGION_ID

OPEN = {"game_mode": "open_world", "starting_planet": "expel"}
OPEN_ON = {**OPEN, "challenge_missions": True}
STORY_ON = {"challenge_missions": True}
STORY_LOCKS = {"challenge_missions": True, "chapter_keys": True, "key_items": True}
NO_PROGRESSION_IDS = {175, 180, 205, 237, 238}
BY_ID = {data.mission_id: (name, data) for name, data in CHALLENGE_MISSION_LOCATION_TABLE.items()}
PREFIX = "Challenge Mission: "


def _name(mission_id: int) -> str:
    return BY_ID[mission_id][0]


def _tier_sample(tier: int) -> str:
    """A tier row with no row-specific prerequisite."""
    return next(name for name, data in CHALLENGE_MISSION_LOCATION_TABLE.items()
                if data.tier == tier and not data.requires and data.start_progress == -1)


def _tier_names(tier: int):
    return {name for name, data in CHALLENGE_MISSION_LOCATION_TABLE.items() if data.tier == tier}


class TestChallengeMissionTable(unittest.TestCase):
    def test_58_rows_with_unique_prefixed_names(self):
        self.assertEqual(58, len(CHALLENGE_MISSION_LOCATION_TABLE))
        self.assertEqual(58, len(set(CHALLENGE_MISSION_LOCATION_TABLE)))
        for name in CHALLENGE_MISSION_LOCATION_TABLE:
            self.assertTrue(name.startswith(PREFIX), msg=name)

    def test_thousands_separators_use_the_live_text(self):
        for mission_id, text in {67: "Collect a total of 1,000 bonus spheres!", 241: "Walk a total of 4,000 steps!",
                                 179: "Deal 5,000 damage with a single attack!",
                                 180: "Deal 9,999 damage with a single attack!",
                                 174: "Deal a total of 500,000 damage!",
                                 175: "Deal a total of 10 million damage!"}.items():
            self.assertEqual(PREFIX + text, _name(mission_id))

    def test_ids_are_base_plus_mission_id_and_unique(self):
        self.assertEqual(5_820_000, CHALLENGE_MISSION_LOCATION_ID_BASE)
        addresses = [data.address for data in CHALLENGE_MISSION_LOCATION_TABLE.values()]
        self.assertEqual(58, len(set(addresses)))
        for data in CHALLENGE_MISSION_LOCATION_TABLE.values():
            self.assertEqual(CHALLENGE_MISSION_LOCATION_ID_BASE + data.mission_id, data.address)
            self.assertTrue(5_820_001 <= data.address <= 5_820_299)

    def test_no_id_or_name_collides_with_another_location(self):
        others = ([d.address for d in CHEST_LOCATION_TABLE.values()] + [d.address for d in BOSS_LOCATION_TABLE.values()]
                  + [d.address for d in GUILD_MISSION_LOCATION_TABLE.values()])
        self.assertFalse(set(others) & {d.address for d in CHALLENGE_MISSION_LOCATION_TABLE.values()})
        self.assertEqual(len(SO2RWorld.location_name_to_id), len(set(SO2RWorld.location_name_to_id.values())))
        self.assertFalse({d.address for d in CHALLENGE_MISSION_LOCATION_TABLE.values()}
                         & {item.code for item in ITEM_TABLE.values()})

    def test_tab_and_tier_counts(self):
        tabs = [data.tab for data in CHALLENGE_MISSION_LOCATION_TABLE.values()]
        self.assertEqual({"Beginner": 27, "Expert": 18, "Specialist": 12, "Legend": 1},
                         {tab: tabs.count(tab) for tab in set(tabs)})
        tiers = [data.tier for data in CHALLENGE_MISSION_LOCATION_TABLE.values()]
        self.assertEqual([17, 16, 16, 9], [tiers.count(tier) for tier in (1, 2, 3, 4)])

    def test_chains_stay_inside_the_set_and_tiers_never_drop(self):
        for data in CHALLENGE_MISSION_LOCATION_TABLE.values():
            if data.previous is not None:
                self.assertIn(data.previous, BY_ID)
                self.assertLessEqual(BY_ID[data.previous][1].tier, data.tier, msg=data.mission_id)

    def test_only_137_and_183_carry_a_start_progress(self):
        carrying = {d.mission_id for d in CHALLENGE_MISSION_LOCATION_TABLE.values() if d.start_progress != -1}
        self.assertEqual({137, 183}, carrying)
        for mission_id in carrying:
            self.assertEqual(4_100_000, BY_ID[mission_id][1].start_progress)
            self.assertLessEqual(4_100_000, HUB_PROGRESS)

    def test_no_progression_rows_are_the_five_grinds(self):
        self.assertEqual(NO_PROGRESSION_IDS,
                         {d.mission_id for d in CHALLENGE_MISSION_LOCATION_TABLE.values() if d.no_progression})

    def test_tier_rules_have_no_orbs(self):
        self.assertEqual({"1": {"keys": 0, "characters": 0, "planet_key": False},
                          "2": {"keys": 3, "characters": 0, "planet_key": False},
                          "3": {"keys": 7, "characters": 1, "planet_key": False},
                          "4": {"keys": 12, "characters": 2, "planet_key": True}},
                         CHALLENGE_MISSION_TIER_RULES["open_world"])

    def test_chest_counter_story_progress(self):
        self.assertEqual(1_600_000, BY_ID[207][1].requires["story_progress"])
        self.assertEqual(3_300_500, BY_ID[208][1].requires["story_progress"])
        self.assertEqual({"nede": True, "story_progress": 5_700_500}, BY_ID[183][1].requires)

    def test_name_groups(self):
        groups = location_name_groups()
        self.assertEqual(set(CHALLENGE_MISSION_LOCATION_TABLE), groups["Challenge Missions"])
        for tab, count in {"Beginner": 27, "Expert": 18, "Specialist": 12, "Legend": 1}.items():
            self.assertEqual(count, len(groups[f"Challenge Missions: {tab}"]))
        for tier, count in {1: 17, 2: 16, 3: 16, 4: 9}.items():
            self.assertEqual(count, len(groups[f"Challenge Missions: Tier {tier}"]))
        families = [groups[f"Challenge Missions: {f}"] for f in ("Battle", "Exploration", "Skills")]
        self.assertEqual(set(CHALLENGE_MISSION_LOCATION_TABLE), set().union(*families))
        self.assertEqual(58, sum(len(f) for f in families))
        self.assertIn(_name(140), families[0])
        self.assertIn(_name(241), families[1])
        self.assertIn(_name(22), families[2])
        self.assertTrue(groups["Challenge Missions"] <= set(SO2RWorld.location_name_to_id))


class TestOptionOff(SO2RTestBase):
    options = {}

    def test_no_challenge_locations_and_no_slot_block(self):
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        self.assertFalse(names & set(CHALLENGE_MISSION_LOCATION_TABLE))
        slot = self.world.fill_slot_data()
        self.assertNotIn("challenge_missions", slot)
        self.assertNotIn("challenge_missions", slot["progression"])
        self.assertFalse(slot["mapping_version"].endswith("-cm1"))

    def test_option_is_a_toggle_off_by_default(self):
        self.assertFalse(self.world.options.challenge_missions.value)
        self.assertEqual("Challenge Missions", type(self.world.options.challenge_missions).display_name)


def _signature(options, seed=5):
    from test.general import setup_multiworld
    multiworld = setup_multiworld(SO2RWorld, seed=seed, options=options)
    world = multiworld.worlds[1]
    return (sorted(loc.name for loc in multiworld.get_locations()), sorted(item.name for item in multiworld.itempool),
            world.fill_slot_data())


class TestOffMatchesPlainWorld(unittest.TestCase):
    def test_off_is_identical_to_an_unset_option_in_both_modes(self):
        for options in ({}, OPEN, {"chapter_keys": True}, {**OPEN, "item_pool": "vanilla"}):
            plain = _signature(options)
            explicit = _signature({**options, "challenge_missions": False})
            self.assertEqual(plain, explicit)

    def test_on_adds_exactly_the_mission_rows(self):
        for options in ({}, OPEN, {"chapter_keys": True, "key_items": True}, {**OPEN, "item_pool": "vanilla"},
                        {**OPEN, "other_planet": "open"}):
            off_locations, off_items, off_slot = _signature(options)
            on_locations, on_items, on_slot = _signature({**options, "challenge_missions": True})
            self.assertEqual(sorted(off_locations + list(CHALLENGE_MISSION_LOCATION_TABLE)), on_locations, msg=options)
            self.assertEqual(len(off_items) + 58, len(on_items), msg=options)
            self.assertEqual(len(on_locations), len(on_items), msg=options)
            extra = set(on_slot) - set(off_slot)
            self.assertEqual({"challenge_missions"}, extra)
            self.assertEqual(off_slot["mapping_version"] + "-cm1", on_slot["mapping_version"])
            # Everything else in slot data is untouched (chest_logic, keys, ...).
            for key in set(off_slot) - {"mapping_version", "progression"}:
                self.assertEqual(off_slot[key], on_slot[key], msg=key)


class TestOpenWorldOn(SO2RTestBase):
    options = OPEN_ON

    def test_58_locations_with_ids_and_names(self):
        locations = {loc.name: loc.address for loc in self.multiworld.get_locations(self.player)
                     if loc.name.startswith(PREFIX)}
        self.assertEqual({name: d.address for name, d in CHALLENGE_MISSION_LOCATION_TABLE.items()}, locations)

    def test_pool_equals_locations(self):
        self.assertEqual(len(self.multiworld.get_locations(self.player)), len(self.multiworld.itempool))

    def test_slot_data_block(self):
        slot = self.world.fill_slot_data()
        block = slot["challenge_missions"]
        self.assertEqual(1, block["version"])
        self.assertEqual(5_820_000, block["location_base"])
        self.assertEqual(58, len(block["missions"]))
        for key, row in block["missions"].items():
            self.assertEqual(5_820_000 + int(key), row["location"])
            self.assertEqual(BY_ID[int(key)][1].tier, row["tier"])
        self.assertEqual({"location": 5_820_140, "tier": 1}, block["missions"]["140"])
        self.assertEqual("so2r-ids-v1-open-world-v4-cm1", slot["mapping_version"])
        self.assertEqual(1, slot["progression"]["challenge_missions"])

    def test_no_progression_rows_refuse_advancement(self):
        progression = self.world.create_item(self.world._active_area_keys()[0].name)
        filler = self.world.create_item(self.world._filler_name())
        for mission_id in NO_PROGRESSION_IDS:
            location = self.world.get_location(_name(mission_id))
            self.assertFalse(location.item_rule(progression), msg=mission_id)
            self.assertTrue(location.item_rule(filler), msg=mission_id)
        other = self.world.get_location(_name(140))
        self.assertTrue(other.item_rule(progression))


class TestOpenWorldTiers(SO2RTestBase):
    """Expel start: the other planet (Nede) is locked behind the L'Aqua key."""
    options = {**OPEN_ON, "starting_planet": "expel", "joinable_characters": 3}

    def setUp(self):
        super().setUp()
        self.keys = [k.name for k in self.world._active_area_keys() if k.locality != MAZE_REGION_ID]
        self.characters = [c.name for c in self.world._character_items()]
        self.planet_key = self.world._open_world_planet_key().name

    def reachable(self, name):
        return self.multiworld.get_location(name, self.player).can_reach(self.multiworld.state)

    def test_there_are_15_non_maze_keys_and_3_character_items(self):
        self.assertEqual(15, len(self.keys))
        self.assertEqual(3, len(self.characters))

    def test_tier_1_needs_nothing(self):
        self.assertTrue(self.reachable(_tier_sample(1)))
        self.assertTrue(all(self.reachable(name) for name in _tier_names(1)))

    def test_tier_2_needs_three_keys(self):
        name = _tier_sample(2)
        self.collect_by_name(self.keys[:2])
        self.assertFalse(self.reachable(name))
        self.collect_by_name(self.keys[2])
        self.assertTrue(self.reachable(name))

    def test_tier_3_needs_seven_keys_and_a_character(self):
        name = _tier_sample(3)
        self.collect_by_name(self.keys[:7])
        self.assertFalse(self.reachable(name))  # keys alone
        self.remove_by_name(self.keys[:1])
        self.collect_by_name(self.characters[0])
        self.assertFalse(self.reachable(name))  # six keys and a character
        self.collect_by_name(self.keys[0])
        self.assertTrue(self.reachable(name))

    def test_tier_4_needs_twelve_keys_two_characters_and_the_planet_key(self):
        name = _tier_sample(4)
        self.collect_by_name(self.keys[:12] + self.characters[:2])
        self.assertFalse(self.reachable(name))  # no planet key
        self.collect_by_name(self.planet_key)
        self.assertTrue(self.reachable(name))
        self.remove_by_name(self.characters[1])
        self.assertFalse(self.reachable(name))
        self.collect_by_name(self.characters[1])
        self.remove_by_name(self.keys[11])
        self.assertFalse(self.reachable(name))  # eleven keys

    def test_maze_key_never_counts(self):
        from ..open_world import AREA_KEY_BY_LOCALITY
        maze_key = AREA_KEY_BY_LOCALITY[MAZE_REGION_ID].name
        name = _tier_sample(2)
        self.collect_by_name(self.keys[:2])
        self.multiworld.state.collect(self.world.create_item(maze_key), True)
        self.assertFalse(self.reachable(name))

    def test_183_needs_the_nede_planet_key_itself(self):
        location = self.multiworld.get_location(_name(183), self.player)
        self.assertFalse(location.access_rule(self.multiworld.state))
        self.collect_by_name(self.planet_key)
        self.assertTrue(location.access_rule(self.multiworld.state))

    def test_137_has_no_rule_in_open_world(self):
        location = self.multiworld.get_location(_name(137), self.player)
        self.assertTrue(location.access_rule(CollectionState(self.multiworld)))
        self.assertEqual(self.reachable(_tier_sample(2)), self.reachable(_name(137)))
        self.collect_by_name(self.keys[:3])
        self.assertTrue(self.reachable(_name(137)))

    def _in_logic_chests(self):
        state = self.multiworld.state
        total = 0
        for _chest_name, data in self.world._active_chest_locations():
            if data.group != "maze" and state.has_all(self.world._open_world_requirements(data.region), self.player):
                total += 1
        return total

    def test_chest_counters_follow_the_chests_in_logic(self):
        low, high = (self.multiworld.get_location(_name(i), self.player) for i in (207, 208))
        self.assertLess(self._in_logic_chests(), 58)  # towns and the start planet only
        self.assertFalse(low.access_rule(self.multiworld.state))
        self.assertFalse(high.access_rule(self.multiworld.state))
        for key in self.keys + [self.planet_key]:
            self.collect_by_name(key)
            count = self._in_logic_chests()
            self.assertEqual(count >= 58, low.access_rule(self.multiworld.state), msg=(key, count))
            self.assertEqual(count >= 115, high.access_rule(self.multiworld.state), msg=(key, count))
        self.assertTrue(low.access_rule(self.multiworld.state) and high.access_rule(self.multiworld.state))
        self.assertGreaterEqual(self._in_logic_chests(), 115)

    def test_only_town_chests_do_not_open_207(self):
        # The 29 town chests of the plan: no dungeon key at all.
        self.assertFalse(self.multiworld.get_location(_name(207), self.player).access_rule(self.multiworld.state))


class TestNedeStart(SO2RTestBase):
    options = {**OPEN_ON, "starting_planet": "nede"}

    def test_183_has_no_extra_rule_on_nede(self):
        location = self.multiworld.get_location(_name(183), self.player)
        self.assertTrue(location.access_rule(CollectionState(self.multiworld)))

    def test_precollected_start_key_counts_toward_tier_2(self):
        keys = [k.name for k in self.world._active_area_keys() if k.locality != MAZE_REGION_ID]
        held = [k for k in keys if self.multiworld.state.has(k, self.player)]
        self.assertEqual(1, len(held))
        name = _tier_sample(2)
        location = self.multiworld.get_location(name, self.player)
        others = [k for k in keys if k not in held]
        self.collect_by_name(others[:1])
        self.assertFalse(location.can_reach(self.multiworld.state))
        self.collect_by_name(others[1])
        self.assertTrue(location.can_reach(self.multiworld.state))


class TestOtherPlanetOpen(SO2RTestBase):
    options = {**OPEN_ON, "other_planet": "open"}

    def test_tier_4_has_no_planet_key_requirement(self):
        keys = [k.name for k in self.world._active_area_keys() if k.locality != MAZE_REGION_ID]
        characters = [c.name for c in self.world._character_items()]
        self.collect_by_name(keys[:12] + characters[:2])
        self.assertTrue(self.multiworld.get_location(_tier_sample(4), self.player).can_reach(self.multiworld.state))

    def test_183_has_no_rule(self):
        location = self.multiworld.get_location(_name(183), self.player)
        self.assertTrue(location.access_rule(CollectionState(self.multiworld)))


class TestClamping(SO2RTestBase):
    options = {**OPEN_ON, "joinable_characters": 1}

    def test_one_character_item_makes_tier_4_reachable(self):
        keys = [k.name for k in self.world._active_area_keys() if k.locality != MAZE_REGION_ID]
        characters = [c.name for c in self.world._character_items()]
        self.assertEqual(1, len(characters))
        self.collect_by_name(keys[:12] + characters + [self.world._open_world_planet_key().name])
        self.assertTrue(self.multiworld.get_location(_tier_sample(4), self.player).can_reach(self.multiworld.state))
        self.assertTrue(self.multiworld.get_location(_tier_sample(3), self.player).can_reach(self.multiworld.state))


class TestOpenWorldVanillaPool(SO2RTestBase):
    options = {**OPEN_ON, "item_pool": "vanilla"}

    def test_pool_equals_locations(self):
        self.assertEqual(len(self.multiworld.get_locations(self.player)), len(self.multiworld.itempool))


class TestStoryOn(SO2RTestBase):
    options = STORY_ON

    def test_58_locations_and_pool_balance(self):
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        self.assertEqual(set(CHALLENGE_MISSION_LOCATION_TABLE), names & set(CHALLENGE_MISSION_LOCATION_TABLE))
        self.assertEqual(len(self.multiworld.get_locations(self.player)), len(self.multiworld.itempool))

    def test_no_locks_means_every_tier_is_sphere_1(self):
        for name in CHALLENGE_MISSION_LOCATION_TABLE:
            self.assertTrue(self.multiworld.get_location(name, self.player).can_reach(CollectionState(self.multiworld)),
                            msg=name)
        slot = self.world.fill_slot_data()
        self.assertEqual("so2r-ids-v1-packs-v1-cm1", slot["mapping_version"])

    def test_no_progression_rows_refuse_advancement(self):
        item = self.world.create_item("Chapter Key: Royal Audience")
        for mission_id in NO_PROGRESSION_IDS:
            self.assertFalse(self.world.get_location(_name(mission_id)).item_rule(item), msg=mission_id)


class TestStoryTiers(SO2RTestBase):
    options = STORY_LOCKS

    def locks(self):
        return self.world._story_locks()

    def required(self, progress):
        return [name for name, unlocks in self.locks() if unlocks <= progress]

    def reachable(self, name):
        return self.multiworld.get_location(name, self.player).can_reach(self.multiworld.state)

    def test_each_tier_needs_every_lock_up_to_its_progress(self):
        progress = CHALLENGE_MISSION_TIER_RULES["story_progress"]
        previous = None
        for tier in (1, 2, 3, 4):
            needed = self.required(progress[str(tier)])
            if previous is not None:
                self.assertTrue(set(previous) <= set(needed))
            previous = needed
        self.assertFalse(self.required(progress["1"]))  # Salva comes before the first lock: sphere 1
        self.assertTrue(self.required(progress["2"]))
        self.assertLess(len(self.required(progress["2"])), len(self.required(progress["3"])))
        self.assertLess(len(self.required(progress["3"])), len(self.required(progress["4"])))
        self.assertIn("Chapter Key: Royal Audience", self.required(progress["2"]))

    def test_tier_rules_with_state(self):
        progress = CHALLENGE_MISSION_TIER_RULES["story_progress"]
        self.assertTrue(self.reachable(_tier_sample(1)))
        for tier in (2, 3, 4):
            name = _tier_sample(tier)
            needed = self.required(progress[str(tier)])
            self.assertFalse(self.reachable(name), msg=tier)
            self.collect_by_name(needed[:-1])
            self.assertFalse(self.reachable(name), msg=tier)
            self.collect_by_name(needed[-1])
            self.assertTrue(self.reachable(name), msg=tier)

    def test_137_183_and_chest_rows_use_their_story_progress(self):
        for mission_id, progress in {137: 4_100_000, 183: 5_700_500, 207: 1_600_000, 208: 3_300_500}.items():
            location = self.multiworld.get_location(_name(mission_id), self.player)
            needed = self.required(max(progress, BY_ID[mission_id][1].start_progress))
            self.assertTrue(needed, msg=mission_id)
            self.assertFalse(location.access_rule(CollectionState(self.multiworld)), msg=mission_id)
            state = CollectionState(self.multiworld)
            for key in needed:
                state.collect(self.world.create_item(key), True)
            self.assertTrue(location.access_rule(state), msg=mission_id)


class TestFilledSeeds(unittest.TestCase):
    def _check_no_progression(self, multiworld):
        for player in multiworld.player_ids:
            for mission_id in NO_PROGRESSION_IDS:
                location = multiworld.get_location(_name(mission_id), player)
                self.assertIsNotNone(location.item)
                self.assertFalse(location.item.advancement, msg=(mission_id, location.item.name))

    def test_no_progression_rows_never_hold_progression_over_several_seeds(self):
        for options in (OPEN_ON, {**OPEN_ON, "other_planet": "open"}, STORY_LOCKS, {**OPEN_ON, "item_pool": "vanilla"}):
            for seed in (1, 2, 3, 4):
                self._check_no_progression(_fill(options, seed=seed))

    def test_full_multiworld_generates_and_beats(self):
        for label, options in (("open world", OPEN_ON), ("story", STORY_ON), ("story locks", STORY_LOCKS),
                               ("open world other planet open", {**OPEN_ON, "other_planet": "open"})):
            multiworld = _fill(options, seed=11, players=2)
            self.assertTrue(multiworld.can_beat_game(CollectionState(multiworld)), msg=label)
            self._check_no_progression(multiworld)

    def test_pool_counts_equal_location_counts_with_the_option_on(self):
        for options in (OPEN_ON, STORY_ON, STORY_LOCKS, {**OPEN_ON, "item_pool": "vanilla"}):
            multiworld = _fill(options, seed=2)
            placed = [loc for loc in multiworld.get_locations() if loc.item is not None]
            self.assertEqual(len(multiworld.get_locations()), len(placed))

    def test_sphere_order_follows_the_tiers(self):
        for options in (OPEN_ON, {**OPEN_ON, "starting_planet": "nede"}):
            for seed in (1, 2, 3):
                multiworld = _fill(options, seed=seed)
                spheres = {}
                for index, sphere in enumerate(multiworld.get_spheres(), 1):
                    for location in sphere:
                        spheres[location.name] = index
                means = [statistics.mean(spheres[name] for name in _tier_names(tier)) for tier in (1, 2, 3, 4)]
                self.assertEqual(means, sorted(means), msg=(seed, means))
                self.assertLess(means[0], means[3], msg=(seed, means))
                self.assertEqual({1}, {spheres[name] for name in _tier_names(1)})
                self.assertGreater(min(spheres[name] for name in _tier_names(4)), 1)
