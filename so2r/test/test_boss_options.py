"""Route/recruitment boss-option filtering and the scripted-party invariant (Milestone 8
step 2). See docs/LOGIC_DESIGN.md for the sourcing behind these placements."""
from . import SO2RTestBase
from ..locations import BOSS_LOCATION_TABLE


def _location_names(test_case) -> set:
    return {loc.name for loc in test_case.multiworld.get_locations()}


class TestClaudeRouteDefault(SO2RTestBase):
    options = {"route": "claude"}

    def test_snow_ogre_not_azam_gille(self):
        names = _location_names(self)
        self.assertIn("Boss: Snow Ogre", names)
        self.assertNotIn("Boss: Azam Gille", names)


class TestRenaRoute(SO2RTestBase):
    options = {"route": "rena"}

    def test_azam_gille_not_snow_ogre(self):
        names = _location_names(self)
        self.assertIn("Boss: Azam Gille", names)
        self.assertNotIn("Boss: Snow Ogre", names)


class TestRecruitmentNone(SO2RTestBase):
    options = {"recruitment_bosses": "none"}

    def test_all_recruitment_bosses_excluded(self):
        names = _location_names(self)
        self.assertNotIn("Boss: Fire Lizard ×2", names)
        self.assertNotIn("Boss: Nightmare", names)
        self.assertNotIn("Boss: Ghost", names)


class TestRecruitmentOperaAndErnest(SO2RTestBase):
    options = {"recruitment_bosses": "opera_and_ernest"}

    def test_opera_and_ernest_included_ashton_excluded(self):
        names = _location_names(self)
        self.assertIn("Boss: Fire Lizard ×2", names)
        self.assertIn("Boss: Ghost", names)
        self.assertNotIn("Boss: Nightmare", names)


class TestRecruitmentAshton(SO2RTestBase):
    options = {"recruitment_bosses": "ashton"}

    def test_ashton_included_opera_and_ernest_excluded(self):
        names = _location_names(self)
        self.assertIn("Boss: Nightmare", names)
        self.assertNotIn("Boss: Fire Lizard ×2", names)
        self.assertNotIn("Boss: Ghost", names)


class TestScriptedPartiesNeverLocations(SO2RTestBase):
    """No option combination may ever create a location for a scripted party (Dias 204,
    Cynne 516, Metatron 520, Zaphkiel 530) -- the game ends those fights without a
    normal win, or continues past a loss, so a check there could never be completed."""
    options = {
        "boss_checks": True,
        "optional_bosses": True,
        "raid_bosses": True,
        "maze_chests": True,
        "route": "rena",
        "recruitment_bosses": "opera_and_ernest",
    }

    def test_no_scripted_party_is_a_location(self):
        # Scripted parties get a documentation-only " (scripted)" name suffix in
        # bosses.json (see build_data.py); none of those names may ever appear as a
        # location, under any option combination.
        scripted_names = {"Boss: Cynne (scripted)", "Boss: Metatron (scripted)",
                          "Boss: Zaphkiel (scripted)", "Boss: Dias (scripted)", "Boss: Dias"}
        self.assertFalse(scripted_names & _location_names(self))

    def test_scripted_party_ids_absent_from_boss_table(self):
        party_ids = {d.party_id for d in BOSS_LOCATION_TABLE.values()}
        self.assertFalse({204, 516, 520, 530} & party_ids)


class TestGoalNames(SO2RTestBase):
    def test_goal_boss_names(self):
        # Either Gabriel reports the goal, but the limiter-off variant replaces the
        # normal fight only on clear data, so it is never a location.
        by_party_id = {d.party_id: d.boss_name for d in BOSS_LOCATION_TABLE.values()}
        self.assertEqual("Gabriel", by_party_id[539])
        self.assertEqual("Gabriel (Limiter Off)", by_party_id[540])
        names = _location_names(self)
        self.assertIn("Boss: Gabriel", names)
        self.assertNotIn("Boss: Gabriel (Limiter Off)", names)
        self.assertEqual([539, 540], self.world.fill_slot_data()["goal_parties"])


class TestZinaeIsAshtonQuestOnly(SO2RTestBase):
    """Zinae (199) is fought only in Ashton's exorcism quest, not the main story."""

    def test_absent_without_ashton_recruitment(self):
        self.assertNotIn("Boss: Zinae", _location_names(self))


class TestZinaeWithAshtonRecruitment(SO2RTestBase):
    options = {"recruitment_bosses": "ashton"}

    def test_present_and_excluded(self):
        from BaseClasses import LocationProgressType
        location = self.multiworld.get_location("Boss: Zinae", self.player)
        self.assertEqual(LocationProgressType.EXCLUDED, location.progress_type)


class TestEveryPlacedBossRegionExists(SO2RTestBase):
    def test_every_placed_boss_has_a_known_region(self):
        from ..regions import REGION_TABLE
        for name, data in BOSS_LOCATION_TABLE.items():
            if data.region is not None:
                self.assertIn(data.region, REGION_TABLE, msg=name)
