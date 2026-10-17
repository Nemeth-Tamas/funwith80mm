import io
import unittest
from PIL import Image
from app import app, build, escpos_bytes, make_sudoku

class ThermalChaosTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_every_mode_generates(self):
        for kind in ["insult", "quest", "puzzle", "mystery", "certificate", "fpv", "fake"]:
            with self.subTest(kind=kind):
                resp = self.client.post("/api/generate", json={"kind":kind,"data":{}})
                self.assertEqual(resp.status_code, 200, resp.get_json())
                self.assertTrue(resp.get_json()["image"].startswith("data:image/png;base64,"))

    def test_sudoku_valid_solution(self):
        for _ in range(5):
            solution, grid = make_sudoku("medium")
            target=set(range(1,10))
            for i in range(9):
                self.assertEqual(set(solution[i]),target)
                self.assertEqual({solution[j][i] for j in range(9)},target)
            for r in (0,3,6):
                for c in (0,3,6):
                    self.assertEqual({solution[y][x] for y in range(r,r+3) for x in range(c,c+3)},target)

    def test_raster_bytes(self):
        im=Image.new("L",(576,130),255)
        blob=escpos_bytes(im,cut=True)
        self.assertTrue(blob.startswith(b"\x1b@"))
        self.assertTrue(blob.endswith(b"\x1dV\x00"))
        self.assertIn(b"\x1dv0",blob)

    def test_invalid_mode(self):
        self.assertEqual(self.client.post("/api/generate",json={"kind":"oops"}).status_code,400)

    def test_cannot_print_without_preview(self):
        self.assertEqual(self.client.post("/api/print",json={"id":"bogus"}).status_code,400)

if __name__=="__main__":
    unittest.main()
