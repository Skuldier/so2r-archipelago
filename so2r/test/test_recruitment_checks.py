"""Synthetic encounter fixtures exercise generation; no fixture promotes native access."""
import random
import unittest
from unittest.mock import patch

from . import SO2RTestBase
from .. import recruitment
from ..characters import CHARACTERS, choose_roster


def fixture_sites():
    return {pid: {'SourcePlayerId': pid, 'RegionId': 'MF_0003', 'StoryProgressRequired': 400050,
                  'VerifiedRoutes': ['claude', 'rena'],
                  'Triggers': [{'Route': route, 'Map': 'MF_0003_01A', 'Event': f'fixture_recruit_{pid}',
                                'MinProgress': 400050, 'MaxProgress': 6000000}
                               for route in ('claude', 'rena')]}
            for pid in recruitment.RECRUITMENT_SITES}


class TestRecruitmentReadiness(unittest.TestCase):
    def test_statically_mapped_but_unverified_catalog_refuses_playable_generation(self):
        for route in ('claude', 'rena'):
            with self.assertRaisesRegex(ValueError, 'not ready for playable seeds'):
                recruitment.prepare_rewards(random.Random(0), choose_roster(random.Random(0), 1), route)

    def test_missing_route_event_or_access_mapping_is_not_promoted(self):
        for key, value in (('Triggers', []), ('VerifiedRoutes', ['claude']),
                           ('RegionId', None), ('StoryProgressRequired', None)):
            sites = fixture_sites()
            sites[3][key] = value
            with self.assertRaises(ValueError):
                recruitment.require_ready('rena', sites)
        sites = fixture_sites()
        sites[3]['Triggers'][1]['MaxProgress'] = 0
        with self.assertRaises(ValueError):
            recruitment.require_ready('rena', sites)

    def test_site_ids_are_separate_from_character_item_ids(self):
        self.assertEqual(7, len(recruitment.LOCATION_IDS))
        self.assertTrue(set(recruitment.LOCATION_IDS.values()).isdisjoint({c.item_id for c in CHARACTERS.values()}))
        self.assertEqual(5950003, recruitment.LOCATION_IDS['Recruitment: Celine'])


class RecruitmentWorldFixture:
    def setUp(self):
        self.site_patch = patch.dict(recruitment.RECRUITMENT_SITES, fixture_sites(), clear=True)
        self.site_patch.start()
        self.addCleanup(self.site_patch.stop)
        super().setUp()

    def test_characters_are_locked_at_local_recruitment_checks(self):
        locations = [loc for loc in self.multiworld.get_locations(self.player) if loc.name.startswith('Recruitment: ')]
        self.assertEqual(7, len(locations))
        self.assertTrue(all(loc.locked and loc.item.player == self.player for loc in locations))
        for loc in locations:
            self.assertTrue(loc.item_rule(loc.item))
            self.assertFalse(loc.item_rule(self.world.create_item('Blueberries')))
            remote = self.world.create_item(loc.item.name)
            remote.player = self.player + 1
            self.assertFalse(loc.item_rule(remote))
        expected = {row.name for row in self.world.character_roster[1:]}
        self.assertEqual(expected, {loc.item.name for loc in locations})
        self.assertTrue(all(loc.item.name != 'Character: ' + loc.name.removeprefix('Recruitment: ') for loc in locations))
        self.assertFalse(any(item.name.startswith('Character: ') for item in self.multiworld.itempool))
        self.assertEqual(len(self.multiworld.get_unfilled_locations(self.player)), len(self.multiworld.itempool))

    def test_contract_matches_actual_local_placements(self):
        slot = self.world.fill_slot_data()
        self.assertEqual(recruitment.RECRUITMENT_MAPPING_VERSION, slot['mapping_version'])
        plan = slot['recruitment_checks']
        self.assertEqual(recruitment.CATALOG_SHA256, plan['catalog_sha256'])
        self.assertEqual(7, len(plan['placements']))
        for location in self.multiworld.get_locations(self.player):
            if not location.name.startswith('Recruitment: '):
                continue
            row = plan['placements'][str(location.address)]
            self.assertEqual(location.item.code, row['reward_item_id'])
            self.assertEqual(location.address, 5950000 + row['source_player_id'])

    def test_catalog_remains_a_fixture_and_does_not_change_on_disk(self):
        self.assertTrue(all(not row['VerifiedRoutes'] for row in recruitment._CATALOG['Sites']))


class TestRecruitmentClaude(RecruitmentWorldFixture, SO2RTestBase):
    options = {"resource_packs": False, 'character_items': True, 'recruitment_checks': True, 'route': 'claude',
               'chapter_keys': True, 'region_keys': True}


class TestRecruitmentRena(RecruitmentWorldFixture, SO2RTestBase):
    options = {"resource_packs": False, 'character_items': True, 'recruitment_checks': True, 'route': 'rena',
               'starting_character': 'celine', 'chapter_keys': True, 'region_keys': True}


class TestRecruitmentChestOnly(RecruitmentWorldFixture, SO2RTestBase):
    options = {"resource_packs": False, 'character_items': True, 'recruitment_checks': True, 'boss_checks': False,
               'chapter_keys': True, 'region_keys': True, 'world_map_chests': True}


class TestRecruitmentOff(SO2RTestBase):
    options = {'character_items': True}

    def test_existing_general_pool_mode_is_preserved(self):
        # joinable_characters (default 3) sizes the general pool; recruitment checks alone use all seven.
        self.assertEqual(3, sum(item.name.startswith('Character: ') for item in self.multiworld.itempool))
        self.assertIsNone(self.world.fill_slot_data()['recruitment_checks'])
        self.assertFalse(any(loc.name.startswith('Recruitment: ') for loc in self.multiworld.get_locations()))
