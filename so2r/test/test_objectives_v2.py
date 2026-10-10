"""Bucket List objectives v2 (world 0.87.0): the 38 appended rows, objective_slots (named objectives and Random categories),
Objectives Auto-Win, and the regression that a seed without slots or auto-win draws exactly what 0.86.0 drew."""
import hashlib
import io
import json
import random
import unittest

from BaseClasses import CollectionState

from . import SO2RTestBase
from .test_loot import _fill
from .test_objectives import OBJ, OPEN, PREFIX, _build, _ctx, _digest
from .. import SO2RWorld
from ..objectives import (CATEGORIES, CATEGORY_BY_NAME, CATEGORY_NAMES, OBJECTIVE_BY_ID, OBJECTIVE_ROWS, SLOT_KEYS,
                          category_members, conflicts, draw, effective_tier, eligible)
from ..open_world import ORB_NAMES

MIX = {"Easy": 3, "Medium": 3, "Hard": 1}
BY_NAME = {r.name: r for r in OBJECTIVE_ROWS}
V2_FAMILIES = {"boss": 19, "dungeon": 12, "party": 3, "collection": 4}

# Captured on world 0.86.0 (before the v2 rows, slots and auto-win existed): with drawn > 0 and no slots the draw is unchanged.
V1_DRAW_DIGEST = "f8f07cc7980f9432aa5d16b1825795a5c49715ea50db66cc79a920ac383b0bb3"
V1_WORLD_DIGESTS = {
    "obj7": (OBJ, 41, "3d403ed6fe2f501b902197854df3be474bb763545f08f32deb7b8de9d6480f23"),
    "obj_nede_objectives": ({**OBJ, "goal": "objectives", "starting_planet": "nede"}, 42,
                            "bb7a34035bf1c0a6d6df97ee2c6ad963a4eda9005bc21be23f54cada02145d91"),
    "obj12_cm": ({**OPEN, "objective_count_drawn": 12, "objectives_required": 8, "goal": "orbs_and_objectives",
                  "challenge_missions": True}, 43, "11b9f970d699c18f05a27c03160d508d809e5821ee3e0cc62b37a57ab4920c24"),
}


AREAS = frozenset({"MF_0002", "MF_0005", "MF_0008", "MF_0011", "MF_0013", "MF_0014", "MF_0020", "MF_0022", "MF_0027",
                   "MF_0033", "MF_0036", "MF_0037", "MF_0038", "MF_0039", "MF_0042"})
ALL_SPOTS = frozenset(p for r in OBJECTIVE_ROWS if r.family == "boss" for p in [r.requires["boss"]])


def _ctx2(**changes):
    changes.setdefault("chest_areas", AREAS)
    changes.setdefault("boss_party_ids", ALL_SPOTS)
    return _ctx(character_count=3, **changes)


def _spoiler(world):
    out = io.StringIO()
    world.write_spoiler(out)
    return out.getvalue()


class TestV2Table(unittest.TestCase):
    def test_new_rows_by_family(self):
        new = [r for r in OBJECTIVE_ROWS if r.id > 36]
        self.assertEqual(list(range(37, 75)), [r.id for r in new])
        for family, count in V2_FAMILIES.items():
            self.assertEqual(count, sum(1 for r in new if r.family == family), msg=family)
        self.assertEqual(38, sum(V2_FAMILIES.values()))
        self.assertTrue(all(r.id <= 199 and r.slot_only and not r.no_progression for r in new))

    def test_every_new_row_uses_an_existing_evaluator_shape(self):
        for r in OBJECTIVE_ROWS:
            if r.id <= 36:
                continue
            self.assertIn(r.kind, ("locations_done", "items_held"), msg=r.id)
            if r.family == "boss":
                self.assertEqual([5_600_000 + r.requires["boss"]], r.params["locations"])

    def test_categories_partition_the_families(self):
        families = {r.family for r in OBJECTIVE_ROWS}
        family_categories = [c for c in CATEGORIES if c.families]
        covered = [f for c in family_categories for f in c.families]
        self.assertEqual(sorted(families), sorted(covered))  # every family in exactly one category
        self.assertEqual(10, len(CATEGORIES))
        self.assertEqual(["Random", "Random Easy", "Random Medium", "Random Hard", "Random Boss", "Random Dungeon Clear",
                          "Random Combat", "Random Exploration", "Random Collection", "Random Side Content"],
                         list(CATEGORY_NAMES))
        for category in CATEGORIES:
            self.assertTrue(category_members(category), msg=category.name)
        self.assertEqual(len(OBJECTIVE_ROWS), len(category_members(CATEGORY_BY_NAME["Random"])))

    def test_slot_option_keys(self):
        from ..options import ObjectiveSlots
        self.assertEqual(set(SLOT_KEYS), set(ObjectiveSlots.valid_keys))
        self.assertEqual(74 + 10, len(SLOT_KEYS))
        self.assertEqual("Objectives", ObjectiveSlots.display_name)

    def test_exclusions_mutual_and_boss_rows_exclude_their_dungeon(self):
        for r in OBJECTIVE_ROWS:
            for other in r.exclusive:
                self.assertIn(r.id, OBJECTIVE_BY_ID[other].exclusive)
        self.assertIn(BY_NAME["Defeat Halfynx"].id, BY_NAME["Fully clear the Hoffman Ruins"].exclusive)
        self.assertIn(BY_NAME["Defeat Jophiel"].id, BY_NAME["Defeat a Wise Man (Jophiel or Metatron)"].exclusive)

    def test_thresholds_of_one_thing_never_coexist(self):
        ctx = _ctx2()
        for a, b in (("Hold 4 area keys", "Hold 7 area keys"), ("Hold 7 area keys", "Hold 11 area keys"),
                     ("Collect 2 Orbs", "Collect 3 Orbs"), ("Recruit 2 characters", "Recruit 4 characters"),
                     ("Open 40 chests", "Open 90 chests")):
            self.assertTrue(conflicts(BY_NAME[a], BY_NAME[b], ctx, False), msg=(a, b))
        # different bosses and different dungeons may coexist
        self.assertFalse(conflicts(BY_NAME["Defeat Halfynx"], BY_NAME["Defeat Lavarre"], ctx, False))
        self.assertFalse(conflicts(BY_NAME["Fully clear Krosse Cave"], BY_NAME["Fully clear Salva Mines"], ctx, False))
        self.assertTrue(conflicts(BY_NAME["Fully clear Krosse Cave"], BY_NAME["Fully clear Salva Mines"], ctx, True))


class TestV1DrawUnchanged(unittest.TestCase):
    def test_draw_without_slots_is_the_0_86_0_draw(self):
        h = hashlib.sha256()
        for seed in range(200):
            for start in ("EXPEL", "NEDE"):
                for goal in ("orbs", "objectives"):
                    d = draw(random.Random(seed), _ctx(start_planet=start, goal=goal), 1 + seed % 12, MIX)
                    h.update(json.dumps([(x.row.id, x.variant, x.tier) for x in d]).encode())
        self.assertEqual(V1_DRAW_DIGEST, h.hexdigest())

    def test_blank_slots_equal_no_slots(self):
        for seed in range(30):
            a = draw(random.Random(seed), _ctx(), 7, MIX)
            b = draw(random.Random(seed), _ctx(), 7, MIX, slots=["", "  "])
            self.assertEqual([(x.row.id, x.variant) for x in a], [(x.row.id, x.variant) for x in b])

    def test_mix_never_draws_slot_only_rows(self):
        for seed in range(100):
            self.assertTrue(all(d.row.id <= 36 for d in draw(random.Random(seed), _ctx2(), 12, MIX)))

    def test_worlds_with_drawn_objectives_and_no_slots_are_byte_identical_to_0_86_0(self):
        for label, (options, seed, expected) in V1_WORLD_DIGESTS.items():
            self.assertEqual(expected, _digest(options, seed), msg=label)

    def test_explicit_defaults_of_the_new_options_change_nothing(self):
        options = {**OBJ, "objective_slots": [], "objectives_auto_win": False}
        self.assertEqual(_digest(OBJ, 41), _digest(options, 41))


class TestSlotDraw(unittest.TestCase):
    def test_exact_names_are_honoured(self):
        names = ["Defeat 100 enemies", "Fully clear Krosse Cave", "Defeat Halfynx", "Recruit 3 characters"]
        for seed in range(40):
            drawn = draw(random.Random(seed), _ctx2(), 6, MIX, slots=names)
            ids = {d.row.id for d in drawn}
            self.assertTrue({BY_NAME[n].id for n in names} <= ids, msg=seed)
            self.assertEqual(6, len(drawn))
            self.assertEqual(4, sum(1 for d in drawn if d.how == "picked"))

    def test_names_are_case_insensitive(self):
        drawn = draw(random.Random(1), _ctx2(), 2, MIX, slots=["defeat 100 ENEMIES"])
        self.assertIn(2, {d.row.id for d in drawn})

    def test_every_category_pick_is_a_member(self):
        for category in CATEGORIES:
            for seed in range(25):
                ctx = _ctx2(start_planet="NEDE" if seed % 2 else "EXPEL")
                drawn = draw(random.Random(seed), ctx, 4, MIX, slots=[category.name, category.name])
                picks = [d for d in drawn if d.how == f"category: {category.name}"]
                self.assertTrue(picks, msg=(category.name, seed))
                for d in picks:
                    self.assertTrue(category.contains(d.row, effective_tier(d.row, ctx)), msg=(category.name, d.row.id))

    def test_random_follows_the_tier_mix_weights(self):
        counts = {1: 0, 2: 0, 3: 0}
        for seed in range(300):
            d = draw(random.Random(seed), _ctx2(), 1, {"Easy": 1, "Medium": 0, "Hard": 0}, slots=["Random"])
            counts[d[0].tier] += 1
        self.assertEqual({1: 300, 2: 0, 3: 0}, counts)
        counts = {1: 0, 2: 0, 3: 0}
        for seed in range(600):
            counts[draw(random.Random(seed), _ctx2(), 1, {"Easy": 3, "Medium": 3, "Hard": 1}, slots=["Random"])[0].tier] += 1
        self.assertGreater(counts[1], counts[3])
        self.assertGreater(counts[2], counts[3])
        self.assertGreater(counts[3], 0)

    def test_unavailable_picks_are_replaced_by_the_same_tier(self):
        no_spots = _ctx2(boss_party_ids=frozenset())
        for name in ("Defeat Halfynx", "Defeat Lavarre", "Defeat Jophiel"):
            row = BY_NAME[name]
            self.assertFalse(eligible(row, no_spots))
            for seed in range(20):
                with self.assertLogs(level="WARNING") as logs:
                    drawn = draw(random.Random(seed), no_spots, 3, MIX, slots=[name])
                self.assertTrue(any("not available" in line for line in logs.output))
                self.assertNotIn(row.id, {d.row.id for d in drawn})
                self.assertEqual(3, len(drawn))
                replaced = [d for d in drawn if d.how == f"replaced {name}"]
                self.assertEqual(1, len(replaced))
                self.assertEqual(row.tier, replaced[0].tier)
                self.assertTrue(eligible(replaced[0].row, no_spots))

    def test_recruit_is_capped_by_the_roster(self):
        for n in (2, 3, 4):
            row = BY_NAME[f"Recruit {n} characters"]
            self.assertEqual(n <= 3, eligible(row, _ctx(character_count=3)), msg=n)
            self.assertEqual(n <= 1, eligible(row, _ctx(character_count=1)), msg=n)
        with self.assertLogs(level="WARNING"):
            drawn = draw(random.Random(3), _ctx(character_count=3), 2, MIX, slots=["Recruit 4 characters"])
        self.assertNotIn(BY_NAME["Recruit 4 characters"].id, {d.row.id for d in drawn})

    def test_area_key_thresholds_are_capped(self):
        self.assertTrue(eligible(BY_NAME["Hold 11 area keys"], _ctx2(area_key_count=15)))
        self.assertFalse(eligible(BY_NAME["Hold 11 area keys"], _ctx2(area_key_count=10)))
        self.assertFalse(eligible(BY_NAME["Hold 7 area keys"], _ctx2(area_key_count=6)))

    def test_boss_rows_need_their_spot(self):
        only = _ctx2(boss_party_ids=frozenset({191}))
        self.assertTrue(eligible(BY_NAME["Defeat Allen Tucks"], only))
        self.assertFalse(eligible(BY_NAME["Defeat Snow Ogre"], only))
        self.assertFalse(any(eligible(BY_NAME[r.name], _ctx2(boss_party_ids=frozenset())) for r in OBJECTIVE_ROWS
                             if r.family == "boss"))
        for seed in range(30):
            drawn = draw(random.Random(seed), _ctx2(boss_party_ids=frozenset()), 4, MIX, slots=["Random Boss"] * 4)
            self.assertFalse(any(d.row.family in ("boss", "named") for d in drawn))

    def test_conflicting_picks_keep_the_first_and_warn(self):
        for a, b in (("Open 40 chests", "Open 90 chests"), ("Hold 4 area keys", "Hold 11 area keys"),
                     ("Fully clear Salva Mines", "Defeat Allen Tucks"), ("Collect 2 Orbs", "Collect 3 Orbs")):
            with self.assertLogs(level="WARNING") as logs:
                drawn = draw(random.Random(5), _ctx2(), 4, MIX, slots=[a, b])
            ids = {d.row.id for d in drawn}
            self.assertIn(BY_NAME[a].id, ids)
            self.assertNotIn(BY_NAME[b].id, ids)
            self.assertTrue(any("conflicts" in line for line in logs.output), msg=(a, b))
            self.assertEqual(4, len(drawn))

    def test_exclusivity_across_picks_categories_and_mix(self):
        for seed in range(120):
            ctx = _ctx2(start_planet="NEDE" if seed % 2 else "EXPEL", other_planet_open=bool(seed % 3 == 0))
            slots = ["Random", "Random Boss", "Random Boss", "Random Collection", "Random Collection",
                     "Random Exploration", "Defeat 100 enemies", "Random Dungeon Clear"]
            drawn = draw(random.Random(seed), ctx, 12, MIX, slots=slots)
            rows = [d.row for d in drawn]
            self.assertEqual(len(rows), len({r.id for r in rows}))
            for a in rows:
                for b in rows:
                    if a is not b:
                        self.assertFalse(conflicts(a, b, ctx, False), msg=(seed, a.id, b.id))

    def test_extra_entries_beyond_the_count_are_ignored_with_a_warning(self):
        with self.assertLogs(level="WARNING") as logs:
            drawn = draw(random.Random(2), _ctx2(), 2, MIX, slots=["Defeat 100 enemies", "Open 40 chests", "Visit 5 towns"])
        self.assertTrue(any("extra" in line for line in logs.output))
        ids = {d.row.id for d in drawn}
        self.assertEqual(2, len(drawn))
        self.assertIn(2, ids)
        self.assertNotIn(8, ids)

    def test_unknown_entry_falls_back_to_the_mix(self):
        with self.assertLogs(level="WARNING") as logs:
            drawn = draw(random.Random(2), _ctx2(), 3, MIX, slots=["Defeat 100 enemies", "Not an objective"])
        self.assertTrue(any("not an objective" in line for line in logs.output))
        self.assertEqual(3, len(drawn))

    def test_deterministic(self):
        slots = ["Random Boss", "Defeat 100 enemies", "Random Hard"]
        for seed in range(30):
            a = draw(random.Random(seed), _ctx2(), 5, MIX, slots=slots)
            b = draw(random.Random(seed), _ctx2(), 5, MIX, slots=slots)
            self.assertEqual([(d.row.id, d.variant, d.how) for d in a], [(d.row.id, d.variant, d.how) for d in b])
            self.assertEqual(5, len(a))

    def test_open_slots_keep_the_tier_mix_roughly(self):
        # 7 drawn, one explicit Hard: the other six follow 3/3/0 of what is still missing
        for seed in range(30):
            drawn = draw(random.Random(seed), _ctx2(), 7, MIX, slots=["Defeat Metatron"])
            self.assertEqual([3, 3, 1], [sum(1 for d in drawn if d.tier == t) for t in (1, 2, 3)], msg=seed)


class TestSlotWorld(unittest.TestCase):
    SLOTS = ["Random Boss", "Defeat 100 enemies", "Random Hard"]
    BASE = {**OPEN, "objective_count_drawn": 5, "objectives_required": 3, "goal": "orbs", "other_planet": "open"}

    def test_world_honours_slots_and_writes_the_spoiler(self):
        _mw, world = _build({**self.BASE, "objective_slots": self.SLOTS}, 61)
        ids = {d.row.id for d in world.objectives}
        self.assertIn(2, ids)
        by_how = {d.how: d for d in world.objectives}
        boss = by_how["category: Random Boss"]
        self.assertIn(boss.row.family, ("boss", "named"))
        self.assertEqual(3, by_how["category: Random Hard"].tier)
        self.assertEqual(5, len(world.objectives))
        text = _spoiler(world)
        self.assertIn("Objectives (3 of 5 required, goal orbs)", text)
        self.assertIn("Defeat 100 enemies (2) - picked", text)
        self.assertIn(" - category: Random Boss", text)
        self.assertIn(" - category: Random Hard", text)
        self.assertIn(" - tier mix", text)

    def test_slot_option_is_validated(self):
        from Options import OptionError
        _mw, world = _build({**self.BASE, "objective_slots": ["Random Hard", "Defeat 100 enemies"]}, 62)
        self.assertEqual(2, sum(1 for d in world.objectives if d.how.startswith(("picked", "category"))))
        from ..options import ObjectiveSlots
        ObjectiveSlots.from_any(["Random Hard", "Defeat 100 enemies"]).verify_keys()
        with self.assertRaises(OptionError):
            ObjectiveSlots.from_any(["Defeat the Moon"]).verify_keys()

    def test_slot_data_shape_is_unchanged_without_auto_win(self):
        _mw, world = _build({**self.BASE, "objective_slots": self.SLOTS}, 63)
        block = world.fill_slot_data()["objectives"]
        self.assertEqual({"version", "location_base", "goal", "required", "gate", "drawn"}, set(block))
        self.assertTrue(world.fill_slot_data()["mapping_version"].endswith("-ob1"))

    def test_boss_objectives_only_exist_with_boss_checks(self):
        slots = ["Random Boss"] * 3 + ["Defeat Halfynx"]
        _mw, on = _build({**self.BASE, "boss_checks": True, "objective_count_drawn": 4, "objective_slots": slots}, 64)
        self.assertEqual(4, sum(1 for d in on.objectives if d.row.family in ("boss", "named")))
        for entry in on.fill_slot_data()["objectives"]["drawn"]:
            if entry["family"] == "boss":
                self.assertEqual(1, len(entry["params"]["locations"]))
        with self.assertLogs(level="WARNING"):
            _mw, off = _build({**self.BASE, "boss_checks": False, "objective_count_drawn": 4, "objective_slots": slots}, 64)
        self.assertEqual(4, len(off.objectives))
        self.assertFalse(any(d.row.family in ("boss", "named", "spots") for d in off.objectives))

    def test_recruit_cap_follows_the_roster(self):
        slots = ["Recruit 2 characters", "Recruit 4 characters"]
        _mw, small = _build({**self.BASE, "objective_slots": slots, "joinable_characters": 2}, 65)
        self.assertNotIn(BY_NAME["Recruit 4 characters"].id, {d.row.id for d in small.objectives})
        _mw, big = _build({**self.BASE, "objective_slots": ["Recruit 4 characters"], "joinable_characters": 5}, 65)
        entry = next(d for d in big.fill_slot_data()["objectives"]["drawn"] if d["text"] == "Recruit 4 characters")
        self.assertEqual(4, entry["params"]["need"])
        self.assertEqual(5, len(entry["params"]["items"]))
        self.assertEqual(sorted(c.item_id for c in big._character_items()), entry["params"]["items"])

    def test_dungeon_clear_lists_chests_and_the_seed_spots(self):
        _mw, world = _build({**self.BASE, "objective_slots": ["Fully clear the Hoffman Ruins"]}, 66)
        entry = next(d for d in world.fill_slot_data()["objectives"]["drawn"] if d["text"] == "Fully clear the Hoffman Ruins")
        locations = entry["params"]["locations"]
        self.assertEqual(12, sum(1 for loc in locations if 5_500_000 <= loc < 5_600_000))
        self.assertEqual([5_600_210, 5_600_211], sorted(loc for loc in locations if loc >= 5_600_000))
        _mw, off = _build({**self.BASE, "boss_checks": False, "objective_slots": ["Fully clear the Hoffman Ruins"]}, 66)
        entry = next(d for d in off.fill_slot_data()["objectives"]["drawn"] if d["text"] == "Fully clear the Hoffman Ruins")
        self.assertEqual(12, len(entry["params"]["locations"]))

    def test_collect_orbs_rows_in_any_goal(self):
        for goal in ("orbs", "objectives", "orbs_and_objectives"):
            _mw, world = _build({**self.BASE, "goal": goal, "objective_slots": ["Collect 2 Orbs"]}, 67)
            entry = next(d for d in world.fill_slot_data()["objectives"]["drawn"] if d["text"] == "Collect 2 Orbs")
            self.assertEqual(2, entry["params"]["need"])
            self.assertEqual(4, len(entry["params"]["items"]))


class TestAutoWin(unittest.TestCase):
    """other_planet open, required = drawn = 3 picks that each need items, so the completion needs those items and no more."""
    SLOTS = ["Hold 4 area keys", "Fully clear Krosse Cave", "Recruit 2 characters"]
    BASE = {**OPEN, "other_planet": "open", "objective_count_drawn": 3, "objectives_required": 3, "goal": "orbs",
            "objective_slots": SLOTS}

    @staticmethod
    def _state(multiworld, skip=lambda item: False):
        state = CollectionState(multiworld)
        for item in multiworld.itempool:
            if not skip(item):
                state.collect(item)
        return state

    def test_off_by_default(self):
        mw, world = _build(self.BASE, 71)
        self.assertFalse(world.objectives_auto_win)
        self.assertNotIn("auto_win", world.fill_slot_data()["objectives"])
        orbless = self._state(mw, lambda i: i.name in ORB_NAMES)
        self.assertFalse(mw.completion_condition[1](orbless))  # the Final Voyage still needs the Orbs
        self.assertTrue(mw.completion_condition[1](self._state(mw)))

    def test_completion_is_the_required_objectives_only(self):
        for goal in ("orbs", "objectives", "orbs_and_objectives"):
            mw, world = _build({**self.BASE, "goal": goal, "objectives_auto_win": True}, 72)
            self.assertTrue(world.objectives_auto_win)
            condition = mw.completion_condition[1]
            self.assertFalse(condition(CollectionState(mw)), msg=goal)
            self.assertTrue(condition(self._state(mw)), msg=goal)
            # no Orbs and no Final Voyage: the objectives alone win
            self.assertTrue(condition(self._state(mw, lambda i: i.name in ORB_NAMES)), msg=goal)
            # missing the Krosse Cave key, a character, or the keys: not done (3 of 3 required)
            self.assertFalse(condition(self._state(mw, lambda i: i.name == "Area Key: Krosse Cave")), msg=goal)
            self.assertFalse(condition(self._state(mw, lambda i: i.name.startswith("Character:"))), msg=goal)
            block = world.fill_slot_data()["objectives"]
            self.assertIs(True, block["auto_win"])
            self.assertEqual(goal, block["goal"])

    def test_goal_still_shapes_the_final_voyage_gate(self):
        mw, world = _build({**self.BASE, "goal": "objectives", "objectives_auto_win": True}, 73)
        slot = world.fill_slot_data()
        self.assertEqual({"event": "ev_5900200", "area": "MF_0048"}, slot["objectives"]["gate"])
        self.assertNotIn("MF_0048", slot["open_world"]["area_locks"])
        mw, world = _build({**self.BASE, "goal": "orbs", "objectives_auto_win": True}, 73)
        slot = world.fill_slot_data()
        self.assertIsNone(slot["objectives"]["gate"])
        self.assertIn("MF_0048", slot["open_world"]["area_locks"])
        # the Phynal entrance is unchanged: the Orbs still open it
        entrance = mw.get_entrance("Menu -> Phynal", 1)
        self.assertFalse(entrance.access_rule(self._state(mw, lambda i: i.name in ORB_NAMES)))
        self.assertTrue(entrance.access_rule(self._state(mw)))

    def test_required_fewer_than_drawn(self):
        mw, world = _build({**self.BASE, "objectives_required": 1, "objectives_auto_win": True}, 74)
        condition = mw.completion_condition[1]
        self.assertFalse(condition(CollectionState(mw)))  # the picks all need items
        keys_only = self._state(mw, lambda i: not i.name.startswith("Area Key:"))
        self.assertTrue(condition(keys_only))

    def test_without_drawn_objectives_it_warns_and_changes_nothing(self):
        with self.assertLogs(level="WARNING") as logs:
            mw, world = _build({**OPEN, "objectives_auto_win": True}, 75)
        self.assertTrue(any("objectives_auto_win" in line for line in logs.output))
        self.assertFalse(world.objectives_auto_win)
        self.assertNotIn("objectives", world.fill_slot_data())
        self.assertFalse(mw.completion_condition[1](CollectionState(mw)))

    def test_story_mode_ignores_it(self):
        with self.assertLogs(level="WARNING"):
            _mw, world = _build({"objective_count_drawn": 5, "objectives_auto_win": True}, 76)
        self.assertFalse(world.objectives_auto_win)


class TestV2Fill(unittest.TestCase):
    def test_several_seeds_generate_and_are_beatable(self):
        variants = [
            {"objective_slots": ["Random Boss", "Defeat 100 enemies", "Random Hard"]},
            {"objective_slots": ["Random Dungeon Clear", "Random Collection", "Random Exploration", "Random"],
             "objectives_auto_win": True},
            {"objective_slots": ["Random"] * 6, "objectives_auto_win": True, "goal": "objectives"},
            {"objective_slots": ["Random Side Content", "Random Combat", "Random Easy", "Random Medium"],
             "goal": "orbs_and_objectives"},
            {"objective_slots": ["Fully clear Salva Mines", "Collect 3 Orbs", "Hold 11 area keys", "Recruit 3 characters"],
             "objectives_auto_win": True, "starting_planet": "nede"},
        ]
        for i, extra in enumerate(variants):
            for seed in (81 + i, 91 + i):
                options = {**OPEN, "objective_count_drawn": 6, "objectives_required": 4, "goal": "orbs", **extra}
                with self.assertNoLogs(level="ERROR"):
                    mw = _fill(options, seed)
                self.assertTrue(mw.can_beat_game(CollectionState(mw)), msg=(i, seed))
                world = mw.worlds[1]
                self.assertEqual(sum(1 for loc in mw.get_locations(1) if loc.name.startswith(PREFIX)),
                                 len(world.objectives))
                for loc in mw.get_locations(1):
                    if loc.name.startswith(PREFIX) and loc.item is not None:
                        self.assertIn(loc.address, {d.row.address for d in world.objectives})

    def test_auto_win_seed_is_beatable_without_the_orbs_in_logic(self):
        options = {**OPEN, "other_planet": "open", "objective_count_drawn": 3, "objectives_required": 3, "goal": "orbs",
                   "objectives_auto_win": True,
                   "objective_slots": ["Hold 4 area keys", "Fully clear Krosse Cave", "Recruit 2 characters"]}
        mw = _fill(options, 99)
        self.assertTrue(mw.can_beat_game(CollectionState(mw)))
        state = CollectionState(mw)
        for item in mw.get_items():
            if item.player == 1 and item.name not in ORB_NAMES:
                state.collect(item)
        self.assertTrue(mw.completion_condition[1](state))


if __name__ == "__main__":
    unittest.main()
