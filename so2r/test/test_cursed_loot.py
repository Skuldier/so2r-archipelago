"""Cursed loot tier (world 0.78.0, docs/crafting/EQUIPMENT_EFFECTS.md section 4): pool data, roll, slot data, spoiler."""
import io
import random
import unittest

from .test_loot import OPEN, _fill
from ..loot import (CURSED_BY_ID, CURSED_POOL, LOOT_TIER_NAMES, cursed_pool_data, format_bonus, roll_cursed_bonuses,
                    roll_item, tier_weights)
from ..options import LootTierWeights

from ..items import ITEM_TABLE
from ..loot import slot_mask
_WEAPON = next(name for name in ITEM_TABLE if slot_mask(name) == 1)
NEVER_ROLL = {169, 170, 43, 255, 256, 257, 258}
SELF_ID = 172
CURSES = {103, 102}
UPSIDES = {94, 68, 89, 67, 173, 174, 195, 190}
CURSED_OPTIONS = {**OPEN, "loot_tiers": True, "cursed_loot": True, "cursed_loot_weight": 40, "monster_drops": True,
                  "equipment_share": 80}


class TestCursedData(unittest.TestCase):
    def test_table_and_never_roll(self):
        ids = [row["effect_id"] for row in CURSED_POOL]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({SELF_ID} | CURSES | UPSIDES, set(ids))
        self.assertFalse(set(ids) & NEVER_ROLL)
        for row in CURSED_POOL:
            self.assertIn(row["role"], ("self", "curse", "upside"))
            self.assertEqual(7, row["slot_mask"])
            self.assertTrue(1 <= row["value"][0] <= row["value"][1])
            self.assertGreater(row["weight"], 0)

    def test_weights_option_keys_unchanged(self):
        self.assertEqual(frozenset(LOOT_TIER_NAMES), LootTierWeights.valid_keys)
        self.assertNotIn("Cursed", LOOT_TIER_NAMES)

    def test_drops_pool_shape(self):
        block = cursed_pool_data()
        self.assertEqual([[172, 7, 12, 12, 1, 1], [103, 7, 10, 20, 2, 0], [102, 7, 1, 1, 2, 0]], block["curses"])
        self.assertEqual({94, 68, 89, 67, 173, 174, 195, 190}, {row[0] for row in block["upsides"]})
        self.assertTrue(all(len(row) == 5 for row in block["upsides"]))


class TestCursedRoll(unittest.TestCase):
    def test_weights_have_fifth_entry_scaled_like_rare(self):
        base = {"Normal": 40, "Magic": 35, "Rare": 20, "Unique": 5}
        self.assertEqual(4, len(tier_weights(base, 0.5)))
        weights = tier_weights(base, 1.0, 8)
        self.assertEqual(5, len(weights))
        self.assertEqual(16.0, weights[4])
        self.assertEqual(4.0, tier_weights(base, 0.0, 8)[4])
        self.assertEqual(8.0, tier_weights(base, None, 8)[4])

    def test_pairs(self):
        rng = random.Random(3)
        seen_self = seen_pair = False
        for mask in (1, 2, 4):
            for _ in range(300):
                pairs = roll_cursed_bonuses(rng, mask)
                ids = [effect for effect, _ in pairs]
                if ids == [SELF_ID]:
                    seen_self = True
                    self.assertEqual([[172, 12]], pairs)
                else:
                    seen_pair = True
                    self.assertEqual(2, len(ids))
                    self.assertIn(ids[0], CURSES)
                    self.assertIn(ids[1], UPSIDES)
                for effect, value in pairs:
                    low, high = CURSED_BY_ID[effect]["value"]
                    self.assertTrue(low <= value <= high)
                self.assertFalse(set(ids) & NEVER_ROLL)
        self.assertTrue(seen_self and seen_pair)

    def test_roll_item_can_return_cursed(self):
        rng = random.Random(1)
        base = {"Normal": 0, "Magic": 0, "Rare": 0, "Unique": 0}
        tiers = {roll_item(rng, _WEAPON, base, None, 10)[0] for _ in range(5)}
        self.assertEqual({"Cursed"}, tiers)

    def test_format(self):
        self.assertEqual("Bloody Armor (drains 12 HP)", format_bonus(172, 12, True))
        self.assertEqual("Random Damage Taken", format_bonus(102, 1, True))
        self.assertEqual("Double Damage Taken +15%", format_bonus(103, 15, True))
        self.assertEqual("Damage Taken Down +25%", format_bonus(94, 25, True))
        self.assertEqual("Berserk", format_bonus(67, 1, True))
        self.assertEqual("Damage Taken Cut +7%", format_bonus(94, 7))


class TestCursedSeed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = _fill(CURSED_OPTIONS, seed=77, players=2).worlds[1]
        cls.slot = cls.world.fill_slot_data()

    def test_loot_block(self):
        loot = self.slot["loot"]
        cursed = loot["cursed"]
        self.assertTrue(cursed)
        self.assertEqual(sorted(cursed), cursed)
        self.assertEqual(1, loot["version"])
        self.assertEqual(set(cursed), {key for key, row in self.world._loot_rolls().items() if row["tier"] == "Cursed"})
        self.assertNotIn("Cursed", set(loot["tiers"].values()))
        for key in cursed:
            self.assertEqual("Rare", loot["tiers"][key])
            self.assertIn(key, loot["factors"])
            ids = [effect for effect, _ in loot["bonuses"][key]]
            self.assertFalse(set(ids) & NEVER_ROLL)
            if ids == [SELF_ID]:
                continue
            self.assertEqual(2, len(ids))
            self.assertIn(ids[0], CURSES)
            self.assertIn(ids[1], UPSIDES)
        # Phase 1 bonuses stay on non-cursed Rare/Unique and never on Cursed
        for key, pairs in loot["bonuses"].items():
            if key not in cursed:
                self.assertFalse({effect for effect, _ in pairs} & (CURSES | {SELF_ID}), key)

    def test_drops_block(self):
        block = self.slot["drops"]["cursed"]
        self.assertEqual(40, block["weight"])
        self.assertEqual({"weight", "curses", "upsides"}, set(block))
        self.assertEqual(cursed_pool_data()["curses"], block["curses"])
        self.assertEqual(cursed_pool_data()["upsides"], block["upsides"])

    def test_spoiler(self):
        handle = io.StringIO()
        self.world.write_spoiler(handle)
        lines = [line for line in handle.getvalue().splitlines() if " - Cursed \"" in line]
        self.assertEqual(len(self.slot["loot"]["cursed"]), len(lines))
        self.assertTrue(any("Double Damage Taken +" in line or "Random Damage Taken" in line
                            or "Bloody Armor (drains 12 HP)" in line for line in lines))

    def test_cursed_without_phase_1_bonuses(self):
        slot = _fill({**CURSED_OPTIONS, "loot_bonus_effects": False}, seed=77, players=2).worlds[1].fill_slot_data()
        loot = slot["loot"]
        self.assertTrue(loot["cursed"])
        self.assertEqual(set(loot["cursed"]), set(loot["bonuses"]))
        self.assertNotIn("bonus_pool", slot["drops"])
        self.assertIn("cursed", slot["drops"])


class TestCursedOff(unittest.TestCase):
    def test_off_has_no_cursed_keys_and_is_deterministic(self):
        options = {**CURSED_OPTIONS, "cursed_loot": False}
        slot = _fill(options, seed=77, players=2).worlds[1].fill_slot_data()
        self.assertNotIn("cursed", slot["loot"])
        self.assertNotIn("cursed", slot["drops"])
        self.assertEqual({"version", "factors", "tiers", "uniques", "bonuses"}, set(slot["loot"]))
        plain = {key: value for key, value in options.items() if key not in ("cursed_loot", "cursed_loot_weight")}
        again = _fill(plain, seed=77, players=2).worlds[1].fill_slot_data()
        self.assertEqual(slot["loot"], again["loot"])
        self.assertEqual(slot["drops"], again["drops"])
        self.assertEqual({"Normal", "Magic", "Rare", "Unique"} | set(), set(LOOT_TIER_NAMES))
        spoiler = io.StringIO()
        _fill(options, seed=77, players=2).worlds[1].write_spoiler(spoiler)
        self.assertNotIn("Cursed", spoiler.getvalue())

    def test_both_off_has_no_bonuses_key(self):
        slot = _fill({**OPEN, "loot_tiers": True, "loot_bonus_effects": False, "equipment_share": 80},
                     seed=77).worlds[1].fill_slot_data()
        self.assertNotIn("bonuses", slot["loot"])
        self.assertNotIn("cursed", slot["loot"])

    def test_cursed_needs_loot_tiers(self):
        slot = _fill({**OPEN, "cursed_loot": True, "monster_drops": True, "equipment_share": 80}, seed=77).worlds[1].fill_slot_data()
        self.assertNotIn("loot", slot)
        self.assertNotIn("cursed", slot["drops"])


if __name__ == "__main__":
    unittest.main()
