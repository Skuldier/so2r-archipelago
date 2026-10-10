"""Loot tiers (docs/LOOT_TIERS_IDEAS.md section 3): rarity tier and one crafting factor for each piece of this player's
gear, rolled at generation after fill so every location is known.

Tiers: Normal (no factor), Magic (one N factor), Rare (one R factor), Unique (a hand-picked fixed factor, data/uniques.json).
Only listed items can be Unique: an unlisted item's Unique weight (after scaling) is added to Rare, and a listed item's Unique
weight is multiplied by UNIQUE_LISTED_MULTIPLIER (before scaling). A Unique weight of 0 means no Uniques at all. A factor must fit the item's slot: weapon mask 1, armor/shield/helmet/greaves
mask 2, accessory mask 4 (FACTOR rows carry a bit mask, 7 = any slot). Picks use the game's own factor weights.

Scaling (loot_tier_scaling): p = the location's sphere index / the last sphere's index, 0..1 (0.5 without a sphere). The
tier weights are multiplied by
    Normal x (1.5 - p)        Magic x 1        Rare x (0.5 + 1.5 p)        Unique x (0.5 + 1.5 p)
so with the default 40/35/20/5 the first sphere gives about 60/35/10/2.5 and the last 20/35/40/10.

Cursed (world 0.78.0, option cursed_loot): a fifth tier with its own weight (cursed_loot_weight, scaled like Rare), an R factor
and one curse plus one upside from data/cursed_effects.json. In slot data a Cursed key is tier "Rare" (older plugins reject
unknown tier names) and is listed in slot_data["loot"]["cursed"].

Factors 127 (High-grade) and 128 (Masterwork) are crafting-material effects that do nothing when worn; they never roll.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from .characters import CHARACTER_NAMES
from .gear_pool import GEAR_BY_ID
from .items import ARMOR_CATEGORIES, ACCESSORY_CATEGORIES, ITEM_TABLE, WEAPON_CATEGORIES
from .resources import read_json

LOOT_TIER_NAMES: List[str] = ["Normal", "Magic", "Rare", "Unique"]
CURSED_TIER = "Cursed"
SLOT_WEAPON, SLOT_ARMOR, SLOT_ACCESSORY = 1, 2, 4
NEVER_ROLLED = frozenset({127, 128})
NEUTRAL_PROGRESSION = 0.5
SLOT_DATA_VERSION = 1
# A listed item (one in uniques.json) has its Unique weight multiplied by this, so the few Unique-capable pieces actually show
# up: at the default 40/35/20/5 a listed item is Unique 50/145, about 1 in 3, before scaling.
UNIQUE_LISTED_MULTIPLIER = 10

FACTORS: List[dict] = [row for row in read_json("factors.json") if row["id"] not in NEVER_ROLLED]
FACTOR_BY_ID: Dict[int, dict] = {row["id"]: row for row in read_json("factors.json")}
UNIQUES: List[dict] = read_json("uniques.json")
UNIQUE_BY_ITEM: Dict[str, dict] = {row["item"]: row for row in UNIQUES}

# Bonus equipment effects (docs/crafting/EQUIPMENT_EFFECTS.md section 4.4, data/bonus_effects.json): Rare gear rolls 1, Unique 2,
# Magic none. Value = uniform int in the tier's range x a band scale from p, rounded, clamped to [1, cap]. Effect 68 is never
# scaled (the doc: it changes by whole hits).
BONUS_COUNTS: Dict[str, int] = {"Magic": 0, "Rare": 1, "Unique": 2}
BONUS_BAND_SCALE: List[float] = [0.7, 1.0, 1.25]
BONUS_UNSCALED = frozenset({68})
BONUS_PERCENT = frozenset({15, 17, 270, 89, 90, 91, 92, 94, 100})
BONUS_POOL: List[dict] = read_json("bonus_effects.json")["rows"]
BONUS_BY_ID: Dict[int, dict] = {row["effect_id"]: row for row in BONUS_POOL}

# Stat bonuses (world 0.79.0, option loot_stat_bonuses, data/stat_effects.json): +% ATK/INT/DEF/Evasion. Magic gets exactly one;
# Rare and Unique draw their bonus rolls from BONUS_POOL plus these. Rows with roll false (Max HP / Max MP) never roll.
STAT_POOL: List[dict] = [row for row in read_json("stat_effects.json")["rows"] if row["roll"]]
STAT_BY_ID: Dict[int, dict] = {row["effect_id"]: row for row in read_json("stat_effects.json")["rows"]}

# Signature effects (world 0.80.0, option loot_signature_effects, data/signature_effects.json): every Unique piece also carries
# one weapon effect from the game's special weapons, picked by weight. A row with a character only fits gear that character can
# wear. Values are plain randint, never band-scaled. In slot data "character" becomes the equip-mask bit (1 << (PlayerID - 1)).
SIGNATURE_POOL: List[dict] = read_json("signature_effects.json")["rows"]
SIGNATURE_BY_ID: Dict[int, dict] = {row["effect_id"]: row for row in SIGNATURE_POOL}
SIGNATURE_PERCENT = frozenset({241, 242, 244, 267, 274, 251, 246, 271})
SIGNATURE_VALUE_SHOWN = frozenset({248, 164, 161, 153})
_PLAYER_ID_BY_NAME: Dict[str, int] = {name.lower(): pid for pid, name in CHARACTER_NAMES.items()}

# Cursed pool: rows with role self | curse | upside, in table order. Values are plain randint, never band-scaled.
CURSED_POOL: List[dict] = read_json("cursed_effects.json")["rows"]
CURSED_BY_ID: Dict[int, dict] = {row["effect_id"]: row for row in CURSED_POOL}
CURSED_PERCENT = frozenset({103, 94, 89})
CURSED_VALUE_SHOWN = frozenset({172, 103, 94, 89, 68})


def slot_mask(item_name: str) -> int:
    """The equipment mask an item fits: 1 weapon, 2 armor, 4 accessory, 0 when it is not equipment.
    Progressive Weapons are weapons."""
    data = ITEM_TABLE.get(item_name)
    if data is None:
        return 0
    if data.category == "PROGRESSIVE_WEAPON" or data.category in WEAPON_CATEGORIES:
        return SLOT_WEAPON
    if data.category in ARMOR_CATEGORIES:
        return SLOT_ARMOR
    if data.category in ACCESSORY_CATEGORIES:
        return SLOT_ACCESSORY
    return 0


def tier_weights(base: Dict[str, int], progression: Optional[float], cursed: Optional[int] = None) -> List[float]:
    """Weights for LOOT_TIER_NAMES, plus a fifth Cursed weight when cursed (the option's weight) is not None.
    progression None = scaling off."""
    weights = [float(max(0, base.get(name, 0))) for name in LOOT_TIER_NAMES]
    if cursed is not None:
        weights.append(float(max(0, cursed)))
    if progression is not None:
        p = min(1.0, max(0.0, progression))
        weights[0] *= 1.5 - p
        weights[2] *= 0.5 + 1.5 * p
        weights[3] *= 0.5 + 1.5 * p
        if cursed is not None:
            weights[4] *= 0.5 + 1.5 * p
    return weights


def item_weights(base: Dict[str, int], progression: Optional[float], listed: bool, cursed: Optional[int] = None) -> List[float]:
    """Weights for one item. Scaling is applied first. A listed item gets its Unique weight x UNIQUE_LISTED_MULTIPLIER; an
    unlisted item never rolls Unique, its (scaled) Unique weight goes to Rare. Cursed is untouched by the Unique logic."""
    weights = tier_weights(base, progression, cursed)
    if listed:
        weights[3] *= UNIQUE_LISTED_MULTIPLIER
    else:
        weights[2] += weights[3]
        weights[3] = 0.0
    return weights


def _pick_factor(random, mask: int, rarity: str) -> Optional[int]:
    rows = [row for row in FACTORS if row["rarity"] == rarity and row["mask"] & mask]
    if not rows:
        return None
    return random.choices(rows, weights=[row["weight"] for row in rows])[0]["id"]


def roll_item(random, item_name: str, base: Dict[str, int], progression: Optional[float],
              cursed: Optional[int] = None, boost: Optional[float] = None) -> Optional[Tuple[str, int]]:
    """(tier, factor id) for one piece of gear, or None for Normal. cursed = the Cursed weight, None = no Cursed tier.
    boost (Descent's Treasure floors): Rare and Unique weights times it, Normal divided by it; None leaves them alone."""
    mask = slot_mask(item_name)
    unique = UNIQUE_BY_ITEM.get(item_name)
    weights = item_weights(base, progression, unique is not None, cursed)
    if boost is not None:
        weights[0] /= boost
        weights[2] *= boost
        weights[3] *= boost
    if not mask or sum(weights) <= 0:
        return None
    names = LOOT_TIER_NAMES if cursed is None else [*LOOT_TIER_NAMES, CURSED_TIER]
    tier = random.choices(names, weights=weights)[0]
    if tier == "Normal":
        return None
    if tier == "Unique":
        return "Unique", unique["factor"]  # only listed items get a nonzero Unique weight
    factor = _pick_factor(random, mask, "N" if tier == "Magic" else "R")  # Rare and Cursed both take an R factor
    return None if factor is None else (tier, factor)


def progression_fractions(multiworld) -> Dict[object, float]:
    """Location -> sphere index / last sphere index, from one get_spheres() pass cached on the multiworld. Locations
    that are never reached (including the unreachable tail) are absent."""
    cached = getattr(multiworld, "_so2r_loot_spheres", None)
    if cached is None:
        spheres: List[Iterable] = []
        for sphere in multiworld.get_spheres():
            if not sphere:
                break
            spheres.append(sphere)
        last = len(spheres) - 1
        cached = {location: (index / last if last > 0 else NEUTRAL_PROGRESSION)
                  for index, sphere in enumerate(spheres) for location in sphere}
        multiworld._so2r_loot_spheres = cached
    return cached


def candidates(multiworld, player: int) -> List:
    """Every location in the whole multiworld holding one of this player's equipment items, in a stable order."""
    found = [location for location in multiworld.get_filled_locations()
             if location.address is not None and location.item is not None and location.item.player == player
             and slot_mask(location.item.name)]
    return sorted(found, key=lambda loc: (loc.player, loc.address))


def bonus_scale(progression: Optional[float]) -> float:
    """Band scale for sphere fraction p: below 0.34 early, below 0.67 mid, else late. No progression (scaling off) = 1.0."""
    if progression is None:
        return BONUS_BAND_SCALE[1]
    return BONUS_BAND_SCALE[0 if progression < 0.34 else 1 if progression < 0.67 else 2]


def roll_bonuses(random, mask: int, tier: str, progression: Optional[float], stats: bool = False) -> List[List[int]]:
    """[[effect id, value], ...] for one tiered item: BONUS_COUNTS[tier] distinct effects that fit the slot mask. stats True
    (Loot Stat Bonuses): Magic gets one stat, Rare and Unique also draw from STAT_POOL; stats False is the Phase 1 roll."""
    count = BONUS_COUNTS.get(tier, 0)
    eligible = [row for row in BONUS_POOL if row["slot_mask"] & mask]
    scale = bonus_scale(progression)
    if stats:
        fitting = [row for row in STAT_POOL if row["slot_mask"] & mask]
        if tier == "Magic":
            if not fitting:
                return []
            row = random.choice(fitting)
            value = round(random.randint(*row["magic"]) * scale)
            return [[row["effect_id"], max(1, min(row["cap"], value))]]
        eligible = eligible + fitting
    if count <= 0 or not eligible:
        return []
    result: List[List[int]] = []
    for row in random.sample(eligible, min(count, len(eligible))):
        low, high = row["unique" if tier == "Unique" else "rare"]
        value = random.randint(low, high)
        if row["effect_id"] not in BONUS_UNSCALED:
            value = round(value * scale)
        result.append([row["effect_id"], max(1, min(row["cap"], value))])
    return result


def roll_cursed_bonuses(random, mask: int) -> List[List[int]]:
    """[[curse id, value], [upside id, value]] for one Cursed item, or [[172, 12]] for the self-cursed Bloody Armor."""
    fitting = [row for row in CURSED_POOL if row["slot_mask"] & mask]
    first = [row for row in fitting if row["role"] in ("curse", "self")]
    if not first:
        return []
    chosen = random.choices(first, weights=[row["weight"] for row in first])[0]
    picked = [chosen]
    if chosen["role"] == "curse":
        upsides = [row for row in fitting if row["role"] == "upside"]
        if upsides:
            picked.append(random.choices(upsides, weights=[row["weight"] for row in upsides])[0])
    return [[row["effect_id"], random.randint(*row["value"])] for row in picked]


def format_cursed_bonus(effect_id: int, value: int) -> str:
    name = CURSED_BY_ID[effect_id]["name"]
    if effect_id == 172:
        return f"{name} (drains {value} HP)"
    if effect_id not in CURSED_VALUE_SHOWN:
        return name
    return f"{name} +{value}%" if effect_id in CURSED_PERCENT else f"{name} +{value}"


def signature_character_mask(row: dict) -> int:
    """The equip-mask bit of a signature row's character (the encoding of drops.table equip masks), 0 for any."""
    name = row.get("character")
    return 0 if not name else 1 << (_PLAYER_ID_BY_NAME[name.lower()] - 1)


def format_signature(effect_id: int, value: int) -> str:
    name = SIGNATURE_BY_ID[effect_id]["name"]
    if effect_id in SIGNATURE_PERCENT:
        return f"Signature: {name} {value}%"
    if effect_id in SIGNATURE_VALUE_SHOWN:
        return f"Signature: {name} {value}"
    return f"Signature: {name}"


def unique_equip_mask(item_name: str) -> int:
    """The equip mask (which characters can wear it) of a Unique item, 0 when unknown."""
    unique = UNIQUE_BY_ITEM.get(item_name)
    gear = GEAR_BY_ID.get(unique["item_id"]) if unique else None
    return gear.equip if gear else 0


def roll_signature(random, mask: int, equip: int, taken=()) -> Optional[List[int]]:
    """[effect id, value] for one Unique item: a weighted pick among rows that fit the slot mask, are character-free or
    for a character in the equip mask, and are not already among the item's bonus ids (taken). None when nothing fits."""
    rows = [row for row in SIGNATURE_POOL
            if row["slot_mask"] & mask and row["effect_id"] not in taken
            and (not signature_character_mask(row) or signature_character_mask(row) & equip)]
    if not rows:
        return None
    row = random.choices(rows, weights=[row["weight"] for row in rows])[0]
    return [row["effect_id"], random.randint(*row["value"])]


def format_bonus(effect_id: int, value: int, cursed: bool = False) -> str:
    if cursed:
        return format_cursed_bonus(effect_id, value)
    if effect_id in SIGNATURE_BY_ID and effect_id not in BONUS_BY_ID and effect_id not in STAT_BY_ID:
        return format_signature(effect_id, value)
    if effect_id in STAT_BY_ID:
        return f"{STAT_BY_ID[effect_id]['name']} +{value}%"
    name = BONUS_BY_ID[effect_id]["name"]
    if effect_id == 68:
        return f"{value} {name}"
    return f"{name} +{value}%" if effect_id in BONUS_PERCENT else f"{name} +{value}"


_NAME_LIMIT = 36
_CURSE_IDS = frozenset({172, 103, 102})
_LOOT_NAMES: dict = read_json("loot_names.json")


def _is_signature(effect_id: int) -> bool:
    return effect_id in SIGNATURE_BY_ID


def loot_name(item_name: str, tier: str, factor_id: int, bonuses: Iterable) -> str:
    """The generated display name of a tiered item (docs/LOOT_NAMES.md section 1); display-only, never the real item.
    Normal: Item. Magic: Prefix Item (prefix from its stat bonus, else its factor). Rare: Prefix Item Suffix (prefix from the
    factor, suffix from its bonus). Unique: prefix from its first non-signature bonus else its factor, suffix from its signature
    else its second bonus. Cursed: prefix from the curse, suffix from the upside (Bloody has none). A name over 36 characters
    drops the prefix, then the suffix. bonuses is [[effect id, value], ...]."""
    ids = [int(pair[0]) for pair in bonuses]
    effects = _LOOT_NAMES["effects"]
    factor_prefix = _LOOT_NAMES["factors"][str(factor_id)]
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    if tier == "Magic":
        prefix = effects[str(ids[0])][0] if ids else factor_prefix
    elif tier == "Rare":
        prefix = factor_prefix
        suffix = effects[str(ids[0])][1] if ids else None
    elif tier == "Unique":
        plain = [i for i in ids if not _is_signature(i)]
        signatures = [i for i in ids if _is_signature(i)]
        prefix = effects[str(plain[0])][0] if plain else factor_prefix
        if signatures:
            suffix = effects[str(signatures[0])][1]
        elif len(ids) > 1:
            suffix = effects[str(ids[1])][1]
    elif tier == CURSED_TIER:
        curses = [i for i in ids if i in _CURSE_IDS]
        upsides = [i for i in ids if i not in _CURSE_IDS]
        prefix = effects[str(curses[0])][0] if curses else factor_prefix
        if upsides:
            suffix = effects[str(upsides[0])][1]

    def build(use_prefix: bool, use_suffix: bool) -> str:
        parts = [prefix if use_prefix else None, item_name, suffix if use_suffix else None]
        return " ".join(part for part in parts if part)

    name = build(True, True)
    if len(name) > _NAME_LIMIT:
        name = build(False, True)
    if len(name) > _NAME_LIMIT:
        name = build(False, False)
    return name


def roll_bonus_effects(multiworld, player: int, random, rolls: Dict[str, dict], scaling: bool,
                       phase1: bool = True, stats: bool = False, signature: bool = False) -> Dict[str, List[List[int]]]:
    """{"<player>:<address>": [[effect id, value], ...]} for the tiered gear in rolls; keys without a bonus are omitted. A
    separate pass after roll() so the tier rolls are the same with the option on or off. Cursed gear always gets its curse
    pairs (never Phase 1 bonuses or stats); phase1 False (Loot Bonus Effects off) rolls only those. stats True = Loot Stat
    Bonuses (needs phase1). signature True = Unique Signature Effects (needs phase1): a second pass, after every bonus roll,
    appends one signature pair to each Unique key, so the pass is invisible to the random sequence when off."""
    found = candidates(multiworld, player)
    fractions = progression_fractions(multiworld) if scaling and found else {}
    result: Dict[str, List[List[int]]] = {}
    for location in found:
        key = f"{location.player}:{location.address}"
        row = rolls.get(key)
        if row is None:
            continue
        progression = fractions.get(location, NEUTRAL_PROGRESSION) if scaling else None
        if row["tier"] == CURSED_TIER:
            bonuses = roll_cursed_bonuses(random, slot_mask(location.item.name))
        elif phase1:
            bonuses = roll_bonuses(random, slot_mask(location.item.name), row["tier"], progression, stats)
        else:
            continue
        if bonuses:
            result[key] = bonuses
    if signature and phase1:
        for location in found:
            key = f"{location.player}:{location.address}"
            row = rolls.get(key)
            if row is None or row["tier"] != "Unique":
                continue
            pairs = result.setdefault(key, [])
            pick = roll_signature(random, slot_mask(location.item.name), unique_equip_mask(location.item.name),
                                  {pair[0] for pair in pairs})
            if pick is not None:
                pairs.append(pick)
            elif not pairs:
                del result[key]
    return result


def bonus_pool_data() -> List[List[int]]:
    """slot_data["drops"]["bonus_pool"]: [[effect_id, slot_mask, rare_min, rare_max, unique_min, unique_max, cap], ...]."""
    return [[row["effect_id"], row["slot_mask"], *row["rare"], *row["unique"], row["cap"]] for row in BONUS_POOL]


def stat_pool_data() -> List[List[int]]:
    """slot_data["drops"]["stat_pool"]: [[effect_id, slot_mask, magic_min, magic_max, rare_min, rare_max, unique_min, unique_max,
    cap], ...], the roll-true stat rows in table order."""
    return [[row["effect_id"], row["slot_mask"], *row["magic"], *row["rare"], *row["unique"], row["cap"]] for row in STAT_POOL]


def signature_pool_data() -> List[List[int]]:
    """slot_data["drops"]["signature_pool"]: [[effect_id, slot_mask, min, max, weight, character_mask], ...]; character_mask
    0 = any character, else the equip-mask bit of that character."""
    return [[row["effect_id"], row["slot_mask"], *row["value"], row["weight"], signature_character_mask(row)]
            for row in SIGNATURE_POOL]


def cursed_pool_data() -> dict:
    """slot_data["drops"]["cursed"] minus the weight (the caller adds it)."""
    return {"curses": [[row["effect_id"], row["slot_mask"], *row["value"], row["weight"], 1 if row["role"] == "self" else 0]
                       for row in CURSED_POOL if row["role"] in ("curse", "self")],
            "upsides": [[row["effect_id"], row["slot_mask"], *row["value"], row["weight"]]
                        for row in CURSED_POOL if row["role"] == "upside"]}


def roll(multiworld, player: int, random, base: Dict[str, int], scaling: bool, cursed: Optional[int] = None,
         boosted: Optional[Dict[int, float]] = None) -> Dict[str, dict]:
    """{"<player>:<address>": {"factor": int, "tier": str}} for this player's tiered gear (Normal omitted). cursed = the
    Cursed tier weight (Cursed Loot on), None = four tiers exactly as before. boosted = location address -> boost for this
    player's own locations (Descent's Treasure floors); None or an unlisted address rolls as before."""
    found = candidates(multiworld, player)
    fractions = progression_fractions(multiworld) if scaling and found else {}
    result: Dict[str, dict] = {}
    for location in found:
        progression = fractions.get(location, NEUTRAL_PROGRESSION) if scaling else None
        boost = boosted.get(location.address) if boosted and location.player == player else None
        rolled = roll_item(random, location.item.name, base, progression, cursed, boost)
        if rolled is not None:
            result[f"{location.player}:{location.address}"] = {"factor": rolled[1], "tier": rolled[0]}
    return result


def slot_data(rolls: Dict[str, dict], bonuses: Optional[Dict[str, List[List[int]]]] = None, cursed: bool = False) -> dict:
    """cursed True (Cursed Loot on): Cursed keys go out as tier "Rare" and are listed under "cursed"."""
    data = {
        "version": SLOT_DATA_VERSION,
        "factors": {key: row["factor"] for key, row in rolls.items()},
        "tiers": {key: ("Rare" if row["tier"] == CURSED_TIER else row["tier"]) for key, row in rolls.items()},
        "uniques": [[row["item_id"], row["factor"]] for row in UNIQUES],
    }
    if bonuses is not None:  # optional key, only with Loot Bonus Effects or Cursed Loot on; older plugins ignore it
        data["bonuses"] = {key: [list(pair) for pair in pairs] for key, pairs in bonuses.items()}
    if cursed:  # optional key, only with Cursed Loot on
        data["cursed"] = sorted(key for key, row in rolls.items() if row["tier"] == CURSED_TIER)
    return data
