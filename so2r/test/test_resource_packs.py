"""Resource packs (docs/RESOURCE_PACKS.md): bundles of several items that replace every
chest consumable and the boss-check filler when resource_packs is on (the default)."""
from collections import Counter
import unittest

from . import SO2RTestBase
from ..items import (ITEM_TABLE, LARGE_PACKS, RESOURCE_PACKS, SMALL_PACKS,
                     keeps_chest_content)
from BaseClasses import ItemClassification

PACK_NAMES = {pack.name for pack in RESOURCE_PACKS}


def _classes(items):
    return Counter("progression" if item.advancement else "useful" if item.useful else "filler"
                   for item in items)


class TestResourcePackTable(unittest.TestCase):
    def test_seven_packs_in_two_sizes(self):
        self.assertEqual(14, len(RESOURCE_PACKS))
        self.assertEqual({"Restorative", "Cooking", "Compounding", "Smithing", "Gemstone", "Art", "Tool"},
                         {pack.pack for pack in RESOURCE_PACKS})
        self.assertEqual(7, len(SMALL_PACKS))
        self.assertEqual(7, len(LARGE_PACKS))

    def test_ids_in_the_plugin_band_and_classes(self):
        for pack in RESOURCE_PACKS:
            with self.subTest(pack=pack.name):
                self.assertTrue(5_900_001 <= pack.item_id <= 5_900_099)
                self.assertEqual(pack.item_id, ITEM_TABLE[pack.name].code)
                expected = ItemClassification.useful if pack.size == "large" else ItemClassification.filler
                self.assertEqual(expected, ITEM_TABLE[pack.name].classification)
                self.assertTrue(pack.contents)
                for item_id, count in pack.contents:
                    self.assertTrue(1 <= item_id <= 9_999 and 1 <= count <= 10)

    def test_large_packs_hold_more(self):
        by_pack = {}
        for pack in RESOURCE_PACKS:
            by_pack.setdefault(pack.pack, {})[pack.size] = sum(count for _, count in pack.contents)
        for name, sizes in by_pack.items():
            self.assertGreater(sizes["large"], sizes["small"], msg=name)


class TestResourcePacksDefault(SO2RTestBase):
    options = {}

    def test_only_equipment_books_and_fol_are_left(self):
        kinds = {ITEM_TABLE[item.name].category for item in self.multiworld.itempool
                 if item.name not in PACK_NAMES}
        from ..items import EQUIPMENT_CATEGORIES
        self.assertTrue(kinds <= EQUIPMENT_CATEGORIES | {"BOOK", "OTHER", "FOL"}, kinds)
        for item in self.multiworld.itempool:
            if item.name not in PACK_NAMES:
                self.assertTrue(keeps_chest_content(item.name), msg=item.name)
        for gone in ("MATERIAL", "UNIDENTIFIED", "BATTLE", "COOKING", "FISH"):
            self.assertNotIn(gone, kinds)

    def test_skill_books_stay_and_curios_become_packs(self):
        pool = {item.name for item in self.multiworld.itempool}
        chest_contents = {d.vanilla_item_name for _, d in self.world._active_chest_locations()}
        self.assertIn("Walls of the Soul", chest_contents & pool)
        self.assertIn("Life in Nature", chest_contents & pool)
        for curio in ("Cinderella Glass", "Aphrodisiac", "Portrait B"):
            self.assertFalse(keeps_chest_content(curio), msg=curio)

    def test_every_replaced_chest_and_boss_filler_became_a_pack(self):
        chests = [data for _, data in self.world._active_chest_locations()]
        replaced = [d for d in chests if not keeps_chest_content(d.vanilla_item_name)]
        rare = [d for d in replaced if ITEM_TABLE[d.vanilla_item_name].classification == ItemClassification.useful]
        bosses = list(self.world._active_boss_locations())
        pool = [item.name for item in self.multiworld.itempool]
        large = sum(1 for name in pool if name in {p.name for p in LARGE_PACKS})
        small = sum(1 for name in pool if name in {p.name for p in SMALL_PACKS})
        self.assertEqual(len(rare), large)
        self.assertEqual(len(replaced) - len(rare) + len(bosses), small)
        # Equipment, books and Fol keep their vanilla content.
        others = Counter(d.vanilla_item_name for d in chests if d not in replaced)
        self.assertEqual(others, Counter(name for name in pool if name not in PACK_NAMES))

    def test_every_pack_kind_appears(self):
        pool = {item.name for item in self.multiworld.itempool}
        self.assertEqual({p.pack for p in RESOURCE_PACKS}, {p.pack for p in RESOURCE_PACKS if p.name in pool})

    def test_filler_requests_are_small_packs(self):
        names = {self.world.get_filler_item_name() for _ in range(50)}
        self.assertTrue(names <= {pack.name for pack in SMALL_PACKS})

    def test_slot_data_contract(self):
        slot = self.world.fill_slot_data()
        self.assertEqual("so2r-ids-v1-packs-v1", slot["mapping_version"])
        self.assertEqual(1, slot["progression"]["resource_packs"])
        packs = slot["resource_packs"]
        self.assertEqual({str(pack.item_id) for pack in RESOURCE_PACKS}, set(packs))
        restorative = packs[str(5_900_001)]
        self.assertEqual("Small Restorative Pack", restorative["name"])
        self.assertEqual([[757, 3], [756, 3], [277, 1], [278, 1]], restorative["contents"])


class TestResourcePacksKeepTheFillerBalance(SO2RTestBase):
    # Packs replace filler with filler and useful with useful, so excluded checks keep
    # exactly the filler they had.
    options = {"maze_chests": True, "optional_bosses": True, "raid_bosses": True}

    def test_same_classes_as_without_packs(self):
        from test.general import setup_multiworld
        from .. import SO2RWorld
        without = setup_multiworld(SO2RWorld, seed=self.multiworld.seed,
                                   options={**self.options, "resource_packs": False})
        self.assertEqual(_classes(without.itempool), _classes(self.multiworld.itempool))


class TestResourcePacksOff(SO2RTestBase):
    options = {"resource_packs": False}

    def test_vanilla_pool_and_no_contract(self):
        pool = {item.name for item in self.multiworld.itempool}
        self.assertEqual(set(), pool & PACK_NAMES)
        self.assertTrue(any(ITEM_TABLE[name].category == "BATTLE" for name in pool))
        slot = self.world.fill_slot_data()
        self.assertIsNone(slot["resource_packs"])
        self.assertEqual("so2r-ids-v1", slot["mapping_version"])


class TestResourcePacksWithEveryContract(SO2RTestBase):
    options = {"key_items": True, "chapter_keys": True, "character_items": True,
               "early_partner_recruit": True, "route": "claude", "starting_character": "celine"}

    def test_packs_tag_covers_story_keys_and_characters(self):
        slot = self.world.fill_slot_data()
        self.assertEqual("so2r-ids-v1-packs-v1", slot["mapping_version"])
        self.assertIsNotNone(slot["story_keys"])
        self.assertIsNotNone(slot["characters"])
        self.assertIsNotNone(slot["recruitment_checks"])
        self.assertEqual(14, len(slot["resource_packs"]))


if __name__ == "__main__":
    unittest.main()
