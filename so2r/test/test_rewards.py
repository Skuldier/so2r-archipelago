"""Battle EXP/BP/SP/Fol multipliers (exp_/bp_/sp_/fol_multiplier), sent to the plugin as slot_data.rewards."""
from . import SO2RTestBase


class TestRewardsDefault(SO2RTestBase):
    options = {"game_mode": "open_world"}

    def test_default_is_three_times_all_four(self):
        self.assertEqual({"version": 1, "exp_percent": 300, "bp_percent": 300, "sp_percent": 300, "fol_percent": 300,
                          "orb_bonus_percent": 200, "orb_items": [item.item_id for item in self.world._open_world_orbs()]},
                         self.world.fill_slot_data()["rewards"])


class TestRewardsStoryMode(SO2RTestBase):
    def test_story_mode_sends_them_too(self):
        self.assertEqual(300, self.world.fill_slot_data()["rewards"]["exp_percent"])


class TestRewardsCustom(SO2RTestBase):
    options = {"exp_multiplier": 150, "bp_multiplier": 100, "sp_multiplier": 200, "fol_multiplier": 10}

    def test_yaml_values_pass_through(self):
        self.assertEqual({"version": 1, "exp_percent": 150, "bp_percent": 100, "sp_percent": 200, "fol_percent": 10},
                         self.world.fill_slot_data()["rewards"])


class TestOrbBonus(SO2RTestBase):
    options = {"game_mode": "open_world", "orb_bonus": 350}

    def test_open_world_sends_bonus_and_four_orb_ids(self):
        from ..items import KEY_ITEM_BY_NAME
        from ..open_world import ORB_NAMES
        rewards = self.world.fill_slot_data()["rewards"]
        self.assertEqual(1, rewards["version"])
        self.assertEqual(350, rewards["orb_bonus_percent"])
        self.assertEqual([KEY_ITEM_BY_NAME[n].item_id for n in ORB_NAMES], rewards["orb_items"])
        self.assertEqual(4, len(set(rewards["orb_items"])))


class TestOrbBonusStoryMode(SO2RTestBase):
    def test_story_mode_omits_both_keys(self):
        rewards = self.world.fill_slot_data()["rewards"]
        self.assertEqual(1, rewards["version"])
        self.assertNotIn("orb_bonus_percent", rewards)
        self.assertNotIn("orb_items", rewards)


class TestOrbBonusDefault(SO2RTestBase):
    def test_default_is_200(self):
        from ..options import OrbBonus
        self.assertEqual(200, OrbBonus.default)
        self.assertEqual(200, self.world.options.orb_bonus.value)
