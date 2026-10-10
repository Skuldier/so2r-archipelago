"""Unique Signature Effects (world 0.80.0): one signature weapon effect on every Unique piece of gear."""
import io
import json
import random
import unittest

from .test_bonus_effects import PHASE_1
from .test_loot import OPEN, _by_key, _fill
from ..gear_pool import GEAR_BY_ID
from ..loot import (SIGNATURE_BY_ID, SIGNATURE_POOL, STAT_BY_ID, UNIQUE_BY_ITEM, UNIQUES, format_bonus, roll_signature,
                    signature_character_mask, signature_pool_data, slot_mask, unique_equip_mask)
from ..resources import read_json

TABLE_IDS = [167, 153, 241, 242, 243, 244, 247, 268, 267, 274, 248, 164, 277, 275, 245, 161, 246, 271, 251, 250, 249]
SIG_OPTIONS = {**OPEN, "loot_tiers": True, "monster_drops": True, "equipment_share": 80, "cursed_loot": True,
               "loot_tier_weights": {"Normal": 10, "Magic": 10, "Rare": 10, "Unique": 100}}
ERNEST, OPERA = 1 << 9, 1 << 8


def _sig_pairs(pairs):
    return [pair for pair in pairs if pair[0] in SIGNATURE_BY_ID]


class TestSignatureData(unittest.TestCase):
    def test_rows(self):
        rows = read_json("signature_effects.json")["rows"]
        self.assertEqual(TABLE_IDS, [row["effect_id"] for row in rows])
        for row in rows:
            self.assertEqual(7, row["slot_mask"])
            self.assertLessEqual(row["value"][0], row["value"][1])
        self.assertEqual({"ernest", "opera"}, {row["character"] for row in rows if row["character"]})
        self.assertFalse(set(SIGNATURE_BY_ID) & PHASE_1)
        self.assertFalse(set(SIGNATURE_BY_ID) & set(STAT_BY_ID))

    def test_character_masks(self):
        self.assertEqual(512, signature_character_mask(SIGNATURE_BY_ID[250]))
        self.assertEqual(256, signature_character_mask(SIGNATURE_BY_ID[249]))
        self.assertEqual(0, signature_character_mask(SIGNATURE_BY_ID[167]))
        # Cat o' Nine Tails is Ernest's whip: the Ernest bit is 512
        self.assertEqual(ERNEST, unique_equip_mask("Cat o' Nine Tails"))

    def test_pool_shape(self):
        pool = signature_pool_data()
        self.assertEqual(len(SIGNATURE_POOL), len(pool))
        for entry, row in zip(pool, SIGNATURE_POOL):
            self.assertEqual(6, len(entry))
            self.assertEqual([row["effect_id"], 7, *row["value"], row["weight"], signature_character_mask(row)], entry)
        by_id = {entry[0]: entry for entry in pool}
        self.assertEqual([250, 7, 1, 1, 2, 512], by_id[250])
        self.assertEqual([249, 7, 1, 1, 2, 256], by_id[249])
        self.assertEqual([274, 7, 10, 25, 4, 0], by_id[274])


class TestRollSignature(unittest.TestCase):
    def test_character_rows_follow_the_equip_mask(self):
        rng = random.Random(5)
        for equip, forbidden in ((1, {250, 249}), (ERNEST, {249}), (OPERA, {250}), (ERNEST | OPERA, set()), (8191, set())):
            seen = set()
            for _ in range(600):
                effect, value = roll_signature(rng, 1, equip)
                seen.add(effect)
                low, high = SIGNATURE_BY_ID[effect]["value"]
                self.assertTrue(low <= value <= high)
            self.assertFalse(seen & forbidden, (equip, seen & forbidden))
            self.assertTrue(seen - {250, 249})
        self.assertIn(250, seen)
        self.assertIn(249, seen)

    def test_taken_ids_are_avoided(self):
        rng = random.Random(6)
        for _ in range(300):
            self.assertNotEqual(167, roll_signature(rng, 1, 8191, {167})[0])

    def test_format(self):
        self.assertEqual("Signature: Shockwave on Hit", format_bonus(167, 1))
        self.assertEqual("Signature: Instant Cast Chance 18%", format_bonus(274, 18))
        self.assertEqual("Signature: Combat Skill Surge 2", format_bonus(248, 2))
        for row in SIGNATURE_POOL:
            self.assertTrue(format_bonus(row["effect_id"], row["value"][0]).startswith("Signature: "))


class TestGenerated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.multiworld = _fill(SIG_OPTIONS, seed=81)
        cls.world = cls.multiworld.worlds[1]
        cls.slot = cls.world.fill_slot_data()

    def test_every_unique_has_exactly_one_signature(self):
        loot, by_key = self.slot["loot"], _by_key(self.multiworld)
        cursed = set(loot["cursed"])
        uniques = [key for key, tier in loot["tiers"].items() if tier == "Unique"]
        self.assertTrue(uniques)
        for key, tier in loot["tiers"].items():
            pairs = loot["bonuses"].get(key, [])
            sigs = _sig_pairs(pairs)
            if tier != "Unique":  # Rare, Magic and Cursed (listed as Rare) get none
                self.assertEqual([], sigs, key)
                continue
            self.assertNotIn(key, cursed)
            self.assertEqual(1, len(sigs), key)
            self.assertEqual(3, len(pairs), key)
            self.assertEqual(sigs[0], pairs[-1])
            effect, value = sigs[0]
            row = SIGNATURE_BY_ID[effect]
            self.assertTrue(row["value"][0] <= value <= row["value"][1])
            self.assertEqual(3, len({pair[0] for pair in pairs}))  # the two normal bonuses plus the signature are distinct ids
            self.assertTrue(row["slot_mask"] & slot_mask(by_key[key].item.name))
            equip = unique_equip_mask(by_key[key].item.name)
            self.assertTrue(equip)
            bit = signature_character_mask(row)
            self.assertTrue(not bit or bit & equip, (key, effect))
        self.assertTrue({tier for tier in loot["tiers"].values()} >= {"Rare", "Unique"})

    def test_character_ids_only_on_wearable_gear(self):
        for item_name, row in UNIQUE_BY_ITEM.items():
            equip = GEAR_BY_ID[row["item_id"]].equip
            rng = random.Random(row["item_id"])
            for _ in range(200):
                effect, _ = roll_signature(rng, slot_mask(item_name), equip)
                bit = signature_character_mask(SIGNATURE_BY_ID[effect])
                self.assertTrue(not bit or bit & equip, (item_name, effect))

    def test_drops_signature_pool(self):
        self.assertEqual(signature_pool_data(), self.slot["drops"]["signature_pool"])
        self.assertEqual(json.loads(json.dumps(self.slot["drops"]["signature_pool"])), self.slot["drops"]["signature_pool"])
        table_equip = {entry[0]: entry[2] for entry in self.slot["drops"]["table"]}
        cat = UNIQUE_BY_ITEM["Cat o' Nine Tails"]["item_id"]
        self.assertEqual(ERNEST, table_equip[cat])  # same encoding as the table's equip masks

    def test_spoiler(self):
        handle = io.StringIO()
        self.world.write_spoiler(handle)
        lines = [line for line in handle.getvalue().splitlines() if ", " in line and " - Unique \"" in line]
        self.assertTrue(lines)
        for line in lines:
            self.assertEqual(1, line.count("Signature: "), line)

    def test_inactive_options_match_the_old_output(self):
        off = {**SIG_OPTIONS, "loot_signature_effects": False}
        reference = _fill(off, seed=81).worlds[1].fill_slot_data()
        again = _fill(off, seed=81).worlds[1].fill_slot_data()
        self.assertNotIn("signature_pool", reference["drops"])
        for pairs in reference["loot"]["bonuses"].values():
            self.assertEqual([], _sig_pairs(pairs))
        self.assertEqual(json.dumps(reference["loot"], sort_keys=True), json.dumps(again["loot"], sort_keys=True))
        self.assertEqual(json.dumps(reference["drops"], sort_keys=True), json.dumps(again["drops"], sort_keys=True))
        # on = off plus one trailing pair on each Unique key, nothing else changes
        self.assertEqual(reference["loot"]["tiers"], self.slot["loot"]["tiers"])
        self.assertEqual(reference["loot"]["factors"], self.slot["loot"]["factors"])
        for key, pairs in self.slot["loot"]["bonuses"].items():
            if self.slot["loot"]["tiers"][key] == "Unique":
                self.assertEqual(reference["loot"]["bonuses"][key], pairs[:-1], key)
            else:
                self.assertEqual(reference["loot"]["bonuses"][key], pairs, key)
        drops_on = {k: v for k, v in self.slot["drops"].items() if k != "signature_pool"}
        self.assertEqual(json.dumps(reference["drops"], sort_keys=True), json.dumps(drops_on, sort_keys=True))

    def test_needs_bonus_effects(self):
        slot = _fill({**SIG_OPTIONS, "loot_bonus_effects": False}, seed=81).worlds[1].fill_slot_data()
        self.assertNotIn("signature_pool", slot["drops"])
        for pairs in slot["loot"].get("bonuses", {}).values():
            self.assertEqual([], _sig_pairs(pairs))

    def test_needs_loot_tiers(self):
        slot = _fill({**SIG_OPTIONS, "loot_tiers": False}, seed=81).worlds[1].fill_slot_data()
        self.assertNotIn("loot", slot)
        self.assertNotIn("signature_pool", slot["drops"])

    def test_uniques_exist(self):
        self.assertTrue(UNIQUES)


if __name__ == "__main__":
    unittest.main()
