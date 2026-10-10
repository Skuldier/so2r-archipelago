"""Bucket List objectives v1 (docs/OBJECTIVES_V1.md): the 36-row table, the drawing algorithm and its caps, locations, rules,
the three goals, the slot-data contract and the off-by-default regression."""
import hashlib
import json
import random
import unittest

from BaseClasses import CollectionState

from . import SO2RTestBase
from .test_loot import _fill
from .. import SO2RWorld
from ..items import ITEM_TABLE
from ..objectives import (OBJECTIVE_BY_ID, OBJECTIVE_LOCATION_ID_BASE, OBJECTIVE_LOCATION_TABLE, OBJECTIVE_ROWS,
                          DrawContext, apportion, conflicts, draw, eligible, effective_tier)
from ..open_world import ORB_NAMES

OPEN = {"game_mode": "open_world", "starting_planet": "expel"}
OBJ = {**OPEN, "objective_count_drawn": 7, "objectives_required": 5,
       "objective_tier_mix": {"Easy": 3, "Medium": 3, "Hard": 1}, "goal": "orbs_and_objectives"}
NP_IDS = {21, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35}
PREFIX = "Objective: "


def _ctx(**changes):
    base = dict(goal="orbs", start_planet="EXPEL", other_planet_open=False, chest_count=164,
                boss_party_ids=frozenset({191, 194, 209, 210, 522, 524, 525, 527, 528, 531, 532, 533, 535}),
                area_key_count=15, town_count=7, fields_ok=True,
                chest_areas=frozenset({"MF_0005", "MF_0033", "MF_0002"}))
    base.update(changes)
    return DrawContext(**base)


def _build(options, seed):
    from test.general import setup_multiworld
    mw = setup_multiworld([SO2RWorld], seed=seed, options=options)
    return mw, mw.worlds[1]


def _digest(options, seed):
    """Fill, then hash the slot data, every placement and every location name (the off-by-default regression)."""
    mw = _fill(options, seed)
    world = mw.worlds[1]
    blob = {"slot": world.fill_slot_data(),
            "placements": sorted((loc.name, loc.item.name) for loc in mw.get_locations(1)),
            "locations": sorted(loc.name for loc in mw.get_locations(1))}
    return hashlib.sha256(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()


# Captured on world 0.85.0, before objectives existed: with objectives off (the defaults) nothing may change.
DEFAULT_DIGESTS = {
    "story": ({}, 11, "61fd4b196ca9b79b779f34f4da167eb21a847ac72ccf19dd1551b8d3460d3cae"),
    "story_keys": ({"chapter_keys": True, "key_items": True, "challenge_missions": True}, 12,
                   "28079a852743e8ebfc4c2592990949ba008ec044bbb1a24c0b7f87e9142befb8"),
    "open": ({"game_mode": "open_world", "starting_planet": "expel"}, 13,
             "1d4602648eb0535de496afc6b653ab91e48c969415a9d1391899b385a357faf4"),
    "open_nede_cm": ({"game_mode": "open_world", "starting_planet": "nede", "challenge_missions": True,
                      "loot_tiers": True, "trap_chance": 20}, 14,
                     "8d8215884446633c3604b18ac08a8e8ca3591575fd9e1829c119d697749f90f3"),
}


class TestObjectiveTable(unittest.TestCase):
    def test_rows_unique_ids_and_names(self):
        """36 v1 rows (ids 1-36, frozen) and the 38 v2 rows appended after them (docs/OBJECTIVES_V1.md, v2)."""
        self.assertEqual(74, len(OBJECTIVE_ROWS))
        self.assertEqual(list(range(1, 75)), [r.id for r in OBJECTIVE_ROWS])
        self.assertEqual(74, len({r.name for r in OBJECTIVE_ROWS}))
        for row in OBJECTIVE_ROWS:
            self.assertEqual(OBJECTIVE_LOCATION_ID_BASE + row.id, row.address)
            self.assertEqual(PREFIX + row.name, row.location_name)
        self.assertEqual(5_840_000, OBJECTIVE_LOCATION_ID_BASE)

    def test_tier_counts_and_no_progression_rows(self):
        v1 = [r for r in OBJECTIVE_ROWS if r.id <= 36]
        tiers = [r.tier for r in v1]
        self.assertEqual((9, 16, 11), (tiers.count(1), tiers.count(2), tiers.count(3)))
        self.assertEqual(NP_IDS, {r.id for r in OBJECTIVE_ROWS if r.no_progression})
        self.assertTrue(all(r.slot_only for r in OBJECTIVE_ROWS if r.id > 36))
        self.assertFalse(any(r.slot_only for r in v1))

    def test_owner_decisions(self):
        self.assertEqual(110, OBJECTIVE_BY_ID[19].requires["n"])
        self.assertEqual("Open 110 chests", OBJECTIVE_BY_ID[19].name)
        self.assertEqual("objectives", OBJECTIVE_BY_ID[36].goal_only)

    def test_exclusions_are_mutual(self):
        for row in OBJECTIVE_ROWS:
            for other in row.exclusive:
                self.assertIn(row.id, OBJECTIVE_BY_ID[other].exclusive, msg=f"{row.id} vs {other}")

    def test_world_knows_every_location_id(self):
        for name, row in OBJECTIVE_LOCATION_TABLE.items():
            self.assertEqual(row.address, SO2RWorld.location_name_to_id[name])
        self.assertEqual(74, len(SO2RWorld.location_name_groups["Objectives"]))

    def test_band_is_free(self):
        others = {addr for name, addr in SO2RWorld.location_name_to_id.items() if not name.startswith(PREFIX)}
        self.assertFalse(others & {r.address for r in OBJECTIVE_ROWS})
        self.assertFalse(any(5_840_000 <= a < 5_850_000 for a in others))


class TestApportion(unittest.TestCase):
    def test_default_mix(self):
        self.assertEqual({1: 3, 2: 3, 3: 1}, apportion(7, {"Easy": 3, "Medium": 3, "Hard": 1}))
        self.assertEqual({1: 2, 2: 2, 3: 1}, apportion(5, {"Easy": 3, "Medium": 3, "Hard": 1}))

    def test_sum_matches_and_ties_prefer_hard(self):
        for count in range(0, 13):
            self.assertEqual(count, sum(apportion(count, {"Easy": 3, "Medium": 3, "Hard": 1}).values()))
        self.assertEqual({1: 0, 2: 0, 3: 1}, apportion(1, {"Easy": 1, "Medium": 1, "Hard": 1}))
        self.assertEqual({1: 0, 2: 1, 3: 1}, apportion(2, {"Easy": 1, "Medium": 1, "Hard": 1}))

    def test_zero_weight_tier_draws_none(self):
        self.assertEqual({1: 0, 2: 4, 3: 4}, apportion(8, {"Easy": 0, "Medium": 1, "Hard": 1}))

    def test_all_zero_is_an_error(self):
        with self.assertRaises(ValueError):
            apportion(3, {"Easy": 0, "Medium": 0, "Hard": 0})


class TestObjectiveDraw(unittest.TestCase):
    MIX = {"Easy": 3, "Medium": 3, "Hard": 1}

    def test_off_draws_nothing_and_consumes_no_randomness(self):
        rng = random.Random(5)
        before = rng.getstate()
        self.assertEqual([], draw(rng, _ctx(), 0, self.MIX))
        self.assertEqual(before, rng.getstate())

    def test_tier_counts_are_honoured_and_deterministic(self):
        for seed in range(60):
            drawn = draw(random.Random(seed), _ctx(), 7, self.MIX)
            self.assertEqual([3, 3, 1], [sum(1 for d in drawn if d.tier == t) for t in (1, 2, 3)], msg=seed)
            self.assertEqual([(d.row.id, d.variant) for d in drawn],
                             [(d.row.id, d.variant) for d in draw(random.Random(seed), _ctx(), 7, self.MIX)])
            self.assertEqual(sorted(drawn, key=lambda d: (d.tier, d.row.id)), drawn)

    def test_exclusivity_groups_and_families_never_collide(self):
        for seed in range(150):
            for goal in ("orbs", "objectives"):
                ctx = _ctx(goal=goal, start_planet="NEDE" if seed % 2 else "EXPEL")
                drawn = draw(random.Random(seed), ctx, 12, self.MIX)
                rows = [d.row for d in drawn]
                self.assertEqual(len(rows), len({r.id for r in rows}))
                self.assertEqual(len(rows), len({r.family for r in rows}), msg=(seed, [r.id for r in rows]))
                for a in rows:
                    for b in rows:
                        if a is not b:
                            self.assertFalse(conflicts(a, b, ctx), msg=(seed, a.id, b.id))
                            self.assertNotIn(b.id, a.exclusive)

    def test_planets_row_never_meets_a_row_on_the_other_planet(self):
        for seed in range(200):
            for start in ("EXPEL", "NEDE"):
                ctx = _ctx(start_planet=start)
                ids = {d.row.id for d in draw(random.Random(seed), ctx, 12, {"Easy": 0, "Medium": 1, "Hard": 3})}
                if 23 in ids:
                    other = {r.id for r in OBJECTIVE_ROWS if r.requires.get("planet") not in (None, start)}
                    self.assertFalse(ids & other, msg=(seed, start, ids & other))

    def test_orbs_row_only_with_the_objectives_goal(self):
        self.assertFalse(eligible(OBJECTIVE_BY_ID[36], _ctx(goal="orbs")))
        self.assertFalse(eligible(OBJECTIVE_BY_ID[36], _ctx(goal="orbs_and_objectives")))
        self.assertTrue(eligible(OBJECTIVE_BY_ID[36], _ctx(goal="objectives")))

    def test_chest_cap_is_seventy_percent(self):
        full = _ctx(chest_count=164)
        self.assertTrue(all(eligible(OBJECTIVE_BY_ID[i], full) for i in (3, 10, 19)))
        small = _ctx(chest_count=100)  # floor(70)
        self.assertTrue(eligible(OBJECTIVE_BY_ID[3], small))
        self.assertFalse(eligible(OBJECTIVE_BY_ID[10], small))
        self.assertFalse(eligible(OBJECTIVE_BY_ID[19], small))
        self.assertFalse(eligible(OBJECTIVE_BY_ID[19], _ctx(chest_count=157)))  # 110 > floor(0.7 * 157) = 109
        self.assertTrue(eligible(OBJECTIVE_BY_ID[19], _ctx(chest_count=158)))

    def test_spot_key_and_town_caps(self):
        spots = frozenset(range(100, 110))  # 10 active spots: n <= 9
        ctx = _ctx(boss_party_ids=spots)
        self.assertTrue(eligible(OBJECTIVE_BY_ID[11], ctx))
        self.assertFalse(eligible(OBJECTIVE_BY_ID[18], ctx))
        self.assertFalse(eligible(OBJECTIVE_BY_ID[6], _ctx(boss_party_ids=frozenset({1, 2, 3, 4}))))  # 4 > 3
        self.assertFalse(eligible(OBJECTIVE_BY_ID[7], _ctx(area_key_count=3)))
        self.assertFalse(eligible(OBJECTIVE_BY_ID[8], _ctx(town_count=4)))
        self.assertFalse(eligible(OBJECTIVE_BY_ID[12], _ctx(fields_ok=False)))

    def test_no_boss_spots_removes_every_spot_dungeon_and_named_row(self):
        ctx = _ctx(boss_party_ids=frozenset())
        for row_id in (6, 11, 18, 17, 20, 22):
            self.assertFalse(eligible(OBJECTIVE_BY_ID[row_id], ctx), msg=row_id)
        for seed in range(30):
            ids = {d.row.id for d in draw(random.Random(seed), ctx, 12, self.MIX)}
            self.assertFalse(ids & {6, 11, 18, 17, 20, 22})

    def test_named_boss_follows_the_active_spots(self):
        only_metatron = _ctx(boss_party_ids=frozenset({535, 191, 522}))
        for seed in range(40):
            for d in draw(random.Random(seed), only_metatron, 12, self.MIX):
                if d.row.id == 20:
                    self.assertEqual("Metatron", d.variant["label"])
                    self.assertEqual("Defeat Metatron", d.text)

    def test_planets_row_is_easy_when_the_other_planet_is_open(self):
        row = OBJECTIVE_BY_ID[23]
        self.assertEqual(3, effective_tier(row, _ctx(other_planet_open=False)))
        self.assertEqual(1, effective_tier(row, _ctx(other_planet_open=True)))

    def test_a_tiny_pool_draws_fewer_and_never_raises(self):
        ctx = _ctx(boss_party_ids=frozenset(), chest_count=10, area_key_count=0, town_count=0, fields_ok=False,
                   chest_areas=frozenset())
        with self.assertLogs(level="WARNING") as logs:
            drawn = draw(random.Random(1), ctx, 12, {"Easy": 1, "Medium": 0, "Hard": 0})
        self.assertEqual(12, len(drawn))  # Easy runs dry and borrows from the tiers above
        self.assertTrue(any("borrowed" in line for line in logs.output))
        with self.assertLogs(level="WARNING") as logs:
            drawn = draw(random.Random(1), ctx, 40, self.MIX)  # more than the table can ever give
        self.assertLess(len(drawn), 40)
        self.assertTrue(any("only" in line for line in logs.output))


class TestObjectivesOffByDefault(SO2RTestBase):
    options = dict(OPEN)

    def test_no_objectives_anywhere(self):
        self.assertEqual([], self.world.objectives)
        self.assertNotIn("objectives", self.world.fill_slot_data())
        self.assertFalse(any(name.startswith(PREFIX) for name in
                             (loc.name for loc in self.multiworld.get_locations(self.player))))
        self.assertFalse(self.world.fill_slot_data()["mapping_version"].endswith("-ob1"))
        self.assertNotIn("objectives", self.world.fill_slot_data()["progression"])

    def test_orbs_still_gate_phynal(self):
        slot = self.world.fill_slot_data()
        self.assertEqual(sorted(i.item_id for i in self.world._open_world_orbs()),
                         slot["open_world"]["area_locks"]["MF_0048"])
        for orb in self.world._open_world_orbs():
            self.assertEqual(["ev_5900200"], slot["chapter_keys"][str(orb.item_id)]["events"])


class TestOffByDefaultRegression(unittest.TestCase):
    def test_default_seeds_are_byte_identical_to_0_85_0(self):
        for label, (options, seed, expected) in DEFAULT_DIGESTS.items():
            self.assertEqual(expected, _digest(options, seed), msg=label)

    def test_explicit_zero_and_orbs_equal_the_defaults(self):
        explicit = {**OPEN, "objective_count_drawn": 0, "goal": "orbs", "objectives_required": 3}
        self.assertEqual(_digest(OPEN, 21), _digest(explicit, 21))

    def test_goal_without_drawn_objectives_collapses_to_orbs(self):
        for goal in ("objectives", "orbs_and_objectives"):
            _mw, world = _build({**OPEN, "goal": goal}, 4)
            self.assertEqual("orbs", world._objective_goal())
            self.assertNotIn("objectives", world.fill_slot_data())
            self.assertEqual(sorted(i.item_id for i in world._open_world_orbs()),
                             world.fill_slot_data()["open_world"]["area_locks"]["MF_0048"])

    def test_story_mode_warns_and_ignores(self):
        with self.assertLogs(level="WARNING") as logs:
            _mw, world = _build({"objective_count_drawn": 7, "goal": "objectives"}, 4)
        self.assertTrue(any("only exist in open_world" in line for line in logs.output))
        self.assertEqual([], world.objectives)
        self.assertNotIn("objectives", world.fill_slot_data())
        self.assertFalse(any(loc.name.startswith(PREFIX) for loc in _mw.get_locations(1)))


class TestObjectivesDrawn(SO2RTestBase):
    options = dict(OBJ)

    def _objective_locations(self):
        return [loc for loc in self.multiworld.get_locations(self.player) if loc.name.startswith(PREFIX)]

    def test_exactly_seven_locations_with_the_right_ids_and_names(self):
        locations = self._objective_locations()
        self.assertEqual(7, len(locations))
        for loc in locations:
            row = OBJECTIVE_LOCATION_TABLE[loc.name]
            self.assertEqual(5_840_000 + row.id, loc.address)
        self.assertEqual({d.row.location_name for d in self.world.objectives}, {loc.name for loc in locations})

    def test_tier_mix_is_three_three_one(self):
        self.assertEqual([3, 3, 1], [sum(1 for d in self.world.objectives if d.tier == t) for t in (1, 2, 3)])

    def test_the_pool_grows_by_one_filler_each(self):
        locations = list(self.multiworld.get_locations(self.player))
        self.assertEqual(len(locations), len(self.multiworld.itempool))

    def test_mapping_suffix(self):
        self.assertTrue(self.world.fill_slot_data()["mapping_version"].endswith("-ob1"))
        self.assertEqual(1, self.world.fill_slot_data()["progression"]["objectives"])

    def test_slot_data_shape(self):
        block = self.world.fill_slot_data()["objectives"]
        self.assertEqual({"version", "location_base", "goal", "required", "gate", "drawn"}, set(block))
        self.assertEqual(1, block["version"])
        self.assertEqual(5_840_000, block["location_base"])
        self.assertEqual("orbs_and_objectives", block["goal"])
        self.assertEqual(5, block["required"])
        self.assertEqual({"event": "ev_5900200", "area": "MF_0048"}, block["gate"])
        self.assertEqual(7, len(block["drawn"]))
        kinds = {"mission_count", "mission_achieved", "locations_done", "items_held", "visited"}
        for entry in block["drawn"]:
            self.assertEqual({"id", "location", "tier", "family", "kind", "params", "text", "no_progression"}, set(entry))
            self.assertEqual(5_840_000 + entry["id"], entry["location"])
            self.assertIn(entry["tier"], (1, 2, 3))
            self.assertIn(entry["kind"], kinds)
            self.assertIsInstance(entry["params"], dict)
            self.assertNotIn("{", entry["text"])
            self.assertEqual(entry["id"] in NP_IDS, entry["no_progression"])
            self.assertTrue(1 <= entry["location"] - 5_840_000 <= 199)
        self.assertEqual([(d["tier"], d["id"]) for d in block["drawn"]], sorted((d["tier"], d["id"]) for d in block["drawn"]))
        json.dumps(block)  # plain JSON

    def test_params_carry_the_seed(self):
        for entry in self.world.fill_slot_data()["objectives"]["drawn"]:
            params = entry["params"]
            if entry["kind"] == "mission_count":
                self.assertIn("mission", params)
                self.assertIn("threshold", params)
            elif entry["kind"] == "visited":
                self.assertTrue(all(g["localities"] and g["need"] >= 1 for g in params["groups"]))
            elif entry["kind"] == "locations_done":
                self.assertTrue("band" in params or params["locations"])
            elif entry["kind"] == "items_held":
                self.assertTrue(params["items"] and params["need"] >= 1)

    def test_spoiler_section(self):
        import io
        out = io.StringIO()
        self.world.write_spoiler(out)
        text = out.getvalue()
        self.assertIn("Objectives (5 of 7 required, goal orbs_and_objectives)", text)
        for d in self.world.objectives:
            self.assertIn(f"[{['', 'Easy', 'Medium', 'Hard'][d.tier]}] {d.text} ({d.row.id}", text)

    def test_every_objective_location_is_in_the_region_with_no_entrance_rule(self):
        entrance = self.multiworld.get_entrance("Menu -> Objectives", self.player)
        self.assertTrue(entrance.access_rule(CollectionState(self.multiworld)))


class TestObjectiveGoals(unittest.TestCase):
    """The Phynal entrance rule per goal, and slot data per goal. other_planet open and required = all drawn, so the
    objectives need the whole item pool and nothing less."""
    BASE = {**OPEN, "other_planet": "open", "objective_count_drawn": 7, "objectives_required": 7}

    def _state(self, world, multiworld, skip=()):
        state = CollectionState(multiworld)
        for item in multiworld.itempool:
            if item.name not in skip:
                state.collect(item)
        return state

    def _entrance(self, multiworld):
        return multiworld.get_entrance("Menu -> Phynal", 1)

    def test_orbs_goal_is_the_four_orbs_only(self):
        mw, world = _build({**self.BASE, "goal": "orbs"}, 31)
        entrance = self._entrance(mw)
        self.assertEqual(7, len(world.objectives))
        self.assertTrue(entrance.access_rule(self._state(world, mw)))
        self.assertFalse(entrance.access_rule(CollectionState(mw)))
        orbs_only = CollectionState(mw)
        for item in mw.itempool:
            if item.name in ORB_NAMES:
                orbs_only.collect(item)
        self.assertTrue(entrance.access_rule(orbs_only))
        block = world.fill_slot_data()["objectives"]
        self.assertEqual("orbs", block["goal"])
        self.assertIsNone(block["gate"])
        self.assertIn("MF_0048", world.fill_slot_data()["open_world"]["area_locks"])

    def test_orbs_and_objectives_needs_both(self):
        mw, world = _build({**self.BASE, "goal": "orbs_and_objectives"}, 32)
        entrance = self._entrance(mw)
        self.assertTrue(entrance.access_rule(self._state(world, mw)))
        self.assertFalse(entrance.access_rule(self._state(world, mw, skip=ORB_NAMES)))
        orbs_only = CollectionState(mw)
        for item in mw.itempool:
            if item.name in ORB_NAMES:
                orbs_only.collect(item)
        self.assertFalse(entrance.access_rule(orbs_only))
        slot = world.fill_slot_data()
        self.assertEqual({"event": "ev_5900200", "area": "MF_0048"}, slot["objectives"]["gate"])
        self.assertIn("MF_0048", slot["open_world"]["area_locks"])
        for orb in world._open_world_orbs():
            self.assertEqual(["ev_5900200"], slot["chapter_keys"][str(orb.item_id)]["events"])

    def test_objectives_goal_ignores_the_orbs_and_drops_their_locks(self):
        mw, world = _build({**self.BASE, "goal": "objectives"}, 33)
        entrance = self._entrance(mw)
        self.assertTrue(entrance.access_rule(self._state(world, mw)))
        self.assertTrue(entrance.access_rule(self._state(world, mw, skip=ORB_NAMES)))
        self.assertFalse(entrance.access_rule(CollectionState(mw)))
        slot = world.fill_slot_data()
        self.assertEqual({"event": "ev_5900200", "area": "MF_0048"}, slot["objectives"]["gate"])
        self.assertEqual("objectives", slot["objectives"]["goal"])
        self.assertNotIn("MF_0048", slot["open_world"]["area_locks"])  # absent, never an empty list
        for orb in world._open_world_orbs():
            self.assertEqual([], slot["chapter_keys"][str(orb.item_id)]["events"])
        self.assertTrue(set(o.native_id for o in world._open_world_orbs()) <= set(slot["story_keys"]["item_ids"]))

    def test_required_is_clamped_to_the_drawn_count(self):
        with self.assertLogs(level="WARNING"):
            _mw, world = _build({**OPEN, "objective_count_drawn": 3, "objectives_required": 9,
                                 "goal": "orbs_and_objectives"}, 5)
        self.assertEqual(3, world.fill_slot_data()["objectives"]["required"])

    def test_all_zero_tier_mix_is_an_option_error(self):
        from Options import OptionError
        with self.assertRaises(OptionError):
            _build({**OPEN, "objective_count_drawn": 5, "objective_tier_mix": {"Easy": 0, "Medium": 0, "Hard": 0}}, 1)

    def test_challenge_missions_suffix_order(self):
        _mw, world = _build({**OBJ, "challenge_missions": True}, 6)
        self.assertTrue(world.fill_slot_data()["mapping_version"].endswith("-cm1-ob1"))


class TestObjectivesFill(unittest.TestCase):
    def test_all_goals_generate_and_are_beatable(self):
        for goal in ("orbs", "objectives", "orbs_and_objectives"):
            for seed, planet in ((41, "expel"), (42, "nede")):
                options = {**OBJ, "goal": goal, "starting_planet": planet}
                mw = _fill(options, seed)
                self.assertTrue(mw.can_beat_game(CollectionState(mw)), msg=(goal, seed))
                world = mw.worlds[1]
                self.assertEqual(7, len(world.objectives))

    def test_no_progression_rows_never_hold_progression(self):
        options = {**OPEN, "objective_count_drawn": 12, "objectives_required": 8, "goal": "orbs_and_objectives",
                   "objective_tier_mix": {"Easy": 0, "Medium": 1, "Hard": 1}}
        seen = 0
        for seed in range(50, 56):
            mw = _fill(options, seed)
            for loc in mw.get_locations(1):
                if loc.name.startswith(PREFIX) and OBJECTIVE_LOCATION_TABLE[loc.name].no_progression:
                    seen += 1
                    self.assertFalse(loc.item.advancement, msg=(seed, loc.name, loc.item.name))
        self.assertGreater(seen, 6)

    def test_the_gear_pool_can_be_the_vanilla_one_too(self):
        mw = _fill({**OBJ, "item_pool": "vanilla"}, 7)
        self.assertTrue(mw.can_beat_game(CollectionState(mw)))
        self.assertEqual(7, sum(1 for loc in mw.get_locations(1) if loc.name.startswith(PREFIX)))

    def test_item_names_in_pool_are_known(self):
        mw = _fill(OBJ, 8)
        self.assertTrue(all(item.name in ITEM_TABLE for item in mw.get_items() if item.player == 1))
