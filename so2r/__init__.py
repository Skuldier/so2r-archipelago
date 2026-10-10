"""Star Ocean: The Second Story R -- Archipelago world.

Chest-and-boss shuffle with optional fast-travel keys, story chapter keys and story
key items. In story mode the item pool starts with vanilla chest contents and boss filler;
key items replace filler. The open world generates its pool instead (gear_pool.py,
docs/GEAR_POOL.md).
See docs/APWORLD.md in the plugin repo for the design and runtime contract.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import ClassVar, Dict, List, Optional, Set

from BaseClasses import ItemClassification, Region, Tutorial
from Options import OptionError
from worlds.AutoWorld import WebWorld, World
from .characters import CHARACTERS, MAX_JOINABLE, CharacterData, choose_roster
from .recruitment import (LOCATION_IDS as RECRUITMENT_LOCATION_IDS, RECRUITMENT_SITES,
                         RECRUITMENT_MAPPING_VERSION, prepare_rewards, slot_contract)
from .early_partner import (EARLY_PARTNER_LOCATION_ID, EARLY_PARTNER_LOCATION_NAME,
                            EARLY_PARTNER_MAPPING_VERSION, EARLY_PARTNER_SITE,
                            prepare_reward as prepare_early_partner_reward,
                            slot_contract as early_partner_slot_contract)

from .items import (
    CHAPTER_KEYS_ENABLED,
    EQUIPMENT_CATEGORIES,
    FILLER_ITEM_NAMES,
    ITEM_TABLE,
    KEY_ITEM_BY_NAME,
    KEY_ITEMS,
    REGION_KEY_BY_REGION,
    REGION_KEYS,
    LARGE_PACKS,
    RESOURCE_PACKS,
    SMALL_PACKS,
    TRAP_NAMES,
    keeps_chest_content,
    ChapterKeyData,
    KeyItemData,
    RegionKeyData,
    ResourcePackData,
    SO2RItem,
    build_item_name_groups,
    fol_item_name,
    progressive_weapon_code,
    progressive_weapon_name,
)
from . import descent, drops, gear_pool, loot, objectives
from .equipment import equipment_slot_data
from .locations import (
    BOSS_LOCATION_ID_BASE,
    BOSS_LOCATION_TABLE,
    CHALLENGE_MISSION_LOCATION_ID_BASE,
    CHALLENGE_MISSION_LOCATION_TABLE,
    CHALLENGE_MISSION_TIER_RULES,
    CHEST_LOCATION_ID_BASE,
    CHEST_LOCATION_TABLE,
    GUILD_MISSION_LOCATION_TABLE,
    LocationProgressType,
    SO2RLocation,
    location_name_groups as _build_location_name_groups,
)
from .open_world import (AREA_KEYS, DUNGEON_TRAVEL, FINAL_VOYAGE_EVENT, FINAL_VOYAGE_NEXT_PROGRESS, GOAL_REGION_ID as OPEN_WORLD_GOAL_ID,
                         HUB_PROGRESS, MAZE_REGION_ID as OPEN_WORLD_MAZE_ID, OPEN_WORLD_CHEST_AREA,
                         OPEN_WORLD_AREAS, OPEN_WORLD_GEAR_MAPPING_VERSION, OPEN_WORLD_MAPPING_VERSION, ORB_NAMES,
                         PLANETS, START_DESTINATIONS, BOSS_SPOTS, AreaKeyData, BossSpot)
from .options import (EnemyScaling, GameMode, ItemPool, OtherPlanet, RecruitmentBosses, Route, SO2ROptions,
                      option_groups)
from .regions import REGION_TABLE, REGIONS_IN_STORY_ORDER, UNPLACED_BOSSES_REGION_NAME
from .rules import (StoryLock, challenge_chest_count_rule, chapter_completion_rule, chest_access_rule, chest_story_gate_rule,
                    postgame_rule, region_access_rule, story_reaches_progress)
from worlds.generic.Rules import add_item_rule, add_rule

GAME_NAME = "Star Ocean: The Second Story R"
MAPPING_VERSION = "so2r-ids-v1"
CHARACTER_MAPPING_VERSION = "so2r-ids-v1-characters-v1"
# Rooms that deliver native key items (slot_data.story_keys); older clients refuse them
# instead of deferring every key item (ArchipelagoIds.StoryKeyMappingVersion).
STORY_KEY_MAPPING_VERSION = "so2r-ids-v1-story-keys-v1"
# Rooms whose pool carries resource packs (slot_data.resource_packs). A client that
# reads packs also reads every earlier contract, so this tag wins over all of them
# (ArchipelagoIds.ResourcePackMappingVersion).
RESOURCE_PACK_MAPPING_VERSION = "so2r-ids-v1-packs-v1"
# Rooms that carry slot_data.challenge_missions append this to their mapping version, so a plugin without the
# feature refuses the room instead of playing locations it can never check.
CHALLENGE_MISSION_MAPPING_SUFFIX = "-cm1"
GOAL_PARTY_IDS = [539, 540]

# The post-game maze's region key stays in the item table for stable ids but is never
# pooled: the maze only exists after the ending, so a travel key cannot open it early
# (docs/LOGIC_AUDIT.md).
MAZE_REGION_ID = "MF_0051"
# The goal fights are in Phynal; post-game content is reachable no earlier than this.
GOAL_REGION_ID = "MF_0048"


# slot_data.chest_logic: the pseudo item id meaning "the goal is complete", for chests
# that only exist after the ending.
CHEST_LOGIC_GOAL = -1


DEPTH_SEAL_KEY = SimpleNamespace(name=descent.DEPTH_SEAL_NAME)  # the pool loop only needs .name

CHEST_NAME_BY_FLAG: Dict[int, str] = {data.flag: name for name, data in CHEST_LOCATION_TABLE.items()}

# Checks that can never hold progression (both user-observed 2026-10-01): 606 needs the bunny mount;
# 607 is behind a barrier that is closed at the open-world hub.
WORLD_MAP_NO_PROGRESSION_FLAGS = frozenset({606, 607})


def _no_progression(item) -> bool:
    """Item rule for post-game checks: equipment and filler may wait behind the credits,
    anything another slot needs may not."""
    return not item.advancement


class SO2RWeb(WebWorld):
    theme = "ocean"
    option_groups = option_groups
    tutorials = [Tutorial(
        tutorial_name="Setup Guide",
        description="Install the BepInEx plugin and connect to an Archipelago room.",
        language="English",
        file_name="setup_en.md",
        link="setup/en",
        authors=["Skuldier"],
    )]


class SO2RWorld(World):
    """Star Ocean: The Second Story R -- chest/boss checks and optional progression keys."""

    game = GAME_NAME
    options_dataclass = SO2ROptions
    options: SO2ROptions
    web = SO2RWeb()
    required_client_version = (0, 6, 0)

    item_name_to_id: ClassVar[Dict[str, int]] = {
        name: data.code for name, data in ITEM_TABLE.items()
    }
    location_name_to_id: ClassVar[Dict[str, int]] = {
        **{name: data.address for name, data in CHEST_LOCATION_TABLE.items()},
        **{name: data.address for name, data in BOSS_LOCATION_TABLE.items()},
        **{name: data.address for name, data in GUILD_MISSION_LOCATION_TABLE.items()},
        **{name: data.address for name, data in CHALLENGE_MISSION_LOCATION_TABLE.items()},
        **{name: row.address for name, row in objectives.OBJECTIVE_LOCATION_TABLE.items()},
        **RECRUITMENT_LOCATION_IDS,
        EARLY_PARTNER_LOCATION_NAME: EARLY_PARTNER_LOCATION_ID,
        **descent.GUARDIAN_LOCATIONS,
    }

    item_name_groups: ClassVar[Dict[str, set]] = build_item_name_groups()
    location_name_groups: ClassVar[Dict[str, set]] = _build_location_name_groups()
    location_name_groups["Recruitment"] = set(RECRUITMENT_LOCATION_IDS)
    location_name_groups["Descent Guardians"] = set(descent.GUARDIAN_LOCATIONS)
    location_name_groups.update(objectives.location_name_groups())

    def _open_world(self) -> bool:
        mode = getattr(self.options, "game_mode", None)  # absent on the tests' hand-built option namespaces
        return mode is not None and mode.value == GameMode.option_open_world

    def _descent(self) -> bool:
        mode = getattr(self.options, "game_mode", None)  # absent on the tests' hand-built option namespaces
        return mode is not None and mode.value == GameMode.option_descent

    def _hub_mode(self) -> bool:
        """Open world or Descent: the modes that start from a hub profile, so the story-only features (region keys, chapter
        keys, key items, guild missions) are off and characters are always items."""
        return self._open_world() or self._descent()

    def _challenge_missions_on(self) -> bool:
        option = getattr(self.options, "challenge_missions", None)  # absent on the tests' hand-built option namespaces
        return option is not None and bool(option.value) and not self._descent()

    def generate_early(self) -> None:
        if getattr(self.options, "cursed_loot", None) and self.options.cursed_loot.value and not self.options.loot_tiers.value:
            logging.warning("SO2R player %s: Cursed Loot needs Loot Tiers; nothing will roll Cursed.", self.player_name)
        self.character_roster: List[CharacterData] = []
        self.recruitment_rewards: Dict[int, CharacterData] = {}
        self.early_partner_reward: CharacterData | None = None
        self.start_planet: str | None = None
        self.start_area_key: AreaKeyData | None = None
        self.gear_ladders: Dict[int, List[int]] = {}
        self.descent_floors: List[descent.Floor] = []
        self.objectives: List[objectives.Drawn] = []
        self.objectives_required = 0
        self.objectives_auto_win = False
        self._objective_rules: List = []
        if self._descent():
            self._descent_generate_early()
        if self._open_world():
            # docs/OPEN_WORLD_PLAN.md: the story's recruitment scenes are closed at the hub, so characters are
            # always items, and the character modes that place them at story encounters do not exist.
            if self.options.recruitment_checks.value or self.options.early_partner_recruit.value:
                raise ValueError("Open world has no story recruitment: recruitment_checks and early_partner_recruit "
                                 "only exist in story mode.")
            planet = self.options.starting_planet.value
            self.start_planet = PLANETS[planet - 1] if planet else self.random.choice(PLANETS)
            if self.start_planet == "NEDE" and self._other_planet() is not None:
                # With Expel locked, Nede's towns hold only 4 chests at the hub (L'Aqua has none), so a Nede start
                # also begins with one of its dungeons' keys: about 11-14 checks in sphere 1 instead of 4.
                self.start_area_key = self.random.choice(
                    [k for k in self._active_area_keys() if OPEN_WORLD_AREAS[k.locality].planet == "NEDE"])
        if self.options.recruitment_checks.value and not self.options.character_items.value:
            raise ValueError("Recruitment checks require character_items: true")
        if self.options.early_partner_recruit.value and not self.options.character_items.value:
            raise ValueError("Early-partner recruitment requires character_items: true")
        if self.options.recruitment_checks.value and self.options.early_partner_recruit.value:
            raise ValueError("Recruitment checks and early-partner recruitment are mutually exclusive")
        if self.options.character_items.value or self._hub_mode():
            if not self._hub_mode() and self.options.recruitment_bosses.value != RecruitmentBosses.option_none:
                raise ValueError("Character items currently require recruitment_bosses: none; "
                                 "vanilla recruitment-quest availability is not modeled for randomized rosters.")
            starter = self.options.starting_character.value or self.random.choice(list(CHARACTERS))
            # Recruitment checks and the early partner place all seven at fixed encounters; otherwise the pool holds
            # joinable_characters of them (absent on the tests' hand-built option namespaces: the full seven).
            joinable = getattr(self.options, "joinable_characters", None)
            fixed_sites = self.options.recruitment_checks.value or self.options.early_partner_recruit.value
            self.character_roster = choose_roster(self.random, starter,
                                                  MAX_JOINABLE if fixed_sites or joinable is None else joinable.value)
            if self.options.recruitment_checks.value:
                self.recruitment_rewards = prepare_rewards(self.random, self.character_roster,
                                                           self.options.route.current_key)
            elif self.options.early_partner_recruit.value:
                self.early_partner_reward = prepare_early_partner_reward(
                    self.random, self.character_roster, self.options.route.current_key)
                # These are this slot's six remaining generated character items only.
                self.options.local_items.value.update(
                    character.name for character in self._character_items()
                    if character != self.early_partner_reward)
            else:
                # Characters are ordinary pool items here: Fill's local early items put this many in the slot's own
                # sphere 1 (reachable with the starting items alone).
                early = getattr(self.options, "early_characters", None)  # absent on hand-built option namespaces
                count = min(early.value if early is not None else 0, len(self._character_items()))
                for character in self.random.sample(self._character_items(), count):
                    self.multiworld.local_early_items[self.player][character.name] = 1
        self._draw_objectives()

    def _objective_options_set(self) -> bool:
        option = getattr(self.options, "objective_count_drawn", None)  # absent on the tests' hand-built option namespaces
        return option is not None and option.value > 0

    def _draw_objectives(self) -> None:
        """docs/OBJECTIVES_V1.md section 2: draws the Bucket List after everything else that consumes randomness, so a
        seed with objectives off (the default) is untouched. Open world only; elsewhere the options are ignored."""
        if not self._objective_options_set():
            auto_win = getattr(self.options, "objectives_auto_win", None)
            if auto_win is not None and auto_win.value:
                logging.warning("SO2R player %s: objectives_auto_win needs drawn objectives; the goal is unchanged.",
                                self.player_name)
            return
        if not self._open_world():
            logging.warning("SO2R player %s: Bucket List objectives only exist in open_world; objective_count_drawn and "
                            "goal are ignored.", self.player_name)
            return
        weights = dict(self.options.objective_tier_mix.value)
        if sum(max(0, w) for w in weights.values()) <= 0:
            raise OptionError(f"SO2R player {self.player_name}: objective_tier_mix has every weight at 0.")
        chests = [data for _name, data in self._active_chest_locations()
                  if data.group != "maze" and data.region != OPEN_WORLD_GOAL_ID]
        keys = [k for k in self._active_area_keys() if k.locality != OPEN_WORLD_MAZE_ID]
        ctx = objectives.DrawContext(
            goal=self.options.goal.current_key, start_planet=self.start_planet,
            other_planet_open=self._other_planet() is None,
            chest_count=len(chests),
            boss_party_ids=frozenset(data.party_id for _name, data in self._active_boss_locations()
                                     if data.region != OPEN_WORLD_GOAL_ID),
            area_key_count=len(keys), town_count=len(objectives.TOWNS[self.start_planet]),
            fields_ok=set(objectives.FIELD_LOCALITIES) <= {k.locality for k in keys},
            chest_areas=frozenset(data.region for data in chests),
            character_count=len(self._character_items()))
        slots = getattr(self.options, "objective_slots", None)  # absent on the tests' hand-built option namespaces
        self.objectives = objectives.draw(self.random, ctx, self.options.objective_count_drawn.value, weights,
                                          self.player_name, list(slots.value) if slots is not None else ())
        asked = self.options.objectives_required.value
        self.objectives_required = min(asked, len(self.objectives))
        if self.objectives and asked > len(self.objectives):
            logging.warning("SO2R player %s: objectives_required %d clamped to the %d drawn.", self.player_name,
                            asked, len(self.objectives))
        auto_win = getattr(self.options, "objectives_auto_win", None)
        self.objectives_auto_win = bool(auto_win is not None and auto_win.value and self.objectives)
        if auto_win is not None and auto_win.value and not self.objectives:
            logging.warning("SO2R player %s: objectives_auto_win needs drawn objectives; the goal is unchanged.",
                            self.player_name)

    def _objective_goal(self) -> str:
        """The effective goal: orbs unless objectives were drawn and the player asked for them."""
        if not self.objectives:
            return objectives.GOAL_ORBS
        return self.options.goal.current_key

    # Options Descent has no use for: ignored with a log line when set (docs/descent/DESIGN_V1.md 1.4).
    _DESCENT_IGNORED = ("boss_checks", "optional_bosses", "raid_bosses", "maze_chests", "world_map_chests", "guild_missions",
                        "challenge_missions", "region_keys", "chapter_keys", "key_items", "starting_planet", "other_planet",
                        "item_pool", "orb_bonus")

    def _descent_generate_early(self) -> None:
        """Forced behaviour and the run's floors, guardians and modifiers (descent.py), drawn once from self.random."""
        o = self.options
        if o.recruitment_checks.value or o.early_partner_recruit.value:
            raise ValueError("Descent has no story recruitment: recruitment_checks and early_partner_recruit "
                             "only exist in story mode.")
        ignored = [name for name in self._DESCENT_IGNORED
                   if getattr(o, name, None) is not None and getattr(o, name).value != type(getattr(o, name)).default]
        if ignored:
            logging.info("SO2R player %s: Descent ignores %s.", self.player_name, ", ".join(ignored))
        # Packs are the supply line (no shops), and scaling must follow depth: `cap` is promoted to `full`, `off` is kept.
        o.resource_packs.value = 1
        if o.enemy_scaling.value == EnemyScaling.option_cap:
            o.enemy_scaling.value = EnemyScaling.option_full
        o.scale_bosses.value = 1
        o.scale_final_battles.value = 1
        self.descent_floors = descent.build_floors(
            self.random, o.descent_floors.value, bool(o.descent_unverified_dungeons.value),
            o.descent_modifier_chance.value, dict(o.descent_modifier_weights.value),
            o.enemy_scaling.value != EnemyScaling.option_off, bool(o.loot_tiers.value),
            bool(o.cursed_loot.value), bool(o.monster_drops.value), o.world_level_start.value, o.world_level_max.value,
            o.scaling_boss_offset.value, o.descent_final_guardian.current_key)

    def _descent_chest_locations(self):
        for floor in self.descent_floors:
            for flag in sorted(floor.dungeon.chests):
                name = CHEST_NAME_BY_FLAG[flag]
                yield name, CHEST_LOCATION_TABLE[name]

    def _descent_strength_on(self) -> bool:
        option = getattr(self.options, "descent_party_strength", None)  # absent on the tests' hand-built option namespaces
        return self._descent() and option is not None and bool(option.value)

    def _descent_seal_count(self) -> int:
        return max(0, len(self.descent_floors) - 1)

    def _descent_boosted(self) -> "Dict[int, float] | None":
        """Treasure floors: their chests' loot rolls better tiers (loot.roll_item boost)."""
        boosted = {CHEST_LOCATION_ID_BASE + flag: descent.TREASURE_BOOST
                   for floor in self.descent_floors if floor.modifier == "treasure" for flag in floor.dungeon.chests}
        return boosted or None

    def _rewards_slot_data(self):
        names = ("exp", "bp", "sp", "fol")
        # Absent on the tests' hand-built option namespaces.
        options = {name: getattr(self.options, f"{name}_multiplier", None) for name in names}
        if any(option is None for option in options.values()):
            return None
        rewards = {"version": 1, **{f"{name}_percent": option.value for name, option in options.items()}}
        orb_bonus = getattr(self.options, "orb_bonus", None)  # absent on the tests' hand-built option namespaces
        if self._open_world() and orb_bonus is not None:
            rewards["orb_bonus_percent"] = orb_bonus.value
            rewards["orb_items"] = [item.item_id for item in self._open_world_orbs()]
        return rewards

    def _equipment_slot_data(self):
        return equipment_slot_data(self.options)

    def _character_items(self) -> List[CharacterData]:
        return self.character_roster[1:]

    def _generated_pool(self) -> bool:
        """docs/GEAR_POOL.md: the open world's pool ignores vanilla chest contents (item_pool: generated)."""
        option = getattr(self.options, "item_pool", None)  # absent on the tests' hand-built option namespaces
        if self._descent():
            return True  # vanilla chest contents mean nothing when the dungeons are drawn from a set
        return self._open_world() and option is not None and option.value == ItemPool.option_generated

    def _progressive_weapons_on(self) -> bool:
        option = getattr(self.options, "progressive_weapons", None)  # absent on the tests' hand-built option namespaces
        return option is None or bool(option.value)

    def _active_chest_locations(self):
        if self._descent():
            yield from self._descent_chest_locations()
            return
        maze_on = bool(self.options.maze_chests.value)
        world_map_on = bool(self.options.world_map_chests.value)
        if self._open_world():
            yield from self._open_world_chest_locations(maze_on, world_map_on)
            return
        for name, data in CHEST_LOCATION_TABLE.items():
            if data.group == "maze" and not maze_on:
                continue
            # A post-game chest outside the maze (Eluria Tower chest 286, VR Expel only)
            # never becomes a location; the goal is already complete by then.
            if data.postgame and data.group != "maze":
                continue
            # World-map terrain access is not yet audited. Keep these catalog rows and
            # their public IDs for existing rooms, but do not create locations or pool
            # rewards for newly generated conservative seeds.
            if data.fieldmap in {"EXPEL", "NEDE"} and not world_map_on:
                continue
            yield name, data

    def _open_world_chest_locations(self, maze_on: bool, world_map_on: bool):
        """Open world (docs/OPEN_WORLD_AREAS.md): every town and dungeon chest that is there and reachable at the hub
        for both heroes, the post-game maze with maze_chests, and the world-map chests with world_map_chests (Nede's always
        on a Nede start). Kurik's
        early chests (maps gone), the story-only lab chest and VR Expel's Eluria Tower chest never become locations.
        The Salva rock and Mountain Palace chests, missable in story mode, are ordinary here: the hub opens both."""
        for name, data in CHEST_LOCATION_TABLE.items():
            if data.fieldmap in {"EXPEL", "NEDE"}:
                # Nede has no vehicle and every Nede barrier is open at the hub: on a Nede start its world-map chests
                # are on foot from the start, so they are checks without the option (live test pending).
                if world_map_on or data.fieldmap == getattr(self, "start_planet", None) == "NEDE":
                    yield name, data
                continue
            if data.flag not in OPEN_WORLD_CHEST_AREA:
                continue
            if data.group == "maze":
                if maze_on:
                    yield name, data
                continue
            if data.postgame:
                continue
            yield name, data

    def _active_area_keys(self) -> List[AreaKeyData]:
        """Open world §7.3 option (a): one key per dungeon. Phynal has none: the four Orbs open the Final Voyage there.
        The maze's key only exists with its chests."""
        if not self._open_world():
            return []
        maze_on = bool(self.options.maze_chests.value)
        return [k for k in AREA_KEYS if k.locality != OPEN_WORLD_GOAL_ID and (maze_on or k.locality != OPEN_WORLD_MAZE_ID)]

    def _open_world_orbs(self) -> list:
        return [KEY_ITEM_BY_NAME[name] for name in ORB_NAMES] if self._open_world() else []

    def _other_planet(self) -> "str | None":
        """The planet the party did not start on, when it opens by item (other_planet: item); None otherwise."""
        start = getattr(self, "start_planet", None)
        if not self._open_world() or start is None:
            return None
        option = getattr(self.options, "other_planet", None)  # absent on the tests' hand-built option namespaces
        if option is not None and option.value == OtherPlanet.option_open:
            return None
        return next(planet for planet in PLANETS if planet != start)

    def _open_world_planet_key(self) -> "RegionKeyData | None":
        """other_planet: item: the other planet's starting town's fast-travel key ("Fast Travel: Arlia" or "Fast Travel:
        L'Aqua"). The plugin's region-key path releases and reveals that town, which puts it on the Guide Map's
        cross-world page, the only way between the planets."""
        other = self._other_planet()
        if other is None:
            return None
        return next(key for key in REGION_KEYS if key.fast_travel_id == START_DESTINATIONS[other])

    @staticmethod
    def _planet_of(region_id: str) -> str:
        """EXPEL or NEDE. The access model's planet first: the maze is on Expel, where its entrance is, although the
        region table files it under Postgame."""
        area = OPEN_WORLD_AREAS.get(region_id)
        return area.planet if area else REGION_TABLE[region_id].continent.upper()

    def _open_world_boss_spots(self) -> List[BossSpot]:
        """The boss spots this seed plays (boss_checks on): all of open_world.json's, less the other route's boss."""
        if not self._open_world() or not self.options.boss_checks.value:
            return []
        route = self.options.route.value
        return [spot for spot in BOSS_SPOTS
                if not (spot.condition == "claude_route" and route != Route.option_claude)
                and not (spot.condition == "rena_route" and route != Route.option_rena)]

    def _open_world_requirements(self, region_id: str) -> List[str]:
        """Every item an open-world area needs (all of them): its area key, or the four Orbs for Phynal, and the other
        planet's key for an area on that planet, except a dungeon in DUNGEON_TRAVEL: its key also opens its Guide Map
        point, so the key alone suffices (the maze keeps both)."""
        keys = {k.locality: k.name for k in self._active_area_keys()}
        orbs_gate = self._objective_goal() != objectives.GOAL_OBJECTIVES  # goal: objectives replaces the Orbs gate
        names = ((list(ORB_NAMES) if orbs_gate else []) if region_id == OPEN_WORLD_GOAL_ID else
                 [keys[region_id]] if region_id in keys else [])
        planet_key = self._open_world_planet_key()
        if (planet_key is not None and self._planet_of(region_id) == self._other_planet()
                and not (region_id in DUNGEON_TRAVEL and region_id in keys)):
            names.append(planet_key.name)
        return names

    def _active_boss_locations(self):
        # Scripted parties (Dias 204, Cynne 516, Metatron 520, Zaphkiel 530) never reach
        # BOSS_LOCATION_TABLE at all (see locations.py's _build_boss_table()); every
        # other condition here only ever narrows the table further, so no combination
        # of options can ever produce a location the plugin cannot check.
        if self._descent():
            return  # a guardian win is the floor's own location (descent.GUARDIAN_LOCATIONS), not a "Boss:" check
        if not self.options.boss_checks.value:
            return
        # Open world: story bosses only exist inside their story windows, closed at the hub, so boss_checks means the
        # boss spots (the plugin restages each fight where its scene would have started it).
        if self._open_world():
            by_party = {data.party_id: (name, data) for name, data in BOSS_LOCATION_TABLE.items()}
            yield from (by_party[spot.party_id] for spot in self._open_world_boss_spots() if spot.party_id in by_party)
            return
        optional_on = bool(self.options.optional_bosses.value)
        raid_on = bool(self.options.raid_bosses.value)
        route = self.options.route.value
        recruitment = self.options.recruitment_bosses.value
        for name, data in BOSS_LOCATION_TABLE.items():
            # Gabriel (Limiter Off) replaces the normal Gabriel only on clear data: it
            # stays a goal party but is never a location (docs/LOGIC_AUDIT.md).
            if data.postgame and data.group == "story":
                continue
            if data.group == "optional" and not optional_on:
                continue
            if data.group == "raid" and not raid_on:
                continue
            if data.condition == "claude_route" and route != Route.option_claude:
                continue
            if data.condition == "rena_route" and route != Route.option_rena:
                continue
            if data.condition == "opera_recruitment" and recruitment != RecruitmentBosses.option_opera_and_ernest:
                continue
            if data.condition == "ernest_recruitment" and recruitment != RecruitmentBosses.option_opera_and_ernest:
                continue
            if data.condition == "ashton_recruitment" and recruitment != RecruitmentBosses.option_ashton:
                continue
            yield name, data

    def _active_guild_mission_locations(self):
        # Off by default; requires plugin support that does not exist yet (docs/MISSIONS.md
        # "World data (guild_missions option)"). Every row already excludes the 9 post-game
        # (FLAG_HAVE_ENDING) and 3 character-gated EX quests at build time (see
        # tools/apworld/build_data.py's build_guild_missions()), so there is nothing further
        # to condition here.
        if not self.options.guild_missions.value or self._hub_mode():
            return
        for name, data in GUILD_MISSION_LOCATION_TABLE.items():
            yield name, data

    def _active_challenge_mission_locations(self):
        """docs/MISSIONS.md "Challenge Missions as checks": the whole table with the option on, in both game modes."""
        if not self._challenge_missions_on():
            return
        yield from CHALLENGE_MISSION_LOCATION_TABLE.items()

    def _challenge_open_world_rule(self, tier: int):
        """Open world tier rule (data/challenge_missions.json tier_rules): non-maze Area Keys, character items and,
        in the top tier, the other planet's key. Counts are clamped to what the seed has. None = no requirement."""
        rule = CHALLENGE_MISSION_TIER_RULES["open_world"][str(tier)]
        keys = [k.name for k in self._active_area_keys() if k.locality != OPEN_WORLD_MAZE_ID]
        characters = [c.name for c in self._character_items()]
        n_keys = min(rule["keys"], len(keys))
        n_chars = min(rule["characters"], len(characters))
        planet_key = self._open_world_planet_key() if rule["planet_key"] else None
        if not n_keys and not n_chars and planet_key is None:
            return None
        player = self.player

        def tier_rule(state) -> bool:
            return ((not n_keys or state.has_from_list(keys, player, n_keys))
                    and (not n_chars or state.has_from_list(characters, player, n_chars))
                    and (planet_key is None or state.has(planet_key.name, player)))

        return tier_rule

    def _challenge_open_world_chest_rule(self, needed: int):
        counts: Dict[str, int] = {}
        for _name, data in self._active_chest_locations():
            if data.group != "maze":
                counts[data.region] = counts.get(data.region, 0) + 1
        return challenge_chest_count_rule(
            self.player, [(self._open_world_requirements(region), count) for region, count in sorted(counts.items())],
            needed)

    def _create_challenge_mission_regions(self) -> None:
        """Four tier regions entered from Menu (same layout in both modes); a row's own prerequisite is a rule on
        the location. Open world counts items; story mode reaches story progress through the locks."""
        if not self._challenge_missions_on():
            return
        menu = self.multiworld.get_region("Menu", self.player)
        open_world = self._open_world()
        locks = [] if open_world else self._story_locks()
        tier_progress = CHALLENGE_MISSION_TIER_RULES["story_progress"]
        regions: Dict[int, Region] = {}
        for tier in (1, 2, 3, 4):
            region = Region(f"Challenge Missions Tier {tier}", self.player, self.multiworld)
            self.multiworld.regions.append(region)
            entrance = menu.connect(region, f"Menu -> {region.name}")
            rule = (self._challenge_open_world_rule(tier) if open_world
                    else story_reaches_progress(tier_progress[str(tier)], self.player, locks))
            if rule is not None:
                entrance.access_rule = rule
            regions[tier] = region
        for name, data in self._active_challenge_mission_locations():
            region = regions[data.tier]
            loc = SO2RLocation(self.player, name, data.address, region)
            requires = data.requires
            if open_world:
                if "chests" in requires:
                    loc.access_rule = self._challenge_open_world_chest_rule(requires["chests"])
                elif requires.get("nede") and self._other_planet() == "NEDE":
                    planet_key = self._open_world_planet_key().name
                    loc.access_rule = lambda state, key=planet_key, player=self.player: state.has(key, player)
            else:
                progress = max(data.start_progress, requires.get("story_progress", 0))
                if progress > tier_progress[str(data.tier)]:
                    loc.access_rule = story_reaches_progress(progress, self.player, locks)
            if data.no_progression:
                add_item_rule(loc, _no_progression)
            region.locations.append(loc)

    # ---- Bucket List objectives (docs/OBJECTIVES_V1.md) ----

    def _objective_boss_region(self, party_id: int) -> str:
        return next(data.region for data in BOSS_LOCATION_TABLE.values() if data.party_id == party_id)

    def _objective_counts(self, spots: bool) -> List[tuple]:
        """(requirements, count) per area for the non-maze, non-Phynal chest checks, or for the boss spots."""
        counts: Dict[str, int] = {}
        source = ((data for _name, data in self._active_boss_locations()) if spots
                  else (data for _name, data in self._active_chest_locations() if data.group != "maze"))
        for data in source:
            if data.region != OPEN_WORLD_GOAL_ID:
                counts[data.region] = counts.get(data.region, 0) + 1
        return [(self._open_world_requirements(region), count) for region, count in sorted(counts.items())]

    def _objective_items_needed(self, *regions: str) -> List[str]:
        names: List[str] = []
        for region in regions:
            names.extend(name for name in self._open_world_requirements(region) if name not in names)
        return names

    def _objective_rule(self, drawn: "objectives.Drawn"):
        """The objective's access predicate: pure item checks only (never can_reach_*), so the goal's sum needs no
        indirect conditions. None = always in logic."""
        row, player = drawn.row, self.player
        parts = []
        tier_rule = self._challenge_open_world_rule(drawn.tier)  # Easy none; Medium 3 keys; Hard 7 keys + a character
        if tier_rule is not None:
            parts.append(tier_rule)
        needed: List[str] = []
        logic, n = row.logic, row.requires.get("n")
        if logic == "chests":
            parts.append(challenge_chest_count_rule(player, self._objective_counts(False), -(-n * 5 // 4)))
        elif logic == "party":
            characters = [c.name for c in self._character_items()]
            parts.append(lambda state, characters=characters, n=n: state.has_from_list(characters, player, n))
        elif logic == "boss":
            needed = self._objective_items_needed(self._objective_boss_region(row.requires["boss"]))
        elif logic == "spots":
            parts.append(challenge_chest_count_rule(player, self._objective_counts(True), n))
        elif logic == "keys":
            keys = [k.name for k in self._active_area_keys() if k.locality != OPEN_WORLD_MAZE_ID]
            parts.append(lambda state, keys=keys, n=n: state.has_from_list(keys, player, n))
        elif logic == "fields":
            needed = self._objective_items_needed(*objectives.FIELD_LOCALITIES)
        elif logic == "dungeon":
            needed = self._objective_items_needed(row.requires["area"])
        elif logic == "named":
            needed = self._objective_items_needed(self._objective_boss_region(drawn.variant["boss"]))
        elif logic == "funcity":
            needed = self._objective_items_needed("MF_0043")
        elif logic == "planets":
            planet_key = self._open_world_planet_key()
            needed = [planet_key.name] if planet_key is not None else []
        elif logic == "orbs" and n:
            parts.append(lambda state, n=n: state.has_from_list(list(ORB_NAMES), player, n))  # "Collect N Orbs"
        elif logic == "orbs":
            needed = list(ORB_NAMES)
        if needed:
            parts.append(lambda state, items=tuple(needed): state.has_all(items, player))
        if not parts:
            return None
        return lambda state, parts=tuple(parts): all(part(state) for part in parts)

    def _objective_params(self, drawn: "objectives.Drawn") -> dict:
        """The slot-data params of docs/OBJECTIVES_V1.md section 5, filled from this seed."""
        row = drawn.row
        params = dict(row.params)
        n = row.requires.get("n")
        if row.kind == "mission_count" and drawn.variant is not None:
            params["mission"] = drawn.variant["mission"]
        elif row.kind == "locations_done":
            kind = params.get("type")
            if kind == "BOSS_SPOTS":
                params["locations"] = sorted(data.address for _name, data in self._active_boss_locations())
                params["need"] = n
            elif kind == "DUNGEON_CLEAR":
                area = row.requires["area"]
                bosses = [row.requires["boss"]] if "boss" in row.requires else sorted(
                    data.party_id for _name, data in self._active_boss_locations()
                    if data.party_id in row.requires.get("bosses", ()))  # v2 rows: the area's boss spots in this seed
                params["locations"] = sorted(data.address for _name, data in self._active_chest_locations()
                                             if data.region == area and data.group != "maze") + [
                                                 BOSS_LOCATION_ID_BASE + boss for boss in bosses]
            elif kind == "BOSS" and drawn.variant is not None:
                params["locations"] = [BOSS_LOCATION_ID_BASE + drawn.variant["boss"]]  # (rows with a fixed boss carry it)
        elif row.kind == "items_held":
            if params.get("type") == "AREA_KEYS":
                params["items"] = sorted(k.item_id for k in self._active_area_keys() if k.locality != OPEN_WORLD_MAZE_ID)
                params["need"] = n
            elif params.get("type") == "CHARACTERS":
                params["items"] = sorted(c.item_id for c in self._character_items())
            else:
                params["items"] = sorted(orb.item_id for orb in self._open_world_orbs())
        elif row.kind == "visited":
            kind = params.get("type")
            if kind == "TOWNS":
                params["groups"] = [{"localities": list(objectives.TOWNS[self.start_planet]), "need": n}]
            elif kind == "FIELDS":
                params["groups"] = [{"localities": list(objectives.FIELD_LOCALITIES), "need": n}]
            else:
                params["groups"] = [{"localities": list(objectives.TOWNS[planet]), "need": 1} for planet in PLANETS]
        return params

    def _create_objective_regions(self) -> None:
        """One Objectives region entered from Menu with no rule; each drawn objective is a location with its own rule."""
        self._objective_rules = []
        if not self.objectives:
            return
        menu = self.multiworld.get_region("Menu", self.player)
        region = Region("Objectives", self.player, self.multiworld)
        self.multiworld.regions.append(region)
        menu.connect(region, "Menu -> Objectives")
        for drawn in self.objectives:
            loc = SO2RLocation(self.player, drawn.row.location_name, drawn.row.address, region)
            rule = self._objective_rule(drawn)
            self._objective_rules.append(rule if rule is not None else (lambda _state: True))
            if rule is not None:
                loc.access_rule = rule
            if drawn.row.no_progression:
                add_item_rule(loc, _no_progression)
            region.locations.append(loc)

    def _objectives_done_rule(self):
        rules, required = tuple(self._objective_rules), self.objectives_required
        return lambda state: sum(1 for rule in rules if rule(state)) >= required

    def create_item(self, name: str) -> SO2RItem:
        data = ITEM_TABLE[name]
        classification = data.classification
        if data.category == "CHARACTER" and (self._challenge_missions_on() or self.objectives):
            # Challenge Mission tiers 3 and 4 and the Hard objective tier count character items held, which logic only
            # sees on progression items.
            classification = ItemClassification.progression
        if self._descent_strength_on() and data.category in ("CHARACTER", "PROGRESSIVE_WEAPON"):
            # The guardians' party-strength rule counts them, which logic only sees on progression items.
            classification = ItemClassification.progression
        return SO2RItem(name, classification, data.code, self.player)

    def get_filler_item_name(self) -> str:
        return self._filler_name()

    def _packs_on(self) -> bool:
        return bool(self.options.resource_packs.value)

    def _random_pack(self, packs: List[ResourcePackData]) -> str:
        return self.random.choices(packs, weights=[p.weight for p in packs])[0].name

    def _filler_name(self) -> str:
        """A filler roll (boss checks, filler guild missions, AP's own requests): a
        small resource pack when packs are on, else the vanilla filler list."""
        if self._packs_on():
            return self._random_pack(SMALL_PACKS)
        return self.random.choice(FILLER_ITEM_NAMES)

    def _chest_pool_item(self, vanilla_name: str) -> str:
        """A chest's pool item: with resource packs on, only equipment, books and Fol stay
        themselves; anything else becomes a pack, large for a useful (rare) item, small
        otherwise, so filler stays filler and useful stays useful."""
        if not self._packs_on() or keeps_chest_content(vanilla_name):
            return vanilla_name
        rare = ITEM_TABLE[vanilla_name].classification == ItemClassification.useful
        return self._random_pack(LARGE_PACKS if rare else SMALL_PACKS)

    def _active_region_keys(self) -> List[RegionKeyData]:
        # Open world keeps vanilla fast travel (unlocked by visiting); area keys do the gating.
        if not self.options.region_keys.value or self._hub_mode():
            return []
        return [k for k in REGION_KEYS if k.region != MAZE_REGION_ID]

    def _active_key_items(self) -> List[KeyItemData]:
        # Open world: the key items' scenes are over at the hub; only the four Orbs are pooled (_open_world_orbs).
        if not self.options.key_items.value or self._hub_mode():
            return []
        route = self.options.route.current_key
        return [k for k in KEY_ITEMS if k.route in (None, route)]

    def _active_chapter_keys(self) -> List[ChapterKeyData]:
        if not self.options.chapter_keys.value or self._hub_mode():
            return []
        # A key item that holds the same scene takes the chapter key's place (the Rune
        # Code is The Four Fields' own event), so the pool never carries both.
        replaced = {k.replaces_chapter_key for k in self._active_key_items()}
        return [k for k in CHAPTER_KEYS_ENABLED if k.n not in replaced]

    def _story_locks(self) -> List[StoryLock]:
        """Every item the story cannot pass without, with the progress it unlocks."""
        return ([(k.name, k.unlocks_progress) for k in self._active_chapter_keys()] +
                [(k.name, k.unlocks_progress) for k in self._active_key_items()])

    def _region_access(self) -> Dict[str, "int | None"]:
        """Each region's story access point: its first touch, or earlier when the physical
        access audit (docs/ACCESS_AUDIT.md) proves one of its chests reachable earlier."""
        access: Dict[str, "int | None"] = {r.id: r.story_progress for r in REGIONS_IN_STORY_ORDER}
        for _name, data in self._active_chest_locations():
            if data.postgame or data.access_progress is None or access.get(data.region) is None:
                continue
            access[data.region] = min(access[data.region], data.access_progress)
        return access

    def create_regions(self) -> None:
        # One AP Region per tools/apworld/data/regions.json entry (a data-driven story
        # region model, docs/LOGIC_DESIGN.md), each entered straight from Menu. A region is
        # reached when the story reaches its access point -- its first touch, or earlier
        # where the physical access audit proves a chest reachable sooner (Marze's houses
        # at the Royal Audience, docs/ACCESS_AUDIT.md) -- or, with region_keys, when its
        # travel key is held. The story point needs every story lock (chapter keys, key
        # items) whose unlocks_progress is at or before it. Each chest then adds its own
        # access point. Bosses with no authored placement go to "Unplaced Bosses". With
        # every option off, no rule is attached anywhere.
        if self._descent():
            self._create_descent_regions()
            return
        if self._open_world():
            self._create_open_world_regions()
            self._create_challenge_mission_regions()
            self._create_objective_regions()
            return
        region_keys_on = bool(self.options.region_keys.value)
        locks = self._story_locks()
        active_key_regions: Set[str] = {k.region for k in self._active_region_keys()}
        region_access = self._region_access()

        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)

        story_regions: Dict[str, Region] = {}
        for region_data in REGIONS_IN_STORY_ORDER:
            region = Region(region_data.name, self.player, self.multiworld)
            self.multiworld.regions.append(region)
            entrance = menu.connect(region, f"Menu -> {region.name}")
            has_key = region_keys_on and region_data.id in active_key_regions
            if has_key or locks:
                key_name = REGION_KEY_BY_REGION[region_data.id].name if has_key else None
                entrance.access_rule = region_access_rule(
                    self.player, region_data.id, locks, key_name=key_name,
                    story_progress=region_access[region_data.id])
            story_regions[region_data.id] = region

        unplaced = Region(UNPLACED_BOSSES_REGION_NAME, self.player, self.multiworld)
        self.multiworld.regions.append(unplaced)
        menu.connect(unplaced, f"Menu -> {UNPLACED_BOSSES_REGION_NAME}")

        after_goal = postgame_rule(self.player, locks, REGION_TABLE[GOAL_REGION_ID].name)

        for name, data in self._active_chest_locations():
            region = story_regions[data.region]
            loc = SO2RLocation(self.player, name, data.address, region)
            if data.flag in WORLD_MAP_NO_PROGRESSION_FLAGS:
                add_item_rule(loc, _no_progression)
            if data.excluded_progress:
                loc.progress_type = LocationProgressType.EXCLUDED
            if data.postgame:
                # Maze chests exist only after the ending: reachable with the goal, and
                # never holding anything another slot needs (docs/LOGIC_AUDIT.md). They
                # are not EXCLUDED, which would allow filler only: the maze's 100 chests
                # could then not hold equipment, and a solo seed runs out of filler.
                loc.access_rule = after_goal
                add_item_rule(loc, _no_progression)
            else:
                access = self._chest_access(data)
                if access is not None and (access > (region_access[data.region] or 0)
                                           or data.story_progress_required is not None):
                    loc.access_rule = chest_access_rule(
                        self.player, data.region, access, data.story_progress_required, locks,
                        key_active=region_keys_on and data.region in active_key_regions)
            region.locations.append(loc)

        for name, data in self._active_boss_locations():
            region = story_regions[data.region] if data.region is not None else unplaced
            loc = SO2RLocation(self.player, name, data.address, region)
            if data.missable:
                # A skippable fight (closing side-quest window, or a one-shot battle the
                # story continues past on a loss) must never hold progression.
                loc.progress_type = LocationProgressType.EXCLUDED
            if data.postgame:
                # Maze superbosses and Ultimate raids exist only after the ending; like
                # the maze chests, no progression, but equipment and filler are fine.
                loc.access_rule = after_goal
                add_item_rule(loc, _no_progression)
            elif data.region is None:
                # Preserve the check/id while its actual encounter access is unknown.
                # It must not hold anyone's progression, or become an early key source.
                loc.progress_type = LocationProgressType.EXCLUDED
                loc.access_rule = chapter_completion_rule(self.player, locks)
            elif data.goal:
                loc.access_rule = chapter_completion_rule(self.player, locks)
            elif data.group == "story":
                # A travel key grants access to the map, not the story event spawning
                # the boss: also require the story to reach the battle event's window
                # (boss_events.json), e.g. Metatron's second Armlock visit.
                loc.access_rule = story_reaches_progress(data.story_progress, self.player, locks)
            else:
                # Optional and raid fights keep their region's first touch: the access audit
                # opens chests early, never an unaudited encounter.
                first = REGION_TABLE[data.region].story_progress
                if first is not None and first > (region_access[data.region] or 0):
                    loc.access_rule = chest_access_rule(
                        self.player, data.region, first, None, locks,
                        key_active=region_keys_on and data.region in active_key_regions)
            region.locations.append(loc)

        def region_check_rule(region_id: str, gate: "int | None"):
            # Guild missions, recruitment and the early partner keep their region's first
            # touch: the access audit opens chests early, never these (docs/ACCESS_AUDIT.md).
            first = REGION_TABLE[region_id].story_progress
            if first is not None and first > (region_access[region_id] or 0):
                return chest_access_rule(self.player, region_id, max(first, gate or 0), gate, locks,
                                         key_active=region_keys_on and region_id in active_key_regions)
            return chest_story_gate_rule(gate, self.player, locks)

        for name, data in self._active_guild_mission_locations():
            region = story_regions[data.region]
            loc = SO2RLocation(self.player, name, data.address, region)
            loc.access_rule = region_check_rule(data.region, data.story_progress_required)
            region.locations.append(loc)

        for source, reward in self.recruitment_rewards.items():
            site = RECRUITMENT_SITES[source]
            name = f"Recruitment: {CHARACTERS[source].label}"
            region = story_regions[site['RegionId']]
            loc = SO2RLocation(self.player, name, RECRUITMENT_LOCATION_IDS[name], region)
            loc.access_rule = region_check_rule(site['RegionId'], site['StoryProgressRequired'])
            loc.item_rule = lambda item, owner=self.player, expected=reward.name: item.player == owner and item.name == expected
            # Fixed local placement: general/multiworld fill cannot replace a character reward.
            loc.place_locked_item(self.create_item(reward.name))
            region.locations.append(loc)

        if self.early_partner_reward:
            site = EARLY_PARTNER_SITE
            region = story_regions[site['RegionId']]
            loc = SO2RLocation(self.player, EARLY_PARTNER_LOCATION_NAME,
                               EARLY_PARTNER_LOCATION_ID, region)
            loc.access_rule = region_check_rule(site['RegionId'], site['StoryProgressRequired'])
            loc.item_rule = (lambda item, owner=self.player, expected=self.early_partner_reward.name:
                             item.player == owner and item.name == expected)
            loc.place_locked_item(self.create_item(self.early_partner_reward.name))
            region.locations.append(loc)

        self._create_challenge_mission_regions()
        self._add_key_item_location_rules()

    def _descent_strength_rule(self, floor: int):
        """The party-strength rule of floor `floor`'s guardian (DESIGN_V1.md section 5), or None when it is off or free. It is
        built from the ladders, so it is only available once create_items has run (set_rules)."""
        if not self._descent_strength_on():
            return None
        count = len(self.descent_floors)
        joinable = len(self._character_items())
        chars = descent.chars_needed(floor, count, joinable)
        weapons = descent.weapons_needed(floor, count, joinable, sum(len(r) for r in self.gear_ladders.values()))
        if not chars and not weapons:
            return None
        player = self.player
        return lambda state: (state.count_group("Characters", player) >= chars
                              and state.count_group("Progressive Weapons", player) >= weapons)

    def _create_descent_regions(self) -> None:
        """Descent (DESIGN_V1.md section 5): Menu -> Floor 1 free, then Floor i -> Floor i+1 needs i Depth Seals (and, with
        descent_party_strength, the strength that beats guardian i, added in set_rules). Floor chests need nothing more; the
        floor's guardian location sits in its region."""
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)
        previous = menu
        self._descent_entrances: Dict[int, object] = {}
        for floor in self.descent_floors:
            region = Region(f"Floor {floor.index}: {floor.dungeon.name}", self.player, self.multiworld)
            self.multiworld.regions.append(region)
            entrance = previous.connect(region, f"{previous.name} -> {region.name}")
            if floor.index > 1:
                needed = floor.index - 1
                entrance.access_rule = lambda state, n=needed, player=self.player: state.count(descent.DEPTH_SEAL_NAME, player) >= n
                self._descent_entrances[floor.index - 1] = entrance
            for flag in sorted(floor.dungeon.chests):
                name = CHEST_NAME_BY_FLAG[flag]
                region.locations.append(SO2RLocation(self.player, name, CHEST_LOCATION_TABLE[name].address, region))
            region.locations.append(SO2RLocation(self.player, descent.guardian_location_name(floor.index),
                                                 floor.location_id, region))
            previous = region

    def _create_open_world_regions(self) -> None:
        """Open world (docs/OPEN_WORLD_PLAN.md §3, §7): the party starts at the hub with the Psynard, so every area is
        entered straight from Menu. Towns are open, a dungeon needs its area key, Phynal (the goal) needs all four Orbs,
        which release the Final Voyage there, and with other_planet: item every area on the other planet also needs
        that planet's key (_open_world_requirements)."""
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)
        regions: Dict[str, Region] = {}

        def area(locality: str) -> Region:
            if locality not in regions:
                region = Region(REGION_TABLE[locality].name, self.player, self.multiworld)
                self.multiworld.regions.append(region)
                entrance = menu.connect(region, f"Menu -> {region.name}")
                needed = self._open_world_requirements(locality)
                if needed:
                    entrance.access_rule = lambda state, items=tuple(needed), player=self.player: state.has_all(items, player)
                regions[locality] = region
            return regions[locality]

        area(OPEN_WORLD_GOAL_ID)
        for name, data in self._active_chest_locations():
            region = area(data.region)
            loc = SO2RLocation(self.player, name, data.address, region)
            if data.flag in WORLD_MAP_NO_PROGRESSION_FLAGS:
                add_item_rule(loc, _no_progression)
            if data.group == "maze":
                # Whether the party can enter the post-game maze at the hub is still a live question
                # (OPEN_WORLD_PLAN.md): its chests may hold equipment and filler, never progression.
                add_item_rule(loc, _no_progression)
            region.locations.append(loc)
        # Boss spots: in logic with their area, like its chests.
        for name, data in self._active_boss_locations():
            region = area(data.region)
            region.locations.append(SO2RLocation(self.player, name, data.address, region))

    def _chest_access(self, data) -> "int | None":
        """A chest's story access point: its audited value, else its region's first touch
        raised to its authored gate (the rule before the audit)."""
        if data.access_progress is not None:
            return data.access_progress
        first = REGION_TABLE[data.region].story_progress
        if first is None:
            return data.story_progress_required
        return max(first, data.story_progress_required or 0)

    def _add_key_item_location_rules(self) -> None:
        """A key item whose scene sits inside a region, before the progress it unlocks,
        also gates what comes after it there: the Idol of the Warrior's scene is what
        lets the Field of Courage Guardian (battle 525) start, and which Field of Courage
        chests lie past the Guardian is not established, so all of them need it."""
        for key in self._active_key_items():
            has_key = lambda state, item=key.name: state.has(item, self.player)
            for name, data in self._active_boss_locations():
                if data.party_id in key.gated_bosses:
                    add_rule(self.get_location(name), has_key)
            for name, data in self._active_chest_locations():
                if data.region in key.gated_regions and not data.postgame:
                    add_rule(self.get_location(name), has_key)

    def _replace_pool_items_with_keys(self, pool: list, keys: list, min_filler: int = 0) -> None:
        """Remove `len(keys)` items from `pool` in place, so the pool stays the same size
        once the key items (region, chapter, key items, characters) are appended
        (docs/APWORLD.md "pool balance"). `keys` only needs a `.name` attribute.

        Phase 1: filler rolls (FILLER_ITEM_NAMES and small resource packs). Phase 2: the
        current most-common consumable (category BATTLE) name still in the pool, ties
        broken by name, repeated until enough are removed; a name is never touched once
        only one instance of it remains. Phase 3 (fallback): the same rule broadened to
        any category. Phase 4: replace the smallest remaining Fol awards if there are too
        few duplicates (eight chapters plus region keys in a chest-only seed). Phase 5: only
        when all of that still falls short (a chest-only seed with region keys and key
        items), replace single filler-class items outside equipment in (category, name)
        order; it never touches equipment or useful items. Unique equipment is always
        preserved.

        `min_filler` is the number of EXCLUDED locations, which only filler may fill. The
        phases first run without taking filler below it (so they reach for duplicate
        useful items instead), and only if that cannot meet the budget run again without
        the floor. Refuse an impossible replacement budget before changing the pool
        instead of silently producing too many items.
        """
        needed = len(keys)
        removed: Set[int] = set()
        filler_names = set(FILLER_ITEM_NAMES) | {pack.name for pack in SMALL_PACKS}

        def is_filler(index: int) -> bool:
            return ITEM_TABLE[pool[index].name].classification == ItemClassification.filler

        def filler_left() -> int:
            return sum(1 for index in range(len(pool)) if index not in removed and is_filler(index))

        def run_phases(floor: int) -> None:
            def allowed(index: int) -> bool:
                return not is_filler(index) or filler_left() > floor

            for index, item in enumerate(pool):
                if len(removed) >= needed:
                    return
                if index not in removed and item.name in filler_names and allowed(index):
                    removed.add(index)

            def _remove_one(category_filter) -> bool:
                counts: Dict[str, int] = {}
                first: Dict[str, int] = {}
                for index, item in enumerate(pool):
                    if index in removed:
                        continue
                    if category_filter is not None and ITEM_TABLE[item.name].category != category_filter:
                        continue
                    counts[item.name] = counts.get(item.name, 0) + 1
                    first.setdefault(item.name, index)
                candidates = [n for n, c in counts.items() if c > 1 and allowed(first[n])]
                if not candidates:
                    return False
                removed.add(first[sorted(candidates, key=lambda n: (-counts[n], n))[0]])
                return True

            while len(removed) < needed:
                if _remove_one("BATTLE"):
                    continue
                if _remove_one(None):
                    continue
                break

            fol_indices = sorted(
                (index for index, item in enumerate(pool)
                 if index not in removed and ITEM_TABLE[item.name].is_fol),
                key=lambda index: (ITEM_TABLE[pool[index].name].fol_amount, index),
            )
            for index in fol_indices:
                if len(removed) >= needed:
                    return
                if allowed(index):
                    removed.add(index)

            singles = sorted(
                (index for index, item in enumerate(pool)
                 if index not in removed and is_filler(index)
                 and ITEM_TABLE[item.name].category not in EQUIPMENT_CATEGORIES),
                key=lambda index: (ITEM_TABLE[pool[index].name].category, pool[index].name, index),
            )
            for index in singles:
                if len(removed) >= needed:
                    return
                if allowed(index):
                    removed.add(index)

        run_phases(min_filler)
        if len(removed) < needed:
            run_phases(0)

        if len(removed) != needed:
            raise ValueError(f"Cannot replace {needed} pool items with progression keys; "
                             f"only {len(removed)} duplicate/filler/Fol items are available.")

        for index in sorted(removed, reverse=True):
            del pool[index]

    def _excluded_location_count(self) -> int:
        return sum(1 for location in self.multiworld.get_locations(self.player)
                   if location.progress_type == LocationProgressType.EXCLUDED)

    def _generated_pool_items(self, key_count: int) -> list:
        """docs/GEAR_POOL.md: one item per free location (locations minus keys), none of them read from a chest."""
        locations = (sum(1 for _ in self._active_chest_locations()) + sum(1 for _ in self._active_boss_locations())
                     + sum(1 for _ in self._active_guild_mission_locations())
                     + sum(1 for _ in self._active_challenge_mission_locations()) + len(getattr(self, "descent_floors", ()))
                     + len(self.objectives))
        share = getattr(self.options, "equipment_share", None)
        packs = self._packs_on()
        extra = {}
        small_weights = [p.weight for p in SMALL_PACKS]
        large_weights = [p.weight for p in LARGE_PACKS]
        if self._descent():
            # No shops: Restorative packs count double and Fol takes a smaller share of the filler.
            small_weights, large_weights = descent.packs_weights(SMALL_PACKS), descent.packs_weights(LARGE_PACKS)
            extra["fol_share"] = descent.FOL_SHARE
        result = gear_pool.build(
            self.random, [character.player_id for character in self.character_roster], locations - key_count,
            share.value if share is not None else 50, progressive_weapon_name, lambda gear: gear.name,
            [p.name for p in SMALL_PACKS] if packs else [], [p.name for p in LARGE_PACKS] if packs else [],
            small_weights, large_weights, FILLER_ITEM_NAMES, fol_item_name,
            progressive=self._progressive_weapons_on(), **extra)
        self.gear_ladders = result.ladders
        names = result.names
        # Excluded locations take filler only: turn the last non-filler, non-progressive-weapon entries into filler.
        shortfall = self._excluded_location_count() - sum(
            1 for name in names if ITEM_TABLE[name].classification == ItemClassification.filler)
        for index in reversed(range(len(names))):
            if shortfall <= 0:
                break
            data = ITEM_TABLE[names[index]]
            if data.classification != ItemClassification.filler and data.category != "PROGRESSIVE_WEAPON":
                names[index] = self._filler_name()
                shortfall -= 1
        return [self.create_item(name) for name in names]

    def create_items(self) -> None:
        region_keys = self._active_region_keys()
        chapter_keys = self._active_chapter_keys()
        key_items = self._active_key_items()
        characters_in_general_pool = ([] if self.recruitment_rewards else
                                      [character for character in self._character_items()
                                       if character != self.early_partner_reward])
        planet_key = self._open_world_planet_key()
        start_area_key = getattr(self, "start_area_key", None)
        if start_area_key is not None:
            self.multiworld.push_precollected(self.create_item(start_area_key.name))
        area_keys = [k for k in self._active_area_keys() if k != start_area_key]
        seals = [DEPTH_SEAL_KEY] * self._descent_seal_count() if self._descent() else []
        all_keys = [*region_keys, *([planet_key] if planet_key else []), *chapter_keys, *key_items,
                    *area_keys, *self._open_world_orbs(), *seals, *characters_in_general_pool]
        if self._generated_pool():
            pool = self._generated_pool_items(len(all_keys))
        else:
            pool = []
            for _name, data in self._active_chest_locations():
                pool.append(self.create_item(self._chest_pool_item(data.vanilla_item_name)))
            for _name, _data in self._active_boss_locations():
                pool.append(self.create_item(self._filler_name()))
            for _name, data in self._active_guild_mission_locations():
                if data.pool_item_kind == "filler":
                    pool.append(self.create_item(self._filler_name()))
                else:
                    pool.append(self.create_item(data.pool_item_name))
            # The game keeps each mission's own reward, so a mission check only adds one filler to the pool.
            for _name, _data in self._active_challenge_mission_locations():
                pool.append(self.create_item(self._filler_name()))
            for _drawn in self.objectives:  # likewise: the objective's reward is the game's, the check holds one filler
                pool.append(self.create_item(self._filler_name()))
            if all_keys:
                # Missable (EXCLUDED) checks take filler only; keep enough of it for them.
                self._replace_pool_items_with_keys(pool, all_keys, min_filler=self._excluded_location_count())
        for key in all_keys:
            pool.append(self.create_item(key.name))

        self._replace_filler_with_traps(pool)
        self.multiworld.itempool += pool

    def _replace_filler_with_traps(self, pool: list) -> None:
        """trap_chance: swap round(n_filler * chance / 100) pure-filler pool items (classification exactly filler,
        never equipment) for traps drawn by trap_weights. Replaces in place, so the pool size is unchanged. Does
        nothing (and draws no randomness) with chance 0 or when every weight is 0."""
        chance = self.options.trap_chance.value
        weights = {name: w for name, w in self.options.trap_weights.value.items() if name in TRAP_NAMES and w > 0}
        if chance <= 0 or not weights:
            return
        candidates = [i for i, item in enumerate(pool)
                      if item.classification == ItemClassification.filler
                      and ITEM_TABLE[item.name].category not in EQUIPMENT_CATEGORIES]
        count = round(len(candidates) * chance / 100)
        if count <= 0:
            return
        names = sorted(weights)
        for index in self.random.sample(candidates, count):
            pool[index] = self.create_item(self.random.choices(names, weights=[weights[n] for n in names])[0])

    def set_rules(self) -> None:
        if self.early_partner_reward:
            remaining_character_items = {character.name for character in self._character_items()
                                         if character != self.early_partner_reward}
            # Character rewards in this mode are local (set in generate_early) and may
            # only fill normal chest checks. Compose rather than replace any future rule.
            for location in self.multiworld.get_locations(self.player):
                if location.name not in CHEST_LOCATION_TABLE:
                    add_item_rule(location, lambda item, owner=self.player,
                                  names=remaining_character_items:
                                  item.player != owner or item.name not in names)
        # The generator models access to the final fight; the plugin reports the
        # actual victory. A Phynal travel key bypasses region access only, so require
        # chapter completion separately. This also works when boss locations are off.
        if self._descent():
            self._set_descent_rules()
            return
        phynal_region_name = REGION_TABLE["MF_0048"].name
        if self._open_world():
            # Phynal's entrance needs all four Orbs; the final boss is fought there.
            if self._objective_goal() != objectives.GOAL_ORBS:
                # goal: objectives / orbs_and_objectives: the required objectives also gate the Final Voyage (the Orbs
                # too, for orbs_and_objectives, through _open_world_requirements). Pure item predicates only.
                add_rule(self.multiworld.get_entrance(f"Menu -> {phynal_region_name}", self.player),
                         self._objectives_done_rule())
            if self.objectives_auto_win:
                # Objectives Auto-Win: the required objectives alone win the seed (pure item predicates, so no indirect
                # conditions). The Phynal entrance above still follows `goal`; the win no longer needs it.
                self.multiworld.completion_condition[self.player] = self._objectives_done_rule()
                return
            self.multiworld.completion_condition[self.player] = (
                lambda state: state.can_reach_region(phynal_region_name, self.player))
            return
        chapters_complete = chapter_completion_rule(self.player, self._story_locks())
        self.multiworld.completion_condition[self.player] = (
            lambda state: chapters_complete(state) and state.can_reach_region(phynal_region_name, self.player)
        )

    def _set_descent_rules(self) -> None:
        """Guardian i needs its party strength; the portal out of floor i needs the same (you beat the guardian to use it)
        on top of the seals set in create_regions. The goal is the last floor's guardian."""
        for floor in self.descent_floors:
            rule = self._descent_strength_rule(floor.index)
            if rule is None:
                continue
            add_rule(self.get_location(descent.guardian_location_name(floor.index)), rule)
            if not floor.goal:
                add_rule(self._descent_entrances[floor.index], rule)
        goal = descent.guardian_location_name(len(self.descent_floors))
        self.multiworld.completion_condition[self.player] = lambda state: state.can_reach_location(goal, self.player)

    def _chest_requirements(self) -> Dict[int, List[frozenset]]:
        """For every active chest, keyed by chest flag: the item-name sets that put it in
        logic (any one suffices), mirroring create_regions' rules. A region is reached by
        its story (every story lock up to its progress) or, with its travel key, by the key
        plus the story up to its window/barrier; a chest adds its own story gate and any
        key-item gate. Post-game chests need the goal ({CHEST_LOGIC_GOAL}). Open world: a dungeon chest needs its
        area key, a Phynal chest all four Orbs, a town chest nothing, plus the other planet's key on that planet."""
        if self._descent():
            return {}  # needs counts (floor i: i - 1 seals), which the Guide Map counter's item sets cannot express
        if self._open_world():
            return {data.flag: [frozenset(self._open_world_requirements(data.region))]
                    for _name, data in self._active_chest_locations()}
        locks = self._story_locks()
        key_regions = {k.region for k in self._active_region_keys()}
        gated: Dict[str, Set[str]] = {}
        for key in self._active_key_items():
            for region in key.gated_regions:
                gated.setdefault(region, set()).add(key.name)

        def story(progress) -> frozenset:
            if progress is None:
                return frozenset()
            return frozenset(name for name, unlocks in locks if unlocks <= progress)

        result: Dict[int, List[frozenset]] = {}
        for _name, data in self._active_chest_locations():
            if data.postgame:
                result[data.flag] = [frozenset({CHEST_LOGIC_GOAL})]
                continue
            # Region and chest together: the story reaches the chest's access point, or the
            # travel key (with its window/barrier) plus the chest's authored gate.
            alternatives = [story(self._chest_access(data))]
            if data.region in key_regions:
                key = REGION_KEY_BY_REGION[data.region]
                thresholds = [p for p in (key.available_from, key.barrier_progress) if p is not None]
                alternatives.append(frozenset({key.name}) | story(max(thresholds) if thresholds else None)
                                    | story(data.story_progress_required))
            extra = frozenset(gated.get(data.region, ()))
            alternatives = {alt | extra for alt in alternatives}
            result[data.flag] = sorted((alt for alt in alternatives
                                        if not any(other < alt for other in alternatives)),
                                       key=lambda alt: (len(alt), sorted(map(str, alt))))
        return result

    def _chest_logic_slot_data(self) -> dict:
        """Compact slot_data.chest_logic for the Guide Map counter: distinct requirement
        sets as AP item ids (CHEST_LOGIC_GOAL for the goal), and each chest flag's list of
        alternative set indices."""
        requirements: List[List[int]] = []
        index: Dict[tuple, int] = {}
        chests: Dict[str, List[int]] = {}
        for flag, alternatives in sorted(self._chest_requirements().items()):
            refs = []
            for alt in alternatives:
                ids = tuple(sorted(item if item == CHEST_LOGIC_GOAL else ITEM_TABLE[item].code for item in alt))
                if ids not in index:
                    index[ids] = len(requirements)
                    requirements.append(list(ids))
                refs.append(index[ids])
            chests[str(flag)] = refs
        return {"version": 1, "requirements": requirements, "chests": chests}

    def _scaling_slot_data(self) -> dict:
        """slot_data.scaling version 1: the plugin rescales enemies to a world level computed from this
        player's own progress (docs/WORLD_SCALING_PLAN.md §3)."""
        o = self.options
        return {
            "version": 1,
            "mode": o.enemy_scaling.current_key,
            "world_level": {"source": o.world_level_source.current_key, "start": o.world_level_start.value,
                            "per_step": o.world_level_per_step.value / 10, "max": o.world_level_max.value},
            "above": o.scaling_above.value,
            "below": o.scaling_below.value,
            "boss_offset": o.scaling_boss_offset.value,
            "scale_bosses": bool(o.scale_bosses.value),
            "scale_final_battles": bool(o.scale_final_battles.value),
            "scale_superbosses": bool(o.scale_superbosses.value),
        }

    def _loot_rolls(self) -> Dict[str, dict]:
        """Loot tiers (loot.py), rolled once after fill and shared by slot data and the spoiler."""
        if getattr(self, "_loot_cache", None) is None:
            self._loot_cache = loot.roll(self.multiworld, self.player, self.random,
                                         dict(self.options.loot_tier_weights.value),
                                         bool(self.options.loot_tier_scaling.value), self._cursed_weight(),
                                         self._descent_boosted() if self._descent() else None)
        return self._loot_cache

    def _cursed_weight(self) -> Optional[int]:
        """The Cursed tier weight, or None when Cursed Loot is off or Loot Tiers is off (then nothing is Cursed)."""
        if not self.options.cursed_loot.value:
            return None
        if not self.options.loot_tiers.value:
            return None
        return int(self.options.cursed_loot_weight.value)

    def _loot_bonuses(self) -> Dict[str, list]:
        """Bonus equipment effects for the tiered gear (loot.roll_bonus_effects), rolled once after the tiers."""
        if getattr(self, "_bonus_cache", None) is None:
            self._bonus_cache = loot.roll_bonus_effects(self.multiworld, self.player, self.random, self._loot_rolls(),
                                                        bool(self.options.loot_tier_scaling.value),
                                                        bool(self.options.loot_bonus_effects.value),
                                                        self._stats_on(), self._signature_on())
        return self._bonus_cache

    def _stats_on(self) -> bool:
        """Loot Stat Bonuses is active only with Loot Tiers and Loot Bonus Effects on too."""
        return bool(self.options.loot_tiers.value and self.options.loot_bonus_effects.value
                    and self.options.loot_stat_bonuses.value)

    def _signature_on(self) -> bool:
        """Unique Signature Effects is active only with Loot Tiers and Loot Bonus Effects on too."""
        return bool(self.options.loot_tiers.value and self.options.loot_bonus_effects.value
                    and self.options.loot_signature_effects.value)

    def _bonuses_on(self) -> bool:
        """Slot data carries a bonuses block with Loot Bonus Effects or Cursed Loot (which needs Loot Tiers)."""
        return bool(self.options.loot_bonus_effects.value) or self._cursed_weight() is not None

    def write_spoiler(self, spoiler_handle) -> None:
        if self.objectives:
            spoiler_handle.write(f"\n\nObjectives ({self.objectives_required} of {len(self.objectives)} required, "
                                 f"goal {self._objective_goal()}{', auto-win' if self.objectives_auto_win else ''}) - "
                                 f"{self.multiworld.get_player_name(self.player)}:\n")
            for drawn in self.objectives:
                spoiler_handle.write(f"[{objectives.TIER_NAMES[drawn.tier]}] {drawn.text} ({drawn.row.id}"
                                     f"{', NP' if drawn.row.no_progression else ''})"
                                     f"{' - ' + drawn.how if drawn.how else ''}\n")
        if self._descent():
            spoiler_handle.write(f"\n\nDescent floors ({self.multiworld.get_player_name(self.player)}):\n")
            for line in descent.spoiler_lines(self.descent_floors):
                spoiler_handle.write(line + "\n")
        if not self.options.loot_tiers.value:
            return
        rolls = self._loot_rolls()
        bonuses = self._loot_bonuses() if self._bonuses_on() else {}
        spoiler_handle.write(f"\n\nLoot tiers ({self.multiworld.get_player_name(self.player)}):\n")
        if not rolls:
            spoiler_handle.write("(none)\n")
        for location in loot.candidates(self.multiworld, self.player):
            row = rolls.get(f"{location.player}:{location.address}")
            if row is not None:
                cursed = row["tier"] == loot.CURSED_TIER
                pairs = bonuses.get(f"{location.player}:{location.address}", [])
                extra = "".join(f" + {loot.format_bonus(effect, value, cursed)}" for effect, value in pairs)
                name = loot.loot_name(location.item.name, row["tier"], row["factor"], pairs)
                spoiler_handle.write(f"{location.name} ({self.multiworld.get_player_name(location.player)}): "
                                     f"{location.item.name} - {row['tier']} \"{name}\", "
                                     f"{loot.FACTOR_BY_ID[row['factor']]['name']}{extra}\n")

    def fill_slot_data(self) -> dict:
        slot = self._slot_data()
        if self.options.loot_tiers.value:
            slot["loot"] = loot.slot_data(self._loot_rolls(), self._loot_bonuses() if self._bonuses_on() else None,
                                          self._cursed_weight() is not None)
        feat_duel = bool(self.options.feat_duel_rewards.value)
        feat_chain = bool(self.options.feat_chain_rewards.value)
        drops_on = bool(self.options.monster_drops.value)
        if feat_duel or feat_chain:
            slot["feats"] = {"version": 1, "duel_rank_a": feat_duel, "chain5_flawless": feat_chain}
        if self.options.death_link.value:
            # docs/DEATHLINK.md: only with the option, so every other seed's slot data is unchanged. Needs plugin 0.92.0+;
            # older plugins ignore both keys.
            slot["death_link"] = True
            slot["death_link_amnesty"] = int(self.options.death_link_amnesty.value)
        if self.options.phynal_doors_open.value:
            # docs/PHYNAL_DOORS.md: only when on (the default); needs plugin 0.93.0+, older plugins ignore the key.
            slot["phynal_doors_open"] = True
        if drops_on or feat_duel or feat_chain:  # feats need the table even with random drops off
            slot["drops"] = drops.slot_data(self.options.monster_drop_chance.value,
                                            self.options.monster_drop_chain_bonus.value,
                                            bool(self.options.monster_drop_bosses.value),
                                            dict(self.options.loot_tier_weights.value),
                                            self.options, bool(self.options.loot_bonus_effects.value), enabled=drops_on,
                                            cursed_weight=self._cursed_weight() if self.options.loot_tiers.value else None,
                                            stat_bonuses=self._stats_on(), signature=self._signature_on())
        return slot

    def _slot_data(self) -> dict:
        # Story mode: empty unless region_keys is on (_active_region_keys()). Open world: only the other planet's key
        # with other_planet: item; the plugin applies it like any region key.
        planet_key = self._open_world_planet_key()
        region_keys_data: Dict[str, dict] = {
            str(key.item_id): {
                "region": key.region,
                "name": key.region_name,
                "fast_travel_id": key.fast_travel_id,
                "fieldmap": key.fieldmap,
            }
            for key in [*self._active_region_keys(), *([planet_key] if planet_key else [])]
        }
        # slot_data.chapter_keys is the plugin's story-lock map (ChapterLockPlanner): any
        # item id -> the scenario events refused until it arrives. Key items join it under
        # their own game-item ids, so the lock needs no plugin change; story_keys then
        # lets the plugin deliver them as the real inventory item.
        chapter_keys_data: Dict[str, dict] = {}
        for key in self._active_chapter_keys():
            chapter_keys_data[str(key.item_id)] = {
                "name": key.label,
                "events": key.events,
                "unlocks_progress": key.unlocks_progress,
            }
        key_items = self._active_key_items()
        for key in key_items:
            chapter_keys_data[str(key.item_id)] = {
                "name": key.name,
                "events": key.events,
                "unlocks_progress": key.unlocks_progress,
            }
        # Open world §7.4: each Orb holds the Final Voyage talk. ChapterLockPlanner keeps an event locked while any
        # key listing it is missing, so the talk opens only with all four.
        orbs = self._open_world_orbs()
        orb_events = [] if self._objective_goal() == objectives.GOAL_OBJECTIVES else [FINAL_VOYAGE_EVENT]
        for orb in orbs:
            chapter_keys_data[str(orb.item_id)] = {
                "name": orb.name,
                "events": orb_events,
                "unlocks_progress": FINAL_VOYAGE_NEXT_PROGRESS,
            }
        delivered = [*key_items, *orbs]
        open_world = self._open_world()
        slot = {
            "mapping_version": (OPEN_WORLD_GEAR_MAPPING_VERSION if self._generated_pool() else
                                OPEN_WORLD_MAPPING_VERSION) if open_world else (
                                RESOURCE_PACK_MAPPING_VERSION if self._packs_on() else
                                STORY_KEY_MAPPING_VERSION if key_items else
                                RECRUITMENT_MAPPING_VERSION if self.recruitment_rewards else
                                EARLY_PARTNER_MAPPING_VERSION if self.early_partner_reward else
                                CHARACTER_MAPPING_VERSION if self.character_roster else MAPPING_VERSION),
            "game_mode": self.options.game_mode.current_key,
            "open_world": None if not open_world else {
                "version": 1,
                "hub_progress": HUB_PROGRESS,
                "start_planet": self.start_planet,
                # One arrival destination per planet (§7.1): the cross-world page reaches a planet through it.
                "start_destinations": dict(START_DESTINATIONS),
                # Released (and visited) by the new game: the start planet's only with other_planet: item, whose key
                # (region_keys) releases the other; both with other_planet: open. Absent in older rooms = both.
                "released_at_start": sorted(START_DESTINATIONS[planet] for planet in PLANETS
                                            if planet != self._other_planet()),
                # Boss spots (boss_checks): the plugin asks to start each fight at its scene's trigger (plugin 0.60.0);
                # a win is the ordinary boss check, location 5_600_000 + party.
                # Dungeon -> the entrance FastTravel row its area key also opens (plugin 0.70.0).
                "dungeon_travel": {locality: row for locality, row in DUNGEON_TRAVEL.items()
                                   if locality in {k.locality for k in self._active_area_keys()}},
                "boss_spots": [{"party_id": spot.party_id, "name": spot.name, "map": spot.map, "event": spot.event}
                               for spot in self._open_world_boss_spots()],                # Area -> the item ids that must all be held before its entrances open (the dungeon lock).
                "area_locks": {**{k.locality: [k.item_id] for k in self._active_area_keys()},
                               # goal: objectives drops the Phynal entry (an empty list is malformed); the gate replaces it.
                               **({} if self._objective_goal() == objectives.GOAL_OBJECTIVES
                                  else {OPEN_WORLD_GOAL_ID: sorted(orb.item_id for orb in orbs)})},
                "goal": "four_orbs",
            },
            "recruitment_checks": (slot_contract(self.recruitment_rewards) if self.recruitment_rewards else
                                   early_partner_slot_contract(self.early_partner_reward)
                                   if self.early_partner_reward else None),
            "goal_parties": GOAL_PARTY_IDS,
            # Effective values: open world's only bosses are its boss spots, and it has no guild missions.
            "boss_checks": int(bool(self.options.boss_checks.value) and (not open_world or bool(self._open_world_boss_spots()))),
            "optional_bosses": int(bool(self.options.optional_bosses.value) and not open_world),
            "raid_bosses": int(bool(self.options.raid_bosses.value) and not open_world),
            "maze_chests": int(self.options.maze_chests.value),
            "world_map_chests": int(self.options.world_map_chests.value),
            "guild_missions": int(bool(self.options.guild_missions.value) and not open_world),
            "route": self.options.route.current_key,
            "recruitment_bosses": self.options.recruitment_bosses.current_key,
            "characters": None if not self.character_roster else {
                "version": 1,
                "mode": "randomized",
                "starter": self.character_roster[0].player_id,
                "roster": sorted(character.player_id for character in self.character_roster),
                "items": {str(character.item_id): {"player_id": character.player_id, "name": character.label}
                          for character in self._character_items()},
            },
            "region_keys": region_keys_data,
            "chapter_keys": chapter_keys_data,
            "story_keys": ({"version": 1, "item_ids": sorted(k.native_id for k in delivered)}
                           if delivered else None),
            # docs/GEAR_POOL.md: each roster character's Progressive Weapon ladder (game item ids, weakest first); the
            # plugin grants the n-th rung for the n-th copy received (AP item 5_860_000 + player id).
            "gear": None if not self._generated_pool() else {
                "version": 1,
                "progressive_weapons": {str(player_id): {"item": progressive_weapon_code(player_id), "rungs": rungs}
                                        for player_id, rungs in sorted(self.gear_ladders.items())},
            },
            # Every pack is listed, not only pooled ones: AP can ask for filler later.
            "resource_packs": ({str(p.item_id): {"name": p.name, "contents": [list(c) for c in p.contents]}
                                for p in RESOURCE_PACKS} if self._packs_on() else None),
            # Which unopened chests are in logic, for the plugin's Guide Map counter.
            "chest_logic": self._chest_logic_slot_data(),
            # World scaling (docs/WORLD_SCALING_PLAN.md): presentation only, no logic effect.
            "scaling": self._scaling_slot_data(),
            # Battle EXP/BP/SP/Fol multipliers in percent, applied by plugin 0.66.1+ (older plugins ignore them).
            "rewards": self._rewards_slot_data(),
            # Equipment effects that stack across equipped items, applied by plugin 0.73.0+ (older plugins ignore it).
            "equipment": self._equipment_slot_data(),
            # Skill-level rebalance for late joiners (docs/SKILL_LEVELS.md); only with characters as items.
            "skill_levels": ({"version": 1, "anchor": 85}
                             if self.character_roster and self.options.rebalance_skill_levels.value
                             else None),
            "progression": {
                "region_keys": int(bool(self._active_region_keys())),
                "chapter_keys": int(bool(self._active_chapter_keys())),
                "key_items": int(bool(key_items)),
                "area_keys": int(bool(self._active_area_keys())),
                "resource_packs": int(self._packs_on()),
            },
        }
        if self._descent():
            # docs/descent/DESIGN_V1.md section 6. Challenge missions, boss checks and every town or world-map check
            # do not exist here, so their effective values are off whatever the YAML says.
            slot["mapping_version"] = descent.DESCENT_MAPPING_VERSION
            slot["goal_parties"] = [self.descent_floors[-1].guardian.party_id]
            for key in ("boss_checks", "optional_bosses", "raid_bosses", "maze_chests", "world_map_chests", "guild_missions"):
                slot[key] = 0
            slot["descent"] = descent.slot_data(self.descent_floors, bool(self.options.descent_heal_on_descent.value))
        if self._challenge_missions_on():
            # docs/MISSIONS.md section 9. Only present with the option, so every other seed's slot data is unchanged.
            slot["mapping_version"] += CHALLENGE_MISSION_MAPPING_SUFFIX
            slot["progression"]["challenge_missions"] = 1
            slot["challenge_missions"] = {
                "version": 1,
                "location_base": CHALLENGE_MISSION_LOCATION_ID_BASE,
                "missions": {str(data.mission_id): {"location": data.address, "tier": data.tier}
                             for _name, data in self._active_challenge_mission_locations()},
            }
        if self.objectives:
            # docs/OBJECTIVES_V1.md section 5. Only with drawn objectives, so every other seed's slot data is unchanged.
            slot["mapping_version"] += objectives.OBJECTIVE_MAPPING_SUFFIX
            slot["progression"]["objectives"] = 1
            goal = self._objective_goal()
            slot["objectives"] = {
                "version": 1,
                "location_base": objectives.OBJECTIVE_LOCATION_ID_BASE,
                "goal": goal,
                "required": self.objectives_required,
                "gate": (None if goal == objectives.GOAL_ORBS
                         else {"event": FINAL_VOYAGE_EVENT, "area": OPEN_WORLD_GOAL_ID}),
                "drawn": [{"id": drawn.row.id, "location": drawn.row.address, "tier": drawn.tier,
                           "family": drawn.row.family, "kind": drawn.row.kind, "params": self._objective_params(drawn),
                           "text": drawn.text, "no_progression": drawn.row.no_progression}
                          for drawn in self.objectives],
            }
            if self.objectives_auto_win:
                slot["objectives"]["auto_win"] = True  # only when on: the block is otherwise unchanged
        return slot
