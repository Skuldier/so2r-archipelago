"""Assertions on apworld/so2r/data/regions.json and its wiring into chests.json /
bosses.json (Milestone 8 step 1: the data-driven story-progress region model)."""
import unittest

from ..locations import BOSS_LOCATION_TABLE, CHEST_LOCATION_TABLE
from ..regions import REGION_TABLE, REGIONS_IN_STORY_ORDER


class TestRegionTable(unittest.TestCase):
    def test_names_unique(self):
        names = [r.name for r in REGION_TABLE.values()]
        self.assertEqual(len(names), len(set(names)))

    def test_story_index_contiguous(self):
        indices = sorted(r.story_index for r in REGION_TABLE.values())
        self.assertEqual(list(range(len(REGION_TABLE))), indices)

    def test_story_index_matches_sorted_order(self):
        self.assertEqual(
            [r.story_index for r in REGIONS_IN_STORY_ORDER],
            list(range(len(REGIONS_IN_STORY_ORDER))),
        )

    def test_null_progress_regions_sort_last(self):
        numbered = [r for r in REGIONS_IN_STORY_ORDER if r.story_progress is not None]
        nulled = [r for r in REGIONS_IN_STORY_ORDER if r.story_progress is None]
        if nulled:
            self.assertEqual(len(numbered), min(r.story_index for r in nulled))

    def test_anchor_progress_values(self):
        # Phynal's spine value is 4904000 (the short first expedition); the region uses
        # the final visit instead, where its chests and bosses are (docs/LOGIC_AUDIT.md).
        anchors = {
            "MF_0005": 602000,
            "MF_0009": 1400500,
            "MF_0027": 3300500,
            "MF_0029": 3500000,
            "MF_0048": 6000500,
        }
        for locality, expected in anchors.items():
            self.assertEqual(expected, REGION_TABLE[locality].story_progress, msg=locality)

    def test_missable_regions(self):
        # Kurik's fields close at progress 1404000 (fields.json endScenarioProgress); the
        # Symbological Weapons Laboratory has no permanent entrance (one scripted visit,
        # region_overrides.json). No other region is missable.
        missable = {r.id for r in REGION_TABLE.values() if r.missable}
        self.assertEqual({"MF_0009", "MF_0041"}, missable)


class TestChestRegions(unittest.TestCase):
    def test_every_chest_has_a_known_region(self):
        # story_progress is legitimately null for the post-game maze (MF_0051, no fixed
        # place in the story); every other region has a numeric story_progress.
        for name, data in CHEST_LOCATION_TABLE.items():
            self.assertIn(data.region, REGION_TABLE, msg=name)
            if data.region != "MF_0051":
                self.assertIsNotNone(REGION_TABLE[data.region].story_progress, msg=name)

    def test_excluded_progress_count(self):
        excluded = [d for d in CHEST_LOCATION_TABLE.values() if d.excluded_progress]
        self.assertEqual(24, len(excluded))


class TestOverworldContinentSplit(unittest.TestCase):
    """Overworld continent split (docs/LOGIC_DESIGN.md "Overworld continent split"):
    each EXPEL/NEDE chest is assigned to a continent sub-region by nearest
    WorldmapSymbols row, instead of the bare EXPEL/NEDE region."""

    EXPECTED_COUNTS = {
        "EXPEL_CROSS": 27,
        "EXPEL_LACUER": 12,
        "EXPEL_HOFFMAN": 5,
        "EXPEL_ER": 6,
        "NEDE_CENTRAL": 6,
        "NEDE_FIELD4": 8,
        "NEDE_ARMLOCK": 4,
        "NEDE_FEENAL": 2,
    }

    def test_continent_subregions_exist(self):
        for region_id in self.EXPECTED_COUNTS:
            self.assertIn(region_id, REGION_TABLE, msg=region_id)

    def test_continent_chest_counts(self):
        counts = {}
        for data in CHEST_LOCATION_TABLE.values():
            if data.region in self.EXPECTED_COUNTS:
                counts[data.region] = counts.get(data.region, 0) + 1
        self.assertEqual(self.EXPECTED_COUNTS, counts)

    def test_no_chest_left_on_bare_overworld_region(self):
        # Every EXPEL/NEDE-fieldmap chest now belongs to a continent sub-region; the
        # bare "EXPEL"/"NEDE" regions hold no chests (they still exist for raid bosses
        # and as a chain anchor).
        overworld_chest_regions = {
            d.region for d in CHEST_LOCATION_TABLE.values() if d.fieldmap in ("EXPEL", "NEDE")
        }
        self.assertEqual(set(), overworld_chest_regions & {"EXPEL", "NEDE"})

    def test_fieldmap_stays_expel_or_nede(self):
        for data in CHEST_LOCATION_TABLE.values():
            if data.region in self.EXPECTED_COUNTS:
                self.assertIn(data.fieldmap, ("EXPEL", "NEDE"), msg=data.region)

    def test_continent_story_progress(self):
        expected = {
            "EXPEL_CROSS": 402000,
            "EXPEL_LACUER": 1800500,
            "EXPEL_HOFFMAN": 2400000,
            "EXPEL_ER": 3000000,
            "NEDE_CENTRAL": 3500000,
            "NEDE_FIELD4": 4200000,
            "NEDE_ARMLOCK": 5200500,
            "NEDE_FEENAL": 6000500,  # only stably open from the final voyage
        }
        for region_id, progress in expected.items():
            self.assertEqual(progress, REGION_TABLE[region_id].story_progress, msg=region_id)

    def test_no_region_key_for_continent_subregions(self):
        from ..items import REGION_KEY_BY_REGION
        for region_id in self.EXPECTED_COUNTS:
            self.assertNotIn(region_id, REGION_KEY_BY_REGION, msg=region_id)


class TestBossRegions(unittest.TestCase):
    def test_seeded_boss_regions_resolve(self):
        by_party_id = {d.party_id: d for d in BOSS_LOCATION_TABLE.values()}
        self.assertEqual("MF_0005", by_party_id[191].region)
        self.assertEqual("Salva Mines", REGION_TABLE[by_party_id[191].region].name)
        self.assertEqual("MF_0048", by_party_id[539].region)
        self.assertEqual("MF_0048", by_party_id[540].region)

    def test_placed_boss_region_is_known(self):
        for name, data in BOSS_LOCATION_TABLE.items():
            if data.region is not None:
                self.assertIn(data.region, REGION_TABLE, msg=name)
