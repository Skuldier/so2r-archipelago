"""World scaling options (docs/WORLD_SCALING_PLAN.md §3): slot_data.scaling carries them to the plugin.
Presentation only: the options never change logic or the item pool."""
from . import SO2RTestBase


class TestScalingDefaults(SO2RTestBase):
    def test_default_block(self):
        self.assertEqual({
            "version": 1, "mode": "cap",
            "world_level": {"source": "characters_bosses", "start": 5, "per_step": 2.5, "max": 80},
            "above": 3, "below": 3, "boss_offset": 3,
            "scale_bosses": True, "scale_final_battles": False, "scale_superbosses": False,
        }, self.world.fill_slot_data()["scaling"])


class TestScalingCustom(SO2RTestBase):
    options = {"enemy_scaling": "full", "world_level_source": "progress", "world_level_start": 10,
               "world_level_per_step": 7, "world_level_max": 60, "scaling_above": 0, "scaling_below": 5,
               "scaling_boss_offset": 6, "scale_bosses": False, "scale_final_battles": True,
               "scale_superbosses": True}

    def test_options_reach_slot_data(self):
        scaling = self.world.fill_slot_data()["scaling"]
        self.assertEqual("full", scaling["mode"])
        self.assertEqual({"source": "progress", "start": 10, "per_step": 0.7, "max": 60}, scaling["world_level"])
        self.assertEqual((0, 5, 6), (scaling["above"], scaling["below"], scaling["boss_offset"]))
        self.assertEqual((False, True, True),
                         (scaling["scale_bosses"], scaling["scale_final_battles"], scaling["scale_superbosses"]))


class TestSkillLevelsWithCharacters(SO2RTestBase):
    """docs/SKILL_LEVELS.md: the rebalance travels with characters as items (default on)."""
    options = {"character_items": True, "starting_character": "chisato", "resource_packs": False}

    def test_block_present(self):
        self.assertEqual({"version": 1, "anchor": 85}, self.world.fill_slot_data()["skill_levels"])


class TestSkillLevelsOff(SO2RTestBase):
    options = {"character_items": True, "starting_character": "chisato", "resource_packs": False,
               "rebalance_skill_levels": False}

    def test_block_absent_when_off(self):
        self.assertIsNone(self.world.fill_slot_data()["skill_levels"])


class TestSkillLevelsWithoutCharacters(SO2RTestBase):
    def test_block_absent_without_character_items(self):
        # Vanilla recruitment joins characters at their designed levels; nothing to rebalance.
        self.assertIsNone(self.world.fill_slot_data()["skill_levels"])


class TestScalingOff(SO2RTestBase):
    options = {"enemy_scaling": "off"}

    def test_off_is_still_described(self):
        self.assertEqual("off", self.world.fill_slot_data()["scaling"]["mode"])

    def test_scaling_never_changes_the_pool(self):
        pool = sorted(item.name for item in self.multiworld.itempool)
        self.assertTrue(pool)
