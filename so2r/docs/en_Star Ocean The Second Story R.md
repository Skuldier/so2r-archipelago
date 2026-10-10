# Star Ocean: The Second Story R

## What does randomization do to this game?

This is a chest-and-boss shuffle, with two optional pacing layers on top. Every
treasure chest that would normally give an ordinary inventory item or Fol is instead an
Archipelago location; opening it gives you whatever the multiworld placed there, and
sends your own item to its owner. Story boss fights are also locations by default
(optional superbosses, the Dias duel, and the ten post-game raid-variant bosses are off
by default and can be turned on). With the base options, there is no logic: every
location is reachable from the very start of the game, and the game's own story
progression is untouched. Three options add optional gating on top without removing
anything from the base shuffle: `region_keys` (items that unlock early fast travel to a
region), `chapter_keys` (items that gate a handful of specific story beats) and
`key_items` (the story's own key items, each holding the scene that would hand it over).

Experimental `character_items` mode (plugin 0.40.0, in-game acceptance pending)
also chooses one random starter plus seven AP character items from all thirteen
characters. Claude and Rena are eligible, incompatible recruits are allowed, and
the permanent party cap stays eight. Your chosen story route remains independent
of the playable roster. Character mode needs a fresh isolated save and an explicit
runtime setting; see the setup guide.

## What are the items?

- **Chest contents.** Whatever the vanilla chest would have given -- a weapon, armor,
  accessory, material, cooking ingredient, fish, consumable, unidentified item, or Fol --
  placed for whichever player's world it belongs to. An unidentified item (`?HERB`,
  `?ARMOR`, `?WEAPON`, `?MINERAL`, `?MACHINE`, `?JEWELRY`) still appraises in-game exactly
  as it always did once you identify it; the shuffle only changes which chest holds which
  underlying item id. A chest that would give more than one of the same item (up to ten)
  is sent as a single bundled item ("Blueberries x3").
- **Resource packs** (`resource_packs`, on by default). Chests keep only equipment,
  books (skill guidebooks and symbology books) and Fol. Every other chest reward
  (consumables, dishes, materials, fish, unidentified "?" items) and every boss check's
  filler gives a resource pack instead: a Restorative, Cooking, Compounding, Smithing,
  Gemstone, Art or Tool pack holding several items at once. A rare item's chest gives a
  large pack. If a stack is already full, the rest of the pack still arrives and the notice
  says so.
- **Fol.** Every chest Fol amount (always a multiple of 10, from 250 up to 3,000,000 in
  the post-game dungeon) is its own item kind.
- **Region keys** (`region_keys` option, off by default). "Fast Travel: (region name)"
  items, one per keyable region (40 of them). Receiving one releases and reveals that
  region's primary fast-travel destination immediately, letting you travel there ahead
  of the story. This never removes or replaces the ordinary story route to that region.
- **Characters** (`character_items`, off by default). Seven distinct "Character: Name"
  items recruit the rest of the seed's chosen roster. The starter is supplied by the
  seed and is not also an item. The five characters outside that roster are not
  permanent recruits for the seed. These are useful combat rewards; collecting all
  seven is not an additional goal requirement.
- **Chapter keys** (`chapter_keys` option, off by default). Eight progression items
  from "Chapter Key: Royal Audience" through "Chapter Key: Final Voyage",
  each tied to one specific story scenario event. Receiving
  one lets that story beat run the next time you reach it; without it, the game gives
  its ordinary waiting line instead, exactly as if the story window had not opened yet.
- **Key items** (`key_items` option, off by default). The story's key items: Rena's
  Hairpin, Travel Permit, Treasure Map, Mud Shoes, House Key (Rena's route only), Armory
  Contest Badge, ID Card, Rune Code, the four orbs, Idol of the Warrior, Minae Cave Key
  Card, LEA Metal and N.P.I.D. (16 on Claude's route, 17 on Rena's). Each one holds the
  scene that would normally give it to you until it arrives, so it locks what that scene
  opens: without the Mud Shoes the Marze elder never sends you into the Forest of
  Symbols, without the ID Card Eluria Tower stays shut, and without all four orbs the
  Phynal expedition never leaves. A received key item appears in your inventory. If a
  lock that starts when you enter a map (the Mud Shoes, House Key, orbs, Minae Cave Key
  Card, LEA Metal) is released while you are standing there, leave the map and come back
  in. The Rune Code replaces the Four Fields chapter key when both options are on.

What stays vanilla (never an Archipelago item, always found in its original chest):
key-item chests (the Lyre, the Ancient Text, the Music Editor), the three
character-specific battle-skill chests, and one placeholder chest. See "What is not
randomized?" below for the location side of the same list.

## What are the locations?

- **Chests.** Every chest whose vanilla reward is an ordinary inventory item, an
  unidentified item, or Fol, one location per distinct chest flag (a handful of chests
  share a flag across a world-map pair and count once). Location names read `"<area>
  Chest <flag> (<vanilla content>)"`, so the chest's original content and its stable
  numeric identity are always visible in the name.
- **Bosses.** The story bosses of the game's enemy-party catalog are locations by
  default (`boss_checks`, on by default); the optional superbosses and Dias duel
  (`optional_bosses`) and the ten post-game raid variants (`raid_bosses`) are separate
  options, off by default. Location names read `"Boss: <English name>"`. A few boss
  fights are excluded from ever becoming a location because they cannot be legitimately
  won or checked more than once in the intended way (a scripted flee, an unwinnable
  fight, and a scripted zero-damage fight) -- see the plugin repo's `docs/APWORLD.md`
  "Boss classification" for the exact list.
- **Maze of Tribulations chests** (`maze_chests` option, off by default): the post-game
  dungeon's 103 chests, including the largest single Fol chest in the game.
- **World-map terrain chests** (`world_map_chests` option, off by default): the 50
  EXPEL and 20 NEDE terrain chests. They are withheld until their terrain/access
  requirements have a dedicated audit; town and dungeon chests are unaffected. In open
  world, a Nede start always includes the 20 Nede chests (on foot from the start).
- **Open world area keys**: each dungeon's "Area Key" also opens its Guide Map point, so
  a dungeon on the locked other planet needs only its key (the Maze also needs the
  planet's town key). Needs plugin 0.70.0+.

Two route-dependent story bosses only ever appear as one or the other, matching whether
`route` is `claude` or `rena`; recruitment-quest bosses similarly depend on
`recruitment_bosses`. See the plugin repo's `docs/APWORLD.md` for the exact tables.

## What is the goal?

Defeat the final boss -- Gabriel with Feria, or Gabriel, whichever your route and
options reach. Plugin 0.39.0+ detects either final-boss victory independently of the
boss-check option and reports your slot as goaled; no manual confirmation is required.

## Options

| Option | Default | Effect |
| --- | --- | --- |
| `route` | `claude` | `claude` or `rena`; must match the protagonist chosen at New Game. Gates one route-specific story boss (Snow Ogre vs. Azam Gille); every other location is unaffected. |
| `recruitment_bosses` | `none` | `none`, `opera_and_ernest`, or `ashton`; adds the boss fight(s) tied to that recruitment path (mutually exclusive quest lines, so only one set can ever exist in a playthrough). |
| `boss_checks` | on | Story boss fights are locations. |
| `character_items` | off | Experimental random starter plus seven character items, eight permanent members, all thirteen eligible. Requires plugin 0.40.0, its explicit character gate, a fresh save and `recruitment_bosses: none`. |
| `starting_character` | `seed_random` | Random starter or a lowercase character name; only used with character items. Does not alter the story route. |
| `joinable_characters` | 3 | 1-7 characters who can join besides the starter (the character items in the pool). Early partner and recruitment checks always use 7. Needs plugin 0.69.0+. |
| `early_characters` | 1 | 0-3 character items guaranteed in your own sphere 1 (checks reachable from the start). Not used with early partner or recruitment checks, which place characters themselves. |
| `optional_bosses` | off | Adds the optional superbosses and the Dias duel as locations. |
| `raid_bosses` | off | Adds the ten post-game raid-variant bosses as locations (require the game's own ending flag either way). |
| `maze_chests` | off | Adds the post-game Maze of Tribulations chests as locations. |
| `world_map_chests` | off | Adds EXPEL and NEDE terrain chests. Keep off until the world-map terrain/access audit is complete; it does not affect town or dungeon chests. |
| `region_keys` | off | Adds "Fast Travel: (region)" items that unlock early fast travel; see above. Does not change what is reachable when off. |
| `chapter_keys` | off | Adds "Chapter Key: (name)" items that gate a small number of specific story beats until received; see above. Only meaningful together with `region_keys` and the plugin's chapter-lock feature; changes the goal's completion condition to require reaching the game's final area. |
| `resource_packs` | on | Every chest reward except equipment, books and Fol, plus boss filler, becomes a resource pack; see above. Needs plugin 0.45.0+; turn off for vanilla consumables or an older plugin. |
| `key_items` | off | Adds the story key items as progression items, each holding its own story scene until received; see above. Needs plugin 0.44.0+ with `EnableChapterLocks` and `EnableItemApplication`. |
| `exp_multiplier` | 300 | EXP from every won battle, in percent (300 = 3x, 100 = the game's own; 10-1000). Stacks with enemy scaling. Needs plugin 0.66.1+. |
| `orb_bonus` | 200 | Open World only: once all four Orbs are held, the EXP, BP, SP and Fol multipliers are multiplied by this, in percent (200 = double; 100-1000). Arena prizes too. 100 turns it off. Needs plugin 0.71.0+. |
| `bp_multiplier` | 300 | BP (battle-skill points) from every won battle, in percent (300 = 3x; 10-1000). Needs plugin 0.66.1+. |
| `sp_multiplier` | 300 | SP (skill points) from every won battle, in percent (300 = 3x; 10-1000). Needs plugin 0.66.1+. |
| `fol_multiplier` | 300 | Fol from every won battle, in percent (300 = 3x; 10-1000). Stacks with enemy scaling. Needs plugin 0.66.1+. |
| `orb_bonus` | 200 | Open World only: once all four Orbs are held, the EXP, BP, SP and Fol multipliers are multiplied by this, in percent (200 = double; 100-1000). Arena prizes too. 100 turns it off. Needs plugin 0.71.0+. |

## Equipment

Needs plugin 0.73.0+; older plugins ignore these options. In the base game most equipment
effects only count the best equipped item (Ring of Lightspeed plus Cat o' Nine Tails gives
+2 extra attacks, not +4). These options make chosen effects add together.

| Option | Default | Effect |
| --- | --- | --- |
| `stack_extra_attacks` | on | Extra-attack effects add together, up to `extra_attack_cap`. |
| `extra_attack_cap` | 6 | 1-10. The most extra attacks stacking can give one character. |
| `stack_regeneration` | on | HP and MP regeneration effects add together. |
| `stack_spell_power` | on | Spell damage % effects add together. |
| `stack_cost_cuts` | on | MP cost, cast time and escape time cuts add together (each capped at 90%). |
| `stack_damage_cuts` | off | Damage taken and damage reflect effects add together (capped at 80% and 75%). Can make a party very sturdy. |

## Loot

Needs plugin 0.77.0+; older plugins give plain gear. Gear you receive can roll a rarity tier with one crafting modifier
(the game's "factor"), decided at generation and shown in the spoiler log.

| Option | Default | Effect |
| --- | --- | --- |
| `loot_tiers` | off | Turns the mode on for your own weapons, armor and accessories. Normal (none, white), Magic (a common modifier, blue), Rare (a rare modifier, yellow), Unique (a fixed signature modifier, orange). |
| `loot_tier_weights` | 40/35/20/5 | Weights for Normal, Magic, Rare, Unique. All 0 means everything is Normal. Unique only applies to the hand-picked unique items (about twenty famous SR/SSR pieces; about a 1-in-3 chance when one appears, their Unique weight counts x10); other gear's Unique share goes to Rare. Unique 0 means no Uniques. |
| `loot_tier_scaling` | on | Later checks (by sphere) roll better: Rare and Unique weights x0.5 to x2.0, Normal x1.5 to x0.5, Magic unchanged. |
| `loot_bonus_effects` | on | Rare gear rolls 1 bonus equipment effect and Unique gear 2 (extra attacks, regeneration, spell power, cost/cast-time cuts, damage cut/reflect), on top of the modifier. Needs plugin 0.79.0+. |

The modifier always fits the item's slot (weapon, armor or accessory).

## Progressive Weapons and Monster Drops

`progressive_weapons` (default on) keeps each character's 4 Progressive Weapons in the pool. Off removes them and
their slots become filler and resource packs (traps can still replace filler). It only applies with Open World and
`item_pool: generated`; otherwise it does nothing.

Monster Drops needs plugin 0.78.0+. Won battles can drop a piece of equipment for someone in your current party, scaled
to your world level, with a loot tier and modifier. Drops are local, not Archipelago items.

| Option | Default | Effect |
| --- | --- | --- |
| `monster_drops` | off | Turns drops on. Uses the `loot_tier_weights` whether or not `loot_tiers` is on. |
| `monster_drop_chance` | 15 | 0-100. Percent chance that a won battle drops equipment. |
| `monster_drop_chain_bonus` | 5 | 0-50. Extra percent for each additional chained battle. |
| `monster_drop_bosses` | on | Boss fights always drop, with better odds. |

## Feats

The "Feats" group (needs plugin 0.80.0+) gives guaranteed loot for two achievements. Rewards are local drops, not
Archipelago items, and they only matter in Archipelago saves. Both are on by default and work without `monster_drops`;
the seed then still carries the drop table, but no random drops happen.

| Option | Default | Effect |
| --- | --- | --- |
| `feat_duel_rewards` | on | Each character's first win at arena duel rank A (Fun City) also drops a guaranteed Unique that character can wear, or a top-band Rare if no listed Unique fits them. |
| `feat_chain_rewards` | on | Winning a chain of 5+ battles with nobody knocked out drops a guaranteed Rare, one power band up. Every time. |

## Traps

Two options in the "Traps" group turn some of the pool's filler into trap items. They are short, harmless setbacks: never
lethal, never touching key items, equipment or saves. Needs plugin 0.72.0+; an older plugin just holds them unused.

- `trap_chance` (0-100, default 0): percent of the pure filler items (resource packs and Fol, never equipment) replaced by traps. 0 means no traps.
- `trap_weights`: relative weight of each of the eleven traps (default 1 each). 0 disables a trap; list all eleven, since a missing one counts as 0. If every weight is 0 there are no traps.

| Trap | Effect |
|---|---|
| Ambush Trap | an encounter now |
| Monster Magnet Trap | encounters x3 for 2 min |
| Chain Trap | the next encounter is a 5-battle chain |
| Lost Trap | a warp to a random Guide Map point you have opened |
| Heavy Boots Trap | no running for 60 s |
| Oracle Trap | an Oracle message you must dismiss |
| Muzak Trap | random field music for 3 min |
| Empowered Foes Trap | the next 3 battles' enemies get +5 levels |
| Back Attack Trap | the next battle starts as a back attack |
| Status Trap | the party starts the next battle with a status ailment |
| Fatigue Trap | party HP/MP drop to 50% (never lethal) |

## Known gaps

- **No location logic beyond `region_keys`/`chapter_keys`/`key_items`.** With those options
  off (the default), every chest and boss location is reachable from the very start as
  far as Archipelago is concerned; the multi-hour progression seed described in the
  wider design plan (character/region-gated items) is not implemented yet.
- **Key items need live coverage.** Generation, logic and the room contract are tested;
  holding and releasing each kind of scene in game, and receiving the item into the
  inventory, still need acceptance on a fresh seed. The Energy Stone, Void Matter,
  Ancient Text, Key Card and the Linga herbs stay vanilla (see the plugin repo's
  `docs/KEY_ITEMS.md` for why).
- **Late chapter gates need live coverage.** All eight gates are now generated,
  including the Four Fields, Phynal Expedition, Armlock and Final Voyage. Their native
  locked/unlocked behavior and a complete fresh seed still need acceptance testing.
- **Character mode needs live acceptance.** Offline generation, protocol, persistence
  and party-guard tests pass. Starter replacement, incompatible-party story behavior,
  guest conversion and scripted departures/returns still need in-game coverage.
- **Story-gated chests inside otherwise-open regions.** A small number of chests sit
  behind a scenario-progress requirement inside a region that is itself open from the
  start (for example, one Lacuer Castle chest behind the tournament sign-up area,
  gated to a point past Lacuer Castle's own story arrival). These are marked internally
  but the list is short and may grow as more are audited; consult the plugin repo's
  `docs/APWORLD.md` and `docs/PROGRESSION_DESIGN.md` for the current list and evidence.
- **What stays vanilla, never randomized:** key-item chests (the Lyre, the Ancient
  Text, the Music Editor -- 3 chests), the three character-specific battle-skill chests
  (Leon, Celine, Ashton), one placeholder (`INVALID`) chest, and -- unless `maze_chests`
  is on -- the entire post-game Maze of Tribulations dungeon (103 chests, 18 of which are
  unidentified-item chests). A handful of chests behind a
  bounded scenario window or a scenario flag are included as locations but marked
  `EXCLUDED` progress type, so another player's required progression item, or any
  equipment, is never placed somewhere possibly missable. Post-game checks (maze chests,
  superbosses, raids) never hold progression but can hold equipment.
- **Item classes.** Weapons, armor and accessories are always useful, as are other rare
  (SR/SSR) items; common consumables, materials, unidentified items and Fol are filler.
- **Story route remains fixed.** The current plugin warns about a route mismatch;
  character-mode mutations refuse it. Pick the seed's route at New Game even if its
  randomized starter is a different character.
