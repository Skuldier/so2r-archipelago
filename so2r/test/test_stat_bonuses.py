"""Loot Stat Bonuses (world 0.79.0): +% ATK/INT/DEF/Evasion on Magic gear, and in the Rare/Unique bonus draw."""
import io
import json
import random
import unittest

from .test_bonus_effects import PHASE_1
from .test_loot import OPEN, _by_key, _fill
from ..loot import (BONUS_BAND_SCALE, BONUS_BY_ID, STAT_BY_ID, STAT_POOL, bonus_scale, format_bonus,
                    roll_bonuses, slot_mask, stat_pool_data)
from ..resources import read_json

ROLL_IDS = {27, 30, 32, 36}
STAT_OPTIONS = {**OPEN, "loot_tiers": True, "monster_drops": True, "equipment_share": 80, "cursed_loot": True,
                "loot_signature_effects": False}


def _stat_bounds(tier, row):
    low, high = row[tier.lower()]
    return (max(1, min(row["cap"], round(low * min(BONUS_BAND_SCALE)))),
            min(row["cap"], round(high * max(BONUS_BAND_SCALE))))


class TestStatData(unittest.TestCase):
    def test_rows(self):
        rows = read_json("stat_effects.json")["rows"]
        self.assertEqual([27, 30, 32, 36, 23, 25], [row["effect_id"] for row in rows])
        self.assertEqual(ROLL_IDS, {row["effect_id"] for row in STAT_POOL})
        for row in rows:
            self.assertEqual(7, row["slot_mask"])
            self.assertEqual([4, 8], row["magic"])
            self.assertEqual([8, 15], row["rare"])
            self.assertEqual([12, 20], row["unique"])
            self.assertEqual(50, row["cap"])
            self.assertEqual(row["effect_id"] in ROLL_IDS, row["roll"])
        self.assertFalse(set(STAT_BY_ID) & PHASE_1)

    def test_stat_pool_shape(self):
        pool = stat_pool_data()
        self.assertEqual(4, len(pool))
        for entry, row in zip(pool, STAT_POOL):
            self.assertEqual([row["effect_id"], 7, 4, 8, 8, 15, 12, 20, 50], entry)
            self.assertEqual(9, len(entry))


class TestRoll(unittest.TestCase):
    def test_magic_gets_exactly_one_stat(self):
        rng = random.Random(3)
        for mask in (1, 2, 4):
            for p in (None, 0.0, 0.5, 1.0):
                scale = bonus_scale(p)
                for _ in range(200):
                    bonuses = roll_bonuses(rng, mask, "Magic", p, True)
                    self.assertEqual(1, len(bonuses))
                    effect, value = bonuses[0]
                    self.assertIn(effect, ROLL_IDS)
                    self.assertTrue(max(1, round(4 * scale)) <= value <= min(50, round(8 * scale)), (effect, value, p))

    def test_rare_unique_pairs_and_ranges(self):
        rng = random.Random(4)
        seen = set()
        for tier, count in (("Rare", 1), ("Unique", 2)):
            for mask in (1, 2, 4):
                for p in (None, 0.0, 0.5, 1.0):
                    for _ in range(300):
                        bonuses = roll_bonuses(rng, mask, tier, p, True)
                        self.assertEqual(count, len(bonuses))
                        self.assertEqual(count, len({effect for effect, _ in bonuses}))
                        for effect, value in bonuses:
                            seen.add(effect)
                            self.assertTrue(effect in PHASE_1 or effect in ROLL_IDS, effect)
                            self.assertNotIn(effect, (23, 25))
                            if effect in ROLL_IDS:
                                low, high = _stat_bounds(tier, STAT_BY_ID[effect])
                                self.assertTrue(low <= value <= high, (effect, value, tier))
                            else:
                                self.assertTrue(1 <= value <= BONUS_BY_ID[effect]["cap"])
        self.assertTrue(ROLL_IDS <= seen)
        self.assertTrue(PHASE_1 & seen)

    def test_inactive_is_the_phase_1_roll(self):
        for tier in ("Magic", "Rare", "Unique"):
            for mask in (1, 2, 4):
                for p in (None, 0.2, 0.9):
                    a, b = random.Random(9), random.Random(9)
                    self.assertEqual(roll_bonuses(a, mask, tier, p), roll_bonuses(b, mask, tier, p, False))
                    self.assertEqual(a.random(), b.random())
        self.assertEqual([], roll_bonuses(random.Random(1), 1, "Magic", 0.5))

    def test_format(self):
        self.assertEqual("ATK +12%", format_bonus(27, 12))
        self.assertEqual("Evasion +5%", format_bonus(36, 5))


class TestGenerated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.multiworld = _fill(STAT_OPTIONS, seed=77)
        cls.world = cls.multiworld.worlds[1]
        cls.slot = cls.world.fill_slot_data()

    def test_every_tier_key(self):
        loot, by_key = self.slot["loot"], _by_key(self.multiworld)
        cursed = set(loot["cursed"])
        tiers = {}
        for key, tier in loot["tiers"].items():
            pairs = loot["bonuses"].get(key, [])
            stats = [pair for pair in pairs if pair[0] in STAT_BY_ID]
            if key in cursed:
                self.assertEqual([], stats, key)
                continue
            tiers[tier] = tiers.get(tier, 0) + 1
            if tier == "Magic":
                self.assertEqual(1, len(pairs), key)
                self.assertEqual(1, len(stats), key)
            else:
                self.assertEqual(1 if tier == "Rare" else 2, len(pairs), key)
            for effect, _ in pairs:
                self.assertTrue(effect in PHASE_1 or effect in ROLL_IDS)
            self.assertTrue(slot_mask(by_key[key].item.name))
        self.assertTrue(tiers.get("Magic") and tiers.get("Rare"))
        self.assertTrue(cursed)

    def test_drops_stat_pool(self):
        self.assertEqual(stat_pool_data(), self.slot["drops"]["stat_pool"])
        self.assertIn("bonus_pool", self.slot["drops"])
        self.assertEqual({"Magic": 0, "Rare": 1, "Unique": 2}, self.slot["drops"]["bonus_counts"])

    def test_spoiler(self):
        handle = io.StringIO()
        self.world.write_spoiler(handle)
        text = handle.getvalue()
        self.assertRegex(text, r"(ATK|INT|DEF|Evasion) \+\d+%")
        for line in text.splitlines():
            if " - Magic, " in line:
                self.assertEqual(1, line.count(" + "), line)

    def test_inactive_options_match_the_old_output(self):
        reference = _fill({**STAT_OPTIONS, "loot_stat_bonuses": False}, seed=77).worlds[1].fill_slot_data()
        self.assertNotIn("stat_pool", reference["drops"])
        # stat bonuses off: no stat ids anywhere and Magic gear has no bonus (the Phase 1 behaviour)
        for key, tier in reference["loot"]["tiers"].items():
            pairs = reference["loot"]["bonuses"].get(key, [])
            self.assertFalse([pair for pair in pairs if pair[0] in STAT_BY_ID])
            if tier == "Magic" and key not in reference["loot"]["cursed"]:
                self.assertEqual([], pairs)
        # tiers and factors are the same either way
        self.assertEqual(reference["loot"]["tiers"], self.slot["loot"]["tiers"])
        self.assertEqual(reference["loot"]["factors"], self.slot["loot"]["factors"])
        # the off output is deterministic and serialises identically
        again = _fill({**STAT_OPTIONS, "loot_stat_bonuses": False}, seed=77).worlds[1].fill_slot_data()
        self.assertEqual(json.dumps(reference["loot"], sort_keys=True), json.dumps(again["loot"], sort_keys=True))
        self.assertEqual(json.dumps(reference["drops"], sort_keys=True), json.dumps(again["drops"], sort_keys=True))

    def test_needs_bonus_effects(self):
        slot = _fill({**STAT_OPTIONS, "loot_bonus_effects": False}, seed=77).worlds[1].fill_slot_data()
        self.assertNotIn("stat_pool", slot["drops"])
        for pairs in slot["loot"]["bonuses"].values():
            self.assertFalse([pair for pair in pairs if pair[0] in STAT_BY_ID])


if __name__ == "__main__":
    unittest.main()
