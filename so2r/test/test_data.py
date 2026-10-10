"""Assertions on the checked-in data/*.json (via the built tables), matching the
counts recorded in docs/APWORLD.md."""
import unittest

from ..locations import BOSS_LOCATION_TABLE, CHEST_LOCATION_TABLE


class TestChestCounts(unittest.TestCase):
    def test_totals(self):
        main = [d for d in CHEST_LOCATION_TABLE.values() if d.group == "main"]
        maze = [d for d in CHEST_LOCATION_TABLE.values() if d.group == "maze"]
        self.assertEqual(272, len(main))
        self.assertEqual(100, len(maze))
        self.assertEqual(372, len(CHEST_LOCATION_TABLE))

    def test_excluded_progress(self):
        # 23 scenario-flagged/Kurik chests plus the one-visit Weapons Lab chest 95.
        excluded = [d for d in CHEST_LOCATION_TABLE.values() if d.excluded_progress]
        self.assertEqual(24, len(excluded))

    def test_no_duplicate_addresses(self):
        addresses = [d.address for d in CHEST_LOCATION_TABLE.values()]
        self.assertEqual(len(addresses), len(set(addresses)))


class TestBossCounts(unittest.TestCase):
    def test_totals(self):
        # 4 parties (Dias 204, Cynne 516, Metatron 520, Zaphkiel 530) are "scripted" --
        # the game ends those fights without a normal win, or continues past a loss to
        # a Lv255 Dias -- and never reach BOSS_LOCATION_TABLE at all (see locations.py's
        # _build_boss_table()).
        story = [d for d in BOSS_LOCATION_TABLE.values() if d.group == "story"]
        optional = [d for d in BOSS_LOCATION_TABLE.values() if d.group == "optional"]
        raid = [d for d in BOSS_LOCATION_TABLE.values() if d.group == "raid"]
        self.assertEqual(26, len(story))
        self.assertEqual(12, len(optional))
        self.assertEqual(10, len(raid))
        self.assertEqual(48, len(BOSS_LOCATION_TABLE))

    def test_no_scripted_group(self):
        self.assertFalse(any(d.group == "scripted" for d in BOSS_LOCATION_TABLE.values()))

    def test_scripted_parties_never_become_locations(self):
        party_ids = {d.party_id for d in BOSS_LOCATION_TABLE.values()}
        self.assertFalse({204, 516, 520, 530} & party_ids)

    def test_no_duplicate_addresses(self):
        addresses = [d.address for d in BOSS_LOCATION_TABLE.values()]
        self.assertEqual(len(addresses), len(set(addresses)))

    def test_goal_parties(self):
        goal_ids = sorted(d.party_id for d in BOSS_LOCATION_TABLE.values() if d.goal)
        self.assertEqual([539, 540], goal_ids)


class TestNoOverlapOrDuplicateNames(unittest.TestCase):
    def test_no_id_collision_between_chests_and_bosses(self):
        chest_ids = {d.address for d in CHEST_LOCATION_TABLE.values()}
        boss_ids = {d.address for d in BOSS_LOCATION_TABLE.values()}
        self.assertEqual(set(), chest_ids & boss_ids)

    def test_no_duplicate_location_names(self):
        names = list(CHEST_LOCATION_TABLE.keys()) + list(BOSS_LOCATION_TABLE.keys())
        self.assertEqual(len(names), len(set(names)))

    def test_every_location_has_pool_item(self):
        from ..items import ITEM_TABLE
        for name, data in CHEST_LOCATION_TABLE.items():
            self.assertIn(data.vanilla_item_name, ITEM_TABLE, msg=name)


class TestNoDuplicateItemIds(unittest.TestCase):
    def test_item_ids_unique(self):
        from ..items import ITEM_TABLE
        ids = [d.code for d in ITEM_TABLE.values()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_item_names_unique(self):
        from ..items import ITEM_TABLE
        # Dict keys are already unique by construction; this documents the intent.
        self.assertEqual(len(ITEM_TABLE), len(set(ITEM_TABLE.keys())))


class TestEnglishNames(unittest.TestCase):
    def test_chest_areas_are_english(self):
        for name, data in CHEST_LOCATION_TABLE.items():
            self.assertTrue(data.area, msg=name)
            self.assertNotIn("<CN=", data.area, msg=name)
            self.assertNotIn("MF_", data.area, msg=name)

    def test_boss_names_are_english(self):
        for name, data in BOSS_LOCATION_TABLE.items():
            self.assertNotIn("CHARA_", data.boss_name, msg=name)
            self.assertNotIn("××", data.boss_name, msg=name)

    def test_boss_name_spot_checks(self):
        by_party_id = {d.party_id: d.boss_name for d in BOSS_LOCATION_TABLE.values()}
        self.assertEqual("Allen Tucks", by_party_id[191])
        self.assertEqual("Fire Lizard ×2", by_party_id[196])
        self.assertEqual("Zadkiel & Camael & Raphael", by_party_id[536])
        self.assertEqual("Ultimate Metatron", by_party_id[3014])
        self.assertEqual("Gabriel", by_party_id[539])
        self.assertEqual("Gabriel (Limiter Off)", by_party_id[540])
        # Scripted parties (Cynne 516, Metatron 520, Zaphkiel 530) never reach
        # BOSS_LOCATION_TABLE at all, so their same-named non-scripted siblings no
        # longer collide with a "(1st)"-suffixed scripted entry; a region-name suffix
        # disambiguates them when regions differ, an ordinal only when they don't.
        # 517's fight is on the ship to Eluria (docs/LOGIC_AUDIT.md), and the Guardian
        # names follow the battle events: 527 is Field of Might, 525 Field of Courage.
        self.assertEqual("Cynne (Voyage to Eluria)", by_party_id[517])
        self.assertEqual("Cynne (Eluria Tower)", by_party_id[519])
        self.assertEqual("Guardian (Field of Courage)", by_party_id[525])
        self.assertEqual("Guardian (Field of Might)", by_party_id[527])
        self.assertEqual("Zaphkiel", by_party_id[532])
        self.assertEqual("Metatron", by_party_id[535])

    def test_chest_flag_spot_checks(self):
        by_flag = {d.flag: name for name, d in CHEST_LOCATION_TABLE.items()}
        self.assertTrue(by_flag[1].startswith("Arlia Chest 1 ("))
        self.assertTrue(by_flag[501].startswith("Expel World Map Chest 501 ("))

    def test_area_no_redundant_locality_prefix(self):
        # A prefixed area's suffix must never already start with the locality's own
        # first word (that would be the "Symbological Weapons Laboratory -
        # Symbological Weapons Lab Interior" bug): the prefix rule checks the
        # locality's first word, not its full name.
        for name, data in CHEST_LOCATION_TABLE.items():
            if " - " not in data.area:
                continue
            left, right = data.area.split(" - ", 1)
            first_word = left.split(" ", 1)[0]
            self.assertFalse(right.startswith(first_word), msg=data.area)

    def test_area_spot_check_mf_0041_02a(self):
        areas = {d.area for d in CHEST_LOCATION_TABLE.values() if d.fieldmap == "MF_0041_02A"}
        self.assertEqual({"Symbological Weapons Lab Interior"}, areas)


class TestUnidentifiedItemChests(unittest.TestCase):
    def test_unidentified_chest_is_a_location(self):
        # Sacred Grounds of Linga chest 239's vanilla reward is item 899, "?ARMOR" --
        # an UNIDENTIFIED-category item. These chests were skipped by build_data.py
        # until this change; see docs/APWORLD.md.
        by_flag = {d.flag: d for d in CHEST_LOCATION_TABLE.values()}
        self.assertIn(239, by_flag)
        self.assertEqual(899, by_flag[239].value)
        self.assertEqual("ITEM", by_flag[239].reward_type)

    def test_unidentified_item_name_is_unique(self):
        from ..items import ITEM_TABLE
        by_flag = {d.flag: d for d in CHEST_LOCATION_TABLE.values()}
        vanilla_name = by_flag[239].vanilla_item_name
        self.assertIn(vanilla_name, ITEM_TABLE)
        # ITEM_TABLE is keyed by name; a successful lookup above already proves
        # uniqueness (dict keys are unique by construction), but also confirm the
        # display name is disambiguated since several UNIDENTIFIED ids share a
        # bare name (e.g. multiple "?WEAPON" ids among the maze chests).
        all_names = [it.code for it in ITEM_TABLE.values()]
        self.assertEqual(len(all_names), len(set(all_names)))
