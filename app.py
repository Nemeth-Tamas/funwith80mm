"""Thermal Chaos — local Windows receipt-printer playground (USB or network)."""
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
from content import BANK
from extra_library import EXTRA
from chaos_games import GAMES, BINGO_THEMES, bingo_card
from psych_horror import PSYCHOLOGICAL_HORROR
from wanted_posters import WANTED, wanted_profile

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
        f = font(size + 1, bold, mono)
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

    def bingo(self, cells):
        """Printable 5x5 game card. Custom compact text only inside this grid."""
        if len(cells) != 25:
            raise ValueError("Bingo requires 25 squares")
        left, cell_width, cell_height = 28, 104, 118
        self.y += 9
        letter_face = font(29, True)
        for col, letter in enumerate("BINGO"):
            center = left + col * cell_width + cell_width / 2
            width = self.d.textlength(letter, font=letter_face)
            self.d.text((int(center-width/2), self.y), letter, font=letter_face, fill=0)
        self.y += 47
        top = self.y

        def wrap_square(value, face, line_width):
            result, current = [], ""
            for word in value.split():
                remaining = word
                # Long Hungarian compound words must still fit in their square.
                while self.d.textlength(remaining, font=face) > line_width:
                    if current:
                        result.append(current)
                        current = ""
                    stop = 1
                    while (stop < len(remaining) and
                           self.d.textlength(remaining[:stop+1], font=face) <= line_width):
                        stop += 1
                    result.append(remaining[:stop])
                    remaining = remaining[stop:]
                if not remaining:
                    continue
                candidate = (current + " " + remaining).strip()
                if self.d.textlength(candidate, font=face) <= line_width:
                    current = candidate
                else:
                    if current:
                        result.append(current)
                    current = remaining
            if current:
                result.append(current)
            return result

        for index, value in enumerate(cells):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Bingo squares must contain text")
            row, col = divmod(index, 5)
            x = left + col*cell_width
            y = top + row*cell_height
            self.d.rectangle((x, y, x+cell_width, y+cell_height),
                             outline=0, width=3 if index == 12 else 2)
            for font_size in (17, 16, 15, 14, 13):
                face = font(font_size, index == 12)
                lines = wrap_square(value, face, cell_width-12)
                line_height = max(19, self.height(face)-2)
                if len(lines) <= 5 and len(lines)*line_height <= cell_height-10:
                    break
            else:
                raise ValueError("A bingo square cannot fit on 80 mm paper")
            text_y = y + (cell_height - len(lines)*line_height)/2
            for line in lines:
                text_width = self.d.textlength(line, font=face)
                self.d.text((int(x+(cell_width-text_width)/2), int(text_y)),
                            line, font=face, fill=0)
                text_y += line_height
        self.y = top + 5*cell_height + 15
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

    def footer(self, message="THERMAL CHAOS", pad_mm=20):
        if message:
            self.rule()
            self.text(message, 17, False, "center", gap=2)
        # 203 DPI is about eight raster rows per millimetre.
        # This extra white area lands AFTER the last text and BEFORE the cut.
        self.y += int(max(12, min(36, pad_mm)) * 8)
        if self.y > 5900:
            raise ValueError("Receipt is too tall")
        return self.im.crop((0, 0, WIDTH, self.y)).point(lambda p: 0 if p < 180 else 255)

def choice(seq):
    return random.choice(seq)

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
        if effect == "mostwanted":
            # A genuine fixed-size mugshot crop: crop before dithering so
            # portrait detail stays legible on 203 DPI thermal paper.
            im = ImageOps.fit(im.convert("RGB"), (448, 548),
                              method=Image.Resampling.LANCZOS,
                              centering=(0.5, 0.42))
        else:
            im.thumbnail((WIDTH-48, 1150), Image.Resampling.LANCZOS)
        if im.width < 1 or im.height < 1:
            raise ValueError("Empty image")
        im = ImageOps.autocontrast(im.convert("L"))
    except (UnidentifiedImageError, OSError, ValueError) as e:
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

def print_wanted_poster(receipt, photo, lang, alias=None):
    """Compose an obviously fictional, newspaper-like 80 mm wanted poster."""
    copy = WANTED[lang]
    record = wanted_profile(lang, alias)

    receipt.text(copy["agency"], 19, True, "center", gap=3)
    receipt.rule(True).space(3)

    # Proper dramatic black title bar with light reversed text.
    label = copy["heading"]
    title_font = font(41, True)
    bar_top = receipt.y
    bar_height = 69
    receipt.d.rectangle((receipt.margin, bar_top, receipt.right,
                         bar_top + bar_height), fill=0)
    title_width = receipt.d.textlength(label, font=title_font)
    receipt.d.text((int((WIDTH-title_width)/2), bar_top+10), label,
                   fill=255, font=title_font)
    receipt.y += bar_height + 13

    receipt.text(copy["file"], 18, True, "center", gap=2)
    receipt.text("CASE " + record["case"], 23, True, "center").space(10)

    # Frame + image intentionally use the same cached, previewed bitmap.
    x = (WIDTH-photo.width)//2
    y = receipt.y
    receipt.d.rectangle((x-7, y-7, x+photo.width+7, y+photo.height+7),
                        fill=255, outline=0, width=4)
    receipt.photo(photo)
    receipt.text(copy["photo"], 17, False, "center", gap=3)

    for field in ("alias", "charges", "seen", "reward", "note"):
        receipt.space(7)
        receipt.text(copy[field], 18, True, gap=1)
        receipt.text(record[field], 25 if field != "note" else 21,
                     field in ("alias", "charges"), gap=2)
    receipt.space(12).rule(True)
    receipt.text(copy["footer"], 17, True, "center", gap=3)
    return receipt


def build(kind, data):
    if not isinstance(data, dict):
        raise ValueError("Invalid options")
    lang = "hu" if data.get("lang") == "hu" else "en"
    hu = lang == "hu"
    bank = BANK[lang]
    r = Receipt()
    answer = None
    meta = ""
    def tx(en, hungarian):
        return hungarian if hu else en

    if kind == "insult":
        level = str(data.get("level", "mean")).lower()
        level = level if level in bank["insults"] else "mean"
        r.heading(tx("Personnel audit", "Személyzeti ellenőrzés"),
                  tx("ROASTED", "LEOLTÁS"))
        r.text(tx("DAMAGE LEVEL: ", "SÉRÜLÉS MÉRTÉKE: ") + level.upper(), 21, True).rule()
        r.text(choice(bank["insults"][level]), 29, True)
        r.space(15).text(tx("OFFICIAL VERDICT: YOU ASKED FOR THIS.", "HIVATALOS DÖNTÉS: TE KÉRTED."), 19)
        meta = tx("A freshly served personal disaster", "Friss, személyre szabott katasztrófa")
    elif kind == "quest":
        level = str(data.get("level", "medium")).lower()
        level = level if level in bank["quests"] else "medium"
        r.heading(tx("Mandatory optional mission", "Kötelező opcionális küldetés"),
                  tx("CHAOS QUEST", "KÁOSZKÜLDETÉS"))
        r.pair(tx("DIFFICULTY", "NEHÉZSÉG"), level.upper()).rule()
        r.text(choice(bank["quests"][level]), 28, True)
        r.space(18).pair("XP", {"easy":"10", "medium":"40", "hard":"150"}[level])
        r.pair(tx("FAILURE", "BUKÁS"), tx("SHAME", "SZÉGYEN"))
        meta = tx("Absolutely unsolicited quest", "Teljesen kéretlen küldetés")
    elif kind == "puzzle":
        level = str(data.get("level", "medium")).lower()
        level = level if level in ("easy", "medium", "hard") else "medium"
        puzzle_type = str(data.get("type", "random")).lower()
        if puzzle_type == "random":
            puzzle_type = choice(["sudoku", "math", "cipher", "riddle"])
        if puzzle_type not in ("sudoku", "math", "cipher", "riddle"):
            raise ValueError("Unknown puzzle type")
        r.heading(tx("Pocket-sized brain damage", "Zsebre vágható agytorna"),
                  {"sudoku":"SUDOKU", "math":tx("NUMBER CODE", "SZÁMSOR"),
                   "cipher":tx("CIPHER", "REJTVÉNY"), "riddle":tx("RIDDLE", "TALÁLÓS KÉRDÉS")}[puzzle_type])
        if puzzle_type == "sudoku":
            solution, board = make_sudoku(level)
            r.text(tx("Fill 1-9 in each row, column and 3x3 box.", "Minden sorban, oszlopban és 3x3-as mezőben legyen 1-9."), 21).space(10)
            r.sudoku(solution, board)
            answer = "\n".join(" ".join(map(str, row)) for row in solution)
        elif puzzle_type == "math":
            a = random.randint(5, 25) * (1 if level == "easy" else 3)
            delta = random.randint(2, 9) * (1 if level != "hard" else 2)
            sequence = [a + delta*i*i for i in range(5)]
            r.text(tx("Find the next number:", "Mi a következő szám?"), 25).space(14)
            r.text("   ".join(map(str, sequence)) + "   ?", 27, True)
            answer = str(a + delta*25) + tx(" (quadratic sequence)", " (négyzetes számsor)")
        elif puzzle_type == "cipher":
            shift = random.randint(1, 25)
            plain = choice(["THE CAKE IS A LIE", "TRUST THE PRINTER", "REBOOT EVERYTHING", "HIDE THE CABLES", "THE SIGNAL IS LOST"])
            if hu:
                plain = choice(["EZ CSAK EGY TESZT", "A NYOMTATO FIGYEL", "INDITS MINDENT UJRA", "REJTSD EL A KABELT", "A JEL ELTUNT"])
            enc = "".join(chr((ord(ch)-65+shift)%26+65) if "A"<=ch<="Z" else ch for ch in plain)
            r.text(tx("Decode the Caesar cipher:", "Fejtsd meg a Caesar-kódot:"), 23).space(15)
            r.text(enc, 29, True).space(16)
            r.text(tx("Every letter was shifted by the same amount.", "Minden betűt ugyanannyival eltoltunk."), 20)
            answer = plain + tx(" (shift back ", " (eltolás visszafelé: ") + str(shift) + ")"
        else:
            question, answer = choice(bank["riddles"])
            r.text(question, 29, True)
        r.space(20).text(tx("ANSWER IN WEB APP", "MEGOLDÁS A WEBOLDALON"), 19, False, "center")
        meta = tx("Puzzles without instant spoilers", "Rejtvény azonnali spoiler nélkül")
    elif kind == "photo":
        effect = str(data.get("effect", "dither"))
        if effect == "mostwanted":
            photo = make_photo(data.get("image"), "mostwanted")
            print_wanted_poster(r, photo, lang, data.get("wanted_alias"))
            meta = tx("Parody most-wanted mugshot poster",
                      "Paródia körözési poszter fekete-fehér fotóval")
        else:
            r.heading(tx("Badly remembered memories", "Pixeles emlékek osztálya"),
                      tx("THERMAL PHOTO", "HŐNYOMAT"))
            r.photo(make_photo(data.get("image"), effect))
            r.text(tx("YOUR MEMORIES NOW HAVE ONLY TWO COLORS", "MOSTANTÓL KÉT SZÍNBŐL ÁLL AZ ÉLETED"), 17, False, "center")
            meta = tx("Gloriously grainy instant photo", "Dicsőségesen szemcsés fénykép")
    elif kind == "mystery":
        r.heading(tx("Unexplained technical incident", "Megmagyarázhatatlan incidens"),
                  tx("UNKNOWN SIGNAL", "ISMERETLEN JEL"))
        r.pair(tx("SOURCE", "FORRÁS"), choice(["CH-09", "LOCALHOST", "VOID", "PORT 666"]))
        r.pair(tx("LEVEL", "SZINT"), choice(["BLACK", "RED", "UNDEFINED"])).rule()
        r.text(choice(bank["mysteries"]), 28, True)
        r.space(12).text(tx("END TRANSMISSION", "ADÁS VÉGE"), 18)
        meta = tx("Something is terribly wrong with the network", "Valami nagyon nincs rendben a hálózattal")
    elif kind == "horror":
        # Minimalist micro-horror: no long preamble to ruin the scare.
        r.text(choice(["03:17", "02:04", "03:33", "UNKNOWN", "NO SIGNAL"]) if not hu
               else choice(["03:17", "02:04", "03:33", "ISMERETLEN", "NINCS JEL"]),
               19, True).rule(True)
        r.space(14).text(choice(bank["horror"]), 33, True)
        r.space(10)
        meta = tx("A very short nightmare", "Nagyon rövid rémálom")
    elif kind == "psychhorror":
        # Psychological horror uses a quiet heading and no jaunty footer.
        # A short receipt feels more like an unsolicited discovery.
        r.text(tx("THE PART YOU DON'T REMEMBER", "AMIRE NEM EMLÉKSZEL"),
               20, True, "center").rule(True)
        r.space(14)
        r.text(choice(PSYCHOLOGICAL_HORROR[lang]), 31, True)
        r.space(12)
        meta = tx("Psychological horror: memories, identity, and impossible details",
                  "Pszichológiai horror: emlékek, identitás és lehetetlen részletek")
    elif kind in ("psyops", "patch", "prophecy", "complaint", "future"):
        body = choice(EXTRA[lang][kind])
        if kind == "psyops":
            # Fictional black-file style without a jokey signature.
            r.heading(tx("Cognitive compliance department", "Kognitív Megfelelőségi Osztály"),
                      "PSYOPS")
            r.pair(tx("FILE", "ÜGYIRAT"), f"PSY-{random.randint(1000, 9999)}")
            r.pair(tx("STATUS", "ÁLLAPOT"), tx("RESTRICTED", "KORLÁTOZOTT"))
            r.rule(True).space(8)
            r.text(body, 29, True).space(16)
            r.text(tx("CONFIRMATION IS NOT REQUIRED.", "VISSZAIGAZOLÁS NEM SZÜKSÉGES."), 17, True, "center")
            meta = tx("A fictional psychological operations notice", "Fiktív pszichológiai műveleti értesítés")
        elif kind == "patch":
            r.heading(tx("Universal change control", "Univerzális változáskezelés"),
                      tx("REALITY PATCH NOTES", "VALÓSÁGFRISSÍTÉS"))
            r.pair("BUILD", f"{random.randint(2000, 9999)}.{random.randint(0, 99)}")
            r.rule()
            r.text(body, 28, True)
            r.space(12).text(tx("RESTART: UNAVAILABLE", "ÚJRAINDÍTÁS: NEM ELÉRHETŐ"), 18)
            meta = tx("A changelog for a defective universe", "Változásnapló egy hibás univerzumhoz")
        elif kind == "prophecy":
            r.heading(tx("Infallible prediction services", "Tévedhetetlen Jóslatok Hivatala"),
                      tx("THE PROPHECY", "A JÓSLAT"))
            r.pair(tx("ACCURACY", "PONTOSSÁG"), f"{random.randint(97, 100)}%")
            r.rule()
            r.text(body, 30, True)
            meta = tx("Unsolicited forecast of questionable accuracy", "Kéretlen és kétes pontosságú előrejelzés")
        elif kind == "complaint":
            r.heading(tx("Bureau of cosmic complaints", "Kozmikus Panaszügyi Főosztály"),
                      tx("FINAL RULING", "VÉGZÉS"))
            r.pair(tx("CASE", "ÜGY"), f"K-{random.randint(10000,99999)}")
            r.rule()
            token = " HATÁROZAT: " if hu else " RULING: "
            if token in body:
                subject, decision = body.split(token, 1)
                r.text(subject, 27, True).space(14)
                r.rule()
                r.text(tx("RULING:", "HATÁROZAT:"), 20, True).space(4)
                r.text(decision, 29, True)
            else:
                r.text(body, 27, True)
            r.space(12).text(tx("THIS DECISION IS UNAPPEALABLE.", "A DÖNTÉS ELLEN FELLEBBEZÉSNEK HELYE NINCS."), 17, False, "center")
            meta = tx("Your formal dispute with existence", "Hivatalos panasz az egész létezés ellen")
        else:
            r.heading(tx("Temporal messaging archive", "Időn Túli Üzenetközpont"),
                      tx("MESSAGE FROM THE FUTURE", "ÜZENET A JÖVŐBŐL"))
            r.pair(tx("DELIVERY", "KÉZBESÍTÉS"), tx("EARLY", "KORAI"))
            r.rule(True).space(8)
            r.text(body, 29, True)
            r.space(12).text(tx("REPLY NOT YET AVAILABLE", "VÁLASZ MÉG NEM LÉTEZIK"), 18)
            meta = tx("A note that hasn't been written yet", "Üzenet, amit még nem írtak meg")
    elif kind == "paranormal":
        observation, verdict = choice(GAMES[lang]["paranormal"])
        r.heading(tx("Paranormal Investigation Bureau", "Paranormális Nyomozóiroda"),
                  tx("INCIDENT REPORT", "INCIDENSJELENTÉS"))
        r.pair(tx("CASE", "ÜGYIRAT"), f"P-{random.randint(10000, 99999)}")
        r.pair(tx("SEVERITY", "VESZÉLY"), choice(["?", "IV", "UNKNOWN"])).rule()
        r.text(tx("REPORTED ANOMALY", "BEJELENTETT JELENSÉG"), 20, True)
        r.space(7).text(observation, 28, True).space(16)
        r.rule()
        r.text(tx("INVESTIGATION RESULT", "VIZSGÁLAT EREDMÉNYE"), 20, True)
        r.space(7).text(verdict, 27, True)
        r.space(10).text(tx("CASE CLOSED. ENTITY DISAPPOINTED.", "ÜGY LEZÁRVA. A SZELLEM CSALÓDOTT."), 17, False, "center")
        meta = tx("A paranormal report with an unexpectedly mundane punchline",
                  "Paranormális ügyirat kellemetlenül hétköznapi megfejtéssel")
    elif kind == "bingo":
        theme = str(data.get("theme", "repair"))
        if theme not in BINGO_THEMES:
            raise ValueError("Unknown bingo theme")
        titles = {
            "repair": tx("IT REPAIR", "SZERVIZKÁOSZ"),
            "customers": tx("CUSTOMERS", "ÜGYFÉLKÁOSZ"),
            "home": tx("HOUSEHOLD", "OTTHONI KÁOSZ"),
            "cosmic": tx("COSMIC", "KOZMIKUS KÁOSZ"),
        }
        r.heading(tx("Paper-based chaos prediction", "Papíralapú káoszelőrejelzés"),
                  "THERMAL BINGO")
        r.text(titles[theme], 23, True, "center").space(6)
        r.bingo(bingo_card(lang, theme))
        r.text(tx("MARK EVENTS AS THEY HAPPEN.", "JELÖLD BE, AMI MEGTÖRTÉNT."), 19, True, "center")
        r.text(tx("FIVE IN A ROW = BINGO!", "ÖT EGY SORBAN = BINGÓ!"), 20, True, "center")
        meta = tx(f"5x5 randomized {theme} bingo with a free center",
                  "5x5-ös, véletlenszerű bingó szabad középső mezővel")
    elif kind == "certificate":
        title, description = choice(bank["certs"])
        name = re.sub(r"[\x00-\x1f]", "", str(data.get("name", "")).strip())[:56] or tx("THE BEARER", "AZ OKLEVÉL TULAJDONOSA")
        r.heading(tx("Office of dubious honors", "Kétes kitüntetések hivatala"),
                  tx("CERTIFICATE", "OKLEVÉL"))
        r.text(tx("THIS CERTIFIES THAT", "EZENNEL TANÚSÍTJUK, HOGY"), 21, False, "center").space(14)
        r.text(name.upper(), 34, True, "center").space(12)
        r.text(tx("HAS BEEN APPOINTED", "ELNYERTE A CÍMET:"), 22, False, "center").space(8)
        r.text(title, 31, True, "center").space(20)
        r.text(description, 24, False, "center")
        r.space(24).rule(True)
        r.text(tx("APPROVED BY THE COMMITTEE", "A BIZOTTSÁG JÓVÁHAGYTA"), 18, True, "center")
        meta = tx("An honor of questionable value", "Megtisztelő, teljesen értéktelen kitüntetés")
    elif kind == "fpv":
        craft = str(data.get("craft", "Meteor75 Pro II"))[:50]
        mode = ("camera" if "Avata" in craft else "five" if "MM-001" in craft else "whoop")
        r.heading(tx("Flight challenge generator", "Repülési kihívásgenerátor"),
                  tx("FPV MISSION", "FPV KÜLDETÉS"))
        r.text(tx("AIRCRAFT: ", "GÉP: ") + craft, 22, True).rule()
        r.text(choice(bank["flight"][mode]), 29, True)
        r.space(14).pair("XP", str(choice([25, 50, 75, 100])))
        r.text(tx("Safe area. Stay legal. Abort if sketchy.", "Biztonságos terület, szabályos repülés. Ha gáz van: leszállás."), 18)
        meta = tx("One objective. One battery. Go.", "Egy feladat. Egy akku. Hajrá.")
    elif kind == "fake":
        shop, products = choice(bank["shops"])
        r.text(tx("FICTIONAL SHOP / PARODY", "KITALÁLT BOLT / PARÓDIA"), 21, True, "center").rule(True)
        r.text(shop, 30, True, "center").space(8)
        r.text(tx("TRANSACTION: PURE NONSENSE", "TRANZAKCIÓ: TELJES KÉPTELENSÉG"), 18, False, "center").rule()
        total = 0
        for label, price in products:
            qty = random.randint(1, 3)
            amount = qty * price
            total += amount
            r.text(str(qty) + "x " + label, 22, True)
            r.pair("  " + str(price) + " CC", str(amount))
        r.rule().pair(tx("TOTAL CC", "ÖSSZES CC"), str(total)).rule(True)
        r.text(tx("PAYMENT: IMAGINATION", "FIZETÉS: KÉPZELET"), 23, True)
        r.text(tx("PARODY / NOT A REAL RECEIPT", "PARÓDIA / NEM VALÓDI NYUGTA"), 19, True, "center")
        meta = tx("Shopping in a broken universe", "Vásárlás egy hibás univerzumban")
    elif kind == "answer":
        value = re.sub(r"[\x00-\x1f]", " ", str(data.get("answer", "")))[:900]
        if not value.strip():
            raise ValueError("No puzzle solution available")
        r.heading(tx("No cheating, allegedly", "Persze, senki sem csalt"),
                  tx("PUZZLE ANSWER", "MEGOLDÁS"))
        r.text(value, 23, True)
        meta = tx("An emergency supply of answers", "Vésztartalék megfejtések")
    else:
        raise ValueError("Unknown print mode")
    try:
        pad_mm = int(data.get("pad_mm", 20))
    except (TypeError, ValueError):
        pad_mm = 20
    footer_text = "" if kind in ("horror", "psychhorror", "psyops", "future") else tx("THERMAL CHAOS // NO REFUNDS", "THERMAL CHAOS // NINCS VISSZATÉRÍTÉS")
    return r.footer(footer_text, pad_mm), answer, meta

def is_eligible_printer(name, port, driver=""):
    """Only show plausible physical queues; exclude obvious PDF/file/fax targets."""
    name, port, driver = str(name).lower(), str(port).lower(), str(driver).lower()
    bad_names = ("microsoft print to pdf", "microsoft xps document writer",
                 "onenote", "adobe pdf", "pdf24", "cutepdf", "foxit pdf",
                 "pdfcreator", "bullzip pdf", "fax")
    bad_ports = ("file:", "portprompt:", "nul:", "shrfax:", "xpsport:")
    if not name.strip() or not port.strip():
        return False
    if any(term in name or term in driver for term in bad_names):
        return False
    if any(port.startswith(part) for part in bad_ports):
        return False
    # Windows physical queues can use USB*, DOT4*, IP_*, WSD-*,
    # host/IP-named ports, Ne00: connections or \\server\printer.
    return True


def windows_printers():
    """List Windows-installed local and shared queues, including network devices."""
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
                driver = str(info.get("pDriverName") or "")
                if is_eligible_printer(name, port, driver):
                    usb = port.upper().startswith(("USB", "DOT4"))
                    kind = "USB" if usb else "Network / Windows"
                    result.append({"name": name, "port": port, "type": kind})
            except Exception:
                pass
            finally:
                if handle is not None:
                    win32print.ClosePrinter(handle)
        return sorted(result, key=lambda e: (
            not any(k in e["name"].lower() for k in ("birch","cp-q","pos","receipt")),
            0 if e["type"] == "USB" else 1, e["name"].lower()
        ))
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

def send_to_windows_printer(printer_name, img, cut):
    import win32print
    allowed = {p["name"] for p in windows_printers()}
    if printer_name not in allowed:
        raise ValueError("Select a Windows-installed receipt printer (USB or network)")
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
    return jsonify({"printers": windows_printers(), "windows": os.name=="nt"})

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
        send_to_windows_printer(str(body.get("printer","")), im, bool(body.get("cut", True)))
        return jsonify({"ok":True, "message":"Sent to selected Windows printer queue"})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

if __name__ == "__main__":
    print("\nTHERMAL CHAOS - open http://127.0.0.1:8765")
    print("Windows-installed USB or network receipt printers. Press Ctrl+C to stop.\n")
    app.run(host="127.0.0.1",port=8765,debug=False,threaded=True)
