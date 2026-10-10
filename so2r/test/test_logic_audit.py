"""Regression tests for the logic audit fixes (docs/LOGIC_AUDIT.md). Each class pins one
finding to the game evidence it came from: battle events (boss_events.json), fast-travel
windows, one-visit localities and post-game-only content."""
import json
import unittest
from pathlib import Path

from BaseClasses import LocationProgressType

from . import SO2RTestBase
from ..items import CHAPTER_KEYS_ENABLED
from ..locations import BOSS_LOCATION_TABLE, CHEST_LOCATION_TABLE

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _chest_name(flag: int) -> str:
    return next(name for name, data in CHEST_LOCATION_TABLE.items() if data.flag == flag)


def _keys_up_to(n: int) -> list:
    return [key.name for key in CHAPTER_KEYS_ENABLED if key.n <= n]


class TestBossDataMatchesBattleEvents(unittest.TestCase):
    def test_every_story_boss_has_a_battle_event(self):
        bosses = json.loads((_DATA_DIR / "bosses.json").read_text(encoding="utf-8"))
        for boss in bosses:
            if boss["group"] == "story" and not boss["postgame"]:
                self.assertTrue(boss["events"], msg=boss["name"])

    def test_every_boss_is_placed(self):
        self.assertTrue(all(data.region is not None for data in BOSS_LOCATION_TABLE.values()))

    def test_fight_progress_comes_from_the_battle_event(self):
        by_party = {data.party_id: data for data in BOSS_LOCATION_TABLE.values()}
        self.assertEqual(5800000, by_party[535].story_progress)  # second Armlock visit
        self.assertEqual(2901000, by_party[517].story_progress)  # ship to Eluria
        self.assertEqual(6002500, by_party[538].story_progress)  # Lucifer, final Phynal
        self.assertEqual("MF_0023", by_party[517].region)
        self.assertEqual("MF_0037", by_party[527].region)  # Field of Might
        self.assertEqual("MF_0038", by_party[525].region)  # Field of Courage


class TestPhynalIsFinalVoyageContent(SO2RTestBase):
    """Phynal's first expedition is a scripted loss at the entrance; its chests and
    bosses 536-539 are only reachable on the final voyage (needs every chapter key)."""
    options = {"chapter_keys": True, "world_map_chests": True}

    def test_phynal_content_needs_the_final_voyage(self):
        names = [_chest_name(410), _chest_name(442), "Boss: Zadkiel & Camael & Raphael",
                 "Boss: Haniel & Michael", "Boss: Lucifer", _chest_name(607)]
        self.collect_by_name(_keys_up_to(7))
        for name in names:
            self.assertFalse(self.can_reach_location(name), msg=name)
        self.collect_by_name("Chapter Key: Final Voyage")
        for name in names:
            self.assertTrue(self.can_reach_location(name), msg=name)


class TestPostgameContentIsNeverEarly(SO2RTestBase):
    options = {"chapter_keys": True, "maze_chests": True, "optional_bosses": True,
               "raid_bosses": True}

    def test_default_postgame_checks_are_not_locations(self):
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        self.assertNotIn(_chest_name(286), names)  # Eluria Tower, VR Expel only
        self.assertNotIn("Boss: Gabriel (Limiter Off)", names)

    def test_maze_superbosses_and_raids_wait_for_the_goal(self):
        postgame = [loc for loc in self.multiworld.get_locations(self.player)
                    if (loc.name in CHEST_LOCATION_TABLE and CHEST_LOCATION_TABLE[loc.name].postgame)
                    or (loc.name in BOSS_LOCATION_TABLE and BOSS_LOCATION_TABLE[loc.name].postgame)]
        self.assertEqual(100 + 12 + 10, len(postgame))
        # No progression may wait behind the credits; equipment and filler may.
        from ..items import ITEM_TABLE
        progression = self.world.create_item("Chapter Key: Final Voyage")
        useful = next(self.world.create_item(n) for n, d in ITEM_TABLE.items() if d.category == "SWORD")
        for location in postgame:
            self.assertEqual(LocationProgressType.DEFAULT, location.progress_type, msg=location.name)
            self.assertFalse(location.item_rule(progression), msg=location.name)
            self.assertTrue(location.item_rule(useful), msg=location.name)
        self.collect_by_name(_keys_up_to(7))
        for location in postgame:
            self.assertFalse(self.can_reach_location(location.name), msg=location.name)
        self.collect_by_name("Chapter Key: Final Voyage")
        for location in postgame:
            self.assertTrue(self.can_reach_location(location.name), msg=location.name)


class TestMissableChecksAreExcluded(SO2RTestBase):
    options = {"chapter_keys": True}

    def test_one_shot_and_one_visit_checks(self):
        for name in (_chest_name(95), "Boss: Cynne (Voyage to Eluria)"):
            location = self.multiworld.get_location(name, self.player)
            self.assertEqual(LocationProgressType.EXCLUDED, location.progress_type, msg=name)

    def test_ship_cynne_needs_the_eluria_voyage(self):
        self.collect_by_name(_keys_up_to(3))
        self.assertFalse(self.can_reach_location("Boss: Cynne (Voyage to Eluria)"))
        self.collect_by_name("Chapter Key: Eluria Voyage")
        self.assertTrue(self.can_reach_location("Boss: Cynne (Voyage to Eluria)"))


class TestGateNpcRegionsOpenBeforeTheirGate(SO2RTestBase):
    """Harley hosts the Lacuer Ferry NPC; its own chests never needed that key. Its town
    house chest is walkable from the start (docs/ACCESS_AUDIT.md); Zandor's mansion keeps
    the town's first touch, which needs the Royal Audience."""
    options = {"chapter_keys": True}

    def test_harley_chests(self):
        self.assertTrue(self.can_reach_location(_chest_name(60)))
        self.assertFalse(self.can_reach_location(_chest_name(61)))
        self.collect_by_name("Chapter Key: Royal Audience")
        self.assertTrue(self.can_reach_location(_chest_name(61)))

    def test_second_armlock_metatron_needs_the_armlock_key(self):
        self.collect_by_name(_keys_up_to(6))
        self.assertFalse(self.can_reach_location("Boss: Metatron"))
        self.collect_by_name("Chapter Key: Armlock")
        self.assertTrue(self.can_reach_location("Boss: Metatron"))
