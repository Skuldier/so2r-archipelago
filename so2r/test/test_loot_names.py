"""Generated loot names (world 0.81.0, docs/LOOT_NAMES.md): the per-tier rules, the length guard and table coverage."""
import json
import unittest

from ..loot import (BONUS_POOL, CURSED_POOL, FACTOR_BY_ID, SIGNATURE_POOL, STAT_BY_ID, STAT_POOL, loot_name)
from ..resources import read_json

NAMES = read_json("loot_names.json")
EFFECT_PREFIXES = {pair[0].lower() for pair in NAMES["effects"].values()}


class TestLootNameTables(unittest.TestCase):
    def test_every_factor_has_a_short_distinct_prefix(self):
        self.assertEqual({str(i) for i in FACTOR_BY_ID}, set(NAMES["factors"]))
        prefixes = [p.lower() for p in NAMES["factors"].values()]
        self.assertEqual(len(prefixes), len(set(prefixes)))
        for prefix in prefixes:
            self.assertLessEqual(len(prefix), 12)
            self.assertNotIn(" ", prefix)
        self.assertFalse(set(prefixes) & EFFECT_PREFIXES)

    def test_47_effects_distinct(self):
        self.assertEqual(47, len(NAMES["effects"]))
        self.assertEqual(47, len({p for p, _ in NAMES["effects"].values()}))
        self.assertEqual(47, len({s for _, s in NAMES["effects"].values()}))

    def test_every_pool_id_has_a_name(self):
        for pool in (BONUS_POOL, STAT_POOL, SIGNATURE_POOL, CURSED_POOL):
            for row in pool:
                self.assertIn(str(row["effect_id"]), NAMES["effects"], row)
        for stat_id in STAT_BY_ID:
            self.assertIn(str(stat_id), NAMES["effects"])

    def test_generated_file_matches_the_script(self):
        from pathlib import Path
        script = Path(__file__).resolve().parents[3] / "tools/apworld/build_loot_names.py"
        if not script.exists():  # a packaged apworld has no tools directory
            self.skipTest("no tools directory")
        import importlib.util
        spec = importlib.util.spec_from_file_location("build_loot_names", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(json.loads(module.render_json()), NAMES)

    def test_every_factor_and_pool_id_names_without_error(self):
        for factor_id in FACTOR_BY_ID:
            for tier in ("Magic", "Rare", "Unique", "Cursed"):
                self.assertTrue(loot_name("Ring", tier, factor_id, []))
        for pool in (BONUS_POOL, STAT_POOL, SIGNATURE_POOL, CURSED_POOL):
            for row in pool:
                for tier in ("Magic", "Rare", "Unique", "Cursed"):
                    self.assertTrue(loot_name("Ring", tier, 1, [[row["effect_id"], 1], [row["effect_id"], 1]]))


class TestNameRules(unittest.TestCase):
    def test_normal_is_the_plain_item(self):
        self.assertEqual("Longsword", loot_name("Longsword", "Normal", 1, []))

    def test_magic_prefix_from_stat_else_factor(self):
        self.assertEqual("Mighty Weird Shoes", loot_name("Weird Shoes", "Magic", 1, [[27, 5]]))
        self.assertEqual("Keen Weird Shoes", loot_name("Weird Shoes", "Magic", 1, []))

    def test_rare_prefix_from_factor_suffix_from_bonus(self):
        self.assertEqual("Savage Leather Armor of Might", loot_name("Leather Armor", "Rare", 21, [[27, 6]]))
        self.assertEqual("Savage Leather Armor", loot_name("Leather Armor", "Rare", 21, []))

    def test_unique_prefix_first_plain_bonus_suffix_signature(self):
        self.assertEqual("Tidal Battle Suit of Starlight",
                         loot_name("Battle Suit", "Unique", 1, [[90, 15], [94, 10], [153, 1]]))
        # a signature listed first is skipped for the prefix
        self.assertEqual("Tidal Ring of Starlight", loot_name("Ring", "Unique", 1, [[153, 1], [90, 15], [94, 10]]))

    def test_unique_fallbacks(self):
        # no signature: the second bonus gives the suffix
        self.assertEqual("Tidal Ring of Warding", loot_name("Ring", "Unique", 1, [[90, 15], [94, 10]]))
        # signature only: the factor gives the prefix
        self.assertEqual("Keen Ring of Starlight", loot_name("Ring", "Unique", 1, [[153, 1]]))
        # one bonus and nothing else
        self.assertEqual("Tidal Ring", loot_name("Ring", "Unique", 1, [[90, 15]]))
        self.assertEqual("Keen Ring", loot_name("Ring", "Unique", 1, []))

    def test_cursed_curse_prefix_upside_suffix(self):
        self.assertEqual("Gambler's Stun Gun of Warding", loot_name("Stun Gun", "Cursed", 1, [[102, 1], [94, 28]]))
        self.assertEqual("Accursed Mind Ring of Rage", loot_name("Mind Ring", "Cursed", 1, [[103, 16], [67, 1]]))
        self.assertEqual("Bloodsworn Open Helmet", loot_name("Open Helmet", "Cursed", 1, [[172, 12]]))

    def test_length_guard_drops_prefix_then_suffix(self):
        # "Savage Reflecting Plate of the Roaring Burst" is 44 > 36; without the prefix it is 37 > 36; both go
        self.assertEqual("Reflecting Plate", loot_name("Reflecting Plate", "Rare", 21, [[246, 1]]))
        # "Quickened Reflecting Plate of the Heavens" is 41 > 36; without the prefix it is 31
        self.assertEqual("Reflecting Plate of the Heavens",
                         loot_name("Reflecting Plate", "Unique", 1, [[270, 22], [89, 20], [274, 15]]))
        self.assertEqual("Savage Ring of Might", loot_name("Ring", "Rare", 21, [[27, 1]]))
        long_item = "Reflecting Plate of Doom and Gloom"
        self.assertEqual(long_item, loot_name(long_item, "Rare", 21, [[27, 1]]))
        name = loot_name("Long Item Name Number One", "Cursed", 1, [[103, 1], [174, 1]])
        self.assertEqual("Long Item Name Number One", name)
        for tier, ids in (("Rare", [[246, 1]]), ("Unique", [[246, 1], [251, 1]]), ("Cursed", [[172, 1]])):
            self.assertLessEqual(len(loot_name("Ring", tier, 1, ids)), 36)


class TestSpoilerNames(unittest.TestCase):
    def test_spoiler_shows_a_generated_name_per_tiered_item(self):
        import io
        import re
        from .test_signature_effects import SIG_OPTIONS
        from .test_loot import _fill
        handle = io.StringIO()
        _fill(SIG_OPTIONS, seed=81).worlds[1].write_spoiler(handle)
        lines = [line for line in handle.getvalue().splitlines() if re.search(r" - (Magic|Rare|Unique|Cursed) \"", line)]
        self.assertTrue(lines)
        for line in lines:
            item, name = re.search(r"\): (.+) - (?:Magic|Rare|Unique|Cursed) \"(.+?)\", ", line).groups()
            self.assertIn(item, name, line)


if __name__ == "__main__":
    unittest.main()
