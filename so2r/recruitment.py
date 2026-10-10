"""Recruitment-check generation. Only locally verified encounters can ship in seeds."""
import hashlib
import json

from .characters import CHARACTERS, shuffle_recruitment_rewards
from .resources import read_text

RECRUITMENT_LOCATION_BASE = 5_950_000
RECRUITMENT_MAPPING_VERSION = 'so2r-ids-v1-recruitment-v1'
_TEXT = read_text('recruitment_checks.json')
CATALOG_SHA256 = hashlib.sha256(_TEXT.encode('utf-8')).hexdigest()
_CATALOG = json.loads(_TEXT)
if _CATALOG['Version'] != 1:
    raise ValueError('Unsupported recruitment catalog')
RECRUITMENT_SITES = {s['SourcePlayerId']: s for s in _CATALOG['Sites']}
if len(RECRUITMENT_SITES) != 7 or len(_CATALOG['Sites']) != 7:
    raise ValueError('Recruitment catalog must contain seven unique sites')
LOCATION_IDS = {f'Recruitment: {CHARACTERS[pid].label}': RECRUITMENT_LOCATION_BASE + pid
                for pid in RECRUITMENT_SITES}


def require_ready(route, sites=None):
    sites = RECRUITMENT_SITES if sites is None else sites
    if route not in ('claude', 'rena') or set(sites) != set(RECRUITMENT_SITES):
        raise ValueError('Invalid recruitment route/site set')
    unresolved = []
    for pid, site in sites.items():
        triggers = [t for t in site['Triggers'] if t['Route'] == route]
        if (route not in site['VerifiedRoutes'] or not site['RegionId']
                or not isinstance(site['StoryProgressRequired'], int)
                or site['StoryProgressRequired'] < 0 or not triggers
                or any(not t['Map'] or not t['Event'] or t['MinProgress'] < 0
                       or t['MaxProgress'] < t['MinProgress'] for t in triggers)):
            unresolved.append(CHARACTERS[pid].label)
    if unresolved:
        raise ValueError('Recruitment checks are not ready for playable seeds; verify native events '
                         'and roster-independent access for: ' + ', '.join(unresolved))


def prepare_rewards(random, roster, route):
    require_ready(route)
    return shuffle_recruitment_rewards(random, list(RECRUITMENT_SITES), roster)


def slot_contract(rewards):
    return {'version': 1, 'catalog_sha256': CATALOG_SHA256,
            'placements': {str(RECRUITMENT_LOCATION_BASE + pid):
                           {'source_player_id': pid, 'reward_item_id': reward.item_id}
                           for pid, reward in sorted(rewards.items())}}
