"""Load and validate the authored JSON packs without changing BANK's public shape.

Run ``python -m content_library`` for a live category/count report.
Each row is an authored entry: a whole shop is one entry, not three products.
"""
import copy
import json
import re
import unicodedata
from pathlib import Path

LANGUAGES = ("en", "hu")
GROUPS = {
    "insults": ("gentle", "mean", "nuclear", "existential"),
    "quests": ("easy", "medium", "hard"),
    "flight": ("whoop", "camera", "five"),
}
CATEGORIES = (*GROUPS, "riddles", "mysteries", "horror", "certs", "shops")
PACK_ROOT = Path(__file__).resolve().parent / "content_packs"


def _require(condition, location, message):
    if not condition:
        raise ValueError(f"{location}: {message}")


def _text(value, location, limit=500):
    _require(isinstance(value, str), location, "expected text")
    _require(bool(value.strip()), location, "empty text")
    _require(value == value.strip(), location, "leading/trailing whitespace")
    _require(len(value) <= limit, location, f"text exceeds {limit} characters")
    _require(not any(unicodedata.category(c) == "Cc" for c in value),
             location, "control characters are not printable content")
    _require(unicodedata.normalize("NFC", value) == value, location,
             "text must use NFC Unicode (including Hungarian accents)")


def _pair(value, location):
    _require(isinstance(value, (list, tuple)) and len(value) == 2,
             location, "expected a two-item pair")


def normalize_identity(value):
    """Ignore case, punctuation and whitespace when spotting repeated entries."""
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[\W_]+", "", value)


def iter_sections(bank):
    """Yield (language, dotted category, entries) for all fifteen leaf categories."""
    for lang in LANGUAGES:
        for category in CATEGORIES:
            value = bank[lang][category]
            if category in GROUPS:
                for group in GROUPS[category]:
                    yield lang, f"{category}.{group}", value[group]
            else:
                yield lang, category, value


def validate_bank(bank):
    """Reject bad schemas, ambiguous identities and unreasonably long receipts.

    Riddle identities are questions, certificate identities are titles, and shop
    identities are names. Answers and product names may legitimately recur.
    All entry identities must be unique within a language, even across sections.
    """
    _require(isinstance(bank, dict) and set(bank) == set(LANGUAGES),
             "BANK", "expected exactly en and hu")
    for lang in LANGUAGES:
        _require(isinstance(bank[lang], dict) and
                 set(bank[lang]) == set(CATEGORIES), lang, "unexpected/missing categories")
        for category, groups in GROUPS.items():
            value = bank[lang][category]
            _require(isinstance(value, dict) and set(value) == set(groups),
                     f"{lang}.{category}", "unexpected/missing subcategories")

    seen = {lang: {} for lang in LANGUAGES}
    for lang, section, entries in iter_sections(bank):
        location = f"{lang}.{section}"
        _require(isinstance(entries, list) and bool(entries), location, "expected a nonempty list")
        category = section.split(".")[0]
        for index, entry in enumerate(entries):
            loc = f"{location}[{index}]"
            if category in ("riddles", "certs"):
                _pair(entry, loc)
                _text(entry[0], loc + "[0]", 500 if category == "riddles" else 80)
                _text(entry[1], loc + "[1]", 500 if category == "riddles" else 300)
                identity = entry[0]
            elif category == "shops":
                _pair(entry, loc)
                _text(entry[0], loc + ".name", 80)
                products = entry[1]
                _require(isinstance(products, list) and 1 <= len(products) <= 6,
                         loc, "expected 1-6 products")
                labels = set()
                for product_index, product in enumerate(products):
                    ploc = f"{loc}.products[{product_index}]"
                    _pair(product, ploc)
                    label, price = product
                    _text(label, ploc + ".label", 48)
                    key = normalize_identity(label)
                    _require(key not in labels, ploc, "duplicate product")
                    labels.add(key)
                    _require(type(price) is int and 0 <= price <= 999999,
                             ploc, "price must be an integer between 0 and 999999")
                identity = entry[0]
            else:
                _text(entry, loc)
                identity = entry
            key = normalize_identity(identity)
            _require(bool(key), loc, "entry has no letters or numbers")
            _require(key not in seen[lang], loc,
                     f"duplicate entry (first at {seen[lang].get(key)})")
            seen[lang][key] = loc


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_packs(root=PACK_ROOT):
    """Read the fixed local pack set; never depend on the process working directory."""
    packs = {}
    for lang in LANGUAGES:
        folder = Path(root) / lang
        expected = {f"{category}.json" for category in CATEGORIES}
        actual = {p.name for p in folder.glob("*.json")}
        _require(actual == expected, str(folder), "unexpected/missing JSON pack files")
        packs[lang] = {}
        for category in CATEGORIES:
            path = folder / f"{category}.json"
            try:
                with path.open(encoding="utf-8") as stream:
                    packs[lang][category] = json.load(stream, object_pairs_hook=_unique_keys)
            except (OSError, ValueError) as exc:
                raise ValueError(f"{path}: {exc}") from exc
    validate_bank(packs)
    # Keep the existing tuple-based question/answer, title/description and shop API.
    for lang in LANGUAGES:
        for category in ("riddles", "certs"):
            packs[lang][category] = [tuple(entry) for entry in packs[lang][category]]
        packs[lang]["shops"] = [
            (name, [tuple(product) for product in products])
            for name, products in packs[lang]["shops"]
        ]
    return packs


def extend_bank(original, packs=None):
    """Append packs, preserving the values and order of every original entry."""
    validate_bank(original)
    packs = load_packs() if packs is None else packs
    validate_bank(packs)
    merged = copy.deepcopy(original)
    for lang, section, entries in iter_sections(packs):
        target = merged[lang]
        for key in section.split("."):
            target = target[key]
        target.extend(copy.deepcopy(entries))
    validate_bank(merged)
    return merged


def content_counts(bank):
    counts = {lang: {} for lang in LANGUAGES}
    for lang, section, entries in iter_sections(bank):
        counts[lang][section] = len(entries)
    return counts


if __name__ == "__main__":
    from content import BANK

    counts = content_counts(BANK)
    added = content_counts(load_packs())
    print("Category                         EN     HU")
    for section in counts["en"]:
        print(f"{section:30} {counts['en'][section]:6} {counts['hu'][section]:6}")
    print(f"{'TOTAL':30} {sum(counts['en'].values()):6} {sum(counts['hu'].values()):6}")
    print(f"{'NEW AUTHORED ENTRIES':30} {sum(added['en'].values()):6} {sum(added['hu'].values()):6}")
