"""Reads the world's data/ files through pkgutil, which works both from a source folder and from a zipped .apworld.
Archipelago 0.6.8 zip-imports custom worlds, so Path(__file__) points inside the archive and cannot be opened."""
import json
import pkgutil
from typing import Any


def read_text(name: str) -> str:
    """data/<name> as text with universal newlines, exactly like Path.read_text."""
    raw = pkgutil.get_data(__name__, "data/" + name)
    if raw is None:
        raise FileNotFoundError("data/" + name)
    return raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def read_json(name: str) -> Any:
    return json.loads(read_text(name))
