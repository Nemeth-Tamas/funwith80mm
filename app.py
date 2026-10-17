"""Thermal Chaos — tiny, offline-friendly Windows USB receipt-printer playground."""
import base64
import io
import os
import random
import re
import time
import uuid
from collections import OrderedDict
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(ROOT / "static"))
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
WIDTH = 576  # 80 mm / 203 DPI ESC/POS raster width (72 bytes)
CACHE = OrderedDict()
CACHE_LIMIT = 35

def font(size=27, bold=False, mono=False):
    if os.name == "nt":
        names = (["consolab.ttf", "consola.ttf"] if mono else
                 ["arialbd.ttf", "arial.ttf"] if bold else ["arial.ttf"])
        candidates = [Path("C:/Windows/Fonts") / n for n in names]
    else:
        candidates = []
    candidates += [Path("/usr/share/fonts/truetype/dejavu") /
                   ("DejaVuSansMono.ttf" if mono else "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")]
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size)
        except OSError:
            continue
    return ImageFont.load_default()

class Receipt:
    def __init__(self):
        self.im = Image.new("L", (WIDTH, 6000), 255)
        self.d = ImageDraw.Draw(self.im)
        self.y = 18
        self.margin = 24
        self.right = WIDTH - self.margin

    def height(self, f):
        bbox = self.d.textbbox((0, 0), "Ag", font=f)
        return max(18, bbox[3] - bbox[1] + 8)

    def text(self, value, size=26, bold=False, align="left", gap=5, mono=False):
        value = str(value)
        f = font(size, bold, mono)
        maxw = self.right - self.margin
        for paragraph in value.split("\n"):
            words = paragraph.split()
            lines, cur = [], ""
            if not words:
                lines = [""]
            for word in words:
                candidate = (cur + " " + word).strip()
                if self.d.textlength(candidate, font=f) <= maxw:
                    cur = candidate
                else:
                    if cur:
                        lines.append(cur)
                    cur = word
                    # Very long unbroken words are split to avoid clipping.
                    while self.d.textlength(cur, font=f) > maxw:
                        cut = len(cur) - 1
                        while cut > 1 and self.d.textlength(cur[:cut], font=f) > maxw:
                            cut -= 1
                        lines.append(cur[:cut])
                        cur = cur[cut:]
            if cur:
                lines.append(cur)
            for line in lines:
                x = self.margin
                w = self.d.textlength(line, font=f)
                if align == "center":
                    x = max(self.margin, (WIDTH - w) / 2)
                elif align == "right":
                    x = self.right - w
                self.d.text((int(x), self.y), line, fill=0, font=f)
                self.y += self.height(f) + gap
        return self

    def space(self, pixels=16):
        self.y += pixels
        return self

    def rule(self, heavy=False):
        self.y += 9
        self.d.line((self.margin, self.y, self.right, self.y), fill=0, width=4 if heavy else 2)
        self.y += 16
        return self

    def heading(self, category, name):
        self.text("THERMAL CHAOS", 22, True, "center", gap=2)
        self.text(category.upper(), 19, False, "center").rule()
        self.text(name.upper(), 36, True, "center", gap=4).rule(True)
        return self

    def pair(self, left, right):
        f = font(25, False, True)
        self.d.text((self.margin, self.y), str(left)[:21], font=f, fill=0)
        rw = self.d.textlength(str(right), font=f)
        self.d.text((self.right-rw, self.y), str(right), font=f, fill=0)
        self.y += 39
        return self

    def sudoku(self, solution, grid):
        side = 504
        c = side // 9
        x0 = (WIDTH - c * 9) // 2
        y0 = self.y
        for n in range(10):
            thick = 5 if n % 3 == 0 else 2
            x = x0 + n*c
            y = y0 + n*c
            self.d.line((x, y0, x, y0+9*c), fill=0, width=thick)
            self.d.line((x0, y, x0+9*c, y), fill=0, width=thick)
        f = font(31, True)
        for row in range(9):
            for col in range(9):
                value = grid[row][col]
                if value:
                    s = str(value)
                    self.d.text((int(x0+col*c+(c-self.d.textlength(s,font=f))/2),
                                 int(y0+row*c+9)), s, font=f, fill=0)
        self.y += 9*c + 17
        return self

    def photo(self, photo):
        photo = photo.convert("L")
        w, h = photo.size
        if h > 1150:
            photo = photo.resize((w, 1150))
            w, h = photo.size
        if self.y + h + 120 > self.im.height:
            raise ValueError("Photo is too tall for one receipt")
        self.im.paste(photo, ((WIDTH-w)//2, self.y))
        self.y += h + 15
        return self

    def footer(self, message="PAPER WAS HARMED IN THIS EXPERIMENT"):
        self.rule()
        self.text(message, 17, False, "center", gap=2)
        self.y += 50
        if self.y > 5900:
            raise ValueError("Receipt is too tall")
        return self.im.crop((0, 0, WIDTH, self.y)).point(lambda p: 0 if p < 155 else 255)

def choice(seq):
    return random.choice(seq)

INSULTS = {
    "gentle": [
        "You are doing great. By the standards of a particularly confused toaster.",
        "Your ambition is inspiring. Your execution has filed for annual leave.",
        "Your productivity has the unmistakable energy of a Windows update stuck at 99%.",
        "Even your procrastination is running behind schedule.",
        "Somewhere, a progress bar is working harder than you."
    ],
    "mean": [
        "You bought a printer to outsource the one thing you do consistently: wasting paper.",
        "Your browser has 38 tabs open and not one contains a completed task.",
        "You have the troubleshooting skills of a wizard and the time management of a potato.",
        "Your printer has completed more jobs today than your entire to-do list.",
        "You can configure BGP but somehow cannot configure a normal bedtime."
    ],
    "nuclear": [
        "BREAKING: Local genius automates insults because even self-criticism was too much manual labor.",
        "Your greatest uptime achievement is a machine you forgot to turn off.",
        "You are a one-person IT department with enterprise-grade chaos and zero change management.",
        "You spent more effort optimizing this receipt than your actual daily routine.",
        "This machine prints at incredible speed, yet cannot process the sheer magnitude of your unfinished projects."
    ],
    "existential": [
        "One day the universe will forget every achievement. But this thermal receipt will fade first.",
        "You are the temporary system administrator of a biological machine with no rollback.",
        "The entropy of the universe grows. So does your pile of USB cables.",
        "Your life is a beta release with no documentation and a terrifyingly long issue tracker.",
        "Civilizations rise and fall. Windows still asks whether you want to restart now."
    ]
}
QUESTS = {
    "easy": [
        "Find an obsolete cable. Explain why you still own it.",
        "Give one of your devices a ridiculous official name.",
        "Organize exactly five items. No more. No less.",
        "Find the oldest battery-powered gadget nearby.",
        "Make a perfect cup of tea or coffee, then rate it like a benchmark."
    ],
    "medium": [
        "Find three completely different USB connector types in the house.",
        "Build a tiny sculpture from spare cables. Give it a technical datasheet.",
        "Locate one device that has never received a firmware update.",
        "Draw a circuit diagram for an appliance that does not need one.",
        "Solve a real problem without buying any additional equipment."
    ],
    "hard": [
        "Identify five things you could repair with the tools already on hand.",
        "Create a museum label for the least impressive object in the room.",
        "Design an absurd new keyboard shortcut and demonstrate it.",
        "Make a 30-second documentary about the life of a single screw.",
        "Invent a useless IoT device, including a complete feature list."
    ]
}
RIDDLES = [
    ("What has keys but cannot open any locks?", "A keyboard"),
    ("I speak without a mouth and hear without ears. What am I?", "An echo"),
    ("What gets wetter the more it dries?", "A towel"),
    ("What has many teeth but never bites?", "A comb"),
    ("The more you take away from me, the bigger I get. What am I?", "A hole"),
    ("What travels around the world while staying in one corner?", "A stamp")
]
MYSTERIES = [
    "The security camera recorded you entering the room. It did not record you leaving. You are reading this outside.",
    "A device has answered a ping. Its power cable was removed yesterday.",
    "The printer received a job dated tomorrow. The author field contains your name.",
    "There are nine devices on the network. The inventory lists eight. The ninth lists itself as the router.",
    "At 03:14, the system logged a backup restore. No backup was ever created.",
    "The camera sees a person standing behind the monitor. The monitor is facing the wall.",
    "A maintenance ticket was opened by a technician who has not been born yet.",
    "The drive has zero free space. The only file is named YOU_ARE_HERE.txt."
]
CERTS = [
    ("EXPERT PROCRASTINATOR", "For outstanding work on a task that has not yet begun."),
    ("USB CABLE ARCHIVIST", "For preserving cables of uncertain origin and doubtful future use."),
    ("CERTIFIED CHAOS ENGINEER", "For maintaining systems in a state of creative disorder."),
    ("MASTER OF THE RESTART", "For solving difficult problems through strategic power cycling."),
    ("UNLICENSED GENIUS", "For demonstrating confidence unsupported by the available evidence."),
    ("SLEEP SCHEDULE REBEL", "For refusing to accept the tyranny of conventional bedtime.")
]
FLIGHT_TASKS = {
    "whoop": [
        "Hover steadily at eye level for 15 seconds in a safe, clear area.",
        "Fly three controlled figure-eights through open space.",
        "Land precisely on a marked pad three times.",
        "Fly a smooth rectangular circuit, then reverse direction.",
        "Practice gentle coordinated turns without altitude hunting."
    ],
    "camera": [
        "Record a smooth, low-speed reveal shot in a permitted open area.",
        "Film a steady orbit around an inanimate landmark with safe clearance.",
        "Capture a cinematic forward tracking shot with constant speed.",
        "Fly a gentle S-shaped camera path and compare three takes.",
        "Practice stable framing on a fixed object in open space."
    ],
    "five": [
        "Perform five precise takeoffs and landings in an open area.",
        "Fly slow straight lines with deliberate heading control.",
        "Practice consistent altitude through four wide turns.",
        "Execute a smooth figure-eight, prioritizing control over speed.",
        "Record a clean, low-speed freestyle line without risky proximity."
    ]
}
FICTIONAL_SHOPS = [
    ("ACME INTERDIMENSIONAL", [("POCKET BLACK HOLE", 499), ("PORTABLE WORMHOLE", 1200), ("TIME REFUND", -15)]),
    ("DEPARTMENT OF NONSENSE", [("BUREAUCRACY LICENSE", 98), ("FORM 42-B", 14), ("QUEUE PRIORITY", 710)]),
    ("GALACTIC TECH SUPPORT", [("REBOOT THE MOON", 360), ("SUN DRIVER UPDATE", 880), ("ERROR 404 REPAIR", 404)]),
    ("DRAGON PARTS DEPOT", [("FIREWALL DRAGON", 925), ("SPARE WING KIT", 199), ("SMOKE TEST", 75)]),
    ("COSMIC CONVENIENCE", [("BOTTLED NOTHING", 100), ("ONE EXTRA TUESDAY", 450), ("GRAVITY REFILL", 99)])
]

def make_sudoku(level):
    # Sudoku solved base, with randomized permutations preserving valid rows/columns/boxes.
    pattern = lambda r, c: (3*(r % 3) + r//3 + c) % 9
    def shuffled(seq):
        return random.sample(seq, len(seq))
    rows = [g*3+r for g in shuffled([0,1,2]) for r in shuffled([0,1,2])]
    cols = [g*3+c for g in shuffled([0,1,2]) for c in shuffled([0,1,2])]
    nums = shuffled(list(range(1,10)))
    solved = [[nums[pattern(r,c)] for c in cols] for r in rows]
    grid = [r[:] for r in solved]
    blanks = {"easy": 35, "medium": 46, "hard": 54}.get(level, 46)
    for i in random.sample(range(81), blanks):
        grid[i//9][i%9] = 0
    return solved, grid

def make_photo(src, effect):
    if not isinstance(src, str) or "," not in src:
        raise ValueError("Choose a picture first")
    raw = base64.b64decode(src.split(",", 1)[1], validate=True)
    if len(raw) > 6_000_000:
        raise ValueError("Image must be smaller than 6 MB")
    try:
        im = Image.open(io.BytesIO(raw))
        im = ImageOps.exif_transpose(im)
        im.thumbnail((WIDTH-48, 1150), Image.Resampling.LANCZOS)
        if im.width < 1 or im.height < 1:
            raise ValueError("Empty image")
        im = ImageOps.autocontrast(im.convert("L"))
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError("That image format is not supported") from e
    if effect == "negative":
        im = ImageOps.invert(im)
    if effect == "threshold":
        im = im.point(lambda p: 0 if p < 128 else 255)
    elif effect == "newsprint":
        im = im.quantize(colors=2, dither=Image.Dither.FLOYDSTEINBERG).convert("L")
    else:
        im = im.convert("1", dither=Image.Dither.FLOYDSTEINBERG).convert("L")
    return im

def build(kind, data):
    r = Receipt()
    answer = None
    meta = ""
    if kind == "insult":
        level = str(data.get("level", "mean")).lower()
        level = level if level in INSULTS else "mean"
        r.heading("Annual performance audit", "YOU HAVE BEEN ROASTED")
        r.text("SEVERITY: " + level.upper(), 22, True).rule()
        r.text(choice(INSULTS[level]), 30, True)
        r.space(15).text("ASSESSMENT: NEEDS COFFEE / RESTART", 18)
        r.text("SIGNED: YOUR DISAPPOINTED PRINTER", 18)
        meta = "One professionally unhelpful insult"
    elif kind == "quest":
        level = str(data.get("level", "medium")).lower()
        level = level if level in QUESTS else "medium"
        r.heading("Unsolicited side mission", "CHAOS QUEST")
        r.pair("DIFFICULTY", level.upper()).rule()
        r.text(choice(QUESTS[level]), 30, True)
        r.space(20).pair("XP REWARD", {"easy":"10", "medium":"30", "hard":"100"}[level])
        r.pair("FAILURE PENALTY", "MILD SHAME")
        meta = "A completely unnecessary objective"
    elif kind == "puzzle":
        level = str(data.get("level", "medium")).lower()
        level = level if level in ("easy", "medium", "hard") else "medium"
        puzzle_type = str(data.get("type", "random")).lower()
        if puzzle_type == "random":
            puzzle_type = choice(["sudoku","math","cipher","riddle"])
        r.heading("Tiny brain gym", puzzle_type + " / " + level)
        if puzzle_type == "sudoku":
            solution, board = make_sudoku(level)
            r.text("Fill 1-9 in each row, column & 3x3 box.", 21).space(10)
            r.sudoku(solution, board)
            answer = "\n".join(" ".join(map(str,row)) for row in solution)
        elif puzzle_type == "math":
            a = random.randint(5, 25) * (1 if level=="easy" else 3)
            delta = random.randint(2, 9) * (1 if level != "hard" else 2)
            sequence = [a + delta*i*i for i in range(5)]
            r.text("Complete the sequence:", 25).space(14)
            r.text("   ".join(map(str,sequence)) + "   ?", 28, True)
            answer = str(a + delta*25) + " (add " + str(delta) + " times the square of the position)"
        elif puzzle_type == "cipher":
            shift = random.randint(1, 25)
            plain = choice(["THE CAKE IS A LIE", "TRUST THE PRINTER", "REBOOT EVERYTHING", "HIDE THE CABLES", "THE SIGNAL IS LOST"])
            enc = "".join(chr((ord(ch)-65+shift)%26+65) if "A"<=ch<="Z" else ch for ch in plain)
            r.text("Caesar cipher: decode this message.", 23).space(15)
            r.text(enc, 29, True).space(16)
            r.text("Hint: every letter was shifted by the same amount.", 20)
            answer = plain + " (shift back " + str(shift) + ")"
        else:
            question, answer = choice(RIDDLES)
            r.text(question, 29, True)
        r.space(20).text("ANSWER AVAILABLE IN WEB APP", 19, False, "center")
        meta = "Solution stays off the paper until requested"
    elif kind == "photo":
        r.heading("Grainy memories department", "THERMAL PHOTO")
        r.photo(make_photo(data.get("image"), str(data.get("effect", "dither"))))
        r.text("INSTANT PHOTOGRAPH / 0% COLOR", 18, False, "center")
        meta = "A monochrome instant photo"
    elif kind == "mystery":
        r.heading("Fictional horror transmission", "SIGNAL UNKNOWN")
        r.pair("SOURCE", choice(["CH-09", "LOCALHOST", "VOID", "PORT 666"]))
        r.pair("PRIORITY", choice(["BLACK", "REDACTED", "UNDEFINED"])).rule()
        r.text(choice(MYSTERIES), 28, True)
        r.space(20).text("END TRANSMISSION // FICTION", 20)
        meta = "A deliberately creepy fictional incident"
    elif kind == "certificate":
        title, description = choice(CERTS)
        name = re.sub(r"[\x00-\x1f]", "", str(data.get("name", "")).strip())[:56] or "THE BEARER"
        r.heading("Office of dubious honors", "CERTIFICATE")
        r.text("THIS OFFICIALLY CERTIFIES", 22, False, "center").space(14)
        r.text(name.upper(), 35, True, "center").space(16)
        r.text("IS NOW A", 23, False, "center").space(8)
        r.text(title, 31, True, "center").space(20)
        r.text(description, 24, False, "center")
        r.space(24).rule(True)
        r.text("APPROVED BY THE COUNCIL OF", 18, False, "center")
        r.text("QUESTIONABLE QUALIFICATIONS", 18, True, "center")
        meta = "A completely worthless honorary certificate"
    elif kind == "fpv":
        craft = str(data.get("craft","Meteor75 Pro II"))[:50]
        mode = ("camera" if "Avata" in craft else "five" if "MM-001" in craft else "whoop")
        r.heading("FPV skill challenge", "MISSION BRIEF")
        r.text("AIRCRAFT: " + craft, 22, True).rule()
        r.text(choice(FLIGHT_TASKS[mode]), 29, True)
        r.space(16).text("RULES: Fly legally, maintain clearance, keep a spotter when required, and abort if unsafe.", 19)
        r.space(14).pair("REWARD", str(random.choice([25,50,75,100])) + " XP")
        meta = "A safe training flight challenge"
    elif kind == "fake":
        shop, products = choice(FICTIONAL_SHOPS)
        r.text("!!! PARODY / NOT A REAL RECEIPT !!!", 21, True, "center").rule(True)
        r.text(shop, 30, True, "center").space(10)
        r.text("FICTIONAL TRANSACTION / VOID", 19, False, "center").rule()
        total = 0
        for label, price in products:
            qty = random.randint(1, 3)
            amount = qty*price
            total += amount
            r.text(str(qty) + "x " + label, 22, True)
            r.pair("  " + str(price) + " CHAOS", str(amount))
        r.rule().pair("TOTAL CHAOS CREDITS", str(total)).rule(True)
        r.text("PAYMENT: IMAGINATION", 23, True)
        r.text("AUTH CODE: " + str(random.randint(100000,999999)), 19)
        r.text("NOT VALID FOR PURCHASES, ACCOUNTING OR TAX", 19, True, "center")
        meta = "A prominently fictional comedy receipt"
    elif kind == "answer":
        value = re.sub(r"[\x00-\x1f]", " ", str(data.get("answer","")))[:900]
        if not value.strip():
            raise ValueError("No puzzle solution available")
        r.heading("The secret appendix", "PUZZLE ANSWER")
        r.text(value, 23, True)
        meta = "Solution slip"
    else:
        raise ValueError("Unknown print mode")
    return r.footer(), answer, meta

def usb_printers():
    if os.name != "nt":
        return []
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        names = {entry[2] for entry in win32print.EnumPrinters(flags)}
        result = []
        for name in names:
            handle = None
            try:
                handle = win32print.OpenPrinter(name)
                info = win32print.GetPrinter(handle, 2)
                port = str(info.get("pPortName") or "")
                # Never select a Wi-Fi or network queue. Normal Windows USB
                # printers are USB001/USB002; some drivers use DOT4.
                if port.upper().startswith(("USB", "DOT4")):
                    result.append({"name": name, "port": port})
            except Exception:
                pass
            finally:
                if handle is not None:
                    win32print.ClosePrinter(handle)
        return sorted(result, key=lambda e: (not any(k in e["name"].lower() for k in ("birch","cp-q","pos","receipt")), e["name"].lower()))
    except ImportError:
        return []

def escpos_bytes(im, cut=True):
    # GS v 0: standard ESC/POS monochrome raster; one means BLACK.
    if im.width != WIDTH or im.height > 5900:
        raise ValueError("Invalid receipt dimensions")
    im = im.convert("L").point(lambda p: 0 if p < 160 else 255, mode="1")
    result = bytearray(b"\x1b@\x1ba\x00")
    width_bytes = WIDTH // 8
    for top in range(0, im.height, 128):
        section = im.crop((0, top, WIDTH, min(top+128, im.height)))
        h = section.height
        raster = bytes(p ^ 255 for p in section.tobytes())
        result += b"\x1dv0\x00" + bytes((width_bytes & 255, width_bytes >> 8, h & 255, h >> 8)) + raster
    result += b"\n\n"
    if cut:
        result += b"\x1dV\x00"  # Full cut; hardware can ignore if unsupported.
    return bytes(result)

def send_usb(printer_name, img, cut):
    import win32print
    allowed = {p["name"] for p in usb_printers()}
    if printer_name not in allowed:
        raise ValueError("Select a locally connected Windows USB printer")
    h = win32print.OpenPrinter(printer_name)
    try:
        job = win32print.StartDocPrinter(h, 1, ("Thermal Chaos", None, "RAW"))
        try:
            win32print.StartPagePrinter(h)
            try:
                written = win32print.WritePrinter(h, escpos_bytes(img, cut))
                if not written:
                    raise OSError("Windows accepted zero printer bytes")
            finally:
                win32print.EndPagePrinter(h)
        finally:
            win32print.EndDocPrinter(h)
    finally:
        win32print.ClosePrinter(h)

@app.get("/")
def index():
    return send_from_directory(str(ROOT / "static"), "index.html")

@app.get("/api/printers")
def printers():
    return jsonify({"printers": usb_printers(), "windows": os.name=="nt"})

@app.post("/api/generate")
def generate():
    body = request.get_json(silent=True) or {}
    try:
        img, answer, description = build(str(body.get("kind", "")), body.get("data") or {})
        stream = io.BytesIO()
        img.save(stream, "PNG")
        payload = stream.getvalue()
        key = uuid.uuid4().hex
        now = time.time()
        for old in list(CACHE):
            if CACHE[old][0] < now-3600:
                CACHE.pop(old, None)
        CACHE[key] = (now, payload)
        while len(CACHE)>CACHE_LIMIT:
            CACHE.popitem(last=False)
        return jsonify({"id":key, "image":"data:image/png;base64,"+base64.b64encode(payload).decode("ascii"),
                        "answer":answer, "description":description})
    except (ValueError, TypeError, OSError, OverflowError) as e:
        return jsonify({"error":str(e)}), 400

@app.post("/api/print")
def do_print():
    body = request.get_json(silent=True) or {}
    item = CACHE.get(str(body.get("id","")))
    if not item or item[0] < time.time()-3600:
        return jsonify({"error":"Preview expired. Generate a new one."}), 400
    try:
        im = Image.open(io.BytesIO(item[1]))
        send_usb(str(body.get("printer","")), im, bool(body.get("cut", True)))
        return jsonify({"ok":True, "message":"Sent to Windows USB print queue"})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

if __name__ == "__main__":
    print("\nTHERMAL CHAOS - open http://127.0.0.1:8765")
    print("Windows USB printer queues only. Press Ctrl+C to stop.\n")
    app.run(host="127.0.0.1",port=8765,debug=False,threaded=True)
