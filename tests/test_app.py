import base64
import io
import unittest

from PIL import Image
from app import app, build, escpos_bytes, make_sudoku, Receipt, is_eligible_printer
from content import BANK
from extra_library import EXTRA, KEYS
from chaos_games import GAMES, BINGO_THEMES, FREE_SPACE, bingo_card
from psych_horror import PSYCHOLOGICAL_HORROR, load_psychological_horror
import random


class ThermalChaosTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_every_mode_in_both_languages(self):
        for lang in ("en", "hu"):
            for kind in ("insult", "quest", "puzzle", "mystery", "horror",
                         "certificate", "fpv", "fake"):
                with self.subTest(lang=lang, kind=kind):
                    result = self.client.post("/api/generate", json={
                        "kind": kind, "data": {"lang": lang}
                    })
                    self.assertEqual(result.status_code, 200, result.get_json())
                    self.assertTrue(result.get_json()["image"].startswith("data:image/png;base64,"))
                    self.assertTrue(result.get_json()["id"])

    def test_five_new_modes_per_language(self):
        for lang in ("en", "hu"):
            for kind in KEYS:
                with self.subTest(lang=lang, kind=kind):
                    self.assertGreaterEqual(len(EXTRA[lang][kind]), 30)
                    response = self.client.post("/api/generate", json={
                        "kind": kind, "data": {"lang": lang, "pad_mm": 20}
                    })
                    self.assertEqual(response.status_code, 200, response.get_json())
                    encoded = response.get_json()["image"].split(",", 1)[1]
                    image = Image.open(io.BytesIO(base64.b64decode(encoded)))
                    self.assertEqual(image.width, 576)
                    self.assertTrue(all(p == 255 for p in image.crop((0, image.height-100, 576, image.height)).getdata()))

    def test_every_new_authored_entry_renders(self):
        from unittest.mock import patch
        import app as app_module
        for lang in ("en", "hu"):
            for kind in KEYS:
                for idx, entry in enumerate(EXTRA[lang][kind]):
                    with self.subTest(lang=lang, kind=kind, index=idx):
                        with patch.dict(app_module.EXTRA[lang], {kind: [entry]}):
                            im, answer, description = build(kind, {"lang": lang})
                        self.assertEqual(im.width, 576)
                        self.assertLess(im.height, 5900)
                        self.assertGreater(im.height, 200)
                        self.assertTrue(escpos_bytes(im).endswith(b"\x1dV\x00"))

    def test_paranormal_reports_and_bingo_api(self):
        for lang in ("en", "hu"):
            for kind in ("paranormal", "bingo"):
                themes = BINGO_THEMES if kind == "bingo" else ("repair",)
                for theme in themes:
                    with self.subTest(lang=lang, kind=kind, theme=theme):
                        response = self.client.post("/api/generate", json={
                            "kind": kind, "data": {
                                "lang": lang, "theme": theme, "pad_mm": 20
                            }
                        })
                        self.assertEqual(response.status_code, 200, response.get_json())
                        raw = base64.b64decode(response.get_json()["image"].split(",", 1)[1])
                        im = Image.open(io.BytesIO(raw)).convert("L")
                        self.assertEqual(im.width, 576)
                        self.assertLess(im.height, 5900)
                        self.assertEqual(set(im.crop((0, im.height-100, 576, im.height)).getdata()), {255})
                        self.assertIn(b"\x1dv0", escpos_bytes(im))

    def test_bingo_cards_are_real_five_by_five_grids(self):
        for lang in ("en", "hu"):
            for theme in BINGO_THEMES:
                for seed in range(8):
                    with self.subTest(lang=lang, theme=theme, seed=seed):
                        card = bingo_card(lang, theme, random.Random(seed))
                        self.assertEqual(len(card), 25)
                        self.assertEqual(card[12], FREE_SPACE[lang])
                        self.assertEqual(len(set(card)), 25)
                        self.assertTrue(
                            set(card[:12] + card[13:]).issubset(set(GAMES[lang]["bingo"][theme]))
                        )

    def test_render_every_paranormal_case(self):
        from unittest.mock import patch
        import app as app_module
        for lang in ("en", "hu"):
            self.assertGreaterEqual(len(GAMES[lang]["paranormal"]), 40)
            for index, case in enumerate(GAMES[lang]["paranormal"]):
                with self.subTest(lang=lang, case=index):
                    with patch.dict(app_module.GAMES[lang], {"paranormal": [case]}):
                        im, answer, description = build("paranormal", {"lang": lang})
                    self.assertEqual(im.width, 576)
                    self.assertLess(im.height, 5900)

    def test_longest_bingo_labels_still_fit_receipt(self):
        from app import Receipt
        for lang in ("en", "hu"):
            for theme in BINGO_THEMES:
                with self.subTest(lang=lang, theme=theme):
                    tiles = sorted(GAMES[lang]["bingo"][theme], key=len, reverse=True)[:24]
                    tiles.insert(12, FREE_SPACE[lang])
                    image = Receipt().bingo(tiles).footer(pad_mm=20)
                    self.assertEqual(image.width, 576)
                    self.assertLess(image.height, 5900)
                    self.assertTrue(all(px == 255 for px in image.crop(
                        (0, image.height-90, 576, image.height)).getdata()))

    def test_invalid_bingo_theme_rejected(self):
        response = self.client.post("/api/generate", json={
            "kind": "bingo", "data": {"lang": "hu", "theme": "invalid"}
        })
        self.assertEqual(response.status_code, 400)


    def test_wanted_poster_never_prints_entire_content_pools(self):
        # Regression: "charges" and "seen" were also used as heading keys,
        # so the poster dumped a repr of all the possible charges/locations.
        from unittest.mock import patch
        from wanted_posters import WANTED
        real_text = Receipt.text
        image = Image.new("RGB", (80, 120), (100, 130, 160))
        stream = io.BytesIO()
        image.save(stream, "PNG")
        uri = "data:image/png;base64," + base64.b64encode(stream.getvalue()).decode("ascii")
        for lang in ("en", "hu"):
            with self.subTest(lang=lang):
                observed = []

                def capture(receipt, value, *args, **kwargs):
                    observed.append(value)
                    return real_text(receipt, value, *args, **kwargs)

                with patch.object(Receipt, "text", capture):
                    im, _, _ = build("photo", {
                        "lang": lang, "effect": "mostwanted", "image": uri
                    })
                self.assertEqual(im.width, 576)
                self.assertTrue(all(isinstance(value, str) for value in observed))
                labels = WANTED[lang]["labels"]
                self.assertEqual(set(labels), {"alias", "charges", "seen", "reward", "note"})
                for name in ("alias", "charges", "seen", "reward", "note"):
                    self.assertEqual(observed.count(labels[name]), 1)
                self.assertEqual(sum(value in WANTED[lang]["charges"]
                                     for value in observed), 1)
                self.assertEqual(sum(value in WANTED[lang]["seen"]
                                     for value in observed), 1)
                self.assertFalse(any(str(WANTED[lang]["charges"]) == value
                                     or str(WANTED[lang]["seen"]) == value
                                     for value in observed))

    def test_most_wanted_is_bilingual_and_printer_ready(self):
        from wanted_posters import WANTED
        sample = Image.new("RGB", (640, 900), (167, 139, 106))
        output = io.BytesIO()
        sample.save(output, "PNG")
        uri = "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")
        for lang in ("en", "hu"):
            with self.subTest(lang=lang):
                response = self.client.post("/api/generate", json={
                    "kind": "photo",
                    "data": {
                        "lang": lang,
                        "effect": "mostwanted",
                        "wanted_alias": "Captain Cable Goblin" if lang == "en" else "Kábelkobold",
                        "image": uri,
                        "pad_mm": 20,
                    },
                })
                self.assertEqual(response.status_code, 200, response.get_json())
                body = response.get_json()
                self.assertIn("poster" if lang == "en" else "poszter",
                              body["description"].lower())
                im = Image.open(io.BytesIO(base64.b64decode(body["image"].split(",", 1)[1])))
                self.assertEqual(im.width, 576)
                self.assertLess(im.height, 5900)
                self.assertGreater(im.height, 1200)
                self.assertEqual(set(im.crop((0, im.height-100, 576, im.height)).getdata()), {255})
                self.assertEqual(set(im.getdata()), {0, 255})
                self.assertTrue(escpos_bytes(im, cut=True).endswith(b"\x1dV\x00"))

    def test_most_wanted_preserves_regular_photo_effects(self):
        from app import make_photo
        sample = Image.new("RGB", (200, 120), (140, 190, 220))
        output = io.BytesIO()
        sample.save(output, "PNG")
        uri = "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")
        for effect in ("dither", "threshold", "newsprint", "negative"):
            with self.subTest(effect=effect):
                photo = make_photo(uri, effect)
                self.assertLessEqual(photo.width, 528)
                self.assertLessEqual(photo.height, 1150)
        poster = make_photo(uri, "mostwanted")
        self.assertEqual(poster.size, (448, 548))

    def test_most_wanted_custom_alias_and_random_fallback(self):
        from wanted_posters import WANTED, wanted_profile
        for lang in ("en", "hu"):
            custom = wanted_profile(lang, "  CAPTAIN\\nCABLE  ", random.Random(4))
            self.assertNotIn("\n", custom["alias"])
            self.assertIn("CAPTAIN", custom["alias"])
            self.assertEqual(len(custom["case"]), 12)
            fallback = wanted_profile(lang, "   ", random.Random(4))
            self.assertIn(fallback["alias"], WANTED[lang]["aliases"])
            self.assertTrue(fallback["charges"])

    def test_most_wanted_rejects_missing_image(self):
        response = self.client.post("/api/generate", json={
            "kind": "photo", "data": {"lang": "en", "effect": "mostwanted"}
        })
        self.assertEqual(response.status_code, 400)

    def test_most_wanted_effect_visible_in_photo_ui(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('["mostwanted",s.effects[4]]', html)
        self.assertIn('KÖRÖZÉS poszter', html)
        self.assertIn('wanted_alias', html)

    def test_psychological_horror_content_validation(self):
        loaded = load_psychological_horror()
        for lang in ("en", "hu"):
            with self.subTest(lang=lang):
                self.assertEqual(len(loaded[lang]), 89)
                self.assertEqual(len(set(loaded[lang])), len(loaded[lang]))
                self.assertTrue(all(45 <= len(story) <= 280 for story in loaded[lang]))

    def test_psychological_horror_api_bilingual(self):
        for lang in ("en", "hu"):
            response = self.client.post("/api/generate", json={
                "kind": "psychhorror", "data": {"lang": lang, "pad_mm": 20}
            })
            self.assertEqual(response.status_code, 200, response.get_json())
            result = response.get_json()
            image = Image.open(io.BytesIO(base64.b64decode(result["image"].split(",", 1)[1])))
            self.assertEqual(image.width, 576)
            self.assertLess(image.height, 5900)
            self.assertEqual(image.getpixel((20, image.height - 30)), 255)
            self.assertTrue(escpos_bytes(image).endswith(b"\x1dV\x00"))
            self.assertIsNone(result["answer"])

    def test_each_psychological_horror_story_renders(self):
        from unittest.mock import patch
        for lang in ("en", "hu"):
            for index, story in enumerate(PSYCHOLOGICAL_HORROR[lang]):
                with self.subTest(lang=lang, story=index):
                    with patch("app.choice", return_value=story):
                        receipt, answer, description = build("psychhorror", {"lang": lang})
                    self.assertEqual(receipt.width, 576)
                    self.assertGreater(receipt.height, 200)
                    self.assertLess(receipt.height, 5900)
                    self.assertIsNone(answer)
                    self.assertTrue(escpos_bytes(receipt, cut=True).endswith(b"\x1dV\x00"))
                    last_rows = receipt.crop((0, receipt.height-90, 576, receipt.height))
                    self.assertEqual(set(last_rows.getdata()), {255})

    def test_psychological_horror_ui_is_available(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('{id:"psychhorror",emoji:', html)
        self.assertIn("PSYCHO HORROR", html)
        self.assertIn("PSZICHOHORROR", html)
        self.assertIn('"mystery","horror","psychhorror"', html)

    def test_photo_in_both_languages(self):
        pic = Image.new("RGB", (70, 70), (121, 92, 44))
        output = io.BytesIO()
        pic.save(output, "PNG")
        uri = "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")
        for lang in ("en", "hu"):
            resp = self.client.post("/api/generate", json={
                "kind": "photo", "data": {"image": uri, "lang": lang}
            })
            self.assertEqual(resp.status_code, 200, resp.get_json())

    def test_content_banks_have_more_chaos(self):
        for lang in ("en", "hu"):
            self.assertGreaterEqual(len(BANK[lang]["horror"]), 30)
            self.assertGreaterEqual(len(BANK[lang]["insults"]["nuclear"]), 12)
            self.assertGreaterEqual(len(BANK[lang]["quests"]["hard"]), 12)

    def test_bottom_margin_actually_changes_image_height(self):
        short = Receipt().text("hello").footer(pad_mm=12)
        long = Receipt().text("hello").footer(pad_mm=30)
        self.assertEqual(short.width, 576)
        self.assertGreaterEqual(long.height - short.height, 140)

    def test_sudoku_valid_solution(self):
        target = set(range(1, 10))
        for _ in range(4):
            solved, _ = make_sudoku("hard")
            for i in range(9):
                self.assertEqual(set(solved[i]), target)
                self.assertEqual({solved[j][i] for j in range(9)}, target)
            for r in (0, 3, 6):
                for c in (0, 3, 6):
                    self.assertEqual({solved[y][x] for y in range(r, r+3)
                                      for x in range(c, c+3)}, target)

    def test_windows_usb_and_network_queues(self):
        self.assertTrue(is_eligible_printer("Birch CP-Q1UN", "USB001", "Birch"))
        self.assertTrue(is_eligible_printer("Birch CP-Q1UN", "IP_192.168.1.80", "Birch"))
        self.assertTrue(is_eligible_printer("Shop Birch", "WSD-8e7b4c", "Receipt"))
        self.assertTrue(is_eligible_printer(r"\\SHOP-PC\\BIRCH", "Ne00:", "Generic"))
        self.assertFalse(is_eligible_printer("Microsoft Print to PDF", "PORTPROMPT:", "Microsoft Print To PDF"))
        self.assertFalse(is_eligible_printer("OneNote", "Ne01:", "OneNote"))
        self.assertFalse(is_eligible_printer("Fax", "SHRFAX:", "Fax"))

    def test_text_is_one_bit_and_margin_unchanged(self):
        im = Receipt().text("NYOMTATÓ TÚLÉLŐPRÓBA", 21).footer(pad_mm=20)
        self.assertEqual(im.size[0], 576)
        self.assertEqual(set(im.getdata()), {0, 255})

    def test_escpos_raster_and_cutter(self):
        im = Image.new("L", (576, 130), 255)
        data = escpos_bytes(im, cut=True)
        self.assertTrue(data.startswith(b"\x1b@"))
        self.assertTrue(data.endswith(b"\x1dV\x00"))
        self.assertIn(b"\x1dv0", data)

    def test_unsafe_or_invalid_jobs_fail(self):
        self.assertEqual(self.client.post("/api/generate", json={"kind": "oops"}).status_code, 400)
        self.assertEqual(self.client.post("/api/print", json={"id": "nonexistent"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
