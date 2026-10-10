"""The generated open-world item pool (docs/GEAR_POOL.md): roster gear, Progressive Weapon ladders, the share."""
import random
import unittest

from BaseClasses import ItemClassification

from . import SO2RTestBase
from ..gear_pool import GEAR, GEAR_BY_ID, arrival_power, build, roster_mask
from ..items import (EQUIPMENT_CATEGORIES, ITEM_TABLE, PROGRESSIVE_WEAPON_BASE, progressive_weapon_code,
                     progressive_weapon_name)
from ..open_world import OPEN_WORLD_GEAR_MAPPING_VERSION, OPEN_WORLD_MAPPING_VERSION


class TestGearCatalog(unittest.TestCase):
    def test_every_piece_of_equipment_is_an_item(self):
        slots = [gear.slot for gear in GEAR]
        self.assertEqual((216, 113, 122), (slots.count("weapon"), slots.count("armor"), slots.count("accessory")))
        for gear in GEAR:
            self.assertEqual(5_000_000 + gear.id, ITEM_TABLE[gear.name].code, gear.name)
            self.assertEqual(ItemClassification.useful, ITEM_TABLE[gear.name].classification, gear.name)

    def test_leons_books_are_weapons(self):
        books = [gear for gear in GEAR if gear.category == "BOOK"]
        self.assertEqual(18, len(books))
        self.assertTrue(all(gear.slot == "weapon" and gear.usable_by(8) for gear in books))  # 8 = Leon

    def test_progressive_weapons_have_their_own_band(self):
        for player_id in range(1, 14):
            data = ITEM_TABLE[progressive_weapon_name(player_id)]
            self.assertEqual(PROGRESSIVE_WEAPON_BASE + player_id, data.code)
            self.assertEqual("PROGRESSIVE_WEAPON", data.category)
            self.assertEqual(ItemClassification.useful, data.classification)


class TestBuild(unittest.TestCase):
    """The pure builder, over many rosters and seeds."""

    def run_build(self, seed, roster, slots=188, share=50):
        return build(random.Random(seed), roster, slots, share, progressive_weapon_name, lambda gear: gear.name,
                     ["Small Pack"], ["Large Pack"], [1], [1], ["Filler"], lambda amount: f"{amount} Fol")

    def test_ladders_climb_and_fit_their_character(self):
        for seed in range(40):
            rng = random.Random(seed)
            roster = sorted(rng.sample(range(1, 14), 8))
            pool = self.run_build(seed, roster)
            self.assertEqual(set(roster), set(pool.ladders))
            for player_id, rungs in pool.ladders.items():
                self.assertEqual(4, len(rungs))
                gears = [GEAR_BY_ID[item] for item in rungs]
                self.assertTrue(all(gear.slot == "weapon" and gear.usable_by(player_id) for gear in gears))
                self.assertFalse([gear.name for gear in gears if gear.jackpot or gear.gag])
                powers = [gear.power for gear in gears]
                self.assertTrue(all(a < b for a, b in zip(powers, powers[1:])), f"{player_id}: every rung an upgrade {powers}")
                self.assertEqual(4, pool.names.count(progressive_weapon_name(player_id)))

    def test_every_rung_beats_the_weapon_the_character_arrives_with(self):
        # Room 051 (2026-09-24): Leon's first rung was the Reference Book he starts with; Noel joins with a 760-attack
        # claw but his ladder started at 58.
        for seed in range(60):
            rng = random.Random(seed)
            roster = rng.sample(range(1, 14), 8)  # roster[0] is the starter
            pool = self.run_build(seed, roster)
            for index, player_id in enumerate(roster):
                floor = arrival_power(player_id, starter=index == 0)
                powers = [GEAR_BY_ID[item].power for item in pool.ladders.get(player_id, [])]
                self.assertTrue(all(power > floor for power in powers), f"{player_id} (floor {floor}): {powers}")
        leon_starter = self.run_build(1, [8, 1, 2, 3, 4, 5, 6, 7])
        self.assertNotIn(625, leon_starter.ladders[8])  # the Reference Book
        noel_recruit = self.run_build(1, [1, 11, 2, 3, 4, 5, 6, 7])
        self.assertEqual(4, len(noel_recruit.ladders[11]))
        self.assertTrue(all(GEAR_BY_ID[item].power > 760 for item in noel_recruit.ladders[11]))

    def test_only_roster_gear_and_the_share(self):
        for seed in range(40):
            roster = sorted(random.Random(seed).sample(range(1, 14), 8))
            pool = self.run_build(seed, roster)
            self.assertEqual(188, len(pool.names))
            gear = [GEAR_BY_ID[ITEM_TABLE[name].code - 5_000_000] for name in pool.names
                    if name in ITEM_TABLE and ITEM_TABLE[name].category in EQUIPMENT_CATEGORIES]
            self.assertFalse([piece.name for piece in gear if not piece.equip & roster_mask(roster)])
            progressive = sum(1 for name in pool.names if name.startswith("Progressive Weapon: "))
            self.assertEqual(94, len(gear) + progressive)  # 50 % of 188
            self.assertEqual(39, sum(1 for piece in gear if piece.slot == "weapon") + progressive)
            self.assertEqual(len(gear), len({piece.id for piece in gear}), "no piece twice")

    def test_share_and_small_pools(self):
        pool = self.run_build(1, [1, 2, 3, 4, 5, 6, 7, 8], share=80)
        self.assertEqual(150, sum(1 for name in pool.names if name not in ("Small Pack", "Large Pack", "Filler")
                                  and not name.endswith(" Fol")))
        tiny = self.run_build(1, [1, 2, 3, 4, 5, 6, 7, 8], slots=10)
        self.assertEqual(10, len(tiny.names))
        self.assertEqual([], self.run_build(1, [1], slots=0).names)


class TestGeneratedOpenWorld(SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "expel"}

    def test_pool_is_generated_for_the_roster(self):
        pool = [item.name for item in self.multiworld.itempool]
        self.assertEqual(len(self.multiworld.get_locations(self.player)), len(pool))
        roster = [character.player_id for character in self.world.character_roster]
        mask = roster_mask(roster)
        gear = [GEAR_BY_ID[ITEM_TABLE[name].code - 5_000_000] for name in pool
                if ITEM_TABLE[name].category in EQUIPMENT_CATEGORIES]
        self.assertFalse([piece.name for piece in gear if not piece.equip & mask])
        for player_id in range(1, 14):
            count = pool.count(progressive_weapon_name(player_id))
            self.assertEqual(4 if player_id in roster else 0, count, player_id)

    def test_slot_data_carries_the_ladders(self):
        slot = self.world.fill_slot_data()
        self.assertEqual(OPEN_WORLD_GEAR_MAPPING_VERSION, slot["mapping_version"])
        block = slot["gear"]
        self.assertEqual(1, block["version"])
        roster = sorted(character.player_id for character in self.world.character_roster)
        self.assertEqual([str(pid) for pid in roster], list(block["progressive_weapons"]))
        for pid in roster:
            entry = block["progressive_weapons"][str(pid)]
            self.assertEqual(progressive_weapon_code(pid), entry["item"])
            self.assertEqual(self.world.gear_ladders[pid], entry["rungs"])


class TestVanillaPoolStillAvailable(SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "expel", "item_pool": "vanilla"}

    def test_vanilla_pool_has_no_progressive_weapons(self):
        pool = [item.name for item in self.multiworld.itempool]
        self.assertFalse([name for name in pool if ITEM_TABLE[name].category == "PROGRESSIVE_WEAPON"])
        slot = self.world.fill_slot_data()
        self.assertIsNone(slot["gear"])
        self.assertEqual(OPEN_WORLD_MAPPING_VERSION, slot["mapping_version"])


class TestGeneratedWithoutPacks(SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "nede", "resource_packs": False, "equipment_share": 65}

    def test_pool_fills_every_location(self):
        pool = [item.name for item in self.multiworld.itempool]
        self.assertEqual(len(self.multiworld.get_locations(self.player)), len(pool))
        self.assertFalse([name for name in pool if ITEM_TABLE[name].category == "PACK"])
