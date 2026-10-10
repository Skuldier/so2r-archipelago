"""Death Link (docs/DEATHLINK.md): the standard option, the amnesty range and the optional slot_data keys."""
import unittest

from Options import DeathLink

from . import SO2RTestBase
from ..options import DeathLinkAmnesty, SO2ROptions, option_groups


class TestDeathLinkOptions(unittest.TestCase):
    def test_standard_option_and_amnesty_range(self):
        self.assertIs(DeathLink, SO2ROptions.__annotations__["death_link"])
        self.assertEqual(0, DeathLink.default)
        self.assertEqual((1, 10, 1), (DeathLinkAmnesty.range_start, DeathLinkAmnesty.range_end, DeathLinkAmnesty.default))

    def test_both_options_are_in_one_group(self):
        groups = [group for group in option_groups if DeathLink in group.options]
        self.assertEqual(1, len(groups))
        self.assertIn(DeathLinkAmnesty, groups[0].options)


class TestDeathLinkOffByDefault(SO2RTestBase):
    options = {}

    def test_slot_data_has_no_death_link_keys(self):
        slot = self.world.fill_slot_data()
        self.assertNotIn("death_link", slot)
        self.assertNotIn("death_link_amnesty", slot)

    def test_enabling_it_only_adds_the_two_keys(self):
        off = self.world.fill_slot_data()
        self.world.options.death_link.value = 1
        self.world.options.death_link_amnesty.value = 4
        on = self.world.fill_slot_data()
        self.assertEqual({"death_link", "death_link_amnesty"}, set(on) - set(off))
        self.assertEqual({key: off[key] for key in off}, {key: on[key] for key in off})


class TestDeathLinkOn(SO2RTestBase):
    options = {"death_link": True, "death_link_amnesty": 3}

    def test_slot_data_carries_both_keys(self):
        slot = self.world.fill_slot_data()
        self.assertIs(True, slot["death_link"])
        self.assertEqual(3, slot["death_link_amnesty"])
