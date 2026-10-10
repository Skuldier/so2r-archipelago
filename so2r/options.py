from dataclasses import dataclass

from Options import (Choice, DeathLink, DefaultOnToggle, OptionCounter, OptionGroup, OptionList, PerGameCommonOptions, Range,
                     Toggle)

from .descent import MAX_FLOORS, MIN_FLOORS, MODIFIER_DEFAULT_WEIGHTS, MODIFIER_NAMES
from .items import TRAP_NAMES
from .loot import LOOT_TIER_NAMES
from .objectives import SLOT_KEYS as OBJECTIVE_SLOT_KEYS, TIER_NAMES as OBJECTIVE_TIER_NAMES


class GameMode(Choice):
    """story: play the story in order; chapter keys, key items and fast-travel keys pace it.

    open_world: Worlds Collide / Jets of Time style. A new game jumps to the story's most open point, the Final Voyage hold, with the starting planet
    and the Psynard available from the start (the other planet opens by other_planet). Towns are open; each dungeon needs its "Area Key" (15 keys, 16 with
    maze_chests); the key also opens the dungeon's Guide Map point, so on the locked planet it alone is enough (not for the maze). The four Orbs open the Final Voyage to Phynal, and beating the final boss there is the goal.
    Checks are the town and dungeon chests that exist at that point of the story (196, or 296 with maze_chests),
    (plus Nede's 20 world-map chests on a Nede start), plus 18 story-boss spots with boss_checks. Characters are always items in this mode. Chapter keys, key items,
    fast-travel keys, guild missions, optional and raid bosses, and recruitment checks do not apply.

    descent: a roguelike run through a row of dungeons (docs/descent/DESIGN_V1.md). You start alone on floor 1, a dungeon; its chests are the
    checks. At the dungeon's boss spot a guardian from a depth-appropriate pool waits; beating it (a check) opens a portal to the next floor
    once you hold enough Progressive Depth Seals (the portal out of floor N needs N of them). Characters and gear arrive as items, there are no
    towns, and floors may carry a seed-fixed modifier. Beating the last floor's guardian is the goal. Enemy scaling is promoted to full, the
    final guardian is scaled, and resource packs are forced on. Needs a plugin with Descent support."""
    display_name = "Game Mode"
    option_story = 0
    option_open_world = 1
    option_descent = 2
    default = 0


class StartingPlanet(Choice):
    """open_world only: the planet you start on (seed_random picks one). How the other planet opens is
    other_planet."""
    display_name = "Starting Planet"
    option_seed_random = 0
    option_expel = 1
    option_nede = 2
    default = 0


class OtherPlanet(Choice):
    """open_world only: how the planet you did not start on opens.

    item: only the starting planet is open at first. The other planet's starting town is an item ("Fast Travel:
    Arlia" for Expel, "Fast Travel: L'Aqua" for Nede); when it arrives, that town appears on the Guide Map's
    cross-world page. Its towns and world map need it; a dungeon there needs only its Area Key, which opens the
    dungeon's Guide Map point (the maze keeps needing both). Needs plugin 0.70.0+.

    open: both planets from the start, each starting town already on the Guide Map."""
    display_name = "Other Planet"
    option_item = 0
    option_open = 1
    default = 0


class BossChecks(DefaultOnToggle):
    """Add the story boss fights (Expel and Nede) as checks. Defeating either final
    boss (Gabriel with Feria or Gabriel) is the goal, reported automatically by the
    plugin. If this is off, no boss locations exist at all -- optional_bosses and
    raid_bosses are then ignored."""
    display_name = "Boss Checks"


class OptionalBosses(Toggle):
    """Add the optional/superboss fights (including the Dias duel) as checks.
    Requires boss_checks. The Dias duel is a private action, not part of the main
    story path; it is offered here rather than as an unconditional story check."""
    display_name = "Optional Bosses"


class RaidBosses(Toggle):
    """Add the ten raid-variant boss fights as checks. Requires boss_checks."""
    display_name = "Raid Bosses"


class MazeChests(Toggle):
    """Add the post-game maze (MF_0051_*) chests, including the 3,000,000 Fol chest,
    as checks."""
    display_name = "Maze Chests"


class WorldMapChests(Toggle):
    """Add the EXPEL and NEDE world-map terrain chests. (Open world on a Nede start always includes Nede's.) Disabled by default while
    their terrain and access requirements await a dedicated audit. Town and dungeon
    chests, story bosses, and character checks are unaffected."""
    display_name = "World Map Chests (awaiting access audit)"


class GuildMissions(Toggle):
    """Add the Guild Mission catalog (69 rows minus 12 deferred post-game/character-
    gated rows -- 57 locations) as checks, story-windowed the same way chests are.
    This requires plugin support that does not exist yet (planned 0.31.0+: the plugin
    has no guild mission claim detection or reward suppression today) -- turning this
    on today generates a seed with locations the plugin cannot check. With this off
    (the default), no guild mission locations exist at all."""
    display_name = "Guild Missions"


class ChallengeMissions(Toggle):
    """58 Challenge Missions from the in-game Missions menu become checks, sent when you claim each one's
    reward in the menu. Easier missions are in logic early; harder ones need more of the world unlocked. The
    game's own mission rewards are kept. Needs plugin 0.87.0+."""
    display_name = "Challenge Missions"


class RegionKeys(Toggle):
    """Add one progression item per region ("Fast Travel: <region>") that releases that
    region's fast-travel destination when received, so later regions can be visited
    early. This requires plugin support (0.20.0+) to apply the item in-game and does not
    change the story's own pacing -- the story still advances exactly as before, and
    chests behind an in-region story gate (e.g. Lacuer Castle's tournament sign-up chest)
    still need the story to reach them even with the region's key in hand."""
    display_name = "Fast Travel Region Keys"


class ChapterKeys(Toggle):
    """Locks eight story chapter gates, from the Krosse Castle royal audience through
    the final voyage from L'Aqua, until the matching "Chapter Key" item is received -- the
    story itself does not advance past that point without the key. Requires plugin
    support (0.22.0+) to suppress and grant the underlying scenario event. With this
    off, the story is never locked."""
    display_name = "Story Chapter Keys"


class KeyItems(Toggle):
    """Adds the story's key items to the item pool (16 on Claude's route, 17 on Rena's):
    Rena's Hairpin, Travel Permit, Treasure Map, Mud Shoes, House Key (Rena), Armory
    Contest Badge, ID Card, Rune Code, the four orbs, Idol of the Warrior, Minae Cave Key
    Card, LEA Metal and N.P.I.D. Each one holds the story scene that would normally hand
    it to you until it arrives, so it actually locks what comes after: the Mud Shoes the
    Forest of Symbols, the ID Card Eluria Tower, the orbs the Phynal expedition, and so on.
    Received key items appear in your inventory. Requires plugin 0.44.0+ with
    EnableChapterLocks and EnableItemApplication on. The Rune Code takes over the Four
    Fields chapter key when both options are on."""
    display_name = "Key Items"


class ResourcePacks(DefaultOnToggle):
    """Chests keep only equipment, books (skill guidebooks and symbology books) and Fol;
    every other chest reward -- consumables, cooked dishes, materials, fish, unidentified
    "?" items and curios -- and the boss-check filler become resource packs: Restorative,
    Cooking, Compounding, Smithing, Gemstone, Art and Tool packs, each a bundle of several
    items. A rare item becomes a large pack (useful), a common one a small pack (filler),
    so a filler check still gives something worth having. Requires plugin 0.45.0+; turn
    it off to keep the vanilla chest contents (and to play on an older plugin)."""
    display_name = "Resource Packs"


class TrapChance(Range):
    """Percent of filler items replaced by traps (0 = no traps). Traps are short, harmless setbacks: never lethal,
    never touch key items, equipment or saves. Needs plugin 0.72.0+; older plugins just hold them unused."""
    display_name = "Trap Chance"
    range_start = 0
    range_end = 100
    default = 0


class TrapWeights(OptionCounter):
    """Relative weight of each trap among the traps that replace filler (Trap Chance). A trap with weight 10 is twice
    as likely as one with weight 5; a weight of 0 disables that trap. If every weight is 0 there are no traps, even
    with a Trap Chance above 0. A trap you leave out of the list counts as weight 0, so list all twelve."""
    display_name = "Trap Weights"
    min = 0
    valid_keys = frozenset(TRAP_NAMES)
    default = {name: 1 for name in TRAP_NAMES}


class ItemPool(Choice):
    """open_world only (story mode always keeps the vanilla chest contents).

    generated: the pool ignores what the chests held in the vanilla game. About equipment_share percent of it is
    equipment, and only equipment someone in your roster can use:
      - every roster character gets four "Progressive Weapon: <name>" items; each copy you receive is that character's
        next, stronger weapon;
      - a few individual weapons, armor and accessories are drawn at random, weighted by rarity, with superboss and
        Maze-tier gear as rare jackpots.
    The rest is resource packs and Fol. Requires plugin 0.62.0+.

    vanilla: each chest's own vanilla content, as before (resource_packs still applies)."""
    display_name = "Item Pool"
    option_generated = 0
    option_vanilla = 1
    default = 0


class EquipmentShare(Range):
    """item_pool generated: the percentage of the pool (after keys, Orbs and characters) that is equipment."""
    display_name = "Equipment Share"
    range_start = 20
    range_end = 80
    default = 50


class ProgressiveWeapons(DefaultOnToggle):
    """Each character's 4 Progressive Weapons are in the pool. Off: none; their slots become filler and resource packs
    (good with Monster Drops). Only the generated item pool (Open World, item_pool generated) has them; otherwise this
    does nothing."""
    display_name = "Progressive Weapons"


class CharacterItems(Toggle):
    """Choose a roster from all thirteen characters, ignoring vanilla recruitment
    exclusivity. One starts in the party; Joinable Characters more (default 3) are AP items.
    Requires the experimental character runtime (0.40.0+) and a fresh isolated game.
    Story route is independent of the playable roster. Off preserves vanilla recruitment."""
    display_name = "Characters as Items"


class StartingCharacter(Choice):
    """Starting playable character when Characters as Items is on. The story route
    still follows the protagonist chosen at New Game. Random chooses from all thirteen."""
    display_name = "Starting Character"
    option_seed_random = 0
    option_claude = 1
    option_rena = 2
    option_celine = 3
    option_bowman = 4
    option_dias = 5
    option_precis = 6
    option_ashton = 7
    option_leon = 8
    option_opera = 9
    option_ernest = 10
    option_noel = 11
    option_chisato = 12
    option_welch = 13
    default = 0


class JoinableCharacters(Range):
    """How many characters can join besides your starter: the character items in the pool. Default 3 (a party of
    four). Early Partner Recruitment and Recruitment Checks place characters at fixed story encounters and always
    use all 7. Requires plugin 0.69.0+."""
    display_name = "Joinable Characters"
    range_start = 1
    range_end = 7
    default = 3


class EarlyCharacters(Range):
    """How many of your character items are guaranteed in your own sphere 1: checks you can reach from the start
    with nothing else. They are chosen at random from your roster. 0 leaves characters to the normal fill. Applies
    whenever characters are ordinary items (open world, or Characters as Items without Early Partner Recruitment
    or Recruitment Checks)."""
    display_name = "Early Characters"
    range_start = 0
    range_end = 3
    default = 1


class RebalanceSkillLevels(DefaultOnToggle):
    """With Characters as Items, characters who normally join late (Chisato and Noel at 40,
    Dias at 35, ...) learn their battle skills on a curve pulled back to where they really
    start: everything they would know on joining is known from level 1, and the rest of
    their schedule is stretched from their join level down to level 1. Nothing unlocks later
    than vanilla; Claude and Rena are unchanged. See docs/SKILL_LEVELS.md. Requires plugin
    0.50.0+ with Archipelago.EnableSkillLevelRebalance on; no effect without Characters as Items."""
    display_name = "Rebalance Skill Levels"


class RecruitmentChecks(Toggle):
    """Reserve seven fixed recruitment encounters for this player's seven character
    rewards. Requires character_items and verified native encounters for this route.
    Development mode: generation refuses while encounter/access mapping is incomplete."""
    display_name = "Characters at Recruitment Checks (in development)"


class EarlyPartnerRecruit(Toggle):
    """Place one guaranteed, distinct character at the verified early Rena encounter.
    The other six character rewards remain local chest items. Requires character_items
    and Claude's route; it cannot be combined with the seven-site development mode."""
    display_name = "Early Partner Recruitment (Claude route)"


class Route(Choice):
    """Which protagonist's route this playthrough follows. This must match the
    protagonist actually chosen at New Game; the plugin will validate this against the
    live save in a later version. Claude's route adds the Snow Ogre boss check
    (Forest of Symbols); Rena's route adds the Azam Gille boss check there instead."""
    display_name = "Story Route"
    option_claude = 0
    option_rena = 1
    default = 0


class RecruitmentBosses(Choice):
    """Which recruitment-quest boss fight(s) exist in this playthrough. Ashton's
    recruitment quest excludes Opera's and Ernest's, so only one set can ever exist in
    a single playthrough -- pick the one you intend to recruit. "none" omits all three
    (Fire Lizard x2, Nightmare, Ghost); "opera_and_ernest" adds Fire Lizard x2 (Opera)
    and Ghost (Ernest); "ashton" adds Nightmare (Ashton) only."""
    display_name = "Recruitment Quest Bosses"
    option_none = 0
    option_opera_and_ernest = 1
    option_ashton = 2
    default = 0


class EnemyScaling(Choice):
    """Rescale enemies when a battle starts to a world level that rises with your progress,
    along the game's own growth curves (HP, strength, defence, evasion, and the EXP and Fol
    they give). cap: enemies above the world level (plus a small margin) come down to it,
    while easier areas stay as they are. full: every enemy moves to within a few levels of
    the world level. flat: every enemy fights at the world level. off: vanilla enemies.
    Requires plugin 0.49.0+ with Battle.EnableEnemyScaling on; older plugins ignore it."""
    display_name = "Enemy Scaling"
    option_off = 0
    option_cap = 1
    option_full = 2
    option_flat = 3
    default = 1


class WorldLevelSource(Choice):
    """What raises the world level. characters_bosses: each character received and each
    boss check counts one step. checks: every location checked counts one step. progress:
    the share of your locations checked, from the start level to the maximum."""
    display_name = "World Level Source"
    option_characters_bosses = 0
    option_checks = 1
    option_progress = 2
    default = 0


class WorldLevelStart(Range):
    """The world level before any progress."""
    display_name = "World Level Start"
    range_start = 1
    range_end = 50
    default = 5


class WorldLevelPerStep(Range):
    """World levels gained per step, in tenths (25 = 2.5 levels per character or boss).
    Unused with the progress source."""
    display_name = "World Level per Step (tenths)"
    range_start = 1
    range_end = 100
    default = 25


class WorldLevelMax(Range):
    """The highest the world level goes."""
    display_name = "World Level Maximum"
    range_start = 10
    range_end = 99
    default = 80


class ScalingAbove(Range):
    """How many levels above the world level an enemy may keep."""
    display_name = "Levels Above World Level"
    range_start = 0
    range_end = 20
    default = 3


class ScalingBelow(Range):
    """full: how many levels below the world level an enemy may keep."""
    display_name = "Levels Below World Level"
    range_start = 0
    range_end = 20
    default = 3


class ScalingBossOffset(Range):
    """Bosses see the world this many levels higher, so they stay a step above their area."""
    display_name = "Boss Level Offset"
    range_start = 0
    range_end = 20
    default = 3


class ScaleBosses(DefaultOnToggle):
    """Scale bosses along with ordinary enemies."""
    display_name = "Scale Bosses"


class ScaleFinalBattles(Toggle):
    """Also scale the final battles (they keep their native level by default)."""
    display_name = "Scale Final Battles"


class ScaleSuperbosses(Toggle):
    """Also scale raid bosses and post-game (level 100+) enemies (native by default)."""
    display_name = "Scale Superbosses"


class ExpMultiplier(Range):
    """Multiplies the EXP every won battle gives, in percent: 300 is 3x, 100 is the game's own amount. It stacks
    with enemy scaling's EXP. Requires plugin 0.66.0+ with Battle.EnableRewardMultipliers on (the default); older
    plugins ignore it."""
    display_name = "EXP Multiplier (%)"
    range_start = 10
    range_end = 1000
    default = 300


class BpMultiplier(Range):
    """Multiplies the BP (the points that level up battle skills) every won battle gives, in percent: 300 is 3x,
    100 is the game's own amount. Requires plugin 0.66.1+; older plugins ignore it."""
    display_name = "BP Multiplier (%)"
    range_start = 10
    range_end = 1000
    default = 300


class SpMultiplier(Range):
    """Multiplies the SP (the points that learn and raise skills) every won battle gives, in percent: 300 is 3x,
    100 is the game's own amount. Requires plugin 0.66.1+; older plugins ignore it."""
    display_name = "SP Multiplier (%)"
    range_start = 10
    range_end = 1000
    default = 300


class FolMultiplier(Range):
    """Multiplies the Fol every won battle gives, in percent: 300 is 3x, 100 is the game's own amount. It stacks with
    enemy scaling's Fol. Requires plugin 0.66.1+; older plugins ignore it."""
    display_name = "Fol Multiplier (%)"
    range_start = 10
    range_end = 1000
    default = 300


class OrbBonus(Range):
    """Open world: once all four Orbs are held, the EXP, BP, SP and Fol multipliers above are multiplied by this, in
    percent (200 = double: a 500% EXP seed then gives 1000%). Arena prizes too. 100 turns it off. Needs plugin
    0.71.0+."""
    display_name = "Orb Bonus"
    range_start = 100
    range_end = 1000
    default = 200


class StackExtraAttacks(DefaultOnToggle):
    """Extra-attack effects (Ring of Lightspeed, Meteor Ring, Gale Earring, Cat o' Nine Tails, ...) add together
    instead of only the best one counting, up to Extra Attack Cap. Needs plugin 0.73.0+; older plugins ignore it."""
    display_name = "Stack Extra Attacks"


class ExtraAttackCap(Range):
    """The most extra attacks stacking can give one character."""
    display_name = "Extra Attack Cap"
    range_start = 1
    range_end = 10
    default = 6


class StackRegeneration(DefaultOnToggle):
    """HP and MP regeneration effects add together."""
    display_name = "Stack Regeneration"


class StackSpellPower(DefaultOnToggle):
    """Spell damage % effects add together."""
    display_name = "Stack Spell Power"


class StackCostCuts(DefaultOnToggle):
    """MP cost, cast time and escape time cuts add together (each capped at 90%)."""
    display_name = "Stack Cost Cuts"


class StackDamageCuts(Toggle):
    """Damage taken and damage reflect effects add together (capped at 80% and 75%). Can make a party very sturdy."""
    display_name = "Stack Damage Cuts"


class LootTiers(Toggle):
    """Gear you receive rolls a rarity tier with a crafting modifier, Diablo-style: Normal (none), Magic (a common
    modifier, blue), Rare (a rare modifier, yellow), Unique (a fixed signature modifier, orange). Later checks roll
    better. Needs plugin 0.77.0+; older plugins give plain gear."""
    display_name = "Loot Tiers"


class LootTierWeights(OptionCounter):
    """Relative weight of each tier for a piece of your gear (Loot Tiers). With Loot Tier Scaling the weights shift by
    how late the check sits. A tier with weight 0 never rolls; if all four are 0 everything is Normal. Unique only
    applies to the hand-picked unique items (about a 1-in-3 chance when one appears); other gear's Unique share goes to
    Rare. List all four tiers."""
    display_name = "Loot Tier Weights"
    min = 0
    valid_keys = frozenset(LOOT_TIER_NAMES)
    default = {"Normal": 40, "Magic": 35, "Rare": 20, "Unique": 5}


class LootTierScaling(DefaultOnToggle):
    """Shift the odds toward Rare and Unique the later a check sits in the seed's progression (its sphere in the
    generated logic). Rare and Unique weights are multiplied by 0.5 to 2.0 and Normal by 1.5 down to 0.5, from the
    first sphere to the last; Magic stays as it is."""
    display_name = "Loot Tier Scaling"


class LootBonusEffects(DefaultOnToggle):
    """Rare gear rolls 1 bonus equipment effect and Unique gear 2 (extra attacks, regeneration, spell power, cost/cast-time
    cuts, damage cut/reflect), on top of the modifier. Needs plugin 0.79.0+."""
    display_name = "Loot Bonus Effects"


class LootStatBonuses(DefaultOnToggle):
    """Gear bonuses can also be +% ATK, INT, DEF or Evasion. Magic gear gets one small stat bonus; Rare and Unique gear draw
    their bonus rolls from the effects and these stats. Needs Loot Tiers and Loot Bonus Effects. Needs plugin 0.84.0+; older
    plugins skip stat bonuses."""
    display_name = "Loot Stat Bonuses"


class LootSignatureEffects(DefaultOnToggle):
    """Unique gear also carries one signature weapon effect taken from the game's special weapons: shockwave or star guard on
    hit, combat-skill boosts, instant-cast chance, double element damage, and (rarely) always-critical, HP-based damage or
    auto-revive. Character-specific ones only appear on gear that character can wear. Needs Loot Tiers and Loot Bonus
    Effects. Needs plugin 0.85.0+; older plugins skip them."""
    display_name = "Unique Signature Effects"


class CursedLoot(Toggle):
    """Some of your gear rolls Cursed (red): a rare modifier plus a curse that always comes with a strong upside, e.g. a
    chance to take double damage paired with a big damage cut, random damage taken paired with an extra attack, or Bloody
    Armor's invincibility that drains your HP. Monster drops can be Cursed too. Needs Loot Tiers. Needs plugin 0.82.0+;
    older plugins give a plain Rare item."""
    display_name = "Cursed Loot"


class CursedLootWeight(Range):
    """The Cursed tier's weight next to the Loot Tier Weights (Cursed Loot). It scales with the check's depth like Rare."""
    display_name = "Cursed Loot Weight"
    range_start = 1
    range_end = 100
    default = 8


class MonsterDrops(Toggle):
    """Won battles can drop a piece of equipment for someone in your current party, scaled to your world level, with a
    loot tier and modifier (Loot tier weights apply). Drops are local, not Archipelago items. Needs plugin 0.78.0+."""
    display_name = "Monster Drops"


class MonsterDropChance(Range):
    """Percent chance that a won battle drops equipment (Monster Drops)."""
    display_name = "Monster Drop Chance"
    range_start = 0
    range_end = 100
    default = 15


class MonsterDropChainBonus(Range):
    """Extra percent chance for each additional chained battle (Monster Drops)."""
    display_name = "Monster Drop Chain Bonus"
    range_start = 0
    range_end = 50
    default = 5


class MonsterDropBosses(DefaultOnToggle):
    """Boss fights always drop, with better odds (Monster Drops)."""
    display_name = "Monster Drop Bosses"


class FeatDuelRewards(DefaultOnToggle):
    """Each character's first win at arena duel rank A (Fun City) also drops a guaranteed Unique (or top-band Rare) that
    character can wear. Needs plugin 0.80.0+."""
    display_name = "Feat: Duel Rank A Rewards"


class FeatChainRewards(DefaultOnToggle):
    """Winning a chain of 5+ battles with nobody knocked out drops a guaranteed Rare, one power band up. Every time."""
    display_name = "Feat: Flawless Chain Rewards"


class DescentFloors(Range):
    """descent only: how many dungeons (floors) the run has. Each dungeon appears at most once, drawn across the difficulty tiers (early
    dungeons first, Expel before Nede inside a tier). The pool is 12 dungeons, 13 with descent_unverified_dungeons; more floors than the
    pool has is an error. Seals: floors minus one."""
    display_name = "Descent Floors"
    range_start = MIN_FLOORS
    range_end = MAX_FLOORS
    default = 8


class DescentUnverifiedDungeons(Toggle):
    """descent only: also draw Eluria Tower, a dungeon whose Descent route has not been walked yet (turn-away events, an unconfirmed ID Card
    lock, a scripted fight in its last map). Phynal and the Maze are never floors."""
    display_name = "Descent: Unverified Dungeons"


class DescentModifierChance(Range):
    """descent only: percent of floors 2 to N-1 that roll a modifier (the last floor always rolls one, floor 1 never does). At most one per
    floor, never the same twice in a row. A modifier whose requirement is not met in your seed (see Descent Modifier Weights) is left out."""
    display_name = "Descent: Modifier Chance"
    range_start = 0
    range_end = 100
    default = 60


class DescentModifierWeights(OptionCounter):
    """descent only: relative weight of each floor modifier. Empowered Foes (needs enemy scaling not off), Heavy Boots, Ambush (not on Field
    of Might), Back Attack, Silence, Cursed (needs Loot Tiers and Cursed Loot), Treasure (needs Loot Tiers and a floor with 3+ chests: the
    floor's chests roll better tiers), Bounty (needs Monster Drops), Blessed (double EXP and Fol). A weight of 0 removes a modifier; a
    modifier you leave out of the list counts as 0, so list all nine."""
    display_name = "Descent: Modifier Weights"
    min = 0
    valid_keys = frozenset(MODIFIER_NAMES)
    default = dict(MODIFIER_DEFAULT_WEIGHTS)


class DescentFinalGuardian(Choice):
    """descent only: the last floor's guardian, which is the goal. gabriel: the Gabriel fight of the story's end (scaled to the last floor's
    world level). random_top: one of the strongest guardians instead."""
    display_name = "Descent: Final Guardian"
    option_gabriel = 0
    option_random_top = 1
    default = 0


class DescentHealOnDescent(DefaultOnToggle):
    """descent only: arriving on a new floor restores the whole party's HP and MP and revives the fallen."""
    display_name = "Descent: Heal on Descent"


class DescentPartyStrength(DefaultOnToggle):
    """descent only: a floor's guardian, and the portal after it, are only in logic once you could plausibly have the characters and weapons
    for it: more of your character items and Progressive Weapons the deeper the floor, all of them by the last."""
    display_name = "Descent: Party Strength Logic"


class DeathLinkAmnesty(Range):
    """Death Link only: send one Death Link for every N of your own deaths (1 = every death). Deaths you suffer because of a
    received Death Link never send one. A 10 second cooldown between sends applies whatever this is set to. Needs plugin 0.92.0+."""
    display_name = "Death Link Amnesty"
    range_start = 1
    range_end = 10
    default = 1


class PhynalDoorsOpen(DefaultOnToggle):
    """The final dungeon's colour-switch doors (and its two shortcut doors) start open, so you skip the switch puzzles. Story bosses are unaffected. Needs plugin 0.93.0+."""
    display_name = "Phynal Doors Open"


class ObjectiveCountDrawn(Range):
    """open_world only (ignored, with a warning, in other modes): how many Bucket List objectives are drawn for this seed
    (0 = the feature is off). Each drawn objective is a check ("Objective: Open 40 chests") that completes when you do the
    thing in the game, from the game's own counters. The drawn count is split over Easy, Medium and Hard by
    objective_tier_mix. Needs plugin 0.94.0+ (older plugins refuse the room)."""
    display_name = "Objectives Drawn"
    range_start = 0
    range_end = 12
    default = 0


class ObjectivesRequired(Range):
    """How many of the drawn objectives the goal needs (goal: objectives or orbs_and_objectives). Clamped to the number
    actually drawn."""
    display_name = "Objectives Required"
    range_start = 1
    range_end = 12
    default = 5


class ObjectiveTierMix(OptionCounter):
    """Relative weight of Easy, Medium and Hard among the drawn objectives, apportioned to Objectives Drawn by largest
    remainder (7 drawn with 3/3/1 is exactly three Easy, three Medium, one Hard; 5 drawn gives 2/2/1). A weight of 0 draws
    none of that tier; all three at 0 is an error when objectives are drawn."""
    display_name = "Objective Tier Mix"
    min = 0
    valid_keys = frozenset(OBJECTIVE_TIER_NAMES.values())
    default = {"Easy": 3, "Medium": 3, "Hard": 1}


class Goal(Choice):
    """open_world with drawn objectives only (otherwise this is orbs): how the Final Voyage to Phynal opens.

    orbs: the four Orbs, as always.
    objectives: complete Objectives Required of the drawn objectives. The Orbs stay in the pool but gate nothing. Needs plugin 0.94.0+.
    orbs_and_objectives: both the four Orbs and the required objectives."""
    display_name = "Goal"
    option_orbs = 0
    option_objectives = 1
    option_orbs_and_objectives = 2
    default = 0


class ObjectiveSlots(OptionList):
    """Pick objectives slot by slot, like Jets of Time: each entry is an objective's exact name (e.g. "Defeat 100 enemies") or a category ("Random", "Random Hard", "Random Boss", ...). Only the first <Number of Objectives> entries are used; empty or missing slots are drawn from the tier mix."""
    display_name = "Objectives"
    valid_keys = frozenset(OBJECTIVE_SLOT_KEYS)
    default = ()


class ObjectivesAutoWin(Toggle):
    """Completing the required number of objectives wins the seed immediately — no Final Voyage needed."""
    display_name = "Objectives Auto-Win"


@dataclass
class SO2ROptions(PerGameCommonOptions):
    game_mode: GameMode
    starting_planet: StartingPlanet
    other_planet: OtherPlanet
    boss_checks: BossChecks
    optional_bosses: OptionalBosses
    raid_bosses: RaidBosses
    maze_chests: MazeChests
    world_map_chests: WorldMapChests
    guild_missions: GuildMissions
    challenge_missions: ChallengeMissions
    route: Route
    recruitment_bosses: RecruitmentBosses
    region_keys: RegionKeys
    chapter_keys: ChapterKeys
    key_items: KeyItems
    resource_packs: ResourcePacks
    item_pool: ItemPool
    equipment_share: EquipmentShare
    progressive_weapons: ProgressiveWeapons
    character_items: CharacterItems
    starting_character: StartingCharacter
    joinable_characters: JoinableCharacters
    early_characters: EarlyCharacters
    rebalance_skill_levels: RebalanceSkillLevels
    recruitment_checks: RecruitmentChecks
    early_partner_recruit: EarlyPartnerRecruit
    enemy_scaling: EnemyScaling
    world_level_source: WorldLevelSource
    world_level_start: WorldLevelStart
    world_level_per_step: WorldLevelPerStep
    world_level_max: WorldLevelMax
    scaling_above: ScalingAbove
    scaling_below: ScalingBelow
    scaling_boss_offset: ScalingBossOffset
    scale_bosses: ScaleBosses
    scale_final_battles: ScaleFinalBattles
    scale_superbosses: ScaleSuperbosses
    exp_multiplier: ExpMultiplier
    bp_multiplier: BpMultiplier
    sp_multiplier: SpMultiplier
    fol_multiplier: FolMultiplier
    orb_bonus: OrbBonus
    stack_extra_attacks: StackExtraAttacks
    extra_attack_cap: ExtraAttackCap
    stack_regeneration: StackRegeneration
    stack_spell_power: StackSpellPower
    stack_cost_cuts: StackCostCuts
    stack_damage_cuts: StackDamageCuts
    loot_tiers: LootTiers
    loot_tier_weights: LootTierWeights
    loot_tier_scaling: LootTierScaling
    loot_bonus_effects: LootBonusEffects
    loot_stat_bonuses: LootStatBonuses
    loot_signature_effects: LootSignatureEffects
    cursed_loot: CursedLoot
    cursed_loot_weight: CursedLootWeight
    monster_drops: MonsterDrops
    monster_drop_chance: MonsterDropChance
    monster_drop_chain_bonus: MonsterDropChainBonus
    monster_drop_bosses: MonsterDropBosses
    feat_duel_rewards: FeatDuelRewards
    feat_chain_rewards: FeatChainRewards
    trap_chance: TrapChance
    trap_weights: TrapWeights
    descent_floors: DescentFloors
    descent_unverified_dungeons: DescentUnverifiedDungeons
    descent_modifier_chance: DescentModifierChance
    descent_modifier_weights: DescentModifierWeights
    descent_final_guardian: DescentFinalGuardian
    descent_heal_on_descent: DescentHealOnDescent
    descent_party_strength: DescentPartyStrength
    death_link: DeathLink
    death_link_amnesty: DeathLinkAmnesty
    phynal_doors_open: PhynalDoorsOpen
    objective_count_drawn: ObjectiveCountDrawn
    objectives_required: ObjectivesRequired
    objective_tier_mix: ObjectiveTierMix
    objective_slots: ObjectiveSlots
    objectives_auto_win: ObjectivesAutoWin
    goal: Goal


option_groups = [
    OptionGroup("Game Mode", [GameMode, StartingPlanet, OtherPlanet]),
    OptionGroup("Boss Options", [BossChecks, OptionalBosses, RaidBosses, Route, RecruitmentBosses]),
    OptionGroup("Chest and Mission Options", [MazeChests, WorldMapChests, GuildMissions, ChallengeMissions, ResourcePacks, ItemPool,
                                              EquipmentShare, ProgressiveWeapons]),
    OptionGroup("Logic Options", [RegionKeys, ChapterKeys, KeyItems]),
    OptionGroup("Characters", [CharacterItems, StartingCharacter, JoinableCharacters, EarlyCharacters, RebalanceSkillLevels,
                               RecruitmentChecks, EarlyPartnerRecruit]),
    OptionGroup("Enemy Scaling", [EnemyScaling, WorldLevelSource, WorldLevelStart, WorldLevelPerStep, WorldLevelMax,
                                  ScalingAbove, ScalingBelow, ScalingBossOffset, ScaleBosses, ScaleFinalBattles,
                                  ScaleSuperbosses]),
    OptionGroup("Battle Rewards", [ExpMultiplier, BpMultiplier, SpMultiplier, FolMultiplier,
                                   OrbBonus]),
    OptionGroup("Equipment", [StackExtraAttacks, ExtraAttackCap, StackRegeneration, StackSpellPower, StackCostCuts,
                              StackDamageCuts]),
    OptionGroup("Loot", [LootTiers, LootTierWeights, LootTierScaling, LootBonusEffects, LootStatBonuses, LootSignatureEffects,
                         CursedLoot,
                         CursedLootWeight]),
    OptionGroup("Monster Drops", [MonsterDrops, MonsterDropChance, MonsterDropChainBonus, MonsterDropBosses]),
    OptionGroup("Feats", [FeatDuelRewards, FeatChainRewards]),
    OptionGroup("Traps", [TrapChance, TrapWeights]),
    OptionGroup("Death Link", [DeathLink, DeathLinkAmnesty]),
    OptionGroup("Convenience", [PhynalDoorsOpen]),
    OptionGroup("Objectives", [ObjectiveCountDrawn, ObjectivesRequired, ObjectiveTierMix, ObjectiveSlots, ObjectivesAutoWin, Goal]),
    OptionGroup("Descent", [DescentFloors, DescentUnverifiedDungeons, DescentModifierChance, DescentModifierWeights,
                            DescentFinalGuardian, DescentHealOnDescent, DescentPartyStrength]),
]
