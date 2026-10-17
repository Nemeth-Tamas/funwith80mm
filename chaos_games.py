"""Bilingual paranormal case files and printable 5x5 bingo prompt pools.

Separate from the established BANK and EXTRA schemas to avoid breaking
the existing library and its validation/counting logic.
"""
import json
import random
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "new_modes"
BINGO_THEMES = ("repair", "customers", "home", "cosmic")
LANGUAGES = ("en", "hu")
FREE_SPACE = {"en": "FREE SPACE", "hu": "SZABAD MEZŐ"}


def _check_text(value, label, limit):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label}: expected nonempty trimmed text")
    if len(value) > limit:
        raise ValueError(f"{label}: text exceeds {limit} characters")
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError(f"{label}: expected Unicode NFC")
    if any(unicodedata.category(ch) == "Cc" for ch in value):
        raise ValueError(f"{label}: control characters are not printable")


def _unique(items, label):
    identities = ["".join(ch for ch in value.casefold() if ch.isalnum())
                  for value in items]
    if len(set(identities)) != len(identities):
        raise ValueError(f"{label}: repeated content")


def load_games():
    games = {}
    for lang in LANGUAGES:
        path = ROOT / f"{lang}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"paranormal", "bingo"}:
            raise ValueError(f"{path}: expected paranormal and bingo")
        cases = data["paranormal"]
        if not isinstance(cases, list) or len(cases) < 40:
            raise ValueError(f"{path}: paranormal requires 40+ case reports")
        seen_cases = []
        for i, report in enumerate(cases):
            if not isinstance(report, list) or len(report) != 2:
                raise ValueError(f"{path}: case #{i} must be [observation, finding]")
            for j, line in enumerate(report):
                _check_text(line, f"{path}: paranormal[{i}][{j}]", 220)
            seen_cases.append(report[0])
        _unique(seen_cases, f"{path}: paranormal")
        themes = data["bingo"]
        if not isinstance(themes, dict) or set(themes) != set(BINGO_THEMES):
            raise ValueError(f"{path}: bingo themes do not match {BINGO_THEMES}")
        for theme in BINGO_THEMES:
            labels = themes[theme]
            if not isinstance(labels, list) or len(labels) < 40:
                raise ValueError(f"{path}: bingo.{theme} needs at least 40 entries")
            for i, label in enumerate(labels):
                _check_text(label, f"{path}: bingo.{theme}[{i}]", 55)
            _unique(labels, f"{path}: bingo.{theme}")
        games[lang] = data
    return games


GAMES = load_games()


def bingo_card(lang="en", theme="repair", rng=None):
    """Create 24 unique prompts + centered free space. Does not print."""
    if lang not in LANGUAGES:
        raise ValueError("Unknown language")
    if theme not in BINGO_THEMES:
        raise ValueError("Unknown bingo theme")
    rng = rng or random
    result = rng.sample(GAMES[lang]["bingo"][theme], 24)
    result.insert(12, FREE_SPACE[lang])
    return result
