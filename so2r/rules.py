"""Access rules for the region_keys, chapter_keys and key_items options
(docs/PROGRESSION_DESIGN.md §4, docs/KEY_ITEMS.md).

With every option off, every region and location stays reachable from the start
exactly as before (Milestone 8 step 1) -- this module is only consulted when an option
is on.

region_keys (family B): a keyed region is reachable if its key item has been
collected, OR the story has (eventually) reached it on its own linear path
(story_reaches()).

Story locks (chapter_keys, live-verified 2026-09-15, and key_items): each lock is an
item plus the story progress it unlocks. The plugin refuses the lock's scenario event
until the item arrives, so the story cannot pass that chokepoint without it. "The story
reaches progress P" means every lock whose unlocks_progress is at or before P has been
collected. With no locks, story_reaches() stays unconditionally True (no gate exists
in-game to suppress).

The `locks` argument below is either the world's list of (item name, unlocks_progress)
pairs, or, for older callers, a bool: True for the enabled chapter keys, False for none.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Sequence, Tuple, Union

from .items import CHAPTER_KEYS_ENABLED, REGION_KEY_BY_REGION
from .regions import REGION_TABLE

if TYPE_CHECKING:
    from BaseClasses import CollectionState

StateRule = Callable[["CollectionState"], bool]
StoryLock = Tuple[str, int]
Locks = Union[bool, Sequence[StoryLock]]


def chapter_key_locks() -> Tuple[StoryLock, ...]:
    return tuple((key.name, key.unlocks_progress) for key in CHAPTER_KEYS_ENABLED)


def _locks(locks: Locks) -> Tuple[StoryLock, ...]:
    if locks is True:
        return chapter_key_locks()
    if not locks:
        return ()
    return tuple(locks)


def chapter_completion_rule(player: int, locks: Locks) -> StateRule:
    """Finishing the story requires every story lock, even when a travel key grants an
    early visit to the final dungeon. Disabled candidate gates never enter the pool and
    must not become requirements here."""
    required = tuple(name for name, _ in _locks(locks))
    return lambda state: all(state.has(name, player) for name in required)


def postgame_rule(player: int, locks: Locks, goal_region_name: str) -> StateRule:
    """Content that only exists after the ending (clear save: the maze, VR Expel, the
    Ultimate raids) is reachable no earlier than the goal itself. Such locations also
    refuse progression items (an item rule, not EXCLUDED, so they can still hold
    equipment), so nothing another slot needs ever waits behind the credits."""
    chapters_complete = chapter_completion_rule(player, locks)
    return lambda state: chapters_complete(state) and state.can_reach_region(goal_region_name, player)


def story_reaches_progress(story_progress: "int | None", player: int, locks: Locks) -> StateRule:
    """Access rule: whether the story's own pacing reaches `story_progress`.

    With no locks, or a region/chest with no story_progress at all (e.g. the post-game
    maze), this is unconditionally True -- nothing in the game suppresses a native
    progress advance. Otherwise every lock whose unlocks_progress is at or before
    `story_progress` must be collected -- those are exactly the chokepoints the story
    cannot pass without the matching item. Locks whose unlocks_progress is later than
    `story_progress` are irrelevant (the story reaches this point before them).
    """
    if story_progress is None:
        return lambda _state: True

    required = [name for name, unlocks in _locks(locks) if unlocks <= story_progress]
    if not required:
        return lambda _state: True

    def rule(state: "CollectionState") -> bool:
        return all(state.has(name, player) for name in required)

    return rule


def challenge_chest_count_rule(player: int, region_requirements: "Sequence[Tuple[Sequence[str], int]]",
                               needed: int) -> StateRule:
    """Open world: the Challenge Mission chest counters (207, 208) need at least `needed` active chests in logic.
    `region_requirements` is one (item names that must all be held, chest count) pair per area."""
    areas = tuple((tuple(names), count) for names, count in region_requirements)

    def rule(state: "CollectionState") -> bool:
        total = 0
        for names, count in areas:
            if state.has_all(names, player):
                total += count
                if total >= needed:
                    return True
        return False

    return rule


def story_reaches(region_id: str, player: int, locks: Locks) -> StateRule:
    """Access rule: whether the story's own linear path reaches this region, independent
    of any region key. Delegates to story_reaches_progress() using the region's own
    story_progress (docs/LOGIC_DESIGN.md)."""
    return story_reaches_progress(REGION_TABLE[region_id].story_progress, player, locks)


def key_travel_rule(player: int, region_id: str, locks: Locks) -> StateRule:
    """A region key grants travel once its destination is listed at all: the key must be
    held and the story must have reached the destination row's window start, if it has
    one (Phynal/Phynal Pier only exist from 6000500; docs/LOGIC_AUDIT.md). A region with
    an in-region story barrier (Forest of Symbols, Eluria Tower, Field of Love, Minae
    Cave) also needs the story to lift it: the key reaches the door, not past it."""
    key = REGION_KEY_BY_REGION[region_id]
    thresholds = [p for p in (key.available_from, key.barrier_progress) if p is not None]
    listed = story_reaches_progress(max(thresholds) if thresholds else None, player, locks)
    return lambda state: state.has(key.name, player) and listed(state)


def region_access_rule(player: int, region_id: str, locks: Locks,
                        key_name: "str | None" = None, story_progress: "int | None" = None) -> StateRule:
    """Access rule for a region's entrance from Menu: the key grants access (region_keys,
    family B) once its destination is listed; otherwise the story must reach the region,
    gated by the story locks. `story_progress` overrides the region's first touch with its
    audited physical access point (the earliest of its chests', docs/ACCESS_AUDIT.md).
    """
    reach = (story_reaches_progress(story_progress, player, locks) if story_progress is not None
             else story_reaches(region_id, player, locks))
    by_key = key_travel_rule(player, region_id, locks) if key_name is not None else None

    def rule(state: "CollectionState") -> bool:
        if by_key is not None and by_key(state):
            return True
        return reach(state)

    return rule


def region_key_rule(player: int, region_id: str, locks: Locks = False) -> StateRule:
    """Access rule for the direct Menu -> <region> entrance gated by that region's key
    (region_keys, family B)."""
    return key_travel_rule(player, region_id, locks)


def chest_access_rule(player: int, region_id: str, access_progress: int, gate: "int | None", locks: Locks,
                      key_active: bool) -> StateRule:
    """A chest inside a reached region: the story reaches the chest's own audited access
    point, or the region's travel key is held (with the story past the chest's authored
    in-region gate, which a key never bypasses). Equals the old region-then-gate rule for
    every chest whose access point is its region's first touch (docs/ACCESS_AUDIT.md)."""
    story = story_reaches_progress(access_progress, player, locks)
    if not key_active:
        return story
    by_key = key_travel_rule(player, region_id, locks)
    gate_rule = story_reaches_progress(gate, player, locks)
    return lambda state: story(state) or (by_key(state) and gate_rule(state))


def chest_story_gate_rule(story_progress_required: "int | None", player: int, locks: Locks) -> StateRule:
    """Access rule for a chest with an authored in-region story gate
    (chest_story_gates.json). Delegates to story_reaches_progress()."""
    return story_reaches_progress(story_progress_required, player, locks)
