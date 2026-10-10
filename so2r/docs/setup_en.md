# Star Ocean: The Second Story R -- Setup Guide

This integration is a BepInEx 6 IL2CPP plugin for the Steam release of STAR OCEAN THE
SECOND STORY R. It is still an early prototype: read "Limitations" below before you
start.

## Requirements

- STAR OCEAN THE SECOND STORY R on Steam, build 20267265.
- BepInEx 6 IL2CPP already installed for that build (the plugin repo's
  `tools/Install-Loader.ps1`; this is a one-time setup step, already done if you were
  handed a working install).
- The SO2R-AP plugin itself (`SO2R.DebugTools.dll`, `SO2R.ModApi.dll`,
  `SO2R.Archipelago.dll` in `BepInEx/plugins/SO2R-AP`), deployed by the plugin repo's
  `tools/Deploy-Plugin.ps1` -- see the plugin repo's `docs/SETUP.md` if you need to build
  and deploy it yourself. Version 0.19.0 or later is required; it is the first build
  that understands this world's item and location ids.
- This `.apworld` (or the `apworld/so2r` source) placed where your generator/launcher
  expects worlds, to generate a seed.

## One-time: enable the Archipelago features

Close the game, then edit `BepInEx/config/local.so2r.ap.debugtools.cfg` and set the
following to `true` under `[Archipelago]`:

```ini
Archipelago.EnableSaveIsolation
Archipelago.EnableSession
Archipelago.EnableItemApplication
Archipelago.EnableBossChecks
Archipelago.EnableChestChecks
```

Seeds with `resource_packs` on (the default) need **plugin 0.45.0**; an older plugin
refuses them at connection instead of losing the packs.

If your seed uses the `region_keys`, `chapter_keys` or `key_items` options (see
"Generating a seed" below), also enable the matching gates; `key_items` needs
`EnableChapterLocks` (it holds each key item's scene) and plugin 0.44.0 or later:

```ini
Archipelago.EnableRegionKeys
Archipelago.EnableChapterLocks
```

Since plugin 0.23.0 a single `Archipelago.EnableRandomizer = true` line turns on the whole
gameplay set at once (it never enables the debug mutation switches or the hold-to-run
feature). If you prefer, set the individual gates listed above instead -- each one lists
its own prerequisite in the config
file's own description text, and none of them do anything until the ones they depend on
are also on.

Experimental character seeds require **plugin 0.40.0** and the separate
`EnableCharacterItems = true` entry under `[Archipelago]`. The master switch does
not enable it. Start a fresh isolated game; do not copy a previous save into this
seed. Character mode has passed offline checks but still needs in-game acceptance.

Every one of these defaults to `false`; the plugin never mutates game state until you
turn them on, and switching back to normal (vanilla) saves at the title screen returns
you to ordinary play regardless of these settings. **Back up your save folder** before
your first session with item application enabled, the same way you would before trying
any other game mod.

## Generating a seed

Use the Archipelago website or your local generator with `apworld/so2r` installed as a
world. The options that matter for this game:

- `route` (`claude` or `rena`, default `claude`): **must match the story protagonist
  you pick at New Game**, even when your playable starter is randomized. The current
  plugin warns about a mismatch; character mutations refuse a mismatched route.
- `character_items` (default off, experimental): chooses eight distinct permanent
  characters from all thirteen, including Claude and Rena. One starts in your party;
  the other seven arrive as AP items. Normally incompatible recruits are allowed.
  Requires `recruitment_bosses: none` and the explicit runtime gate described above.
- `starting_character` (default `seed_random`): chooses the starter randomly, or use
  a lowercase character name to pin it. Only used with `character_items`.
- `joinable_characters` (default 3, range 1-7): how many characters can join besides
  your starter, i.e. the character items in the pool. Early partner and recruitment
  checks always use all 7. Needs plugin 0.69.0+.
- `early_characters` (default 1, range 0-3): how many of your character items are
  guaranteed in your own sphere 1, the checks you can reach from the start. Used in
  open world, and with `character_items` unless early partner or recruitment checks
  already place the characters.
- `boss_checks` (default on): story boss fights are locations.
- `optional_bosses`, `raid_bosses` (default off): add the optional superbosses/Dias duel
  and the ten raid-variant bosses (post-game only) as locations.
- `maze_chests` (default off): adds the post-game Maze of Tribulations chests.
- `world_map_chests` (default off): adds the 50 EXPEL and 20 NEDE world-map terrain
  chests. Leave this off for now: terrain/access requirements are awaiting a dedicated
  audit. Town and dungeon chests remain in the shuffle either way. In open world, a
  Nede start always includes the 20 Nede chests (reachable on foot from the start).
- `game_mode: open_world`: each dungeon needs its "Area Key"; the key also opens that
  dungeon's Guide Map point, so on the still-locked other planet (`other_planet: item`)
  the area key alone is enough, except the Maze of Tribulations, which also needs the
  planet's town key. Needs plugin 0.70.0+.
- `recruitment_bosses` (`none`, `opera_and_ernest`, or `ashton`, default `none`): which
  recruitment-quest boss fights, if any, are included.
- `region_keys` (default off): adds "Fast Travel: (region name)" items that release and
  reveal a fast-travel destination ahead of the story when you receive them.
- `chapter_keys` (default off): adds "Chapter Key: (name)" items that gate a specific
  story beat until you receive them (see "What to expect in play" below).
- `exp_multiplier`, `bp_multiplier`, `sp_multiplier`, `fol_multiplier` (default 300
  each, range 10-1000): the EXP, BP, SP and Fol every won battle gives, in percent
  (300 = 3x, 100 = the game's own amount). Needs plugin 0.66.1+.
- `orb_bonus` (default 200, range 100-1000, Open World only): once you hold all four Orbs, the four
  multipliers above are multiplied by this, in percent (200 = double: a 500% EXP seed then gives 1000%).
  Arena prizes too. 100 turns it off. Needs plugin 0.71.0+.

Equipment (needs plugin 0.73.0+; older plugins ignore these). In the base game most
equipment effects only count the best equipped item; these make chosen effects add up:

- `stack_extra_attacks` (default on): extra-attack effects add together, up to `extra_attack_cap`.
- `extra_attack_cap` (default 6, range 1-10): the most extra attacks stacking can give one character.
- `stack_regeneration` (default on): HP and MP regeneration effects add together.
- `stack_spell_power` (default on): spell damage % effects add together.
- `stack_cost_cuts` (default on): MP cost, cast time and escape time cuts add together (each capped at 90%).
- `stack_damage_cuts` (default off): damage taken and damage reflect effects add together
  (capped at 80% and 75%). Can make a party very sturdy.

See the game page (`en_Star Ocean The Second Story R.md`) for what is and is not
randomized, and the plugin repo's `docs/APWORLD.md` for the full id scheme and design
notes.

## Connecting from the title menu

1. Launch the game from Steam and let the title screen load.
2. Start your Archipelago server, or join the room you were given.
3. From the title screen, open the **Archipelago** entry (added by the plugin, just
   above Quit). Fill in the server host, port, your slot name, an optional password, and
   the secure-WebSocket (TLS) toggle -- turn TLS **off** for a local/LAN room, since most
   locally hosted rooms are plaintext; leave it on for a room that specifically offers a
   secure address. D-pad/left stick and a controller's confirm/cancel buttons work if you
   are using a gamepad; the keyboard also works, and mouse clicks move focus too.
4. Select **Connect**. A successful connection authenticates you and switches to
   **Archipelago saves** for that exact seed/slot combination (see "What 'Archipelago
   saves' means" below).

## What "Archipelago saves" means

The plugin keeps your Archipelago progress in a save directory that is completely
separate from your normal Steam saves, one directory per seed+slot combination. This
means:

- Connecting to a new seed for the first time starts you with **no saves** in that
  directory -- you begin a New Game for that seed, same as starting the base game fresh.
- Reconnecting to a seed/slot you have already played reuses the same saves; nothing is
  lost between sessions.
- Your normal (vanilla) Steam saves are never touched, read, or overwritten by any of
  this. They remain exactly where and how they were before you ever connected.
- Selecting **Disconnect** on the connection form returns you to your normal saves
  immediately. You can reconnect to the same seed later and your Archipelago saves will
  still be there.

The title screen always shows which save set is currently selected (vanilla or
Archipelago) so you can tell at a glance.

## What to expect in play

- **Notices.** A small gold-bordered "Archipelago" notice appears in the top-right
  corner whenever you receive and apply an item, with a caption describing what
  happened (item received, check sent, item held for later, region unlocked, chapter
  unlocked). Bundled items show a count ("Blueberries x3") and Fol shows its amount
  ("5000 Fol").
- **Chests.** Opening a chest the connected room lists as a location sends that check to
  the server and gives you whatever item the multiworld placed there instead of the
  chest's normal reward. A chest the room does not list (or one excluded from this
  seed's options -- see the game page) opens normally with its vanilla reward and sends
  no check.
- **Bosses.** Winning a story boss fight the room lists as a location sends that check
  automatically; nothing else needs to happen. Re-fighting an already-checked boss (if
  the fight is repeatable) sends nothing new.
- **Received items.** Items other players send you are applied automatically once it is
  safe to do so (not mid-battle or mid-cutscene); anything that cannot be applied yet is
  held and retried automatically, with its own notice caption.
- **Characters** (experimental). The starter replaces the opening playable party
  at the first stable, saveable field; the story choice remains Claude or Rena.
  Character receipts recruit when safe, up to eight permanent members. Temporary
  story guests can still appear. Duplicate receipts do not call native recruitment
  again. A character operation with an uncertain result pauses for review instead
  of retrying; the inspector reports its audit and reason.
- **Region keys** (only if your seed's `region_keys` option is on). Receiving a
  "Fast Travel: (region name)" item immediately releases and reveals that destination on the
  in-game **Guide Map**, so you can travel there right away even if the story has not
  led you there yet. This never removes the ordinary story route to that region; it only
  adds an early option.
- **Chapter locks** (only if your seed's `chapter_keys` option is on). A small number of
  specific story conversations wait for a "Chapter Key: (name)" item before they will
  fire -- the NPC involved gives an ordinary waiting line instead, exactly as if the
  story's own pacing had not reached that point yet. Once the matching chapter key
  arrives (typically from a chest or boss check elsewhere in the seed), the conversation
  runs normally the next time you approach it. This is the only way this integration
  changes story pacing; everything else about the game's story is untouched.

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

## Loot tiers

The "Loot" option group makes the gear you receive roll a rarity tier, Diablo-style. Off by default. Needs plugin 0.77.0+;
an older plugin gives plain gear. Re-Creation Gems and crafting work as before.

- `loot_tiers` (default off): your own weapons, armor and accessories, wherever in the multiworld they are found, roll a tier when the seed is generated. Normal: no modifier (white). Magic: one common modifier (blue). Rare: one rare modifier (yellow). Unique: a fixed signature modifier on a hand-picked famous piece (orange).
- `loot_tier_weights` (default Normal 40, Magic 35, Rare 20, Unique 5): relative weights, 0 or more. If all four are 0 everything is Normal. Unique only applies to the twenty or so hand-picked unique items (about a 1-in-3 chance when one appears, since their Unique weight counts ten times); other gear's Unique share goes to Rare. Unique weight 0 means no Uniques.
- `loot_tier_scaling` (default on): the later a check sits in the seed's progression, the better the odds. Rare and Unique weights are multiplied by 0.5 (first sphere) up to 2.0 (last sphere), Normal by 1.5 down to 0.5, Magic is unchanged.
- `loot_bonus_effects` (default on, needs plugin 0.79.0+): Rare gear rolls 1 bonus equipment effect and Unique gear 2, on top of the modifier. The pool is extra attacks, HP/MP regeneration, MP from spell damage, MP cost cut, casting-time cut, spell damage (all, water, flare, wind), damage taken cut and damage reflect, each limited to what fits the slot. Values grow with how late the check sits (x0.7 early, x1.0 middle, x1.25 late; extra attacks are never scaled). Magic gear gets none. Monster drops roll the same bonuses. The rolled bonuses are in the spoiler log under "Loot tiers". Customizing an item removes its bonuses.

A modifier always fits the item: weapons get weapon modifiers, armor armor modifiers, accessories accessory modifiers. The rolled modifiers are in the spoiler log under "Loot tiers".

## Progressive Weapons and Monster Drops

- `progressive_weapons` (default on, in the "Chest and Mission Options" group): each roster character's 4 Progressive Weapons are in the pool. Off: there are none, and their slots become filler and resource packs (traps can still replace filler through `trap_chance`). Only the generated item pool (Open World with `item_pool: generated`) has Progressive Weapons; in every other setup this option does nothing.

The "Monster Drops" group, off by default, needs plugin 0.78.0+. Won battles can drop a piece of equipment for someone in your current party. Drops are made by the game client, are not Archipelago items and never count as checks. Good with `progressive_weapons` off for a smoother power curve.

- `monster_drops` (default off): turns drops on. The drop is scaled to your world level (stronger gear as the world level rises), and rolls a loot tier and modifier with the `loot_tier_weights` (it works without `loot_tiers`).
- `monster_drop_chance` (default 15): percent chance a won battle drops equipment.
- `monster_drop_chain_bonus` (default 5): extra percent for each additional chained battle.
- `monster_drop_bosses` (default on): boss fights always drop, with better odds.

## Feats

The "Feats" group needs plugin 0.80.0+ and only matters in Archipelago saves. Each feat pays out a guaranteed local drop (not an Archipelago item, never a check). Both work with `monster_drops` off: the seed still carries the drop table, but no random drops happen.

- `feat_duel_rewards` (default on): each character's first win at arena duel rank A (Fun City) also drops a guaranteed Unique that character can wear, or a top-band Rare if no listed Unique fits them. Only rank A pays out.
- `feat_chain_rewards` (default on): winning a chain of 5+ battles with nobody knocked out drops a guaranteed Rare, one power band up. Every time.

## Goal

Defeating the final boss (Gabriel with Feria, or Gabriel, whichever your route reaches)
reports your slot as goaled automatically; no manual confirmation is required.

## Limitations

- **Route must match the story choice.** Choose the route specified by the seed at
  New Game. A randomized starter does not change the story route.
- **Character mode remains experimental.** Native starter replacement, guest handling
  and scripted party changes still need live coverage. Use a fresh isolated test
  seed; New Game Plus is unsupported. Specialties are not AP unlock items yet.
- **Offline play only keeps chapter locks while the seed's saves are selected.** Chapter
  locks (and the rest of the Archipelago-specific behavior) are computed from the
  connected room's data and your local received-item ledger; they only apply while you
  are on that seed's Archipelago saves with the relevant gates on. Loading a vanilla save,
  or a different seed's saves, behaves exactly like ordinary vanilla play with no story
  gating at all -- there is nothing to carry over.
- This is a v1 chest-and-boss shuffle with no location logic: every location is reachable
  from the very start of the game as far as Archipelago is concerned (region keys and
  chapter keys, when enabled, add access/pacing on top of this, they do not remove any).
  See the game page for the current scope.
- Deferred items received during battle or an event normally retry when safe.
  Uncertain native character operations remain paused until their audit is reviewed.

## Troubleshooting

- **Plugin log.** Check `BepInEx/LogOutput.log` (or `BepInEx/LogOutput.txt`) in your game
  folder for plugin messages, including `[SO2R-AP] Plugin loaded. Runtime inspector
  <version>.` at startup and any warnings/errors from the Archipelago session.
- **Inspecting live state.** If you (or whoever is helping you troubleshoot) have the
  plugin repo checked out, `tools/Send-DebugCommand.ps1 -Command archipelago-ui` prints a
  read-only snapshot of the connection form and session state (never your password),
  including the current save-selection label, item/region-key/chapter-lock counters, and
  any connection error. For example:

  ```powershell
  ./tools/Send-DebugCommand.ps1 -GamePath 'C:\path\to\STAR OCEAN THE SECOND STORY R' -Command archipelago-ui
  ```

  This requires the game to be running with the plugin loaded; it does not open, close,
  or change anything by itself.
- **Connection fails immediately with a secure-connection error.** Turn the TLS toggle
  off if you are connecting to a local or LAN room; most locally hosted rooms are
  plaintext and a TLS attempt against one fails safely with its own clear message rather
  than retrying forever.
- **Names show as "Unknown item"/"Unknown location" in the server's own room log.** This
  is a server-side data package issue (the room was not generated with `apworld/so2r`
  available to the server), not a client-side problem; report it to whoever is hosting
  the room.
