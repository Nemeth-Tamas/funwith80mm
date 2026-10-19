"""Local-only bridge to the existing trusted Raspberry Pi EagleEye PTZ API."""
import json
import os
import urllib.error
import urllib.request
from flask import Blueprint, jsonify, request

bp = Blueprint("eagle_ptz", __name__, url_prefix="/api/eagle-ptz")
HOSTS = {"lan": "http://192.168.1.201:8765", "vpn": "http://10.10.10.11:8765"}
PATHS = {"state": ("GET", "/api/state"), "health": ("GET", "/api/health"),
         "home": ("POST", "/api/home"), "nudge": ("POST", "/api/nudge"),
         "set": ("POST", "/api/set"), "presets": ("GET", "/api/presets"),
         "goto": ("POST", "/api/presets/goto")}
RANGES = {"pan_degrees": (-170, 170), "tilt_degrees": (-30, 90),
          "zoom_percent": (0, 100), "pan_delta_degrees": (-15, 15),
          "tilt_delta_degrees": (-15, 15), "zoom_delta_percent": (-15, 15)}
ALLOWED = {"nudge": {"pan_delta_degrees", "tilt_delta_degrees", "zoom_delta_percent", "zoom_aware"},
           "set": {"pan_degrees", "tilt_degrees", "zoom_percent"}, "goto": {"name"}}

@bp.route("/<action>", methods=["GET", "POST"])
def dispatch(action):
    if os.environ.get("THERMAL_CHAOS_CAMERA") != "1":
        return jsonify(error="Indítsd a start_eagle_eye.bat fájlt."), 404
    if action not in PATHS:
        return jsonify(error="Unknown command"), 404
    method, path = PATHS[action]
    if request.method != method:
        return jsonify(error="Wrong HTTP method"), 405
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify(error="Local access only"), 403
    if request.headers.get("Origin") not in (None, "http://127.0.0.1:8765", "http://localhost:8765"):
        return jsonify(error="Invalid origin"), 403
    location = request.args.get("host", "lan")
    if location not in HOSTS:
        return jsonify(error="Invalid PTZ host"), 400
    payload = None
    if method == "POST":
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) - ALLOWED.get(action, set()):
            return jsonify(error="Invalid PTZ payload"), 400
        if action == "goto":
            name = body.get("name")
            if not isinstance(name, str) or not (1 <= len(name) <= 60):
                return jsonify(error="Invalid preset"), 400
            payload = {"name": name}
        elif action == "home":
            payload = {}
        else:
            payload = {}
            for name, value in body.items():
                if name == "zoom_aware":
                    if not isinstance(value, bool):
                        return jsonify(error="Invalid zoom-aware value"), 400
                else:
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        return jsonify(error="Invalid PTZ number"), 400
                    low, high = RANGES[name]
                    if not low <= value <= high:
                        return jsonify(error="PTZ value outside safe range"), 400
                payload[name] = value
    try:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(HOSTS[location] + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=2) as response:
            result = response.read(65536)
        return jsonify(json.loads(result))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return jsonify(error="Pi PTZ unavailable: " + str(error)), 502
