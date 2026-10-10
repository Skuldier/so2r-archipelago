"""Character identity and seed roster; independent of the chosen story route."""
from dataclasses import dataclass

CHARACTER_ITEM_BASE = 5_850_000
CHARACTER_NAMES = {
    1: "Claude", 2: "Rena", 3: "Celine", 4: "Bowman", 5: "Dias", 6: "Precis",
    7: "Ashton", 8: "Leon", 9: "Opera", 10: "Ernest", 11: "Noel",
    12: "Chisato", 13: "Welch",
}


@dataclass(frozen=True)
class CharacterData:
    player_id: int
    label: str

    @property
    def item_id(self) -> int:
        return CHARACTER_ITEM_BASE + self.player_id

    @property
    def name(self) -> str:
        return f"Character: {self.label}"


CHARACTERS = {pid: CharacterData(pid, name) for pid, name in CHARACTER_NAMES.items()}


MAX_JOINABLE = 7  # eight native party slots: the starter plus seven


def choose_roster(random, starter: int, joinable: int = MAX_JOINABLE) -> list[CharacterData]:
    """The starter plus `joinable` distinct characters (1..7; the option joinable_characters, default 3).
    Native route/exclusivity does not restrict AP grants."""
    if starter not in CHARACTERS:
        raise ValueError("Unknown starting character")
    if not 1 <= joinable <= MAX_JOINABLE:
        raise ValueError("A roster has 1 to 7 joinable characters besides the starter")
    others = random.sample([pid for pid in CHARACTERS if pid != starter], joinable)
    return [CHARACTERS[starter], *(CHARACTERS[pid] for pid in sorted(others))]


def shuffle_recruitment_rewards(random, source_player_ids: list[int],
                               roster: list[CharacterData]) -> dict[int, CharacterData]:
    """Prepare seven NPC-site rewards for the future recruitment-check mode.

    Source identities identify the original recruitment actor, not the reward.
    The caller must first select seven supported, reachable recruitment sites.
    This helper neither enables locations nor changes existing seed generation.
    """
    if (len(source_player_ids) != 7 or len(set(source_player_ids)) != 7
            or any(type(pid) is not int or pid not in CHARACTERS for pid in source_player_ids)):
        raise ValueError("Recruitment rewards require seven distinct native source characters")
    roster_ids = [row.player_id for row in roster]
    if (len(roster_ids) != 8 or len(set(roster_ids)) != 8
            or any(type(pid) is not int or pid not in CHARACTERS for pid in roster_ids)):
        raise ValueError("Recruitment rewards require one starter plus seven distinct characters")

    # Canonical order makes the result independent of input table enumeration order.
    sources = sorted(source_player_ids)
    remaining = set(roster_ids[1:])
    assignments: dict[int, CharacterData] = {}

    def assign(index: int) -> bool:
        if index == len(sources):
            return True
        source = sources[index]
        candidates = sorted(remaining - {source})
        random.shuffle(candidates)
        for reward in candidates:
            assignments[source] = CHARACTERS[reward]
            remaining.remove(reward)
            if assign(index + 1):
                return True
            remaining.add(reward)
            del assignments[source]
        return False

    # Backtrack instead of retrying a random shuffle indefinitely or leaving the last
    # NPC with its own identity. No AP/world state changes until the assignment exists.
    if not assign(0):
        raise ValueError("No distinct recruitment-reward assignment exists")
    return assignments
