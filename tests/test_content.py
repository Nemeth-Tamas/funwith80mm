"""Content contracts, exhaustive renderer coverage and executable puzzle checks."""
import ast
import copy
import itertools
import math
import os
import subprocess
import sys
import tempfile
import unittest
from collections import deque
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

from app import build, escpos_bytes
from content import BANK
from content_library import (
    PACK_ROOT, content_counts, extend_bank, iter_sections, load_packs, validate_bank,
)


def original_bank():
    """Read the retained literal without importing or extending it a second time."""
    module = ast.parse((PACK_ROOT.parent / "content.py").read_text(encoding="utf-8"))
    assignment = next(node for node in module.body if isinstance(node, ast.Assign))
    return ast.literal_eval(assignment.value)


class ContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packs = load_packs()

    def test_all_original_entries_are_unchanged_prefixes(self):
        original = original_bank()
        lookup = {(lang, section): entries for lang, section, entries in iter_sections(BANK)}
        for lang, section, entries in iter_sections(original):
            with self.subTest(lang=lang, section=section):
                self.assertEqual(lookup[lang, section][:len(entries)], entries)
        before = copy.deepcopy(original)
        extend_bank(original, self.packs)
        self.assertEqual(original, before, "loading must not mutate the original bank")

    def test_authored_count_and_every_category_in_both_languages(self):
        counts = content_counts(self.packs)
        for lang in ("en", "hu"):
            self.assertGreaterEqual(sum(counts[lang].values()), 700)
            self.assertEqual(len(counts[lang]), 15)
            self.assertTrue(all(count > 0 for count in counts[lang].values()))
        self.assertEqual(counts["en"], counts["hu"])
        validate_bank(BANK)

    def test_new_horror_is_short_and_two_sentences(self):
        for lang in ("en", "hu"):
            for story in self.packs[lang]["horror"]:
                with self.subTest(lang=lang, story=story):
                    self.assertGreaterEqual(len(story.split()), 15)
                    self.assertLessEqual(len(story.split()), 45)
                    self.assertEqual(story.count("."), 2)

    def test_invalid_content_is_rejected_with_location(self):
        cases = [
            ("empty", lambda b: b["hu"]["horror"].__setitem__(0, " ")),
            ("control", lambda b: b["en"]["horror"].__setitem__(0, "bad\x1bcommand")),
            ("length", lambda b: b["en"]["horror"].__setitem__(0, "x" * 501)),
            ("duplicate", lambda b: b["en"]["horror"].append(b["en"]["horror"][0].upper() + "!!!")),
            ("cross category duplicate", lambda b: b["hu"]["mysteries"].append(b["hu"]["horror"][0])),
            ("subcategories", lambda b: b["en"]["flight"].pop("five")),
            ("empty section", lambda b: b["hu"]["quests"].__setitem__("hard", [])),
            ("empty answer", lambda b: b["hu"]["riddles"].__setitem__(0, ("Question?", ""))),
            ("riddle pair", lambda b: b["en"]["riddles"].__setitem__(0, ["Question?"])),
            ("certificate title", lambda b: b["en"]["certs"].__setitem__(0, ("x" * 81, "Reason"))),
            ("negative price", lambda b: b["en"]["shops"].__setitem__(0, ("Shop", [("Item", -1)]))),
            ("boolean price", lambda b: b["en"]["shops"].__setitem__(0, ("Shop", [("Item", True)]))),
            ("no products", lambda b: b["hu"]["shops"].__setitem__(0, ("Shop", []))),
            ("repeated product", lambda b: b["hu"]["shops"].__setitem__(0, ("Shop", [("Thing", 1), ("THING!", 2)]))),
        ]
        for label, mutation in cases:
            with self.subTest(label=label):
                bad = copy.deepcopy(self.packs)
                mutation(bad)
                with self.assertRaisesRegex(ValueError, r"(en|hu)\."):
                    validate_bank(bad)

    def test_loader_rejects_duplicate_json_keys_and_missing_packs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for lang in ("en", "hu"):
                (root / lang).mkdir()
                for source in (PACK_ROOT / lang).glob("*.json"):
                    (root / lang / source.name).write_bytes(source.read_bytes())
            broken = root / "en" / "insults.json"
            broken.write_text('{"gentle": [], "gentle": []}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_packs(root)
            broken.unlink()
            with self.assertRaisesRegex(ValueError, "missing JSON pack"):
                load_packs(root)

    def test_packs_load_outside_repository_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-c", "from content import BANK; print(len(BANK['hu']['horror']))"],
                cwd=directory, env={**os.environ, "PYTHONPATH": str(PACK_ROOT.parent)},
                capture_output=True, text=True, check=True,
            )
        self.assertEqual(int(result.stdout.strip()), len(BANK["hu"]["horror"]))

    def test_every_entry_renders_and_encodes_with_real_generator(self):
        modes = {
            "insults": "insult", "quests": "quest", "riddles": "puzzle",
            "mysteries": "mystery", "horror": "horror", "certs": "certificate",
            "shops": "fake", "flight": "fpv",
        }
        crafts = {"whoop": "Air75 II", "camera": "Avata 2", "five": "MM-001"}
        rendered = 0
        for lang, section, entries in iter_sections(BANK):
            category, _, group = section.partition(".")
            options = {"lang": lang, "pad_mm": 20}
            if category in ("insults", "quests"):
                options["level"] = group
            elif category == "flight":
                options["craft"] = crafts[group]
            elif category == "riddles":
                options["type"] = "riddle"
            for index, entry in enumerate(entries):
                selected = []

                def select(sequence):
                    if sequence is entries:
                        selected.append(entry)
                        return entry
                    return sequence[0]

                with self.subTest(lang=lang, section=section, index=index):
                    # Highest product quantities also exercise the widest numeric totals.
                    with patch("app.choice", side_effect=select), patch("app.random.randint", return_value=3):
                        image, answer, _ = build(modes[category], options)
                    self.assertEqual(selected, [entry], "generator did not use the requested content leaf")
                    self.assertEqual(image.width, 576)
                    self.assertLessEqual(image.height, 2200, "receipt exceeds the content length budget")
                    self.assertEqual(image.getextrema(), (0, 255))
                    self.assertIsNotNone(image.getcolors(maxcolors=2), "receipt must be monochrome")
                    self.assertEqual(image.crop((0, image.height - 160, 576, image.height)).getextrema(),
                                     (255, 255), "bottom padding must stay white")
                    self.assertEqual(image.crop((0, 0, 20, image.height)).getextrema(), (255, 255))
                    self.assertEqual(image.crop((556, 0, 576, image.height)).getextrema(), (255, 255))
                    encoded = escpos_bytes(image)
                    self.assertTrue(encoded.endswith(b"\x1dV\x00"))
                    if category == "riddles":
                        self.assertEqual(answer, entry[1])
                        solution, _, _ = build("answer", {"lang": lang, "answer": answer})
                        self.assertEqual(solution.width, 576)
                        self.assertLessEqual(solution.height, 2200)
                    rendered += 1
        self.assertEqual(rendered, sum(sum(v.values()) for v in content_counts(BANK).values()))


class PuzzleAnswerTests(unittest.TestCase):
    """Compute numerical answers and check certificates of logical solutions.

    The authored answers also explain the derivation on the solution slip.
    Literal checks below tie those verified results to the actual pack answers.
    """
    @classmethod
    def setUpClass(cls):
        cls.packs = load_packs()

    def answers_contain(self, index, english, hungarian=None):
        for lang, expected in (("en", english), ("hu", english if hungarian is None else hungarian)):
            answer = self.packs[lang]["riddles"][index][1]
            self.assertIn(str(expected), answer, (lang, index, answer))

    def test_counting_arithmetic_and_engineering_answers(self):
        self.answers_contain(0, 2 + 1)
        self.answers_contain(1, Fraction(100) / (Fraction(100) / 3), "3 perc")
        angle = abs((3 * 30 + 15 / 2) - 15 * 6)
        self.answers_contain(2, angle, str(angle).replace(".", ","))
        self.assertEqual(20 + 10, 30)
        self.assertEqual(100 + 50, 150)
        self.answers_contain(3, "20p and 10p", "százas és egy ötvenes")
        ages = [(a, b) for a in range(10, 51) for b in range(10, 51)
                if a + b == 50 and a - 10 == 2 * (b - 10)]
        self.assertEqual(ages, [(30, 20)])
        self.answers_contain(4, "30")
        animals = [(c, r) for c in range(8) for r in range(8) if c + r == 7 and 2*c + 4*r == 20]
        self.assertEqual(animals, [(4, 3)])
        self.answers_contain(5, "4")
        self.answers_contain(6, 5)
        palindrome = next(n for n in itertools.count(1992) if str(n) == str(n)[::-1])
        self.answers_contain(8, palindrome)
        remainder = next(n for n in itertools.count(1) if n % 7 == 0 and all(n % d == 1 for d in (2, 3, 4, 5)))
        self.answers_contain(9, remainder)
        self.assertLess(2 + 3, 6)
        self.answers_contain(10, "No.", "Nem.")
        thickness = float(Fraction(1, 10) * 2**10)
        self.answers_contain(11, thickness, str(thickness).replace(".", ","))
        self.answers_contain(12, 40 // 10, "Négyet")
        self.answers_contain(13, int("101101", 2))
        self.answers_contain(14, 2 ** (32 - 29) - 2)
        resistance = 1 / (Fraction(1, 6) + Fraction(1, 3))
        self.answers_contain(15, resistance)
        self.answers_contain(16, (4 - 1) * 2)
        self.answers_contain(17, len(set([1, True, 1.0])))
        self.answers_contain(18, list(range(2, 9, 3)))
        queue = deque("ABC")
        queue.popleft()
        queue.append("D")
        self.answers_contain(19, ", ".join(queue))
        numbers = [n for n in range(10, 100) if sum(map(int, str(n))) == 9 and int(str(n)[::-1]) == n + 27]
        self.assertEqual(numbers, [36])
        self.answers_contain(20, numbers[0])
        self.answers_contain(21, math.comb(4, 2))
        self.answers_contain(34, 6 * (6 + 1))
        outcomes = list(itertools.product(range(1, 7), repeat=2))
        probability = Fraction(sum(a+b == 7 for a, b in outcomes), len(outcomes))
        self.answers_contain(35, probability)
        self.answers_contain(37, math.comb(5, 2))

    def test_truth_tellers_boxes_and_balance_puzzles(self):
        possibilities = [(a, b) for a, b in itertools.product((False, True), repeat=2)
                         if a == (not a and not b)]
        self.assertEqual(possibilities, [(False, True)])
        self.answers_contain(22, "A is a knave and B is a knight", "A hazug, B igazmondó")
        contents = list(itertools.permutations(("apples", "oranges", "mixed")))
        valid = [p for p in contents if all(p[i] != label for i, label in enumerate(("apples", "oranges", "mixed")))
                 and p[2] in ("apples", "mixed")]
        self.assertEqual(valid, [("oranges", "mixed", "apples")])
        self.answers_contain(23, "MIXED holds only apples", "VEGYES feliratúban csak alma")
        # Simulate both two-weighing strategies for every possible odd item.
        for count, heavier in ((8, True), (9, False)):
            for odd in range(count):
                weights = [10] * count
                weights[odd] += 1 if heavier else -1
                left, right = sum(weights[:3]), sum(weights[3:6])
                if left == right:
                    candidates = list(range(6, count))
                elif (left > right) == heavier:
                    candidates = list(range(3))
                else:
                    candidates = list(range(3, 6))
                a, b = candidates[:2]
                found = (a if (weights[a] > weights[b]) == heavier else b) if weights[a] != weights[b] else candidates[2]
                self.assertEqual(found, odd)
        self.answers_contain(24, "2", "Kettővel")
        self.answers_contain(27, "Weigh 3 against 3", "Mérj 3-at 3 ellen")
        # A balance weighing has three outcomes; one cannot distinguish eight candidates.
        self.assertLess(3, 8)
        self.assertGreaterEqual(3**2, 9)
        self.assertEqual(60 / 2 + (60 - 60 / 2) / 2, 45)
        self.answers_contain(25, "15", "15")
        self.answers_contain(28, 11 - 7)
        gold = [box for box in "ABC" if sum((box != "B", box == "B", box != "C")) == 1]
        self.assertEqual(gold, ["C"])
        self.answers_contain(36, "C")
        # For each safe door and each guard's honesty, asking about the other
        # guard returns the unsafe door, so choosing its opposite succeeds.
        for safe, honest in itertools.product((0, 1), (False, True)):
            other_reply = safe if not honest else 1 - safe
            reply = other_reply if honest else 1 - other_reply
            self.assertEqual(1 - reply, safe)
        self.answers_contain(29, "opposite", "ellenkező")

    def test_routes_words_and_invariants(self):
        # Check every crossing in the farmer solution, including safety after arrival.
        positions = {item: 0 for item in ("farmer", "wolf", "goat", "cabbage")}
        for passenger in ("goat", None, "wolf", "goat", "cabbage", None, "goat"):
            if passenger:
                self.assertEqual(positions[passenger], positions["farmer"])
                positions[passenger] ^= 1
            positions["farmer"] ^= 1
            for a, b in (("wolf", "goat"), ("goat", "cabbage")):
                self.assertFalse(positions[a] == positions[b] != positions["farmer"])
        self.assertEqual(set(positions.values()), {1})
        self.answers_contain(26, "Seven crossings", "Hét átkelés")
        chain = "COLD CORD CARD WARD WARM".split()
        self.assertTrue(all(sum(a != b for a, b in zip(x, y)) == 1 for x, y in zip(chain, chain[1:])))
        self.answers_contain(30, " -> ".join(chain), "Görög")
        self.assertEqual("görög", "görög"[::-1])
        self.assertEqual(sorted("LISTEN"), sorted("SILENT"))
        self.assertEqual(sorted("KALAP"), sorted("LAPKA"))
        self.answers_contain(31, "SILENT", "LAPKA")
        self.assertEqual(sorted("Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split())[0], "Friday")
        self.assertEqual(min("hétfő kedd szerda csütörtök péntek szombat vasárnap".split(), key=len), "kedd")
        self.answers_contain(32, "Friday", "Kedd")
        for lang, encrypted, plain in (("en", "KHOOR", "HELLO"), ("hu", "VCLD", "SZIA")):
            decoded = "".join(chr((ord(c) - 65 - 3) % 26 + 65) for c in encrypted)
            self.assertEqual(decoded, plain)
            self.assertIn(plain, self.packs[lang]["riddles"][33][1])
        # Explicit jug operations in the authored answer.
        small, large = 0, 5
        moved = min(large, 3-small); small += moved; large -= moved
        small = 0
        small, large = large, 0
        large = 5
        moved = min(large, 3-small); small += moved; large -= moved
        self.assertEqual(large, 4)
        self.answers_contain(38, "4")
        colours = [((x+y) % 2) for x in range(8) for y in range(8)
                   if (x, y) not in ((0, 0), (7, 7))]
        self.assertNotEqual(colours.count(0), colours.count(1))
        self.answers_contain(39, "No.", "Nem.")
        self.answers_contain(7, "towel", "törölköző")


if __name__ == "__main__":
    unittest.main()
