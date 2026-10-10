"""WorldTestBase runs for default options, every toggle on, and one rena+ashton
combination (Milestone 8 step 2)."""
from . import SO2RTestBase


class TestDefaultOptions(SO2RTestBase):
    options = {}


class TestAllOptionsOn(SO2RTestBase):
    options = {
        "boss_checks": True,
        "optional_bosses": True,
        "raid_bosses": True,
        "maze_chests": True,
        "world_map_chests": True,
        "route": "claude",
        "recruitment_bosses": "opera_and_ernest",
    }


class TestRenaAshtonCombination(SO2RTestBase):
    options = {
        "boss_checks": True,
        "route": "rena",
        "recruitment_bosses": "ashton",
    }


class TestRegionKeysDefault(SO2RTestBase):
    options = {"region_keys": True}


class TestRegionKeysAllOptionsOn(SO2RTestBase):
    options = {
        "boss_checks": True,
        "optional_bosses": True,
        "raid_bosses": True,
        "maze_chests": True,
        "world_map_chests": True,
        "route": "claude",
        "recruitment_bosses": "opera_and_ernest",
        "region_keys": True,
    }


class TestRegionKeysNoBossChecks(SO2RTestBase):
    """region_keys with boss_checks off: no boss filler items exist at all, so every
    replaced pool item must come from the vanilla consumable phase (docs/APWORLD.md
    "pool balance")."""
    options = {
        "boss_checks": False,
        "region_keys": True,
    }


class TestChapterKeysDefault(SO2RTestBase):
    options = {"chapter_keys": True}


class TestChapterKeysAllOptionsOn(SO2RTestBase):
    options = {
        "boss_checks": True,
        "optional_bosses": True,
        "raid_bosses": True,
        "maze_chests": True,
        "world_map_chests": True,
        "route": "claude",
        "recruitment_bosses": "opera_and_ernest",
        "region_keys": True,
        "chapter_keys": True,
    }


class TestChapterKeysNoBossChecks(SO2RTestBase):
    """chapter_keys with boss_checks off: no boss filler items exist at all, so every
    replaced pool item must come from the vanilla consumable phase (docs/APWORLD.md
    "pool balance")."""
    options = {
        "boss_checks": False,
        "chapter_keys": True,
    }


class TestGuildMissionsDefault(SO2RTestBase):
    options = {"guild_missions": True}


class TestGuildMissionsAllOptionsOn(SO2RTestBase):
    options = {
        "boss_checks": True,
        "optional_bosses": True,
        "raid_bosses": True,
        "maze_chests": True,
        "world_map_chests": True,
        "route": "claude",
        "recruitment_bosses": "opera_and_ernest",
        "region_keys": True,
        "chapter_keys": True,
        "guild_missions": True,
    }
