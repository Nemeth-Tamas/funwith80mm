"""Offline workflow tests: never touch a physical camera or printer."""
import base64
import io
import time
import unittest
from unittest.mock import patch

from PIL import Image
import app as module


def sample_photo():
    output = io.BytesIO()
    Image.new("RGB", (320, 400), (120, 140, 90)).save(output, "PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


class CameraTests(unittest.TestCase):
    def setUp(self):
        self.workflow = module.camera_workflow
        self.workflow.clear()
        self.config = patch.dict(module.app.config, EAGLE_EYE_ENABLED=True)
        self.config.start()
        self.sender = patch("app.send_to_windows_printer")
        self.send = self.sender.start()
        self.client = module.app.test_client()
        self.token = None

    def tearDown(self):
        self.workflow.clear()
        self.sender.stop()
        self.config.stop()

    def post(self, action, **data):
        return self.client.post("/api/camera/" + action, json={"token": self.token, **data})

    def arm(self):
        response = self.post("arm", consent=True, participant_only=True)
        self.assertEqual(response.status_code, 200, response.get_json())
        self.token = response.get_json()["token"]

    def capture(self, **options):
        response = self.post("capture", image=sample_photo(), **options)
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def test_disabled_by_default_and_no_implicit_activation(self):
        with patch.dict(module.app.config, EAGLE_EYE_ENABLED=False):
            self.assertFalse(self.client.get("/api/camera/status").get_json()["enabled"])
            self.assertEqual(self.post("arm", consent=True, participant_only=True).status_code, 404)
            self.assertIsNone(self.workflow.session)
        self.send.assert_not_called()

    def test_consent_targeting_and_exclusive_session(self):
        for consent, zone in ((False, True), (True, False), ("yes", True)):
            self.assertEqual(self.post("arm", consent=consent, participant_only=zone).status_code, 400)
        self.arm()
        self.assertEqual(self.post("arm", consent=True, participant_only=True).status_code, 409)
        self.assertEqual(self.post("capture", token="wrong", image=sample_photo()).status_code, 400)
        self.send.assert_not_called()

    def test_one_shot_hungarian_shop_renderer_and_margin(self):
        self.arm()
        with patch("app.build", wraps=module.build) as renderer:
            result = self.capture(pad_mm=30)
        options = renderer.call_args.args[1]
        self.assertEqual((options["lang"], options["wanted_theme"], options["effect"]),
                         ("hu", "shop", "mostwanted"))
        photo = Image.open(io.BytesIO(base64.b64decode(result["image"].split(",")[1])))
        self.assertEqual(photo.width, 576)
        self.assertEqual(photo.crop((0, photo.height-240, 576, photo.height)).getextrema(), (255, 255))
        self.assertEqual(self.post("capture", image=sample_photo()).status_code, 400)
        self.send.assert_not_called()

    def test_reroll_reuses_snapshot_invalidates_old_preview(self):
        self.arm()
        first = self.capture()
        snapshot = self.workflow.session["snapshot"]
        deadline = self.workflow.session["deadline"]
        response = self.post("reroll", wanted_alias="Pogácsa Kapitány", pad_mm=12)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(snapshot, self.workflow.session["snapshot"])
        self.assertEqual(deadline, self.workflow.session["deadline"])
        self.assertNotEqual(first["id"], response.get_json()["id"])
        self.assertEqual(self.post("print", id=first["id"], confirm_print=True, printer="Birch").status_code, 400)
        self.send.assert_not_called()

    def test_brightness_adjustment_preserves_photo_jokes_margin_and_expiry(self):
        self.arm()
        first = self.capture(pad_mm=30)
        original = self.workflow.session.copy()
        response = self.post("adjust", photo_gamma=2.1)
        self.assertEqual(response.status_code, 200, response.get_json())
        current = self.workflow.session
        for field in ("snapshot", "record", "pad_mm", "deadline"):
            self.assertEqual(current[field], original[field])
        self.assertEqual(response.get_json()["photo_gamma"], 2.1)
        self.assertNotEqual(first["id"], response.get_json()["id"])
        self.assertNotEqual(original["poster"], current["poster"])
        for invalid in (0, 3, "NaN", "bad"):
            self.assertEqual(self.post("adjust", photo_gamma=invalid).status_code, 400)
        self.send.assert_not_called()

    def test_shadow_lift_happens_before_dithering(self):
        output = io.BytesIO()
        Image.new("RGB", (100, 100), (70, 70, 70)).save(output, "PNG")
        uri = "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")
        normal = module.make_photo(uri, "mostwanted")
        brighter = module.make_photo(uri, "mostwanted", 1.8)
        self.assertEqual(set(brighter.getdata()), {0, 255})
        white_fraction = lambda image: image.histogram()[255] / (image.width * image.height)
        self.assertGreater(white_fraction(brighter), white_fraction(normal) + 0.15)
        self.assertEqual(brighter.size, normal.size)

    def test_page_assets_follow_csp_without_inline_code(self):
        with self.client.get("/eagle-eye") as response:
            html = response.get_data(as_text=True)
            self.assertIn('src="/static/eagle-eye.js"', html)
            self.assertIn('href="/static/eagle-eye.css"', html)
            self.assertNotIn("<style", html)
            self.assertNotIn('style="', html)
            self.assertNotIn("<script>", html)
            self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])
        for path in ("/static/eagle-eye.js", "/static/eagle-eye.css"):
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)

    def test_print_requires_separate_confirmation_and_exact_frozen_bitmap(self):
        self.arm()
        result = self.capture()
        for confirmation in (None, False, "true", 1):
            self.assertEqual(self.post("print", id=result["id"], printer="Birch",
                                       confirm_print=confirmation).status_code, 400)
        self.assertEqual(self.client.post("/api/print", json={"id": result["id"]}).status_code, 400)
        self.send.assert_not_called()
        expected = Image.open(io.BytesIO(base64.b64decode(result["image"].split(",")[1])))
        printed = []
        self.send.side_effect = lambda printer, image, cut: printed.append((printer, image.copy(), cut))
        response = self.post("print", id=result["id"], printer="Birch", confirm_print=True, cut=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(printed[0][0], "Birch")
        self.assertFalse(printed[0][2])
        self.assertEqual(printed[0][1].tobytes(), expected.tobytes())
        self.assertIsNone(self.workflow.session)
        self.assertEqual(self.post("print", id=result["id"], printer="Birch", confirm_print=True).status_code, 400)
        self.assertEqual(self.send.call_count, 1)

    def test_cancel_and_foreign_tokens(self):
        self.arm()
        result = self.capture()
        self.assertEqual(self.post("cancel", token="other tab").status_code, 400)
        self.assertIsNotNone(self.workflow.session)
        self.assertEqual(self.post("cancel").status_code, 200)
        self.assertIsNone(self.workflow.session)
        self.assertEqual(self.post("reroll").status_code, 400)
        self.assertEqual(self.post("print", id=result["id"], confirm_print=True, printer="Birch").status_code, 400)
        self.assertNotIn(result["id"], module.CACHE)
        self.send.assert_not_called()

    def test_expiry_releases_memory_without_another_request(self):
        with patch.object(self.workflow, "PHOTO_SECONDS", 0.06):
            self.arm()
            self.capture()
            time.sleep(0.15)
        self.assertIsNone(self.workflow.session)
        self.send.assert_not_called()

    def test_stale_arm_timer_cannot_expire_new_photo_deadline(self):
        self.arm()
        self.capture()
        self.workflow._expire(self.token)
        self.assertIsNotNone(self.workflow.session)

    def test_expired_session_cannot_print_even_if_timer_delayed(self):
        self.arm()
        result = self.capture()
        self.workflow.session["deadline"] = time.monotonic() - 1
        self.assertEqual(self.post("print", id=result["id"], confirm_print=True, printer="Birch").status_code, 400)
        self.assertIsNone(self.workflow.session)
        self.send.assert_not_called()

    def test_printer_failure_keeps_frozen_preview_for_deliberate_retry(self):
        self.arm()
        result = self.capture()
        self.send.side_effect = OSError("offline")
        self.assertEqual(self.post("print", id=result["id"], confirm_print=True, printer="Birch").status_code, 503)
        self.assertEqual(self.workflow.session["preview_id"], result["id"])
        self.assertEqual(self.send.call_count, 1)

    def test_invalid_image_and_options_never_print(self):
        self.arm()
        for image in (None, "not a photo", "data:image/jpeg;base64,!!!!", "data:image/svg+xml;base64,AAAA"):
            self.assertEqual(self.post("capture", image=image).status_code, 400)
        self.assertEqual(self.post("capture", image=sample_photo(), pad_mm=800).status_code, 400)
        self.assertIsNone(self.workflow.session)
        self.send.assert_not_called()

    def test_remote_hosts_origins_and_non_json_are_rejected(self):
        for headers in ({"Origin": "https://evil.example"}, {"Host": "evil.example"}, {"Sec-Fetch-Site": "cross-site"}):
            self.assertEqual(self.client.post("/api/camera/arm", json={}, headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/camera/status", environ_base={"REMOTE_ADDR": "192.168.1.9"}).status_code, 403)
        for body in ([], "text", None):
            self.assertEqual(self.client.post("/api/camera/arm", json=body).status_code, 400)
        response = self.client.get("/api/camera/status")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.send.assert_not_called()

    def test_no_capture_event_or_timeout_endpoint_can_print(self):
        self.arm()
        for event in ("motion", "face", "timeout", "camera-event", "track"):
            self.assertEqual(self.post(event).status_code, 400)
        self.send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
