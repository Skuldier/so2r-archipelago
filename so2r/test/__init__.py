from test.bases import WorldTestBase


class SO2RTestBase(WorldTestBase):
    game = "Star Ocean: The Second Story R"


# Imported after SO2RTestBase is defined so `python -m unittest worlds.so2r.test`
# (which loads test cases from this package's __init__ module only) picks up every
# TestCase subclass defined in the sibling test modules.
from .test_world import *  # noqa: E402,F401,F403
from .test_ids import *  # noqa: E402,F401,F403
from .test_data import *  # noqa: E402,F401,F403
from .test_regions import *  # noqa: E402,F401,F403
from .test_boss_options import *  # noqa: E402,F401,F403
from .test_region_keys import *  # noqa: E402,F401,F403
from .test_chapter_keys import *  # noqa: E402,F401,F403
from .test_characters import *  # noqa: E402,F401,F403
from .test_recruitment_checks import *  # noqa: E402,F401,F403
from .test_early_partner import *  # noqa: E402,F401,F403
from .test_guild_missions import *  # noqa: E402,F401,F403
from .test_world_map_chests import *  # noqa: E402,F401,F403
from .test_logic_audit import *  # noqa: E402,F401,F403
from .test_key_items import *  # noqa: E402,F401,F403
from .test_resource_packs import *  # noqa: E402,F401,F403
from .test_chest_logic import *  # noqa: E402,F401,F403
from .test_access_audit import *  # noqa: E402,F401,F403
from .test_scaling import *  # noqa: E402,F401,F403
from .test_open_world import *  # noqa: E402,F401,F403
from .test_open_world_070 import *  # noqa: E402,F401,F403
from .test_gear_pool import *  # noqa: E402,F401,F403
from .test_rewards import *  # noqa: E402,F401,F403
from .test_traps import *  # noqa: E402,F401,F403
from .test_equipment import *  # noqa: E402,F401,F403
from .test_loot import *  # noqa: E402,F401,F403
from .test_drops import *  # noqa: E402,F401,F403
from .test_bonus_effects import *  # noqa: E402,F401,F403
from .test_cursed_loot import *  # noqa: E402,F401,F403
from .test_stat_bonuses import *  # noqa: E402,F401,F403
from .test_signature_effects import *  # noqa: E402,F401,F403
from .test_loot_names import *  # noqa: E402,F401,F403
from .test_challenge_missions import *  # noqa: E402,F401,F403
from .test_descent import *  # noqa: E402,F401,F403
from .test_death_link import *  # noqa: E402,F401,F403
from .test_phynal_doors import *  # noqa: E402,F401,F403
from .test_objectives import *  # noqa: E402,F401,F403
from .test_objectives_v2 import *  # noqa: E402,F401,F403
