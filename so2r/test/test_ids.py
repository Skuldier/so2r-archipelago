"""Concrete id-formula assertions, mirrored by the C# side (ArchipelagoIds.cs) and
docs/APWORLD.md."""
import unittest

from ..items import bundle_item_code, fol_item_code
from ..locations import BOSS_LOCATION_ID_BASE, CHEST_LOCATION_ID_BASE


class TestIdFormulas(unittest.TestCase):
    def test_chest_location(self):
        self.assertEqual(5500132, CHEST_LOCATION_ID_BASE + 132)

    def test_boss_location(self):
        self.assertEqual(5600191, BOSS_LOCATION_ID_BASE + 191)

    def test_game_item_single(self):
        self.assertEqual(5000756, bundle_item_code(756, 1))

    def test_bundle_item(self):
        # "Blueberries x3" -> 5_000_000 + 10_000 * 2 + 757 = 5_020_757
        self.assertEqual(5020757, bundle_item_code(757, 3))

    def test_fol_small(self):
        self.assertEqual(5100025, fol_item_code(250))

    def test_fol_large(self):
        self.assertEqual(5400000, fol_item_code(3000000))
