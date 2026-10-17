"""Opt-in USB souvenir workflow. Camera access stays in the local browser.

One participant at a time; no files, recognition, network-camera APIs or
automatic printing. The existing photo renderer and Windows spooler are reused.
"""
import base64
import binascii
import io
import secrets
import threading
import time
from urllib.parse import urlsplit

from flask import Blueprint, jsonify, request
from PIL import Image, UnidentifiedImageError
from wanted_posters import wanted_profile


class CameraWorkflow:
    ARM_SECONDS = 120
    PHOTO_SECONDS = 300

    def __init__(self, enabled, render, send):
        self.enabled = enabled
        self.render = render
        self.send = send
        self.lock = threading.RLock()
        self.timer = None
        self.session = None
        self.blueprint = Blueprint("camera", __name__)
        self._routes()

    def clear(self):
        with self.lock:
            if self.timer:
                self.timer.cancel()
            self.timer = None
            self.session = None

    def _expire(self, token):
        with self.lock:
            if (self.session and self.session["token"] == token and
                    time.monotonic() >= self.session["deadline"]):
                self.clear()

    def _deadline(self, seconds):
        if self.timer:
            self.timer.cancel()
        self.session["deadline"] = time.monotonic() + seconds
        self.timer = threading.Timer(seconds, self._expire,
                                     args=(self.session["token"],))
        self.timer.daemon = True
        self.timer.start()

    def _session(self, body):
        if self.session and time.monotonic() >= self.session["deadline"]:
            self.clear()
        if (not self.session or not isinstance(body.get("token"), str) or
                not secrets.compare_digest(body["token"], self.session["token"])):
            raise ValueError("A munkamenet lejárt. Élesíts újra a résztvevő beleegyezésével.")
        return self.session

    def _poster(self, options, reroll=True):
        s = self.session
        try:
            pad = int(options.get("pad_mm", s.get("pad_mm", 20)))
        except (ValueError, TypeError):
            raise ValueError("Érvénytelen alsó ráhagyás.")
        if pad not in (12, 20, 30):
            raise ValueError("Az alsó ráhagyás 12, 20 vagy 30 mm lehet.")
        try:
            gamma = float(options.get("photo_gamma", s.get("gamma", 1.6)))
        except (TypeError, ValueError):
            raise ValueError("Érvénytelen világosság.") from None
        if not 1 <= gamma <= 2.5:
            raise ValueError("A világosság 1 és 2,5 között lehet.")
        record = (wanted_profile("hu", options.get("wanted_alias", ""), theme="shop")
                  if reroll else s["record"])
        img, _, description = self.render("photo", {
            "image": s["snapshot"], "effect": "mostwanted", "lang": "hu",
            "wanted_theme": "shop", "wanted_alias": options.get("wanted_alias", ""),
            "pad_mm": pad, "photo_gamma": gamma,
        }, record)
        output = io.BytesIO()
        img.save(output, "PNG")
        s["poster"] = output.getvalue()
        s["preview_id"] = secrets.token_hex(16)
        s["record"] = record
        s["gamma"] = gamma
        s["pad_mm"] = pad
        s["phase"] = "preview"
        return {"id": s["preview_id"],
                "image": "data:image/png;base64," + base64.b64encode(s["poster"]).decode("ascii"),
                "description": description,
                "photo_gamma": gamma,
                "expires_in": max(0, int(s["deadline"] - time.monotonic()))}

    @staticmethod
    def _snapshot(value):
        if not isinstance(value, str) or len(value) > 8_000_000:
            raise ValueError("Hiányzó vagy túl nagy fénykép.")
        try:
            header, encoded = value.split(",", 1)
            if header not in ("data:image/jpeg;base64", "data:image/png;base64"):
                raise ValueError()
            raw = base64.b64decode(encoded, validate=True)
            if len(raw) > 6_000_000:
                raise ValueError()
            with Image.open(io.BytesIO(raw)) as photo:
                if photo.width * photo.height > 4_000_000 or photo.width < 64 or photo.height < 64:
                    raise ValueError()
                photo.load()
                # Strip metadata; keep just one modest in-memory frame.
                photo = photo.convert("RGB")
                photo.thumbnail((1280, 1280))
                output = io.BytesIO()
                photo.save(output, "JPEG", quality=90)
            return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")
        except (ValueError, OSError, binascii.Error, UnidentifiedImageError,
                Image.DecompressionBombError):
            raise ValueError("A fénykép nem használható. Fotózz újra.") from None

    def _routes(self):
        bp = self.blueprint

        @bp.before_request
        def local_only():
            if (request.remote_addr not in ("127.0.0.1", "::1") or
                    urlsplit(request.host_url).hostname not in ("127.0.0.1", "localhost", "::1")):
                return jsonify(error="Csak ezen a számítógépen használható."), 403
            origin = request.headers.get("Origin")
            if ((origin and origin != request.host_url.rstrip("/")) or
                    request.headers.get("Sec-Fetch-Site") == "cross-site"):
                return jsonify(error="Idegen weboldal nem vezérelheti a kamerát."), 403
            if request.method == "POST" and not isinstance(request.get_json(silent=True), dict):
                return jsonify(error="JSON objektum szükséges."), 400
            if request.path != "/api/camera/status" and not self.enabled():
                return jsonify(error="A kamera mód ki van kapcsolva. Indítsd a start_eagle_eye.bat fájlt."), 404

        @bp.after_request
        def private(response):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response

        @bp.get("/api/camera/status")
        def status():
            return jsonify(enabled=bool(self.enabled()), arm_seconds=self.ARM_SECONDS,
                           photo_seconds=self.PHOTO_SECONDS, aiming="manual-usb")

        @bp.post("/api/camera/<action>")
        def action(action):
            body = request.get_json()
            with self.lock:
                try:
                    if action == "arm":
                        if body.get("consent") is not True or body.get("participant_only") is not True:
                            raise ValueError("A résztvevő beleegyezése és elkülönített képmező szükséges.")
                        if self.session and time.monotonic() >= self.session["deadline"]:
                            self.clear()
                        if self.session:
                            return jsonify(error="Már van aktív fotózás. Előbb Mégse, vagy várd meg a lejáratot."), 409
                        self.session = {"token": secrets.token_hex(32), "phase": "armed"}
                        self._deadline(self.ARM_SECONDS)
                        return jsonify(token=self.session["token"], expires_in=self.ARM_SECONDS)
                    s = self._session(body)
                    if action == "cancel":
                        self.clear()
                        return jsonify(ok=True)
                    if action == "capture":
                        if s["phase"] != "armed":
                            raise ValueError("Egy élesítéssel csak egy fénykép készülhet.")
                        snapshot = self._snapshot(body.get("image"))
                        s["snapshot"] = snapshot
                        self._deadline(self.PHOTO_SECONDS)
                        try:
                            return jsonify(self._poster(body))
                        except Exception:
                            self.clear()
                            raise
                    if action in ("reroll", "adjust"):
                        if s["phase"] != "preview":
                            raise ValueError("Előbb fényképet kell készíteni.")
                        return jsonify(self._poster(body, reroll=action == "reroll"))
                    if action == "print":
                        if (s["phase"] != "preview" or body.get("confirm_print") is not True or
                                body.get("id") != s["preview_id"]):
                            raise ValueError("A jelenlegi előnézet külön Nyomtatás kattintást igényel.")
                        if not isinstance(body.get("printer"), str) or not body["printer"].strip():
                            raise ValueError("Válassz Windows blokknyomtatót.")
                        try:
                            with Image.open(io.BytesIO(s["poster"])) as image:
                                self.send(body["printer"], image, bool(body.get("cut", True)))
                        except Exception:
                            return jsonify(error="Nyomtatóhiba. Újrapróbálás előtt ellenőrizd a papírt és a Windows sort; részleges nyomtatás történhetett."), 503
                        self.clear()
                        return jsonify(ok=True, message="A Windows nyomtatási sor átvette. A fotót töröltük.")
                    raise ValueError("Ismeretlen kamera művelet.")
                except (ValueError, TypeError, OSError, OverflowError) as exc:
                    return jsonify(error=str(exc)), 400
