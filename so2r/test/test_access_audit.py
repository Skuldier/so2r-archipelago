"""Physical access audit (docs/ACCESS_AUDIT.md): chests open where the game actually lets
the party reach them, not only once the story first visits their area."""
from . import SO2RTestBase
from ..items import KEY_ITEM_BY_NAME
from ..locations import CHEST_LOCATION_TABLE


def _chest(flag: int) -> str:
    return next(name for name, data in CHEST_LOCATION_TABLE.items() if data.flag == flag)


EARLY_LOCKS = ["Rena's Hairpin", "Chapter Key: Royal Audience", "Travel Permit", "Treasure Map"]


class TestAccessAuditLocks(SO2RTestBase):
    options = {"chapter_keys": True, "key_items": True}

    def test_marze_houses_need_no_key(self):
        # Live 2026-09-22: looted at story progress 1000000, before the Royal Audience.
        for flag in (50, 51, 52, 53):
            self.assertTrue(self.can_reach_location(_chest(flag)), msg=flag)

    def test_krosse_castle_hall_chests_before_the_audience(self):
        for flag in (31, 32):
            self.assertTrue(self.can_reach_location(_chest(flag)), msg=flag)
        # Chest 30 sits upstairs behind the audience itself.
        self.assertFalse(self.can_reach_location(_chest(30)))
        self.collect_by_name(["Rena's Hairpin", "Chapter Key: Royal Audience"])
        self.assertTrue(self.can_reach_location(_chest(30)))

    def test_krosse_cave_chests_need_no_map(self):
        # Live 2026-09-22 (room 047): 151-158 opened at 1000000, before the Treasure Map.
        for flag in range(151, 159):
            self.assertTrue(self.can_reach_location(_chest(flag)), msg=flag)
        # The unproven hidden chamber keeps the Treasure Map.
        self.collect_by_name(["Rena's Hairpin", "Chapter Key: Royal Audience", "Travel Permit"])
        for flag in range(159, 163):
            self.assertFalse(self.can_reach_location(_chest(flag)), msg=flag)
        self.collect_by_name("Treasure Map")
        for flag in range(159, 163):
            self.assertTrue(self.can_reach_location(_chest(flag)), msg=flag)

    def test_dungeons_without_evidence_keep_their_story_point(self):
        # The model sees no barrier at Eluria Tower or the Fields, but their seals are not
        # in the data, so they keep their first touch.
        self.collect_by_name(EARLY_LOCKS + ["Mud Shoes", "Chapter Key: Lacuer Ferry", "Armory Contest Badge",
                                            "Chapter Key: Hoffman Passage", "Chapter Key: Eluria Voyage"])
        self.assertFalse(self.can_reach_location(_chest(271)))  # Eluria Tower 1F/2F
        self.collect_by_name("ID Card")
        self.assertTrue(self.can_reach_location(_chest(271)))

    def test_forest_of_symbols_entrance_chest_needs_no_key(self):
        # Live 2026-09-22: chest 170 opened at 1000000, before both turn-back points; the rest lie past them.
        self.assertTrue(self.can_reach_location(_chest(170)))
        self.collect_by_name(EARLY_LOCKS[:3] + ["Mud Shoes"])
        for flag in range(171, 176):
            self.assertFalse(self.can_reach_location(_chest(flag)), msg=flag)
        self.collect_by_name("Treasure Map")
        for flag in range(171, 176):
            self.assertTrue(self.can_reach_location(_chest(flag)), msg=flag)

    def test_salva_mines_rock_chests_wait_for_harley(self):
        # Chests past the rock appear only with FLAG_SLBCAV_ROCK_ENABLE, set by Ashton's side quest in
        # Harley (1600000-1800500); the rest of the mines open with the Hairpin.
        self.collect_by_name("Rena's Hairpin")
        self.assertTrue(self.can_reach_location(_chest(135)))
        self.collect_by_name(EARLY_LOCKS[1:])
        for flag in (134, 139, 146):
            self.assertFalse(self.can_reach_location(_chest(flag)), msg=flag)
        self.collect_by_name("Mud Shoes")
        for flag in (134, 139, 146):
            self.assertTrue(self.can_reach_location(_chest(flag)), msg=flag)

    def test_authored_gate_stays_a_floor(self):
        self.assertEqual(1900000, self.world._chest_access(CHEST_LOCATION_TABLE[_chest(72)]))


class TestAccessAuditRegionKeys(SO2RTestBase):
    options = {"chapter_keys": True, "region_keys": True}

    def test_travel_key_still_opens_its_region(self):
        # Zandor's mansion keeps Harley's first touch, but the Harley key still opens it.
        self.assertFalse(self.can_reach_location(_chest(61)))
        self.collect_by_name("Fast Travel: Harley")
        self.assertTrue(self.can_reach_location(_chest(61)))

    def test_travel_key_never_bypasses_an_authored_gate(self):
        self.collect_by_name("Fast Travel: Lacuer Castle")
        self.assertFalse(self.can_reach_location(_chest(72)))
