import base64
import io
import unittest

from PIL import Image
from app import app, build, escpos_bytes, make_sudoku, Receipt, is_eligible_printer
from content import BANK
from extra_library import EXTRA, KEYS


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
