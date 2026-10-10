"""Progressive Weapons off and Monster Drops (0.75.0): the pool keeps its size, the drops block follows its contract."""
import json
import unittest

from . import SO2RTestBase
from ..drops import BAND_LEVELS, BANDS, band_levels_for, build_table, slot_data
from ..gear_pool import GEAR_BY_ID
from ..items import ITEM_TABLE
from ..loot import FACTORS, NEVER_ROLLED

OPEN = {"game_mode": "open_world", "starting_planet": "expel"}


def progressive_count(world) -> int:
    return sum(1 for item in world.multiworld.itempool if ITEM_TABLE[item.name].category == "PROGRESSIVE_WEAPON")


class TestProgressiveWeaponsOff(SO2RTestBase):
    options = {**OPEN, "progressive_weapons": False}

    def test_no_progressive_weapons_same_count(self):
        self.assertEqual(0, progressive_count(self.world))
        self.assertEqual(len(self.multiworld.get_locations(self.player)), len(self.multiworld.itempool))

    def test_slot_data_keeps_its_shape_with_empty_ladders(self):
        block = self.world.fill_slot_data()["gear"]
        self.assertEqual({"version": 1, "progressive_weapons": {}}, block)
        self.assertEqual({}, self.world.gear_ladders)
        self.assertIn("feats", self.world.fill_slot_data())  # feats default on: table-only drops block
        self.assertFalse(self.world.fill_slot_data()["drops"]["enabled"])


class TestProgressiveWeaponsOn(SO2RTestBase):
    options = dict(OPEN)

    def test_baseline_has_ladders(self):
        self.assertGreater(progressive_count(self.world), 0)


class TestMoreFiller(unittest.TestCase):
    def test_off_swaps_rungs_for_filler(self):
        import random
        from ..gear_pool import build
        from ..items import progressive_weapon_name

        def run(progressive):
            return build(random.Random(5), [1, 2, 3, 4, 5], 188, 50, progressive_weapon_name, lambda gear: gear.name,
                         ["Small"], ["Large"], [1], [1], ["Filler"], lambda amount: f"{amount} Fol",
                         progressive=progressive)

        on, off = run(True), run(False)
        self.assertEqual(188, len(on.names))
        self.assertEqual(188, len(off.names))
        self.assertEqual({}, off.ladders)
        self.assertFalse([name for name in off.names if name.startswith("Progressive")])
        rungs = sum(len(r) for r in on.ladders.values())
        self.assertGreater(rungs, 0)
        gear_names = {gear.name for gear in GEAR_BY_ID.values()}
        count = lambda pool: sum(1 for name in pool.names if name in gear_names)
        self.assertEqual(count(on), count(off))
        # the freed slots are all filler (packs, Fol): the non-gear, non-ladder entries grew by the rung count
        self.assertEqual(rungs, (188 - count(off)) - (188 - count(on) - rungs))


class TestDropTable(unittest.TestCase):
    def test_no_gag_and_valid_rows(self):
        table = build_table()
        self.assertTrue(table)
        seen = set()
        for item_id, slot, mask, band in table:
            gear = GEAR_BY_ID[item_id]
            self.assertFalse(gear.gag, gear.name)
            self.assertNotIn(item_id, seen)
            seen.add(item_id)
            self.assertIn(slot, (1, 2, 4))
            self.assertEqual(gear.equip, mask)
            self.assertIn(band, range(BANDS))

    def test_every_group_spans_all_bands(self):
        table = build_table()
        groups = {}
        for item_id, slot, _mask, band in table:
            gear = GEAR_BY_ID[item_id]
            key = "weapon" if slot == 1 else "accessory" if slot == 4 else gear.category
            groups.setdefault(key, set()).add(band)
        self.assertEqual({"weapon", "accessory", "ARMOR", "SHIELD", "HELMET", "GREEVE"}, set(groups))
        for key, bands in groups.items():
            self.assertEqual(set(range(BANDS)), bands, key)

    def test_accessory_rarity_ranges(self):
        ranges = {"N": (0, 2), "R": (3, 5), "SR": (6, 7), "SSR": (8, 9)}
        for item_id, slot, _mask, band in build_table():
            if slot == 4:
                low, high = ranges[GEAR_BY_ID[item_id].rarity]
                self.assertTrue(low <= band <= high, GEAR_BY_ID[item_id].name)

    def test_weapon_bands_follow_power(self):
        weapons = sorted((GEAR_BY_ID[i].power, band) for i, slot, _m, band in build_table() if slot == 1)
        self.assertEqual(sorted(band for _p, band in weapons), [band for _p, band in weapons])

    def test_band_levels_ascending(self):
        self.assertEqual(BANDS, len(BAND_LEVELS))
        self.assertEqual(sorted(set(BAND_LEVELS)), BAND_LEVELS)

    def test_band_levels_follow_world_level_range(self):
        from types import SimpleNamespace as NS

        def opts(start, top):
            return NS(world_level_start=NS(value=start), world_level_max=NS(value=top))

        default = band_levels_for(opts(5, 80))
        self.assertEqual(BANDS, len(default))
        self.assertEqual((5, 80), (default[0], default[-1]))
        self.assertEqual(sorted(set(default)), default)
        narrow = band_levels_for(opts(5, 12))
        self.assertEqual(BANDS, len(narrow))
        self.assertEqual(5, narrow[0])
        self.assertEqual(sorted(set(narrow)), narrow)
        self.assertEqual(1, band_levels_for(opts(0, 50))[0])
        self.assertEqual(BAND_LEVELS, band_levels_for(NS()))
        self.assertEqual(BAND_LEVELS, band_levels_for(None))

    def test_slot_data_contract(self):
        data = slot_data(15, 5, True, {"Normal": 40, "Magic": 35, "Rare": 20, "Unique": 5})
        self.assertEqual({"version", "chance", "chain_bonus", "boss_always", "tier_weights", "unique_multiplier",
                          "band_levels", "table", "factors", "uniques", "enabled"}, set(data))
        self.assertTrue(data["enabled"])
        self.assertEqual({"Normal": 40, "Magic": 35, "Rare": 20, "Unique": 5}, data["tier_weights"])
        self.assertEqual(10, data["unique_multiplier"])
        self.assertEqual(len(FACTORS), len(data["factors"]))
        for factor_id, mask, rarity, weight in data["factors"]:
            self.assertNotIn(factor_id, NEVER_ROLLED)
            self.assertIn(mask & 7, (1, 2, 4, 3, 5, 6, 7))
            self.assertIn(rarity, (1, 2))
            self.assertGreater(weight, 0)
        table_ids = {row[0] for row in data["table"]}
        for item_id, factor_id in data["uniques"]:
            self.assertIn(item_id, GEAR_BY_ID)
        self.assertTrue(table_ids)
        json.dumps(data)


class TestDropsOff(SO2RTestBase):
    options = {**OPEN, "feat_duel_rewards": False, "feat_chain_rewards": False}

    def test_no_drops_key(self):
        slot = self.world.fill_slot_data()
        self.assertNotIn("drops", slot)
        self.assertNotIn("feats", slot)


class TestFeatDefaults(SO2RTestBase):
    options = dict(OPEN)

    def test_defaults_on(self):
        self.assertTrue(self.world.options.feat_duel_rewards.value)
        self.assertTrue(self.world.options.feat_chain_rewards.value)
        self.assertFalse(self.world.options.monster_drops.value)

    def test_feats_with_drops_off_gives_table_only(self):
        slot = self.world.fill_slot_data()
        self.assertEqual({"version": 1, "duel_rank_a": True, "chain5_flawless": True}, slot["feats"])
        drops = slot["drops"]
        self.assertIs(False, drops["enabled"])
        self.assertEqual((0, 0, False), (drops["chance"], drops["chain_bonus"], drops["boss_always"]))
        self.assertEqual(build_table(), drops["table"])
        self.assertTrue(drops["factors"] and drops["uniques"] and drops["bonus_pool"])
        json.dumps(slot["feats"])


class TestSingleFeat(SO2RTestBase):
    options = {**OPEN, "feat_duel_rewards": False}

    def test_one_feat(self):
        slot = self.world.fill_slot_data()
        self.assertEqual({"version": 1, "duel_rank_a": False, "chain5_flawless": True}, slot["feats"])
        self.assertIn("drops", slot)


class TestDropsOn(SO2RTestBase):
    options = {**OPEN, "monster_drops": True, "monster_drop_chance": 20, "monster_drop_chain_bonus": 7,
               "monster_drop_bosses": False, "loot_tier_weights": {"Normal": 10, "Magic": 20, "Rare": 30, "Unique": 40}}

    def test_drops_block(self):
        slot = self.world.fill_slot_data()
        drops = slot["drops"]
        self.assertEqual(1, drops["version"])
        self.assertIs(True, drops["enabled"])
        self.assertEqual((20, 7, False), (drops["chance"], drops["chain_bonus"], drops["boss_always"]))
        self.assertEqual({"Normal": 10, "Magic": 20, "Rare": 30, "Unique": 40}, drops["tier_weights"])
        self.assertNotIn("loot", slot)  # drops are independent of loot_tiers
