"""Equipment stacking options (Equipment group), sent to the plugin as slot_data.equipment."""
from . import SO2RTestBase

DEFAULT_STACK = [8, 15, 16, 17, 68, 86, 87, 89, 90, 91, 92, 270]
DEFAULT_CAPS = {"15": 100, "17": 90, "68": 6, "86": 90, "87": 10, "270": 90}


class TestEquipmentDefault(SO2RTestBase):
    def test_defaults(self):
        self.assertEqual({"version": 1, "stack": DEFAULT_STACK, "caps": DEFAULT_CAPS},
                         self.world.fill_slot_data()["equipment"])


class TestEquipmentOpenWorld(SO2RTestBase):
    options = {"game_mode": "open_world"}

    def test_same_block_in_open_world(self):
        self.assertEqual({"version": 1, "stack": DEFAULT_STACK, "caps": DEFAULT_CAPS},
                         self.world.fill_slot_data()["equipment"])


class TestEquipmentNoExtraAttacks(SO2RTestBase):
    options = {"stack_extra_attacks": False}

    def test_removed(self):
        block = self.world.fill_slot_data()["equipment"]
        self.assertNotIn(68, block["stack"])
        self.assertNotIn("68", block["caps"])


class TestEquipmentNoRegeneration(SO2RTestBase):
    options = {"stack_regeneration": False}

    def test_removed(self):
        block = self.world.fill_slot_data()["equipment"]
        self.assertFalse({8, 15, 16} & set(block["stack"]))
        self.assertNotIn("15", block["caps"])


class TestEquipmentNoSpellPower(SO2RTestBase):
    options = {"stack_spell_power": False}

    def test_removed(self):
        self.assertFalse({89, 90, 91, 92} & set(self.world.fill_slot_data()["equipment"]["stack"]))


class TestEquipmentNoCostCuts(SO2RTestBase):
    options = {"stack_cost_cuts": False}

    def test_removed(self):
        block = self.world.fill_slot_data()["equipment"]
        self.assertFalse({17, 86, 87, 270} & set(block["stack"]))
        self.assertFalse({"17", "86", "87", "270"} & set(block["caps"]))


class TestEquipmentDamageCuts(SO2RTestBase):
    options = {"stack_damage_cuts": True}

    def test_added(self):
        block = self.world.fill_slot_data()["equipment"]
        self.assertEqual(sorted(DEFAULT_STACK + [94, 100]), block["stack"])
        self.assertEqual(80, block["caps"]["94"])
        self.assertEqual(75, block["caps"]["100"])


class TestEquipmentCap(SO2RTestBase):
    options = {"extra_attack_cap": 3}

    def test_cap_reflected(self):
        self.assertEqual(3, self.world.fill_slot_data()["equipment"]["caps"]["68"])


class TestEquipmentAllOff(SO2RTestBase):
    options = {"stack_extra_attacks": False, "stack_regeneration": False, "stack_spell_power": False,
               "stack_cost_cuts": False, "stack_damage_cuts": False}

    def test_empty_block_still_emitted(self):
        self.assertEqual({"version": 1, "stack": [], "caps": {}}, self.world.fill_slot_data()["equipment"])
