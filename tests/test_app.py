import base64
import io
import unittest

from PIL import Image
from app import app, build, escpos_bytes, make_sudoku, Receipt
from content import BANK


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
