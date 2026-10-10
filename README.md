# Star Ocean: The Second Story R — Archipelago world

Source for the [Archipelago](https://archipelago.gg) multiworld randomizer world for
**STAR OCEAN THE SECOND STORY R** (Steam).

- **World version:** 0.87.0
- **Archipelago:** 0.6.8
- **Game name in YAMLs:** `Star Ocean: The Second Story R`

## For hosts

The world lives in the [`so2r/`](so2r) folder. Either:

- **Use the source:** copy the `so2r` folder into your Archipelago install's `worlds/` folder
  (so it becomes `worlds/so2r/`), or
- **Build an .apworld:** zip the `so2r` folder itself (the zip must contain `so2r/` at its top
  level) and rename the zip to `so2r.apworld`, then place it in `custom_worlds/`.

Then generate as usual. Player YAMLs need nothing special beyond the game name above; every
option has a default.

The world's own tests run with Archipelago's test runner:
`python -m unittest worlds.so2r.test` from the Archipelago root.

## For players

Playing needs the SO2R-AP BepInEx plugin for the game, which is distributed separately from
this repository. See [`so2r/docs/setup_en.md`](so2r/docs/setup_en.md) for setup, and
[`so2r/docs/en_Star Ocean The Second Story R.md`](<so2r/docs/en_Star Ocean The Second Story R.md>)
for what the randomizer does.

## Highlights

- Story mode or an open-world mode with area keys and character items.
- Optional loot tiers (Magic / Rare / Unique / Cursed) with bonus effects and generated names,
  monster drops and feats.
- Challenge Missions and Bucket List objectives as checks, with a goal option
  (Orbs, objectives, or both) and Objectives Auto-Win.
- Traps, DeathLink, and convenience options such as open Phynal doors.
