"""The two Windows entry points must not accidentally open the wrong UI."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_regular_launcher_always_defaults_to_ordinary_app(self):
        script = (ROOT / "start.bat").read_text(encoding="utf-8").lower()
        self.assertIn('set "thermal_chaos_camera=0"', script)
        self.assertIn('set "thermal_chaos_page=http://127.0.0.1:8765/"', script)
        self.assertIn('if /i "%~1"=="--eagle-eye"', script)
        self.assertIn('start "" "%thermal_chaos_page%"', script)

    def test_camera_launcher_requires_explicit_opt_in(self):
        script = (ROOT / "start_eagle_eye.bat").read_text(encoding="utf-8").lower()
        self.assertIn('call "%~dp0start.bat" --eagle-eye', script)
        self.assertNotIn("set thermal_chaos_camera=1", script)


if __name__ == "__main__":
    unittest.main()
