"""Traps: 11 junk items that replace pure filler (trap_chance / trap_weights)."""
from collections import Counter
import unittest

from BaseClasses import ItemClassification

from . import SO2RTestBase
from ..items import EQUIPMENT_CATEGORIES, ITEM_TABLE, TRAP_NAMES, build_item_name_groups
from ..options import TrapWeights

EXPECTED = {
    5_910_001: "Ambush Trap", 5_910_002: "Monster Magnet Trap", 5_910_003: "Chain Trap",
    5_910_004: "Lost Trap", 5_910_005: "Heavy Boots Trap", 5_910_006: "Oracle Trap",
    5_910_007: "Muzak Trap", 5_910_008: "Empowered Foes Trap", 5_910_009: "Back Attack Trap",
    5_910_010: "Status Trap", 5_910_011: "Fatigue Trap",
}
TRAPS = set(EXPECTED.values())


def _build(options, seed=None):
    from test.general import setup_multiworld
    from .. import SO2RWorld
    return setup_multiworld(SO2RWorld, seed=seed, options=options)


def _pure_filler(item):
    return item.classification == ItemClassification.filler and ITEM_TABLE[item.name].category not in EQUIPMENT_CATEGORIES


class TestTrapTable(unittest.TestCase):
    def test_ids_names_and_classification(self):
        for code, name in EXPECTED.items():
            self.assertEqual(code, ITEM_TABLE[name].code)
            self.assertEqual(ItemClassification.trap, ITEM_TABLE[name].classification)
        self.assertEqual(sorted(EXPECTED.values()), sorted(TRAP_NAMES))
        self.assertEqual(TRAPS, build_item_name_groups()["Traps"])

    def test_stingy_foes_is_retired(self):
        self.assertNotIn("Stingy Foes Trap", ITEM_TABLE)
        self.assertNotIn("Stingy Foes Trap", TRAP_NAMES)
        self.assertNotIn("Stingy Foes Trap", TrapWeights.valid_keys)
        self.assertNotIn(5_910_012, {data.code for data in ITEM_TABLE.values()})

    def test_default_weights_cover_every_trap(self):
        self.assertEqual({name: 1 for name in TRAP_NAMES}, TrapWeights.default)


class TestNoTrapsByDefault(SO2RTestBase):
    options = {}

    def test_chance_zero_gives_none(self):
        self.assertFalse(TRAPS & {item.name for item in self.multiworld.itempool})


class TestAllFillerBecomesTraps(SO2RTestBase):
    options = {"trap_chance": 100}

    def test_every_pure_filler_is_a_trap_and_count_is_kept(self):
        base = _build({}, seed=self.multiworld.seed)
        pool = self.multiworld.itempool
        self.assertEqual(len(base.itempool), len(pool))
        self.assertEqual(len(self.multiworld.get_unfilled_locations()), len(pool))
        self.assertFalse(any(_pure_filler(item) for item in pool))
        self.assertEqual(sum(1 for item in base.itempool if _pure_filler(item)),
                         sum(1 for item in pool if item.name in TRAPS))
        for item in pool:
            if item.name in TRAPS:
                self.assertEqual(ItemClassification.trap, item.classification)


class TestNothingElseIsReplaced(SO2RTestBase):
    options = {"trap_chance": 40, "game_mode": "open_world", "starting_planet": "nede"}

    def test_only_pure_filler_changed(self):
        base = _build({k: v for k, v in self.options.items() if k != "trap_chance"}, seed=self.multiworld.seed)
        before = Counter(item.name for item in base.itempool)
        after = Counter(item.name for item in self.multiworld.itempool)
        self.assertEqual(len(base.itempool), len(self.multiworld.itempool))
        gained = {name for name in after if after[name] > before[name]}
        self.assertTrue(gained and gained <= TRAPS, gained)
        for name in set(before) | set(after):
            if name not in TRAPS and after[name] < before[name]:
                data = ITEM_TABLE[name]
                self.assertEqual(ItemClassification.filler, data.classification, name)
                self.assertNotIn(data.category, EQUIPMENT_CATEGORIES)
            if name not in TRAPS and after[name] > before[name]:
                self.fail(name)
        filler = sum(1 for item in base.itempool if _pure_filler(item))
        self.assertEqual(round(filler * 40 / 100), sum(after[t] for t in TRAPS))


class TestZeroedWeight(SO2RTestBase):
    options = {"trap_chance": 100, "trap_weights": {name: (0 if name in ("Ambush Trap", "Lost Trap") else 1) for name in TRAP_NAMES}}

    def test_disabled_traps_never_appear(self):
        names = {item.name for item in self.multiworld.itempool}
        self.assertFalse(names & {"Ambush Trap", "Lost Trap"})
        self.assertTrue(names & TRAPS)


class TestOneWeightOnly(SO2RTestBase):
    options = {"trap_chance": 100, "trap_weights": {name: (5 if name == "Chain Trap" else 0) for name in TRAP_NAMES}}

    def test_only_that_trap(self):
        self.assertEqual({"Chain Trap"}, TRAPS & {item.name for item in self.multiworld.itempool})


class TestAllWeightsZero(SO2RTestBase):
    options = {"trap_chance": 100, "trap_weights": {name: 0 for name in TRAP_NAMES}}

    def test_no_traps(self):
        self.assertFalse(TRAPS & {item.name for item in self.multiworld.itempool})


if __name__ == "__main__":
    unittest.main()
