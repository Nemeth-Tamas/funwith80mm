"""Curated psychological horror: short, original, unsettling, bilingual microstories.

These live beside the existing horror library rather than replacing it.
Every story is independently authored and validated at application startup.
"""
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "psychological_horror"


def load_psychological_horror():
    stories = {}
    for lang in ("en", "hu"):
        path = ROOT / f"{lang}.json"
        entries = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(entries, list) or len(entries) < 80:
            raise ValueError(f"{path}: expected at least 80 original stories")
        seen = set()
        for i, entry in enumerate(entries):
            label = f"{path}: story {i}"
            if not isinstance(entry, str) or entry != entry.strip():
                raise ValueError(f"{label}: invalid text")
            if not 45 <= len(entry) <= 280:
                raise ValueError(f"{label}: story length must be 45-280 characters")
            if unicodedata.normalize("NFC", entry) != entry:
                raise ValueError(f"{label}: Unicode must be NFC")
            if any(unicodedata.category(ch) == "Cc" for ch in entry):
                raise ValueError(f"{label}: control characters are not allowed")
            identity = "".join(ch for ch in entry.casefold() if ch.isalnum())
            if identity in seen:
                raise ValueError(f"{label}: repeated story")
            seen.add(identity)
        stories[lang] = tuple(entries)
    return stories


PSYCHOLOGICAL_HORROR = load_psychological_horror()
