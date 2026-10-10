"""Loot tiers (docs/LOOT_TIERS_IDEAS.md section 3): the roll, the slot-data contract, uniques.json and the spoiler."""
import io
import random
import unittest
from collections import Counter

from . import SO2RTestBase
from ..items import ITEM_TABLE
from ..loot import (FACTOR_BY_ID, UNIQUE_LISTED_MULTIPLIER, FACTORS, LOOT_TIER_NAMES, NEVER_ROLLED, UNIQUE_BY_ITEM, UNIQUES, candidates,
                    progression_fractions, roll_item, slot_mask, tier_weights)
from ..options import LootTierWeights

OPEN = {"game_mode": "open_world", "starting_planet": "expel"}
DEFAULT_WEIGHTS = {"Normal": 40, "Magic": 35, "Rare": 20, "Unique": 5}


def _fill(options, seed, players=1):
    from Fill import distribute_items_restrictive
    from test.general import setup_multiworld
    from worlds.AutoWorld import call_all
    from .. import SO2RWorld
    multiworld = setup_multiworld([SO2RWorld] * players, seed=seed, options=options)
    distribute_items_restrictive(multiworld)
    call_all(multiworld, "post_fill")
    return multiworld


def _by_key(multiworld):
    return {f"{loc.player}:{loc.address}": loc for loc in multiworld.get_locations() if loc.address is not None}


class TestFactorData(unittest.TestCase):
    def test_103_rows_with_the_game_enum_values(self):
        self.assertEqual(103, len(FACTOR_BY_ID))
        for factor_id, row in FACTOR_BY_ID.items():
            self.assertEqual(factor_id, int(row["key"].rsplit("_", 1)[1]))
            self.assertIn(row["rarity"], ("N", "R"))
            self.assertTrue(1 <= row["mask"] <= 7)
            self.assertGreater(row["weight"], 0)
        self.assertEqual(103 - len(NEVER_ROLLED), len(FACTORS))

    def test_every_slot_has_both_pools(self):
        for mask in (1, 2, 4):
            for rarity in ("N", "R"):
                self.assertTrue([f for f in FACTORS if f["rarity"] == rarity and f["mask"] & mask], (mask, rarity))


class TestUniques(unittest.TestCase):
    def test_count_and_distinct(self):
        self.assertTrue(12 <= len(UNIQUES) <= 20, len(UNIQUES))
        self.assertEqual(len(UNIQUES), len(UNIQUE_BY_ITEM))
        self.assertEqual(len(UNIQUES), len({row["item_id"] for row in UNIQUES}))

    def test_entries_are_real_gear_with_fitting_rare_factors(self):
        for row in UNIQUES:
            data = ITEM_TABLE[row["item"]]
            self.assertEqual(data.game_item_id, row["item_id"], row["item"])
            mask = slot_mask(row["item"])
            self.assertTrue(mask, row["item"])
            factor = FACTOR_BY_ID[row["factor"]]
            self.assertTrue(factor["mask"] & mask, row["item"])
            self.assertEqual("R", factor["rarity"], row["item"])
            self.assertNotIn(row["factor"], NEVER_ROLLED)
            self.assertTrue(row["why"])


class TestWeights(unittest.TestCase):
    def test_default_and_keys(self):
        self.assertEqual(DEFAULT_WEIGHTS, LootTierWeights.default)
        self.assertEqual(set(LOOT_TIER_NAMES), set(LootTierWeights.valid_keys))

    def test_scaling_formula(self):
        self.assertEqual([60.0, 35.0, 10.0, 2.5], tier_weights(DEFAULT_WEIGHTS, 0.0))
        self.assertEqual([20.0, 35.0, 40.0, 10.0], tier_weights(DEFAULT_WEIGHTS, 1.0))
        self.assertEqual([40.0, 35.0, 20.0, 5.0], tier_weights(DEFAULT_WEIGHTS, None))

    def test_pure_roll_fits_slot_and_rarity(self):
        rng = random.Random(1)
        for name in ("Godslayer", "Plate Helmet", "Silver Idol", "Progressive Weapon: Claude", "Cat o' Nine Tails"):
            mask = slot_mask(name)
            self.assertTrue(mask, name)
            for _ in range(300):
                rolled = roll_item(rng, name, DEFAULT_WEIGHTS, 0.5)
                if rolled is None:
                    continue
                tier, factor = rolled
                row = FACTOR_BY_ID[factor]
                self.assertTrue(row["mask"] & mask)
                if tier == "Magic":
                    self.assertEqual("N", row["rarity"])
                elif tier == "Rare":
                    self.assertEqual("R", row["rarity"])
                else:
                    self.assertEqual(UNIQUE_BY_ITEM[name]["factor"], factor)

    def test_unique_without_entry_falls_back_to_rare(self):
        rng = random.Random(2)
        weights = {"Normal": 0, "Magic": 0, "Rare": 0, "Unique": 1}
        for _ in range(50):
            tier, factor = roll_item(rng, "Silver Idol", weights, None)
            self.assertEqual("Rare", tier)
            self.assertEqual("R", FACTOR_BY_ID[factor]["rarity"])
        self.assertEqual("Unique", roll_item(rng, "Godslayer", weights, None)[0])

    def test_non_equipment_is_never_rolled(self):
        self.assertIsNone(roll_item(random.Random(3), "Blackberries ×3", DEFAULT_WEIGHTS, 0.5))

    def test_scaling_shifts_the_odds(self):
        def counts(progression):
            rng = random.Random(4)
            return Counter((roll_item(rng, "Silver Idol", DEFAULT_WEIGHTS, progression) or ("Normal",))[0]
                           for _ in range(4000))
        early, late = counts(0.0), counts(1.0)
        self.assertGreater(early["Normal"], late["Normal"] * 2)
        self.assertGreater(late["Rare"], early["Rare"] * 2)

    def test_all_zero_weights_roll_nothing(self):
        rng = random.Random(5)
        self.assertIsNone(roll_item(rng, "Godslayer", {name: 0 for name in LOOT_TIER_NAMES}, 0.5))


class TestUniqueRule(unittest.TestCase):
    UNLISTED = ("Silver Idol", "Plate Helmet", "Progressive Weapon: Claude")

    def test_unlisted_items_are_never_unique(self):
        rng = random.Random(10)
        for name in self.UNLISTED:
            self.assertNotIn(name, UNIQUE_BY_ITEM)
            for progression in (None, 0.0, 1.0):
                for _ in range(500):
                    rolled = roll_item(rng, name, DEFAULT_WEIGHTS, progression)
                    self.assertNotEqual("Unique", (rolled or ("Normal",))[0])

    def test_unique_share_moves_to_rare_after_scaling(self):
        from ..loot import item_weights
        self.assertEqual([60.0, 35.0, 12.5, 0.0], item_weights(DEFAULT_WEIGHTS, 0.0, False))
        self.assertEqual([20.0, 35.0, 50.0, 0.0], item_weights(DEFAULT_WEIGHTS, 1.0, False))
        self.assertEqual([60.0, 35.0, 10.0, 25.0], item_weights(DEFAULT_WEIGHTS, 0.0, True))

    def test_listed_items_roll_unique_at_about_a_third(self):
        self.assertEqual(10, UNIQUE_LISTED_MULTIPLIER)
        rng = random.Random(11)
        draws = 6000
        for name in ("Godslayer", UNIQUES[-1]["item"]):
            hits = sum(1 for _ in range(draws)
                       if (roll_item(rng, name, DEFAULT_WEIGHTS, None) or ("Normal",))[0] == "Unique")
            self.assertTrue(0.28 < hits / draws < 0.41, (name, hits / draws))  # expected 50/145 = 0.345

    def test_unique_weight_zero_gives_no_uniques(self):
        rng = random.Random(12)
        weights = dict(DEFAULT_WEIGHTS, Unique=0)
        for name in ("Godslayer", "Silver Idol"):
            for progression in (None, 0.5, 1.0):
                for _ in range(500):
                    rolled = roll_item(rng, name, weights, progression)
                    self.assertNotEqual("Unique", (rolled or ("Normal",))[0])


class TestOff(SO2RTestBase):
    options = dict(OPEN)

    def test_no_loot_key_and_no_spoiler(self):
        self.assertNotIn("loot", self.world.fill_slot_data())
        handle = io.StringIO()
        self.world.write_spoiler(handle)
        self.assertEqual("", handle.getvalue())


class TestOnWorld(unittest.TestCase):
    """Real generation: open world, generated gear pool, two SO2R players so keys must name the finder."""

    @classmethod
    def setUpClass(cls):
        cls.options = {**OPEN, "loot_tiers": True, "equipment_share": 80}
        cls.multiworld = _fill(cls.options, seed=77, players=2)
        cls.world = cls.multiworld.worlds[1]
        cls.loot = cls.world.fill_slot_data()["loot"]

    def test_contract_shape(self):
        self.assertEqual(1, self.loot["version"])
        self.assertEqual(set(self.loot["factors"]), set(self.loot["tiers"]))
        self.assertTrue(self.loot["factors"])
        self.assertEqual([[row["item_id"], row["factor"]] for row in UNIQUES], self.loot["uniques"])
        for value in self.loot["factors"].values():
            self.assertIsInstance(value, int)
        self.assertTrue(set(self.loot["tiers"].values()) <= {"Magic", "Rare", "Unique"})

    def test_keys_are_real_locations_with_this_players_equipment(self):
        by_key = _by_key(self.multiworld)
        finders = set()
        for key in self.loot["factors"]:
            location = by_key[key]
            finders.add(location.player)
            self.assertEqual(1, location.item.player)
            self.assertTrue(slot_mask(location.item.name), location.item.name)
        self.assertEqual({1, 2}, finders)  # player 2's locations hold player 1's gear too

    def test_factors_fit_the_slot_and_tier(self):
        by_key = _by_key(self.multiworld)
        for key, factor in self.loot["factors"].items():
            item = by_key[key].item.name
            row = FACTOR_BY_ID[factor]
            self.assertTrue(row["mask"] & slot_mask(item), (item, row["name"]))
            tier = self.loot["tiers"][key]
            if tier == "Magic":
                self.assertEqual("N", row["rarity"])
            elif tier == "Rare":
                self.assertEqual("R", row["rarity"])
            else:
                self.assertEqual(UNIQUE_BY_ITEM[item]["factor"], factor)

    def test_progressive_weapons_are_included(self):
        names = {loc.item.name for loc in candidates(self.multiworld, 1)}
        self.assertTrue(any(name.startswith("Progressive Weapon") for name in names))

    def test_spoiler_section(self):
        handle = io.StringIO()
        self.world.write_spoiler(handle)
        text = handle.getvalue()
        self.assertIn("Loot tiers", text)
        listed = [line for line in text.splitlines() if " - Magic \"" in line or " - Rare \"" in line
                  or " - Unique \"" in line]
        self.assertEqual(len(self.loot["factors"]), len(listed))

    def test_deterministic(self):
        again = _fill(self.options, seed=77, players=2).worlds[1].fill_slot_data()["loot"]
        self.assertEqual(self.loot, again)

    def test_slot_data_is_stable_across_calls(self):
        self.assertEqual(self.loot, self.world.fill_slot_data()["loot"])


class TestZeroWeights(unittest.TestCase):
    def test_all_zero_gives_no_entries(self):
        multiworld = _fill({**OPEN, "loot_tiers": True,
                            "loot_tier_weights": {name: 0 for name in LOOT_TIER_NAMES}}, seed=5)
        loot = multiworld.worlds[1].fill_slot_data()["loot"]
        self.assertEqual({}, loot["factors"])
        self.assertEqual({}, loot["tiers"])


class TestScalingOnWorld(unittest.TestCase):
    def test_late_checks_roll_better(self):
        early, late = [], []
        for seed in (11, 12, 13):
            multiworld = _fill({**OPEN, "loot_tiers": True, "equipment_share": 80,
                                "loot_tier_weights": {"Normal": 25, "Magic": 25, "Rare": 25, "Unique": 25}}, seed=seed)
            loot = multiworld.worlds[1].fill_slot_data()["loot"]
            fractions = progression_fractions(multiworld)
            for location in candidates(multiworld, 1):
                if location not in fractions:
                    continue
                key = f"{location.player}:{location.address}"
                (late if loot["tiers"].get(key) in ("Rare", "Unique") else early).append(fractions[location])
        self.assertTrue(early and late)
        self.assertGreater(sum(late) / len(late), sum(early) / len(early))


if __name__ == "__main__":
    unittest.main()
