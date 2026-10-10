"""The single verified early-partner recruitment reward.

This intentionally does not share the seven-site recruitment-check readiness gate:
only Rena's Claude-route encounter has the required live verification.
"""
import hashlib
import json

from .characters import CHARACTERS, CharacterData
from .resources import read_text

EARLY_PARTNER_SOURCE_PLAYER_ID = 2
EARLY_PARTNER_LOCATION_ID = 5_950_002
EARLY_PARTNER_LOCATION_NAME = "Recruitment: Rena"
EARLY_PARTNER_MAPPING_VERSION = "so2r-ids-v1-early-partner-v1"

_TEXT = read_text("early_partner.json")
CATALOG_SHA256 = hashlib.sha256(_TEXT.encode("utf-8")).hexdigest()
_CATALOG = json.loads(_TEXT)
if _CATALOG.get("Version") != 1:
    raise ValueError("Unsupported early-partner catalog")

_SITES = [site for site in _CATALOG.get("Sites", [])
          if site.get("SourcePlayerId") == EARLY_PARTNER_SOURCE_PLAYER_ID]
if len(_SITES) != 1:
    raise ValueError("Early-partner catalog must contain exactly one Rena source")
EARLY_PARTNER_SITE = _SITES[0]


def require_ready(route: str, site: dict | None = None) -> None:
    """Refuse all routes other than the one independently live-verified encounter."""
    site = EARLY_PARTNER_SITE if site is None else site
    triggers = [trigger for trigger in site.get("Triggers", []) if trigger.get("Route") == route]
    if (route != "claude"
            or site.get("SourcePlayerId") != EARLY_PARTNER_SOURCE_PLAYER_ID
            or site.get("RegionId") != "MF_0003"
            or site.get("StoryProgressRequired") != 800_000
            or route not in site.get("VerifiedRoutes", [])
            or len(triggers) != 1
            or not triggers[0].get("Map")
            or not triggers[0].get("Event")
            or not isinstance(triggers[0].get("MinProgress"), int)
            or not isinstance(triggers[0].get("MaxProgress"), int)
            or triggers[0]["MinProgress"] < 0
            or triggers[0]["MaxProgress"] < triggers[0]["MinProgress"]):
        raise ValueError("Early-partner recruitment is only ready for the verified Claude-route Rena encounter")


def prepare_reward(random, roster: list[CharacterData], route: str) -> CharacterData:
    """Pick a seeded, distinct recruit from the seven non-starter character items."""
    require_ready(route)
    roster_ids = [character.player_id for character in roster]
    if (len(roster_ids) != 8 or len(set(roster_ids)) != 8
            or any(type(player_id) is not int or player_id not in CHARACTERS for player_id in roster_ids)):
        raise ValueError("Early-partner recruitment requires one starter plus seven distinct characters")
    candidates = [character for character in roster[1:]
                  if character.player_id != EARLY_PARTNER_SOURCE_PLAYER_ID]
    if not candidates:
        raise ValueError("Early-partner recruitment has no distinct reward candidate")
    return random.choice(sorted(candidates, key=lambda character: character.player_id))


def slot_contract(reward: CharacterData) -> dict:
    return {
        "version": 2,
        "mode": "early_partner",
        "catalog_sha256": CATALOG_SHA256,
        "placements": {
            str(EARLY_PARTNER_LOCATION_ID): {
                "source_player_id": EARLY_PARTNER_SOURCE_PLAYER_ID,
                "reward_item_id": reward.item_id,
            },
        },
    }
