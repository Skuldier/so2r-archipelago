"""Open-world game mode (docs/OPEN_WORLD_PLAN.md): the hub's chests, area keys, the four-Orb goal and slot_data."""
from types import SimpleNamespace
import unittest

from . import SO2RTestBase
from .test_characters import EarlyCharacterChecks
from .. import SO2RWorld
from ..items import ITEM_TABLE, KEY_ITEM_BY_NAME
from ..locations import BOSS_LOCATION_TABLE, CHEST_LOCATION_TABLE
from ..open_world import (AREA_KEY_BY_LOCALITY, AREA_KEYS, LOST_CHESTS, OPEN_WORLD_AREAS, OPEN_WORLD_CHEST_AREA,
                          OPEN_WORLD_GEAR_MAPPING_VERSION, ORB_NAMES, PLANETS)
from ..regions import REGION_TABLE

CHEST_BY_FLAG = {data.flag: name for name, data in CHEST_LOCATION_TABLE.items()}
ARLIA_KEY = "Fast Travel: Arlia"
LAQUA_KEY = "Fast Travel: L'Aqua"


def chest(flag: int) -> str:
    return CHEST_BY_FLAG[flag]


def town_chest(locality: str) -> int:
    """A chest in this town. L'Aqua has none at the hub; Noel's home (MF_0032) is the Nede town used here."""
    return next(flag for flag, area in OPEN_WORLD_CHEST_AREA.items() if area == locality)


class TestOpenWorldData(unittest.TestCase):
    def test_area_keys_are_the_games_dungeons_in_their_own_band(self):
        self.assertEqual(17, len(AREA_KEYS))
        self.assertTrue(all(5_770_001 <= key.item_id <= 5_770_099 for key in AREA_KEYS))
        self.assertTrue(all(ITEM_TABLE[key.name].code == key.item_id for key in AREA_KEYS))

    def test_lost_chests_are_not_open_world_chests(self):
        # 72: a guard keeps Lacuer Castle's side room closed at the hub (room 051, 2026-09-24).
        self.assertEqual((41, 42, 43, 72, 95), LOST_CHESTS)
        self.assertFalse(set(LOST_CHESTS) & set(OPEN_WORLD_CHEST_AREA))

    def test_story_recruitment_modes_are_refused(self):
        world = object.__new__(SO2RWorld)
        world.options = SimpleNamespace(
            game_mode=SimpleNamespace(value=1), starting_planet=SimpleNamespace(value=0),
            recruitment_checks=SimpleNamespace(value=False), early_partner_recruit=SimpleNamespace(value=True),
            character_items=SimpleNamespace(value=True))
        with self.assertRaisesRegex(ValueError, "no story recruitment"):
            world.generate_early()


class TestOpenWorldDefault(EarlyCharacterChecks, SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "expel"}

    def test_locations_are_the_hub_chests_and_boss_spots(self):
        names = {location.name for location in self.multiworld.get_locations(self.player)}
        chests = names - set(BOSS_LOCATION_TABLE)
        bosses = names & set(BOSS_LOCATION_TABLE)
        self.assertEqual(196, len(chests))  # 297 reachable at the hub, minus the maze's 100 and VR Expel's one
        # 19 boss spots, less the other route's Forest of Symbols boss (Claude's route by default: Snow Ogre).
        self.assertEqual(18, len(bosses))
        self.assertIn("Boss: Snow Ogre", bosses)
        self.assertNotIn("Boss: Azam Gille", bosses)
        self.assertFalse({name for name in bosses if BOSS_LOCATION_TABLE[name].region == "MF_0048"})  # Phynal: the goal
        self.assertIn(chest(134), names)  # Salva rock, missable in story mode, ordinary here
        self.assertIn(chest(190), names)  # Mountain Palace
        for flag in LOST_CHESTS:
            self.assertNotIn(chest(flag), names)

    def test_pool_has_area_keys_orbs_and_characters(self):
        pool = [item.name for item in self.multiworld.itempool]
        keys = [name for name in pool if ITEM_TABLE[name].category == "AREA_KEY"]
        self.assertEqual(15, len(keys))  # 17 dungeons, less Phynal (the Orbs) and the maze (no chests)
        self.assertNotIn(AREA_KEY_BY_LOCALITY["MF_0048"].name, keys)
        self.assertTrue(all(pool.count(orb) == 1 for orb in ORB_NAMES))
        self.assertEqual(3, sum(1 for name in pool if ITEM_TABLE[name].category == "CHARACTER"))  # joinable_characters
        self.assertFalse([name for name in pool if ITEM_TABLE[name].category == "CHAPTER_KEY"])
        # other_planet: item (default): the other planet's starting town is the only region key.
        self.assertEqual([LAQUA_KEY], [name for name in pool if ITEM_TABLE[name].category == "REGION_KEY"])
        # Expel's towns are sphere 1 enough: no starting key (only a Nede start carries one).
        self.assertFalse([item for item in self.multiworld.precollected_items[self.player]
                          if ITEM_TABLE[item.name].category == "AREA_KEY"])
        self.assertEqual(len(self.multiworld.get_locations(self.player)), len(pool))

    def test_towns_are_open_and_dungeons_need_their_key(self):
        self.assertTrue(self.can_reach_location(chest(town_chest("MF_0003"))))
        self.assertFalse(self.can_reach_location(chest(134)))
        self.collect_by_name(AREA_KEY_BY_LOCALITY["MF_0005"].name)
        self.assertTrue(self.can_reach_location(chest(134)))

    def test_the_other_planet_needs_its_town_key(self):
        nede_town = chest(town_chest("MF_0032"))
        self.assertFalse(self.can_reach_location(nede_town))
        self.collect_by_name(LAQUA_KEY)
        self.assertTrue(self.can_reach_location(nede_town))

    def test_a_dungeon_on_the_other_planet_needs_only_its_key(self):
        dungeon = next(k for k in AREA_KEYS if OPEN_WORLD_AREAS[k.locality].planet == "NEDE" and k.locality != "MF_0048")
        target = chest(OPEN_WORLD_AREAS[dungeon.locality].chests[0])
        self.assertFalse(self.can_reach_location(target))
        self.collect_by_name(dungeon.name)
        self.assertTrue(self.can_reach_location(target))  # 0.70.0: the key also opens its Guide Map point

    def test_a_boss_spot_is_in_logic_with_its_area(self):
        allen = "Boss: Allen Tucks"  # Salva Mines, on the start planet
        self.assertFalse(self.can_reach_location(allen))
        self.collect_by_name(AREA_KEY_BY_LOCALITY["MF_0005"].name)
        self.assertTrue(self.can_reach_location(allen))
        guardian = "Boss: Guardian (Field of Might)"  # a Nede dungeon: its key and the planet's
        self.assertFalse(self.can_reach_location(guardian))
        self.collect_by_name(AREA_KEY_BY_LOCALITY["MF_0037"].name)
        self.assertTrue(self.can_reach_location(guardian))

    def test_phynal_and_the_goal_need_all_four_orbs(self):
        # Phynal is on Nede: from Expel it also needs L'Aqua.
        phynal = REGION_TABLE["MF_0048"].name
        self.collect_by_name([LAQUA_KEY, *ORB_NAMES[:3]])
        self.assertFalse(self.can_reach_region(phynal))
        self.assertBeatable(False)
        self.collect_by_name(ORB_NAMES[3])
        self.assertTrue(self.can_reach_region(phynal))
        self.assertBeatable(True)

    def test_slot_data(self):
        slot = self.world.fill_slot_data()
        # item_pool: generated (default) carries Progressive Weapons, which need the v2 contract (test_gear_pool.py).
        self.assertEqual(OPEN_WORLD_GEAR_MAPPING_VERSION, slot["mapping_version"])
        self.assertEqual("open_world", slot["game_mode"])
        orb_ids = sorted(KEY_ITEM_BY_NAME[name].item_id for name in ORB_NAMES)
        block = slot["open_world"]
        self.assertEqual((1, 5900200, "EXPEL", "four_orbs"),
                         (block["version"], block["hub_progress"], block["start_planet"], block["goal"]))
        self.assertEqual({"EXPEL": 2, "NEDE": 58}, block["start_destinations"])
        self.assertEqual(orb_ids, block["area_locks"]["MF_0048"])
        self.assertEqual([5770005], block["area_locks"]["MF_0005"])
        self.assertEqual(16, len(block["area_locks"]))
        # The Orbs hold the Final Voyage talk together (ChapterLockPlanner is all-of per event).
        self.assertEqual({str(i): ["ev_5900200"] for i in orb_ids},
                         {k: v["events"] for k, v in slot["chapter_keys"].items()})
        self.assertEqual({"version": 1, "item_ids": [1578, 1579, 1580, 1581]}, slot["story_keys"])
        # Only Arlia is released by the new game; L'Aqua comes by its key, applied like any region key.
        self.assertEqual([2], block["released_at_start"])
        self.assertEqual({"5700046": {"region": "MF_0046", "name": "L'Aqua", "fast_travel_id": 58,
                                      "fieldmap": "MF_0046_01A"}}, slot["region_keys"])
        self.assertEqual((1, 0, 0, 0), (slot["boss_checks"], slot["optional_bosses"], slot["raid_bosses"],
                                        slot["guild_missions"]))
        spots = {spot["party_id"]: spot for spot in block["boss_spots"]}
        self.assertEqual(18, len(spots))
        self.assertEqual({"party_id": 527, "name": "Guardian (Field of Might)", "map": "MF_0037_04A",
                          "event": "ev_4204000"}, spots[527])
        self.assertIsNone(spots[524]["event"])  # Guard Hand: entering its arena map starts it
        self.assertIsNotNone(slot["characters"])
        self.assertEqual({"version": 1, "anchor": 85}, slot["skill_levels"])

    def test_chest_logic_names_the_area_key_or_the_orbs(self):
        logic = self.world.fill_slot_data()["chest_logic"]
        requirements = [sorted(r) for r in logic["requirements"]]
        salva = [requirements[i] for i in logic["chests"]["134"]]
        self.assertEqual([[5770005]], salva)
        self.assertEqual([[]], [requirements[i] for i in logic["chests"][str(town_chest("MF_0003"))]])
        self.assertEqual([[5700046]], [requirements[i] for i in logic["chests"][str(town_chest("MF_0032"))]])


class TestOpenWorldFromNede(EarlyCharacterChecks, SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "nede", "maze_chests": True}

    def test_expel_needs_arlia_and_the_maze_is_on_expel(self):
        pool = [item.name for item in self.multiworld.itempool]
        self.assertEqual([ARLIA_KEY], [name for name in pool if ITEM_TABLE[name].category == "REGION_KEY"])
        self.assertTrue(self.can_reach_location(chest(town_chest("MF_0032"))))
        self.assertFalse(self.can_reach_location(chest(town_chest("MF_0003"))))
        maze = chest(OPEN_WORLD_AREAS["MF_0051"].chests[0])
        self.collect_by_name(AREA_KEY_BY_LOCALITY["MF_0051"].name)
        self.assertFalse(self.can_reach_location(maze))
        self.collect_by_name(ARLIA_KEY)
        self.assertTrue(self.can_reach_location(maze))
        block = self.world.fill_slot_data()["open_world"]
        self.assertEqual(("NEDE", [58]), (block["start_planet"], block["released_at_start"]))

    def test_phynal_is_on_the_start_planet(self):
        self.collect_by_name(list(ORB_NAMES))
        self.assertTrue(self.can_reach_region(REGION_TABLE["MF_0048"].name))

    def test_a_nede_start_begins_with_one_nede_dungeon_key(self):
        # Nede's towns hold only 4 chests at the hub, so the start carries one of its dungeons.
        nede_keys = {k.name for k in AREA_KEYS if OPEN_WORLD_AREAS[k.locality].planet == "NEDE" and k.locality != "MF_0048"}
        start = [item.name for item in self.multiworld.precollected_items[self.player]
                 if ITEM_TABLE[item.name].category == "AREA_KEY"]
        self.assertEqual(1, len(start))
        self.assertIn(start[0], nede_keys)
        pool = [item.name for item in self.multiworld.itempool]
        self.assertNotIn(start[0], pool)
        self.assertEqual(len(nede_keys) - 1, sum(1 for name in pool if name in nede_keys))
        self.assertEqual(len(self.multiworld.get_locations(self.player)), len(pool))
        dungeon = next(k.locality for k in AREA_KEYS if k.name == start[0])
        self.assertTrue(self.can_reach_location(chest(OPEN_WORLD_AREAS[dungeon].chests[0])))


class TestOpenWorldWithoutBosses(SO2RTestBase):
    options = {"game_mode": "open_world", "boss_checks": False}

    def test_no_boss_spots(self):
        names = {location.name for location in self.multiworld.get_locations(self.player)}
        self.assertFalse(names & set(BOSS_LOCATION_TABLE))
        slot = self.world.fill_slot_data()
        self.assertEqual((0, []), (slot["boss_checks"], slot["open_world"]["boss_spots"]))


class TestOpenWorldRenaRoute(SO2RTestBase):
    options = {"game_mode": "open_world", "route": "rena"}

    def test_the_forest_boss_follows_the_route(self):
        names = {location.name for location in self.multiworld.get_locations(self.player)}
        self.assertIn("Boss: Azam Gille", names)
        self.assertNotIn("Boss: Snow Ogre", names)


class TestOpenWorldOtherPlanetOpen(SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "expel", "other_planet": "open"}

    def test_both_planets_open_without_a_key(self):
        pool = [item.name for item in self.multiworld.itempool]
        self.assertFalse([name for name in pool if ITEM_TABLE[name].category == "REGION_KEY"])
        self.assertTrue(self.can_reach_location(chest(town_chest("MF_0032"))))
        slot = self.world.fill_slot_data()
        self.assertEqual({}, slot["region_keys"])
        self.assertEqual([2, 58], slot["open_world"]["released_at_start"])


class TestOpenWorldMaze(SO2RTestBase):
    options = {"game_mode": "open_world", "starting_planet": "expel", "maze_chests": True}

    def test_maze_adds_its_chests_and_key_without_progression(self):
        locations = [loc for loc in self.multiworld.get_locations(self.player) if loc.name in CHEST_LOCATION_TABLE]
        self.assertEqual(296, len(locations))
        pool = [item.name for item in self.multiworld.itempool]
        self.assertIn(AREA_KEY_BY_LOCALITY["MF_0051"].name, pool)
        maze = [loc for loc in locations if CHEST_LOCATION_TABLE[loc.name].group == "maze"]
        self.assertEqual(100, len(maze))
        orb = self.world.create_item(ORB_NAMES[0])
        self.assertFalse(maze[0].item_rule(orb))


class TestOpenWorldRandomPlanet(SO2RTestBase):
    options = {"game_mode": "open_world", "resource_packs": False}

    def test_a_planet_is_chosen(self):
        self.assertIn(self.world.fill_slot_data()["open_world"]["start_planet"], PLANETS)


class TestStoryModeUnchanged(SO2RTestBase):
    def test_story_mode_slot_data(self):
        slot = self.world.fill_slot_data()
        self.assertEqual("story", slot["game_mode"])
        self.assertIsNone(slot["open_world"])
        pool = [item.name for item in self.multiworld.itempool]
        self.assertFalse([name for name in pool if ITEM_TABLE[name].category == "AREA_KEY"])
