"""guild_missions option assertions (docs/MISSIONS.md "World data (guild_missions
option)"). World-side only: the plugin does not send this check yet."""
import unittest

from . import SO2RTestBase
from ..items import CHAPTER_KEYS_ENABLED, ITEM_TABLE
from ..locations import GUILD_MISSION_LOCATION_ID_BASE, GUILD_MISSION_LOCATION_TABLE

DEFERRED_QUEST_IDS = {24, 25, 26, 32, 40, 42, 43, 44, 45, 46, 47, 69}


class TestGuildMissionTable(unittest.TestCase):
    def test_total_count(self):
        # 69 rows minus 9 post-game (FLAG_HAVE_ENDING) minus 3 character-gated EX rows.
        self.assertEqual(57, len(GUILD_MISSION_LOCATION_TABLE))

    def test_names_unique(self):
        names = list(GUILD_MISSION_LOCATION_TABLE.keys())
        self.assertEqual(len(names), len(set(names)))

    def test_names_prefixed(self):
        for name in GUILD_MISSION_LOCATION_TABLE:
            self.assertTrue(name.startswith("Guild Mission: "), msg=name)

    def test_ids_in_band_and_unique(self):
        addresses = [d.address for d in GUILD_MISSION_LOCATION_TABLE.values()]
        self.assertEqual(len(addresses), len(set(addresses)))
        for address in addresses:
            self.assertTrue(
                GUILD_MISSION_LOCATION_ID_BASE < address <= GUILD_MISSION_LOCATION_ID_BASE + 99,
                msg=address,
            )

    def test_every_row_has_a_region_and_matching_story_gate(self):
        for name, data in GUILD_MISSION_LOCATION_TABLE.items():
            self.assertTrue(data.region, msg=name)
            self.assertEqual(data.start_progress, data.story_progress_required, msg=name)

    def test_no_deferred_quest_ids_present(self):
        quest_ids = {d.quest_id for d in GUILD_MISSION_LOCATION_TABLE.values()}
        self.assertEqual(set(), DEFERRED_QUEST_IDS & quest_ids)

    def test_every_pool_item_is_in_the_item_table(self):
        for name, data in GUILD_MISSION_LOCATION_TABLE.items():
            if data.pool_item_kind == "filler":
                self.assertIsNone(data.pool_item_name, msg=name)
                continue
            self.assertIn(data.pool_item_name, ITEM_TABLE, msg=name)


class TestGuildMissionsOffUnchanged(SO2RTestBase):
    options = {"guild_missions": False}

    def test_no_guild_mission_locations(self):
        location_names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        self.assertEqual(set(), location_names & set(GUILD_MISSION_LOCATION_TABLE.keys()))

    def test_default_location_count_unchanged(self):
        # 224 before the logic audit, minus Eluria Tower chest 286 (post-game), Zinae
        # (Ashton's quest only) and Gabriel (Limiter Off) (clear data only).
        self.assertEqual(221, len(self.multiworld.get_locations(self.player)))

    def test_slot_data_guild_missions_off(self):
        slot_data = self.world.fill_slot_data()
        self.assertEqual(0, slot_data["guild_missions"])


class TestGuildMissionsOffAllOptionsUnchanged(SO2RTestBase):
    options = {
        "boss_checks": True,
        "optional_bosses": True,
        "raid_bosses": True,
        "maze_chests": True,
        "world_map_chests": True,
        "route": "claude",
        "recruitment_bosses": "opera_and_ernest",
        "guild_missions": False,
    }

    def test_all_options_location_count_unchanged(self):
        # 419 before the logic audit, minus chest 286, Zinae, Gabriel (Limiter Off) and
        # the scripted Lacuer Armory Contest Dias (docs/LOGIC_AUDIT.md).
        self.assertEqual(415, len(self.multiworld.get_locations(self.player)))


class TestGuildMissionsOnDefault(SO2RTestBase):
    options = {"guild_missions": True}

    def test_57_more_locations(self):
        self.assertEqual(221 + 57, len(self.multiworld.get_locations(self.player)))

    def test_pool_size_matches_location_count(self):
        self.assertEqual(
            len(self.multiworld.get_locations(self.player)),
            len(self.multiworld.itempool) + len(self.multiworld.precollected_items.get(self.player, [])),
        )

    def test_every_guild_mission_location_present(self):
        location_names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        self.assertTrue(set(GUILD_MISSION_LOCATION_TABLE.keys()) <= location_names)

    def test_slot_data_guild_missions_on(self):
        slot_data = self.world.fill_slot_data()
        self.assertEqual(1, slot_data["guild_missions"])


class TestGuildMissionsOnAllOptions(SO2RTestBase):
    options = {
        "boss_checks": True,
        "optional_bosses": True,
        "raid_bosses": True,
        "maze_chests": True,
        "world_map_chests": True,
        "route": "claude",
        "recruitment_bosses": "opera_and_ernest",
        "guild_missions": True,
    }

    def test_57_more_locations_on_all_options(self):
        self.assertEqual(415 + 57, len(self.multiworld.get_locations(self.player)))

    def test_pool_size_matches_location_count(self):
        self.assertEqual(
            len(self.multiworld.get_locations(self.player)),
            len(self.multiworld.itempool) + len(self.multiworld.precollected_items.get(self.player, [])),
        )


class TestGuildMissionsWithChapterKeys(SO2RTestBase):
    # "Guild Mission: Customization Mission 2" (quest id 5) opens at story_progress
    # 1,300,000 -- past Chapter Key 1 "Royal Audience" (unlocks_progress 1,001,000)
    # but before Chapter Key 2 "Lacuer Ferry" (unlocks_progress 1,800,000), so it needs
    # exactly the first key and not the second (docs/LOGIC_DESIGN.md "Chapter gate list").
    options = {"guild_missions": True, "chapter_keys": True}

    def _location_name(self) -> str:
        for name, data in GUILD_MISSION_LOCATION_TABLE.items():
            if data.quest_id == 5:
                return name
        raise KeyError(5)

    def test_needs_royal_audience_key(self):
        name = self._location_name()
        self.assertFalse(self.can_reach_location(name))
        royal_audience = next(k.name for k in CHAPTER_KEYS_ENABLED if k.n == 1)
        self.collect_by_name([royal_audience])
        self.assertTrue(self.can_reach_location(name))

    def test_does_not_need_lacuer_ferry_key(self):
        name = self._location_name()
        lacuer_ferry = next(k.name for k in CHAPTER_KEYS_ENABLED if k.n == 2)
        self.collect_by_name([lacuer_ferry])
        self.assertFalse(self.can_reach_location(name))
