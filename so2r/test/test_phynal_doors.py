"""Phynal Doors Open (docs/PHYNAL_DOORS.md): a default-on toggle that adds one slot_data key only when on."""
import unittest

from Options import DefaultOnToggle

from . import SO2RTestBase
from ..options import PhynalDoorsOpen, SO2ROptions, option_groups


class TestPhynalDoorsOptions(unittest.TestCase):
    def test_default_on_toggle_with_display_name(self):
        self.assertIs(PhynalDoorsOpen, SO2ROptions.__annotations__["phynal_doors_open"])
        self.assertTrue(issubclass(PhynalDoorsOpen, DefaultOnToggle))
        self.assertEqual(1, PhynalDoorsOpen.default)
        self.assertEqual("Phynal Doors Open", PhynalDoorsOpen.display_name)

    def test_in_exactly_one_group(self):
        self.assertEqual(1, len([group for group in option_groups if PhynalDoorsOpen in group.options]))


class TestPhynalDoorsOnByDefault(SO2RTestBase):
    options = {}

    def test_slot_data_carries_the_key(self):
        self.assertIs(True, self.world.fill_slot_data()["phynal_doors_open"])

    def test_turning_it_off_removes_only_that_key(self):
        on = self.world.fill_slot_data()
        self.world.options.phynal_doors_open.value = 0
        off = self.world.fill_slot_data()
        self.assertEqual({"phynal_doors_open"}, set(on) - set(off))
        self.assertEqual({key: on[key] for key in off}, off)


class TestPhynalDoorsOff(SO2RTestBase):
    options = {"phynal_doors_open": False}

    def test_slot_data_has_no_key(self):
        self.assertNotIn("phynal_doors_open", self.world.fill_slot_data())
