"""Thermal Toolbox and legal prepayment regression tests (no printer required)."""
import base64
import io
import random
import unittest
from unittest.mock import patch

from PIL import Image
from app import app, Receipt, build, escpos_bytes
from utility_modes import (
    CHEATSHEETS, UTILITY_KINDS, draw_utility, qr_payload,
    legal_terms, parts_order_terms,
)


class UtilityTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def preview(self, kind, data):
        response = self.client.post("/api/generate", json={"kind": kind, "data": data})
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertTrue(body["id"])
        self.assertIsNone(body["answer"])
        image = Image.open(io.BytesIO(base64.b64decode(body["image"].split(",", 1)[1])))
        self.assertEqual(image.width, 576)
        self.assertLess(image.height, 5900)
        self.assertGreater(image.height, 190)
        self.assertEqual(image.getextrema(), (0, 255))
        self.assertEqual(set(image.crop((0, image.height-90, 576, image.height)).getdata()), {255})
        self.assertTrue(escpos_bytes(image, cut=True).endswith(b"\x1dV\x00"))
        return image

    def test_all_utilities_in_both_languages(self):
        base = {
            "qr": {"qr_type": "url", "qr_value": "https://example.com/qr", "title": "Scan this"},
            "checklist": {"title": "To do", "items": "- Alpha\n- Beta\n[ ] Gamma\n4. Delta"},
            "note": {"title": "Remember", "message": "Call the customer.\nBuy tea.", "timestamp": True},
            "cheatsheet": {"sheet": "mikrotik"},
            "legal": {"product": "New monitor", "seller": "Cellnet Kft.",
                      "price_huf": "110000", "sale_kind": "new_eligible", "sale_channel": "store"},
            "deposit": {"seller": "Cellnet Kft.", "customer": "Test Customer",
                        "part": "Replacement laptop fan", "total_huf": "25000",
                        "paid_huf": "10000", "payment_kind": "advance"},
        }
        self.assertEqual(set(base), UTILITY_KINDS)
        for lang in ("en", "hu"):
            for mode, data in base.items():
                with self.subTest(lang=lang, kind=mode):
                    self.preview(mode, {"lang": lang, **data, "pad_mm": 20})

    def test_qr_types_and_escaping(self):
        self.assertEqual(qr_payload({"qr_type": "url", "qr_value": "https://example.com"}), "https://example.com")
        self.assertEqual(qr_payload({"qr_type": "text", "qr_value": "Helló, világ!"}), "Helló, világ!")
        text = qr_payload({"qr_type": "wifi", "ssid": r'A;B:C\D,"E"',
                           "wifi_password": r"pass;:\word", "wifi_security": "WPA",
                           "wifi_hidden": True})
        self.assertIn(r'S:A\;B\:C\\D\,\"E\"', text)
        self.assertIn(r'P:pass\;\:\\word', text)
        self.assertIn("H:true", text)
        self.assertEqual(qr_payload({"qr_type": "wifi", "ssid": "Guest",
                                     "wifi_security": "nopass"}), "WIFI:T:nopass;S:Guest;H:false;;")
        self.assertTrue(qr_payload({"qr_type": "contact", "contact_name": "Jóska",
                                    "contact_phone": "+3612345678"}).startswith("MECARD:N:"))
        self.preview("qr", {"lang": "hu", "qr_type": "wifi",
                            "ssid": "CellnetGuest", "wifi_security": "nopass"})

    def test_qr_rejects_bad_protocol_and_missing_essentials(self):
        cases = [
            {"qr_type": "url", "qr_value": "javascript:alert(1)"},
            {"qr_type": "url", "qr_value": "example.org"},
            {"qr_type": "wifi", "ssid": "Secret", "wifi_security": "WPA"},
            {"qr_type": "wifi", "ssid": "", "wifi_security": "nopass"},
            {"qr_type": "contact", "contact_name": "No number"},
            {"qr_type": "weird", "qr_value": "https://example.org"},
        ]
        for data in cases:
            with self.subTest(data=data):
                response = self.client.post("/api/generate", json={
                    "kind": "qr", "data": data
                })
                self.assertEqual(response.status_code, 400)

    def test_checklists_render_one_actual_checkbox_per_task(self):
        import app as app_module
        boxes = []
        draw_rect = Receipt().d.rectangle
        # Observability of wrapping with original text, including newlines.
        observed = []
        original = Receipt.text
        def capture(receipt, value, *args, **kwargs):
            observed.append(value)
            return original(receipt, value, *args, **kwargs)
        with patch.object(Receipt, "text", capture):
            self.preview("checklist", {"lang": "hu", "title": "Ellenőrzés",
                                        "items": "- Első\n- Második\n[ ] Harmadik\n4. Negyedik"})
        for word in ("Első", "Második", "Harmadik", "Negyedik"):
            self.assertEqual(observed.count(word), 1)

    def test_cheat_sheets_and_custom_hungarian_text(self):
        for lang in ("en", "hu"):
            for topic in CHEATSHEETS[lang]:
                with self.subTest(lang=lang, topic=topic):
                    self.preview("cheatsheet", {"lang": lang, "sheet": topic})
        self.preview("cheatsheet", {"lang": "hu", "sheet": "custom",
                      "title": "Saját puska", "items": "Első sor\nMásodik sor\nHarmadik sor"})

    def test_warranty_category_thresholds_and_certificate_information(self):
        for gross, years, cert in (
            (9999, None, False), (10000, 2, False),
            (100000, 2, False), (100001, 2, True),
            (250000, 2, True), (250001, 3, True),
        ):
            with self.subTest(gross=gross):
                result = legal_terms({"product": "Test", "price_huf": str(gross),
                                      "sale_kind": "new_eligible"})
                self.assertEqual(result["mandatory_years"], years)
                self.assertEqual(result["certificate_required"], cert)
        for category in ("new_other", "used", "unknown"):
            result = legal_terms({"product": "Test", "price_huf": "999999",
                                  "sale_kind": category})
            self.assertIsNone(result["mandatory_years"])

    def test_legal_slip_never_claims_to_be_warranty_certificate(self):
        observed = []
        real_text = Receipt.text
        def capture(receipt, value, *args, **kwargs):
            observed.append(value)
            return real_text(receipt, value, *args, **kwargs)
        with patch.object(Receipt, "text", capture):
            self.preview("legal", {"lang": "en", "seller": "Cellnet Kft.",
                                    "product": "Laptop", "price_huf": "249000",
                                    "sale_kind": "new_eligible", "sale_channel": "distance"})
        self.assertIn("NEM JÓTÁLLÁSI JEGY", observed)
        joined = " ".join(str(v) for v in observed)
        self.assertIn("2 év kötelező jótállás", joined)
        self.assertIn("jótállási jegy átadása", joined)
        self.assertIn("14 napos", joined)
        self.assertNotIn("NO REFUNDS", joined)

    def test_parts_deposit_legal_fork(self):
        base = {"seller": "Cellnet Kft.", "customer": "Test Person",
                "part": "A specific charger", "total_huf": "27000",
                "paid_huf": "9000"}
        adv = parts_order_terms({**base, "payment_kind": "advance"})
        self.assertEqual(adv["balance_huf"], 18000)
        self.assertEqual(adv["payment_kind"], "advance")
        self.preview("deposit", {**base, "payment_kind": "advance"})
        foglalo = parts_order_terms({**base, "payment_kind": "earnest",
                                    "earnest_agreed": True})
        self.assertEqual(foglalo["payment_kind"], "earnest")
        self.preview("deposit", {**base, "payment_kind": "earnest",
                                  "earnest_agreed": True})
        for bad in (
            {"payment_kind": "earnest"},
            {"payment_kind": "earnest", "earnest_agreed": "true"},
            {"payment_kind": "advance", "paid_huf": "29000"},
            {"payment_kind": "advance", "paid_huf": "-1"},
        ):
            response = self.client.post("/api/generate", json={
                "kind": "deposit", "data": {**base, **bad}
            })
            self.assertEqual(response.status_code, 400, response.get_json())

    def test_no_auto_print_and_ui_accessible(self):
        for kind in ("qr", "checklist", "note", "cheatsheet", "legal", "deposit"):
            self.assertEqual(self.client.post("/api/print", json={
                "id": "not-generated", "kind": kind
            }).status_code, 400)
        html = self.client.get("/").get_data(as_text=True)
        for needle in ('id:"qr"', 'id:"checklist"', 'id:"note"',
                       'id:"cheatsheet"', 'id:"legal"', 'id:"deposit"',
                       'earnest_agreed', 'qr_type', 'legal', 'NEM jótállási jegy'):
            self.assertIn(needle, html)


if __name__ == "__main__":
    unittest.main()
