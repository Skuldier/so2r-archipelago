"""Bonus equipment effects on loot tiers (docs/crafting/EQUIPMENT_EFFECTS.md section 4.4): pool data, roll, slot data, spoiler."""
import io
import random
import re
import unittest

from .test_loot import OPEN, _by_key, _fill
from ..loot import (BONUS_BAND_SCALE, BONUS_BY_ID, BONUS_COUNTS, BONUS_POOL, bonus_pool_data, bonus_scale, roll_bonuses,
                    slot_mask)

PHASE_1 = {68, 8, 16, 15, 17, 270, 89, 90, 91, 92, 94, 100}
NEVER_ROLL = ({66, 99, 273, 269, 67, 43, 102, 103, 255, 256, 257, 258, 21, 63, 145, 146, 147, 148, 161, 162, 266, 3, 4, 5,
               96, 97, 98, 191, 192, 248, 56, 46, 49, 54, 59, 60, 28, 29, 33, 86, 87, 88, 27, 38}
              | set(range(241, 254)) | {267, 268} | set(range(271, 278)) | set(range(168, 175)) | {153, 190, 195})


def _bounds(row, tier):
    low, high = row["unique" if tier == "Unique" else "rare"]
    if row["effect_id"] == 68:
        return low, min(row["cap"], high)
    return max(1, min(row["cap"], round(low * min(BONUS_BAND_SCALE)))), min(row["cap"], round(high * max(BONUS_BAND_SCALE)))


class TestPoolData(unittest.TestCase):
    def test_ids_are_exactly_phase_1_and_none_never_roll(self):
        ids = [row["effect_id"] for row in BONUS_POOL]
        self.assertEqual(PHASE_1, set(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(set(ids) & NEVER_ROLL)

    def test_rows_are_sane(self):
        for row in BONUS_POOL:
            self.assertTrue(1 <= row["slot_mask"] <= 7)
            for key in ("rare", "unique"):
                low, high = row[key]
                self.assertTrue(1 <= low <= high <= row["cap"], row)
            self.assertLessEqual(row["rare"][0], row["unique"][0])
        self.assertEqual(2, BONUS_BY_ID[68]["cap"])

    def test_drops_pool_shape(self):
        pool = bonus_pool_data()
        self.assertEqual(len(BONUS_POOL), len(pool))
        for entry, row in zip(pool, BONUS_POOL):
            self.assertEqual([row["effect_id"], row["slot_mask"], *row["rare"], *row["unique"], row["cap"]], entry)
            self.assertEqual(7, len(entry))
            self.assertTrue(all(isinstance(value, int) for value in entry))


class TestRoll(unittest.TestCase):
    def test_counts_distinct_and_fit(self):
        rng = random.Random(5)
        for tier, count in (("Magic", 0), ("Rare", 1), ("Unique", 2)):
            for mask in (1, 2, 4):
                for p in (None, 0.0, 0.5, 1.0):
                    for _ in range(100):
                        bonuses = roll_bonuses(rng, mask, tier, p)
                        self.assertEqual(count, len(bonuses))
                        self.assertEqual(len(bonuses), len({effect for effect, _ in bonuses}))
                        for effect, _ in bonuses:
                            self.assertTrue(BONUS_BY_ID[effect]["slot_mask"] & mask)

    def test_values_in_range_times_scale_and_clamped(self):
        rng = random.Random(6)
        for tier in ("Rare", "Unique"):
            for p in (0.0, 0.5, 1.0):
                for _ in range(300):
                    for effect, value in roll_bonuses(rng, 2, tier, p):
                        low, high = _bounds(BONUS_BY_ID[effect], tier)
                        self.assertTrue(low <= value <= high, (effect, value, tier, p))

    def test_band_scale_edges(self):
        self.assertEqual([0.7, 0.7, 1.0, 1.0, 1.25, 1.25, 1.0],
                         [bonus_scale(p) for p in (0.0, 0.33, 0.34, 0.66, 0.67, 1.0, None)])

    def test_late_unscaled_and_clamped(self):
        rng = random.Random(7)
        for _ in range(300):
            for effect, value in roll_bonuses(rng, 1, "Unique", 1.0):
                self.assertLessEqual(value, BONUS_BY_ID[effect]["cap"])
                if effect == 68:
                    self.assertEqual(1, value)

    def test_no_eligible_effect_means_no_bonus(self):
        self.assertEqual([], roll_bonuses(random.Random(1), 0, "Unique", 0.5))

    def test_deterministic(self):
        first = [roll_bonuses(random.Random(9), 4, "Unique", 0.8) for _ in range(3)]
        self.assertEqual(first[0], first[1])


class TestWorld(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.options = {**OPEN, "loot_tiers": True, "monster_drops": True, "equipment_share": 80,
                       "loot_stat_bonuses": False, "loot_signature_effects": False}
        cls.multiworld = _fill(cls.options, seed=77, players=2)
        cls.world = cls.multiworld.worlds[1]
        cls.slot = cls.world.fill_slot_data()

    def test_bonuses_match_tiers(self):
        loot, by_key = self.slot["loot"], _by_key(self.multiworld)
        bonuses = loot["bonuses"]
        self.assertEqual(1, loot["version"])
        self.assertTrue(bonuses)
        expected = {key for key, tier in loot["tiers"].items() if tier != "Magic"}
        self.assertEqual(expected, set(bonuses))
        for key, pairs in bonuses.items():
            tier = loot["tiers"][key]
            self.assertEqual(BONUS_COUNTS[tier], len(pairs))
            self.assertEqual(len(pairs), len({effect for effect, _ in pairs}))
            mask = slot_mask(by_key[key].item.name)
            for effect, value in pairs:
                row = BONUS_BY_ID[effect]
                self.assertTrue(row["slot_mask"] & mask)
                low, high = _bounds(row, tier)
                self.assertTrue(low <= value <= high, (effect, value, tier))

    def test_both_tiers_present(self):
        tiers = {self.slot["loot"]["tiers"][key] for key in self.slot["loot"]["bonuses"]}
        self.assertEqual({"Rare", "Unique"}, tiers)

    def test_drops_block(self):
        drops = self.slot["drops"]
        self.assertEqual(bonus_pool_data(), drops["bonus_pool"])
        self.assertEqual([0.7, 1.0, 1.25], drops["bonus_band_scale"])
        self.assertEqual({"Magic": 0, "Rare": 1, "Unique": 2}, drops["bonus_counts"])
        self.assertEqual(1, drops["version"])

    def test_spoiler_lists_bonuses(self):
        handle = io.StringIO()
        self.world.write_spoiler(handle)
        lines = [line for line in handle.getvalue().splitlines() if " - Rare \"" in line or " - Unique \"" in line]
        self.assertTrue(lines)
        for line in lines:
            self.assertEqual(1 if " - Rare \"" in line else 2, line.count(" + "), line)
        self.assertTrue(any(re.search(r"\+\d+%|\d+ Extra Attacks|Regeneration \+\d", line) for line in lines))

    def test_deterministic(self):
        again = _fill(self.options, seed=77, players=2).worlds[1].fill_slot_data()
        self.assertEqual(self.slot["loot"], again["loot"])
        self.assertEqual(self.slot["drops"], again["drops"])

    def test_tier_rolls_unchanged_by_the_option(self):
        off = _fill({**self.options, "loot_bonus_effects": False}, seed=77, players=2).worlds[1].fill_slot_data()
        self.assertEqual(self.slot["loot"]["tiers"], off["loot"]["tiers"])
        self.assertEqual(self.slot["loot"]["factors"], off["loot"]["factors"])


class TestOptionOff(unittest.TestCase):
    def test_no_bonuses_no_pool_and_plain_spoiler(self):
        multiworld = _fill({**OPEN, "loot_tiers": True, "monster_drops": True, "loot_bonus_effects": False,
                            "equipment_share": 80}, seed=77)
        world = multiworld.worlds[1]
        slot = world.fill_slot_data()
        self.assertNotIn("bonuses", slot["loot"])
        for key in ("bonus_pool", "bonus_band_scale", "bonus_counts"):
            self.assertNotIn(key, slot["drops"])
        handle = io.StringIO()
        world.write_spoiler(handle)
        self.assertNotIn(" + ", handle.getvalue())

    def test_drops_off_means_no_drops_block(self):
        multiworld = _fill({**OPEN, "loot_tiers": True, "equipment_share": 80,
                            "feat_duel_rewards": False, "feat_chain_rewards": False}, seed=77)
        slot = multiworld.worlds[1].fill_slot_data()
        self.assertNotIn("drops", slot)
        self.assertIn("bonuses", slot["loot"])


if __name__ == "__main__":
    unittest.main()
