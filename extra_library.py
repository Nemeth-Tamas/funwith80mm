"""Curated bilingual one-button receipts, independent of the legacy BANK packs.

Each category has at least 30 hand-authored entries per language. The loader
fails fast if a new content pack is incomplete or accidentally duplicated.
"""
import json
import unicodedata
from pathlib import Path

KEYS = ("psyops", "patch", "prophecy", "complaint", "future")
ROOT = Path(__file__).resolve().parent / "extra_modes"


def load_extra():
    packs = {}
    for lang in ("en", "hu"):
        path = ROOT / f"{lang}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        if set(data) != set(KEYS):
            raise ValueError(f"{path}: expected {KEYS}, got {list(data)}")
        observed = set()
        for key in KEYS:
            items = data[key]
            if not isinstance(items, list) or len(items) < 30:
                raise ValueError(f"{path}: {key} needs at least 30 entries")
            for i, item in enumerate(items):
                if not isinstance(item, str) or not item or item != item.strip():
                    raise ValueError(f"{path}: invalid {key}[{i}]")
                if len(item) > 420 or any(unicodedata.category(c) == "Cc" for c in item):
                    raise ValueError(f"{path}: nonprintable or excessive {key}[{i}]")
                if unicodedata.normalize("NFC", item) != item:
                    raise ValueError(f"{path}: non-NFC content in {key}[{i}]")
                identity = "".join(ch for ch in item.casefold() if ch.isalnum())
                if identity in observed:
                    raise ValueError(f"{path}: duplicate content in {key}[{i}]")
                observed.add(identity)
        packs[lang] = data
    return packs


EXTRA = load_extra()
