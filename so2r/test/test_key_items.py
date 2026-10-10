"""Key items as story locks (docs/KEY_ITEMS.md).

Each pooled key item holds the scene that would normally hand it over, so the story
cannot pass that point without it. build_data.py proves every lock against the game's
story tables; these tests pin the resulting table and check the world's pool, rules and
slot_data contract.
"""
import unittest

from . import SO2RTestBase
from ..items import CHAPTER_KEYS_ENABLED, ITEM_TABLE, KEY_ITEM_BY_NAME, KEY_ITEMS
from ..locations import BOSS_LOCATION_TABLE, CHEST_LOCATION_TABLE
from ..regions import REGION_TABLE
from BaseClasses import ItemClassification

KEY_NAMES_BOTH_ROUTES = {k.name for k in KEY_ITEMS if k.route is None}


def _region_chests(region_id: str):
    return [name for name, data in CHEST_LOCATION_TABLE.items()
            if data.region == region_id and not data.postgame]


class TestKeyItemTable(unittest.TestCase):
    def test_sixteen_locks_one_rena_only(self):
        self.assertEqual(16, len(KEY_ITEMS))
        self.assertEqual({"House Key"}, {k.name for k in KEY_ITEMS if k.route == "rena"})
        self.assertEqual(15, len(KEY_NAMES_BOTH_ROUTES))

    def test_ids_are_the_single_game_item_ids(self):
        for key in KEY_ITEMS:
            with self.subTest(key=key.name):
                self.assertEqual(5_000_000 + key.native_id, key.item_id)
                self.assertEqual(key.item_id, ITEM_TABLE[key.name].code)
                self.assertEqual(ItemClassification.progression, ITEM_TABLE[key.name].classification)
                self.assertTrue(key.native_id == 743 or 1560 <= key.native_id <= 1587)

    def test_every_lock_event_is_unique(self):
        events = [event for key in KEY_ITEMS for event in key.events]
        self.assertEqual(len(events), len(set(events)))

    def test_spot_checks(self):
        shoes = KEY_ITEM_BY_NAME["Mud Shoes"]
        self.assertEqual(["ev_1501500_c", "ev_1501500_r"], shoes.events)
        self.assertEqual(1501700, shoes.unlocks_progress)
        rune = KEY_ITEM_BY_NAME["Rune Code"]
        self.assertEqual(["ev_4100000"], rune.events)
        self.assertEqual(5, rune.replaces_chapter_key)
        idol = KEY_ITEM_BY_NAME["Idol of the Warrior"]
        self.assertEqual([525], idol.gated_bosses)
        self.assertEqual(["MF_0038"], idol.gated_regions)
        self.assertEqual(4, sum(1 for k in KEY_ITEMS if k.name.startswith("Orb of")))

    def test_excluded_items_are_not_locks(self):
        # Energy Stone and Void Matter hold points are confined by fast-travel limits,
        # the Ancient Text's source is an unlisted chest, the Key Card's grant is a field
        # NPC script, and the herbs stay a native pickup (docs/KEY_ITEMS.md).
        for name in ["Energy Stone", "Void Matter", "Ancient Text", "Key Card", "Clarisage", "Dillwhip"]:
            self.assertNotIn(name, KEY_ITEM_BY_NAME)


class TestKeyItemsOff(SO2RTestBase):
    options = {"resource_packs": False, "key_items": False}

    def test_no_key_items_in_pool_or_slot_data(self):
        pool = {item.name for item in self.multiworld.itempool}
        self.assertEqual(set(), pool & set(KEY_ITEM_BY_NAME))
        slot_data = self.world.fill_slot_data()
        self.assertIsNone(slot_data["story_keys"])
        self.assertEqual(0, slot_data["progression"]["key_items"])
        self.assertEqual("so2r-ids-v1", slot_data["mapping_version"])


class TestKeyItemsClaude(SO2RTestBase):
    options = {"resource_packs": False, "key_items": True, "route": "claude"}

    def test_pool_has_each_both_route_key_once(self):
        names = [item.name for item in self.multiworld.itempool if item.name in KEY_ITEM_BY_NAME]
        self.assertEqual(sorted(KEY_NAMES_BOTH_ROUTES), sorted(names))

    def test_pool_size_matches_locations(self):
        self.assertEqual(len(self.multiworld.get_unfilled_locations(self.player)),
                         len(self.multiworld.itempool))

    def test_slot_data_contract(self):
        slot_data = self.world.fill_slot_data()
        self.assertEqual("so2r-ids-v1-story-keys-v1", slot_data["mapping_version"])
        self.assertEqual({"version": 1, "item_ids": sorted(KEY_ITEM_BY_NAME[n].native_id
                                                           for n in KEY_NAMES_BOTH_ROUTES)},
                         slot_data["story_keys"])
        self.assertEqual(1, slot_data["progression"]["key_items"])
        # The lock map is keyed by the key item's own id; the plugin refuses these events.
        shoes = slot_data["chapter_keys"][str(5_000_743)]
        self.assertEqual({"name": "Mud Shoes", "events": ["ev_1501500_c", "ev_1501500_r"],
                          "unlocks_progress": 1501700}, shoes)
        self.assertEqual({str(KEY_ITEM_BY_NAME[n].item_id) for n in KEY_NAMES_BOTH_ROUTES},
                         set(slot_data["chapter_keys"]))

    def test_forest_needs_the_mud_shoes(self):
        # Past the turn-back points; the entrance chest (170) needs nothing (docs/ACCESS_AUDIT.md).
        forest = next(name for name, data in CHEST_LOCATION_TABLE.items() if data.flag == 171)
        earlier = [k.name for k in KEY_ITEMS if k.unlocks_progress < 1501700 and k.route is None]
        self.collect_by_name(earlier)
        self.assertTrue(self.can_reach_region(REGION_TABLE["MF_0010"].name))
        self.assertFalse(self.can_reach_location(forest))
        self.collect_by_name("Mud Shoes")
        self.assertTrue(self.can_reach_location(forest))

    def test_each_key_gates_its_own_progress(self):
        # Every chest whose (audited) access point is at or past a key's unlock needs it;
        # chests the access audit opens earlier do not (docs/ACCESS_AUDIT.md).
        all_keys = [k.name for k in KEY_ITEMS if k.route is None]
        self.collect_by_name(all_keys)
        chests = [(name, self.world._chest_access(data)) for name, data in self.world._active_chest_locations()
                  if not data.postgame and not REGION_TABLE[data.region].missable]
        for key in KEY_ITEMS:
            if key.route is not None:
                continue
            gated = [name for name, access in chests if access is not None and access >= key.unlocks_progress]
            open_early = [name for name, access in chests if access is not None and access < key.unlocks_progress
                          and not any(k.gated_regions and CHEST_LOCATION_TABLE[name].region in k.gated_regions
                                      for k in KEY_ITEMS)]
            with self.subTest(key=key.name):
                removed = self.remove_by_name(key.name)
                try:
                    for name in gated:
                        self.assertFalse(self.can_reach_location(name), msg=name)
                    self.assertFalse(self.multiworld.completion_condition[self.player](self.multiworld.state))
                finally:
                    self.collect(removed)
                if key.name == "Rena's Hairpin":
                    # The very first lock: every chest opened earlier needs nothing at all.
                    removed = self.remove_by_name(all_keys)
                    try:
                        for name in open_early:
                            if CHEST_LOCATION_TABLE[name].story_progress_required is None:
                                self.assertTrue(self.can_reach_location(name), msg=name)
                    finally:
                        self.collect(removed)
        self.assertTrue(self.multiworld.completion_condition[self.player](self.multiworld.state))

    def test_courage_guardian_and_chests_need_the_idol(self):
        others = [k.name for k in KEY_ITEMS if k.route is None and k.name != "Idol of the Warrior"
                  and k.unlocks_progress <= 4200000]
        self.collect_by_name(others)
        self.assertTrue(self.can_reach_region(REGION_TABLE["MF_0038"].name))
        guardian = next(name for name, data in BOSS_LOCATION_TABLE.items() if data.party_id == 525)
        courage_chests = _region_chests("MF_0038")
        self.assertEqual(8, len(courage_chests))
        self.assertFalse(self.can_reach_location(guardian))
        for name in courage_chests:
            self.assertFalse(self.can_reach_location(name), msg=name)
        self.collect_by_name("Idol of the Warrior")
        self.assertTrue(self.can_reach_location(guardian))
        for name in courage_chests:
            self.assertTrue(self.can_reach_location(name), msg=name)


class TestKeyItemsRena(SO2RTestBase):
    options = {"key_items": True, "route": "rena"}

    def test_house_key_is_pooled_and_gates_harley(self):
        # Harley's house chest is open from the start (docs/ACCESS_AUDIT.md); Zandor's
        # mansion keeps the town's first touch, past the Rena-only House Key scene.
        names = {item.name for item in self.multiworld.itempool}
        self.assertIn("House Key", names)
        mansion = next(name for name, data in CHEST_LOCATION_TABLE.items() if data.flag == 61)
        self.collect_by_name([k.name for k in KEY_ITEMS if k.unlocks_progress < 1506400])
        self.assertTrue(self.can_reach_region(REGION_TABLE["MF_0011"].name))
        self.assertFalse(self.can_reach_location(mansion))
        self.collect_by_name("House Key")
        self.assertTrue(self.can_reach_location(mansion))


class TestKeyItemsWithChapterKeys(SO2RTestBase):
    options = {"key_items": True, "chapter_keys": True}

    def test_rune_code_replaces_the_four_fields_key(self):
        pool = {item.name for item in self.multiworld.itempool}
        self.assertIn("Rune Code", pool)
        self.assertNotIn("Chapter Key: The Four Fields", pool)
        for key in CHAPTER_KEYS_ENABLED:
            if key.n != 5:
                self.assertIn(key.name, pool)
        chapter_keys = self.world.fill_slot_data()["chapter_keys"]
        self.assertNotIn(str(5_750_005), chapter_keys)
        self.assertEqual(["ev_4100000"], chapter_keys[str(5_001_577)]["events"])

    def test_both_kinds_gate_the_goal(self):
        locks = [k.name for k in CHAPTER_KEYS_ENABLED if k.n != 5] + list(KEY_NAMES_BOTH_ROUTES)
        self.collect_by_name(locks)
        self.assertTrue(self.multiworld.completion_condition[self.player](self.multiworld.state))
        for name in ["Chapter Key: Royal Audience", "Travel Permit", "Orb of Love", "N.P.I.D."]:
            with self.subTest(lock=name):
                removed = self.remove_by_name(name)
                self.assertFalse(self.multiworld.completion_condition[self.player](self.multiworld.state))
                self.collect(removed)


class TestKeyItemsChestOnlyEveryKey(SO2RTestBase):
    # The tightest budget: no boss filler, every key family. The last replacement tier
    # takes single filler-class non-equipment items, so every distinct piece of
    # equipment and every useful item keeps at least one copy.
    options = {"boss_checks": False, "region_keys": True, "chapter_keys": True, "key_items": True}

    def test_pool_fits_and_keeps_equipment(self):
        from ..items import EQUIPMENT_CATEGORIES
        self.assertEqual(len(self.multiworld.get_unfilled_locations(self.player)), len(self.multiworld.itempool))
        pool = [item.name for item in self.multiworld.itempool]
        self.assertTrue(KEY_NAMES_BOTH_ROUTES <= set(pool))
        vanilla_equipment = {data.vanilla_item_name for _, data in self.world._active_chest_locations()
                             if ITEM_TABLE[data.vanilla_item_name].category in EQUIPMENT_CATEGORIES}
        self.assertEqual(set(), vanilla_equipment - set(pool))
        # Rare non-equipment rewards become large resource packs (resource_packs is on).
        from ..items import keeps_chest_content
        useful = {data.vanilla_item_name for _, data in self.world._active_chest_locations()
                  if ITEM_TABLE[data.vanilla_item_name].classification == ItemClassification.useful
                  and keeps_chest_content(data.vanilla_item_name)}
        self.assertEqual(set(), useful - set(pool))


class TestKeyItemsWithRegionKeys(SO2RTestBase):
    options = {"key_items": True, "region_keys": True}

    def test_travel_keys_do_not_bypass_key_item_barriers(self):
        barriers = {"MF_0011": "Mud Shoes", "MF_0027": "ID Card", "MF_0039": "Rune Code",
                    "MF_0042": "Minae Cave Key Card"}
        for region_id, key_name in barriers.items():
            region = REGION_TABLE[region_id]
            earlier = [k.name for k in KEY_ITEMS if k.route is None and k.name != key_name
                       and k.unlocks_progress < KEY_ITEM_BY_NAME[key_name].unlocks_progress]
            # The forest's entrance chest needs nothing (docs/ACCESS_AUDIT.md): probe past the turn-back.
            reach = ((lambda: self.can_reach_location(next(name for name, data in CHEST_LOCATION_TABLE.items() if data.flag == 171)))
                     if region_id == "MF_0011" else (lambda: self.can_reach_region(region.name)))
            with self.subTest(region=region.name):
                self.collect_by_name([f"Fast Travel: {region.name}", *earlier])
                self.assertFalse(reach())
                self.collect_by_name(key_name)
                self.assertTrue(reach())
                self.remove_by_name([f"Fast Travel: {region.name}", key_name, *earlier])


if __name__ == "__main__":
    unittest.main()
