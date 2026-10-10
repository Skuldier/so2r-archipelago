"""Descent game mode (docs/descent/DESIGN_V1.md): generation, locations, items, logic and the slot-data contract."""
import io
import random
import unittest

from . import SO2RTestBase
from .test_loot import _fill
from .. import SO2RWorld
from .. import descent
from ..descent import (DEPTH_SEAL_ID, DEPTH_SEAL_NAME, DESCENT_MAPPING_VERSION, DUNGEON_BY_LOCALITY, GUARDIAN_BY_PARTY,
                       GUARDIANS, MODIFIER_BY_KEY, MODIFIERS, build_floors, choose_dungeons, choose_guardians, eligible)
from ..items import ITEM_TABLE
from ..locations import CHEST_LOCATION_TABLE

# BossSpotProbe.KnownBossParties (src/SO2R.ModApi/BossSpotProbe.cs).
KNOWN_BOSS_PARTIES = {191, 194, 195, 196, 197, 199, 209, 210, 211, 517, 519, 521, 522, 524, 525, 527, 528, 531, 532, 533, 535,
                      536, 537, 538, 539}
NEVER = {"MF_0048", "MF_0051"}  # Phynal and the Maze
ZONELESS = {"MF_0002", "MF_0008"}  # Sacred Forest (Ghark is a tutorial), Krosse Cave (no authored zone yet)
CHEST_BY_ADDRESS = {data.address: data for data in CHEST_LOCATION_TABLE.values()}
ALL_MODIFIERS = {m.name: 1 for m in MODIFIERS}


def _floors(seed, count=8, unverified=False, chance=60, weights=None, scaling=True, loot=True, cursed=True, drops=True,
            final="gabriel"):
    return build_floors(random.Random(seed), count, unverified, chance, weights or {m.name: m.weight for m in MODIFIERS},
                        scaling, loot, cursed, drops, 5, 80, 3, final)


def _options(count=8, **extra):
    return {"game_mode": "descent", "descent_floors": count, **extra}


class TestDescentData(unittest.TestCase):
    def test_phynal_and_the_maze_are_never_rows(self):
        self.assertFalse(NEVER & set(DUNGEON_BY_LOCALITY))

    def test_krosse_cave_has_no_zone_yet_so_it_is_not_eligible(self):
        # Data hook: author a zone for MF_0008 in tools/apworld/build_descent.py ZONE_OVERRIDES and it joins the pool.
        self.assertIsNone(DUNGEON_BY_LOCALITY["MF_0008"].zone)
        self.assertTrue(DUNGEON_BY_LOCALITY["MF_0008"].verified)
        self.assertIsNone(DUNGEON_BY_LOCALITY["MF_0002"].zone)
        self.assertFalse(ZONELESS & {d.locality for d in eligible(True)})

    def test_pool_is_twelve_dungeons_thirteen_with_the_unverified_toggle(self):
        self.assertEqual(12, len(eligible(False)))
        self.assertEqual(13, len(eligible(True)))
        self.assertEqual({"MF_0027"}, {d.locality for d in eligible(True)} - {d.locality for d in eligible(False)})

    def test_every_dungeon_row_is_consistent(self):
        seen_maps = set()
        for dungeon in descent.DUNGEONS:
            self.assertRegex(dungeon.locality, r"^MF_\d{4}$")
            self.assertTrue(all(m.startswith(dungeon.locality + "_") for m in dungeon.maps), dungeon.name)
            self.assertFalse(seen_maps & set(dungeon.maps))
            seen_maps |= set(dungeon.maps)
            self.assertIn(dungeon.entrance_map, dungeon.maps)
            if dungeon.zone is not None:
                self.assertIn(dungeon.zone["map"], dungeon.maps)
            for flag in dungeon.chests:
                data = CHEST_LOCATION_TABLE[next(n for n, d in CHEST_LOCATION_TABLE.items() if d.flag == flag)]
                self.assertFalse(data.postgame, dungeon.name)
                self.assertEqual(dungeon.locality, data.region)

    def test_guardians_are_known_boss_parties_with_gabriel_last(self):
        self.assertTrue({g.party_id for g in GUARDIANS} <= KNOWN_BOSS_PARTIES)
        self.assertFalse({517, 521} & {g.party_id for g in GUARDIANS})
        self.assertEqual("final", GUARDIAN_BY_PARTY[539].group)

    def test_ids_and_names(self):
        self.assertEqual(5_920_000, DEPTH_SEAL_ID)
        self.assertEqual(DEPTH_SEAL_ID, ITEM_TABLE[DEPTH_SEAL_NAME].code)
        self.assertEqual("Floor 3 Guardian", descent.guardian_location_name(3))
        self.assertEqual(5_830_003, SO2RWorld.location_name_to_id["Floor 3 Guardian"])
        self.assertEqual(5_830_003, descent.GUARDIAN_LOCATIONS["Floor 3 Guardian"])
        # The reserved band stays clear of every other id table.
        others = {**{n: d.address for n, d in CHEST_LOCATION_TABLE.items()}}
        self.assertFalse(set(descent.GUARDIAN_LOCATIONS.values()) & set(others.values()))


class TestDescentGeneration(unittest.TestCase):
    def test_determinism(self):
        self.assertEqual(_floors(5), _floors(5))
        self.assertNotEqual(_floors(5), _floors(6))

    def test_each_dungeon_once_tier_and_planet_order_floor_one(self):
        for count in range(3, 14):
            for seed in range(60):
                floors = _floors(seed, count, unverified=True)
                self.assertEqual(count, len(floors))
                dungeons = [f.dungeon for f in floors]
                self.assertEqual(len(dungeons), len({d.locality for d in dungeons}), (count, seed))
                keys = [(d.tier, descent.PLANET_ORDER[d.planet]) for d in dungeons]
                self.assertEqual(sorted(keys), keys, (count, seed))
                self.assertGreaterEqual(len(dungeons[0].chests), 6, (count, seed, dungeons[0].name))
                self.assertEqual([f.index for f in floors], list(range(1, count + 1)))

    def test_no_excluded_dungeon_is_ever_picked(self):
        for count in range(3, 13):
            for seed in range(80):
                picked = {f.dungeon.locality for f in _floors(seed, count)}
                self.assertFalse(picked & (NEVER | ZONELESS | {"MF_0027"}), (count, seed))
        for seed in range(80):
            picked = {f.dungeon.locality for f in _floors(seed, 13, unverified=True)}
            self.assertEqual({d.locality for d in eligible(True)}, picked)

    def test_stratified_by_tier(self):
        # 12 dungeons: T1 2, T2 3, T3 2, T4 5. Eight floors draw about 1.3 / 2 / 1.3 / 3.3.
        for seed in range(40):
            tiers = [f.dungeon.tier for f in _floors(seed, 8)]
            self.assertTrue(1 <= tiers.count(1) <= 2 and 1 <= tiers.count(3) <= 2 and 2 <= tiers.count(2) <= 3
                            and 3 <= tiers.count(4) <= 4, tiers)

    def test_too_many_floors_is_an_error_naming_the_count(self):
        with self.assertRaisesRegex(ValueError, "12 eligible"):
            choose_dungeons(random.Random(1), 13, False)

    def test_guardians_are_distinct_vetted_and_the_last_is_gabriel(self):
        for count in range(3, 14):
            for seed in range(40):
                guardians = choose_guardians(random.Random(seed), count)
                parties = [g.party_id for g in guardians]
                self.assertEqual(len(parties), len(set(parties)), (count, seed))
                self.assertEqual(539, parties[-1])
                self.assertTrue(all(g.vetted for g in guardians[:-1]))

    def test_guardians_deepen_with_the_floor(self):
        for seed in range(40):
            guardians = choose_guardians(random.Random(seed), 8)
            self.assertTrue(all(g.group == 1 for g in guardians[:2]))
            self.assertTrue(all(g.group in (3, 4) for g in guardians[4:7]))

    def test_random_top_final_guardian_is_a_top_group_draw(self):
        finals = {choose_guardians(random.Random(seed), 8, "random_top")[-1].party_id for seed in range(60)}
        self.assertNotIn(539, finals)
        self.assertTrue(finals <= {g.party_id for g in GUARDIANS if g.group == 4})
        self.assertGreater(len(finals), 1)

    def test_world_levels_run_start_to_max(self):
        floors = _floors(1, 8)
        self.assertEqual(5, floors[0].world_level)
        self.assertEqual(80, floors[-1].world_level)
        self.assertEqual(sorted(f.world_level for f in floors), [f.world_level for f in floors])
        self.assertEqual(floors[3].world_level + 3, floors[3].guardian_level)

    def test_modifier_rules(self):
        for seed in range(150):
            floors = _floors(seed, 8)
            mods = [f.modifier for f in floors]
            self.assertIsNone(mods[0])
            self.assertIsNotNone(mods[-1])  # the finale is never plain
            self.assertTrue(all(a is None or a != b for a, b in zip(mods, mods[1:])), mods)
            for floor in floors:
                if floor.modifier == "ambush":
                    self.assertNotEqual("MF_0037", floor.dungeon.locality)
                if floor.modifier == "treasure":
                    self.assertGreaterEqual(len(floor.dungeon.chests), 3)

    def test_modifier_dependencies_are_filtered(self):
        for seed in range(150):
            mods = {f.modifier for f in _floors(seed, 8, chance=100, scaling=False, loot=False, cursed=False, drops=False)}
            self.assertFalse(mods & {"empowered_foes", "treasure", "cursed", "bounty"}, mods)
        with_all = set()
        for seed in range(150):
            with_all |= {f.modifier for f in _floors(seed, 8, chance=100)}
        self.assertEqual({m.key for m in MODIFIERS}, with_all - {None})

    def test_modifier_chance_zero_leaves_only_the_finale(self):
        for seed in range(40):
            mods = [f.modifier for f in _floors(seed, 8, chance=0)]
            self.assertEqual([None] * 7, mods[:7])
            self.assertIsNotNone(mods[7])

    def test_zero_weight_removes_a_modifier(self):
        weights = {m.name: (0 if m.key == "blessed" else 5) for m in MODIFIERS}
        for seed in range(100):
            self.assertNotIn("blessed", {f.modifier for f in _floors(seed, 8, chance=100, weights=weights)})
        self.assertEqual([None] * 8, [f.modifier for f in _floors(1, 8, chance=100, weights={m.name: 0 for m in MODIFIERS})])

    def test_strength_numbers_at_eight_floors_three_joinable(self):
        # Design section 5: floor 8 needs all 3 characters and 4 weapon copies, floor 4 one character and one weapon.
        self.assertEqual((0, 0), (descent.chars_needed(1, 8, 3), descent.weapons_needed(1, 8, 3, 12)))
        self.assertEqual((1, 1), (descent.chars_needed(4, 8, 3), descent.weapons_needed(4, 8, 3, 12)))
        self.assertEqual((3, 4), (descent.chars_needed(8, 8, 3), descent.weapons_needed(8, 8, 3, 12)))
        self.assertEqual(2, descent.weapons_needed(8, 8, 3, 2))  # clamped to the ladder

    def test_restorative_packs_weigh_double(self):
        from ..items import SMALL_PACKS
        for pack, weight in zip(SMALL_PACKS, descent.packs_weights(SMALL_PACKS)):
            self.assertEqual(pack.weight * (2 if pack.pack == "Restorative" else 1), weight)


class TestTreasureBoost(unittest.TestCase):
    def test_boost_shifts_tiers_up_and_none_changes_nothing(self):
        from ..loot import roll_item
        base = {"Normal": 40, "Magic": 35, "Rare": 20, "Unique": 5}
        name = next(n for n, d in ITEM_TABLE.items() if d.category == "ARMOR")

        def rare_share(boost, seed):
            rng = random.Random(seed)
            rolls = [roll_item(rng, name, base, None, None, boost) for _ in range(3000)]
            return sum(1 for r in rolls if r is not None and r[0] in ("Rare", "Unique")) / len(rolls)

        self.assertGreater(rare_share(descent.TREASURE_BOOST, 3), rare_share(None, 3) * 1.4)
        a, b = random.Random(9), random.Random(9)
        self.assertEqual([roll_item(a, name, base, 0.5) for _ in range(50)],
                         [roll_item(b, name, base, 0.5, None, None) for _ in range(50)])


class DescentFilled:
    """Mixin: one filled descent multiworld per class."""
    count = 8
    extra: dict = {}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.options = _options(cls.count, **cls.extra)
        cls.multiworld = _fill(cls.options, seed=2026)
        cls.world = cls.multiworld.worlds[1]
        cls.floors = cls.world.descent_floors
        cls.slot = cls.world.fill_slot_data()

    def _locations(self):
        return self.multiworld.get_locations(1)

    def test_locations_are_floor_chests_and_guardians_only(self):
        names = {loc.name for loc in self._locations()}
        chests = sum(len(f.dungeon.chests) for f in self.floors)
        self.assertEqual(chests + self.count, len(names))
        guardians = {n for n in names if n.endswith(" Guardian")}
        self.assertEqual({f"Floor {i} Guardian" for i in range(1, self.count + 1)}, guardians)
        for loc in self._locations():
            if loc.name in guardians:
                self.assertEqual(5_830_000 + int(loc.name.split()[1]), loc.address)
            else:
                self.assertIn(loc.address, CHEST_BY_ADDRESS)
                self.assertEqual(5_500_000 + CHEST_BY_ADDRESS[loc.address].flag, loc.address)
        self.assertFalse([n for n in names if n.startswith(("Boss:", "Guild Mission", "Challenge Mission", "Recruitment"))])

    def test_pool_size_equals_location_count_and_has_the_right_keys(self):
        pool = [item.name for item in self.multiworld.itempool] + [
            item.name for item in self.multiworld.precollected_items[1]]
        precollected = len(self.multiworld.precollected_items[1])
        self.assertEqual(len(self._locations()), len(self.multiworld.itempool))
        self.assertEqual(0, precollected)
        self.assertEqual(self.count - 1, pool.count(DEPTH_SEAL_NAME))
        self.assertEqual(3, sum(1 for n in pool if ITEM_TABLE[n].category == "CHARACTER"))  # joinable_characters
        self.assertFalse([n for n in pool if ITEM_TABLE[n].category in ("AREA_KEY", "REGION_KEY", "CHAPTER_KEY", "KEY_ITEM")])

    def test_beatable_and_floor_one_is_sphere_one(self):
        self.assertTrue(self.multiworld.can_beat_game())
        spheres = [{loc.name for loc in sphere if loc.player == 1} for sphere in self.multiworld.get_spheres()]
        first = spheres[0]
        self.assertGreaterEqual(len(first), 7)  # >= 6 chests and the guardian
        self.assertIn("Floor 1 Guardian", first)
        self.assertTrue(all(CHEST_BY_ADDRESS[SO2RWorld.location_name_to_id[n]].flag in self.floors[0].dungeon.chests
                            for n in first if not n.endswith("Guardian")))
        reached = set().union(*spheres)
        self.assertEqual(len(self._locations()), len(reached))

    def test_each_floor_needs_the_seals_before_it(self):
        from BaseClasses import CollectionState
        state_items = [loc.item for loc in self._locations() if loc.item.name != DEPTH_SEAL_NAME]
        for floor in self.floors:
            region = f"Floor {floor.index}: {floor.dungeon.name}"
            for seals in range(self.count):
                state = CollectionState(self.multiworld)
                for item in state_items:  # everything but seals: the strength rule is met
                    state.collect(item, True)
                for _ in range(seals):
                    state.collect(self.world.create_item(DEPTH_SEAL_NAME), True)
                self.assertEqual(seals >= floor.index - 1, state.can_reach_region(region, 1), (floor.index, seals))

    def test_slot_data_contract(self):
        slot = self.slot
        self.assertEqual("descent", slot["game_mode"])
        self.assertEqual(DESCENT_MAPPING_VERSION, slot["mapping_version"])
        self.assertEqual("so2r-ids-v1-descent-v1", slot["mapping_version"])
        self.assertIsNone(slot["open_world"])
        self.assertEqual([539], slot["goal_parties"])
        self.assertEqual(0, slot["boss_checks"])
        for key in ("gear", "characters", "resource_packs", "scaling", "rewards", "equipment"):
            self.assertIsNotNone(slot[key], key)
        block = slot["descent"]
        self.assertEqual({"version", "hub_progress", "floor_count", "goal_floor", "seal", "guardian_location_base",
                          "heal_on_descent", "lock_message", "modifiers", "floors"}, set(block))
        self.assertEqual(1, block["version"])
        self.assertEqual(5_900_200, block["hub_progress"])
        self.assertEqual((self.count, self.count), (block["floor_count"], block["goal_floor"]))
        self.assertEqual({"item_id": 5_920_000, "name": "Progressive Depth Seal"}, block["seal"])
        self.assertEqual(5_830_000, block["guardian_location_base"])
        self.assertIs(True, block["heal_on_descent"])
        self.assertEqual({"empowered_foes", "heavy_boots", "back_attack", "silence", "ambush", "treasure", "bounty", "blessed",
                          "cursed"}, set(block["modifiers"]))
        self.assertEqual(5, block["modifiers"]["empowered_foes"]["world_level_bonus"])
        self.assertEqual(2.0, block["modifiers"]["ambush"]["rate_factor"])
        floors = block["floors"]
        self.assertEqual(list(range(1, self.count + 1)), [f["index"] for f in floors])
        maps = set()
        for floor in floors:
            self.assertEqual({"index", "dungeon", "name", "tier", "planet", "entrance_row", "entrance_map", "maps", "zone",
                              "guardian_party", "guardian_name", "guardian_level", "world_level", "guardian_location",
                              "modifier", "chests", "seals_to_descend", "next"}, set(floor))
            self.assertRegex(floor["dungeon"], r"^MF_\d{4}$")
            self.assertTrue(all(__import__("re").fullmatch(r"MF_\d{4}_\d{2}[A-Z]", m) for m in floor["maps"]))
            self.assertFalse(maps & set(floor["maps"]))
            maps |= set(floor["maps"])
            self.assertIn(floor["entrance_map"], floor["maps"])
            self.assertIn(floor["zone"]["map"], floor["maps"])
            self.assertIn("event", floor["zone"])
            self.assertIn(floor["guardian_party"], KNOWN_BOSS_PARTIES)
            self.assertEqual(5_830_000 + floor["index"], floor["guardian_location"])
            self.assertTrue(floor["modifier"] is None or floor["modifier"] in MODIFIER_BY_KEY)
            self.assertTrue(floor["chests"])
            self.assertTrue(all(5_500_000 + flag in CHEST_BY_ADDRESS for flag in floor["chests"]))
            if floor["index"] == self.count:
                self.assertEqual([], floor["next"])
                self.assertIsNone(floor["seals_to_descend"])
            else:
                self.assertEqual([floor["index"] + 1], floor["next"])
                self.assertEqual(floor["index"], floor["seals_to_descend"])
        self.assertEqual(539, floors[-1]["guardian_party"])
        self.assertEqual("Gabriel", floors[-1]["guardian_name"])
        self.assertIsNotNone(floors[-1]["modifier"])
        self.assertIsNone(floors[0]["modifier"])
        parties = [f["guardian_party"] for f in floors]
        self.assertEqual(len(parties), len(set(parties)))

    def test_forced_scaling_and_packs(self):
        self.assertEqual("full", self.slot["scaling"]["mode"])
        self.assertTrue(self.slot["scaling"]["scale_bosses"])
        self.assertTrue(self.slot["scaling"]["scale_final_battles"])
        self.assertEqual(1, self.slot["progression"]["resource_packs"])
        self.assertEqual({"version": 1, "requirements": [], "chests": {}}, self.slot["chest_logic"])

    def test_spoiler_lists_one_line_per_floor(self):
        out = io.StringIO()
        self.world.write_spoiler(out)
        text = out.getvalue()
        self.assertIn("Descent floors (Tester1):", text)
        section = text.split("Descent floors (Tester1):\n", 1)[1].split("\n\n", 1)[0].strip().splitlines()
        self.assertEqual(self.count, len(section))
        self.assertIn("Gabriel (539", section[-1])
        self.assertIn("(goal)", section[-1])
        self.assertIn("seals to descend: 1", section[0])
        self.assertIn(self.floors[0].dungeon.name, section[0])


class TestDescentThreeFloors(DescentFilled, unittest.TestCase):
    count = 3


class TestDescentEightFloors(DescentFilled, unittest.TestCase):
    count = 8


class TestDescentThirteenFloors(DescentFilled, unittest.TestCase):
    count = 13
    extra = {"descent_unverified_dungeons": True}


class TestDescentStrengthAndOptions(unittest.TestCase):
    def test_strength_rule_gates_the_guardians_by_party(self):
        from BaseClasses import CollectionState
        multiworld = _fill(_options(8), seed=11)
        world = multiworld.worlds[1]
        state = CollectionState(multiworld)
        for _ in range(7):
            state.collect(world.create_item(DEPTH_SEAL_NAME), True)
        self.assertTrue(state.can_reach_location("Floor 1 Guardian", 1))
        self.assertFalse(state.can_reach_location("Floor 8 Guardian", 1))  # seals alone are not a party
        self.assertFalse(state.can_reach_region(f"Floor 8: {world.descent_floors[7].dungeon.name}", 1))
        every = [loc.item for loc in multiworld.get_locations(1) if loc.item.name != DEPTH_SEAL_NAME]
        for item in every:
            state.collect(item, True)
        self.assertTrue(state.can_reach_location("Floor 8 Guardian", 1))
        self.assertTrue(multiworld.can_beat_game())

    def test_strength_off_and_final_guardian_option(self):
        multiworld = _fill(_options(8, descent_party_strength=False, descent_final_guardian="random_top",
                                    descent_heal_on_descent=False, enemy_scaling="off"), seed=12)
        slot = multiworld.worlds[1].fill_slot_data()
        self.assertNotEqual(539, slot["descent"]["floors"][-1]["guardian_party"])
        self.assertEqual([slot["descent"]["floors"][-1]["guardian_party"]], slot["goal_parties"])
        self.assertIs(False, slot["descent"]["heal_on_descent"])
        self.assertEqual("off", slot["scaling"]["mode"])  # off is respected
        self.assertNotIn("empowered_foes", {f["modifier"] for f in slot["descent"]["floors"]})
        self.assertTrue(multiworld.can_beat_game())
        from BaseClasses import ItemClassification
        names = {i.name: i.classification for i in multiworld.itempool}
        self.assertFalse(any(c & ItemClassification.progression for n, c in names.items()
                             if ITEM_TABLE[n].category in ("CHARACTER", "PROGRESSIVE_WEAPON")))

    def test_multiworld_with_a_second_slot(self):
        multiworld = _fill(_options(5), seed=3, players=2)
        self.assertTrue(multiworld.can_beat_game())

    def test_too_many_floors_refuses_generation(self):
        with self.assertRaisesRegex(ValueError, "eligible"):
            _fill(_options(13), seed=1)

    def test_story_recruitment_options_are_refused(self):
        with self.assertRaisesRegex(ValueError, "no story recruitment"):
            _fill(_options(5, early_partner_recruit=True), seed=1)

    def test_treasure_floor_chests_roll_better(self):
        weights = {m.name: (100 if m.key == "treasure" else 0) for m in MODIFIERS}
        multiworld = _fill(_options(8, loot_tiers=True, descent_modifier_chance=100, descent_modifier_weights=weights,
                                    cursed_loot=False), seed=21)
        world = multiworld.worlds[1]
        self.assertIn("treasure", {f.modifier for f in world.descent_floors})
        boosted = world._descent_boosted()
        self.assertTrue(boosted)
        self.assertTrue(all(address in CHEST_BY_ADDRESS for address in boosted))


class TestDescentOffChangesNothing(SO2RTestBase):
    """The default (story) world carries nothing of Descent."""

    def test_no_descent_block_seals_or_guardian_locations(self):
        slot = self.world.fill_slot_data()
        self.assertNotIn("descent", slot)
        self.assertNotEqual(DESCENT_MAPPING_VERSION, slot["mapping_version"])
        names = {loc.name for loc in self.multiworld.get_locations(1)}
        self.assertFalse({n for n in names if n.endswith(" Guardian")})
        self.assertNotIn(DEPTH_SEAL_NAME, {item.name for item in self.multiworld.itempool})
        self.assertEqual([], self.world.descent_floors)

    def test_open_world_has_no_descent_block(self):
        multiworld = _fill({"game_mode": "open_world", "starting_planet": "expel"}, seed=1)
        slot = multiworld.worlds[1].fill_slot_data()
        self.assertNotIn("descent", slot)
        self.assertNotIn(DEPTH_SEAL_NAME, {item.name for item in multiworld.itempool})
