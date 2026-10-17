"""Offline, 80 mm utility receipts and cautious Hungarian consumer-rights handouts.

The legal slip supplements a durable document. It is deliberately NOT a
warranty certificate (jótállási jegy), invoice, cash receipt, or contract.
Reviewed against the 2026-03-01 consolidated 151/2003 Korm. rendelet,
10/2024 IM, 19/2014 NGM, Ptk 6:163, 45/2014 Korm. rendelet.
"""
from datetime import datetime
import re
import qrcode
from PIL import Image

UTILITY_KINDS = frozenset(("qr", "checklist", "note", "cheatsheet", "legal"))

CHEATSHEETS = {
    "en": {
        "subnet": ("IPv4 SUBNETTING", [
            "/24 = 255.255.255.0 = 254 hosts",
            "/25 = 255.255.255.128 = 126 hosts",
            "/26 = 255.255.255.192 = 62 hosts",
            "/27 = 255.255.255.224 = 30 hosts",
            "/28 = 255.255.255.240 = 14 hosts",
            "/29 = 255.255.255.248 = 6 hosts",
            "/30 = 255.255.255.252 = 2 hosts",
            "Usable IPv4 hosts usually 2^(32-prefix)-2; /31 and /32 differ.",
            "RFC1918: 10/8, 172.16/12, 192.168/16.",
        ]),
        "windows": ("WINDOWS QUICK COMMANDS", [
            "ipconfig /all — address and DNS",
            "ipconfig /flushdns — clear DNS resolver",
            "ping HOST — test ICMP reachability",
            "tracert HOST — trace route",
            "nslookup HOST — query DNS",
            "whoami — current identity",
            "tasklist — running processes",
            "sfc /scannow — system file verification (admin)",
            "Get-NetIPConfiguration (PowerShell)",
        ]),
        "linux": ("LINUX QUICK COMMANDS", [
            "ip a — network addresses",
            "ip route — routes and gateways",
            "ss -tulpen — listening sockets",
            "df -h — mounted disk free space",
            "free -h — memory usage",
            "journalctl -xe — recent system log",
            "systemctl status NAME — service",
            "du -sh PATH — folder size",
            "find PATH -type f — list files",
        ]),
        "mikrotik": ("MIKROTIK READ-ONLY CHEAT SHEET", [
            "/ip/address/print — configured IPs",
            "/ip/route/print — routing table",
            "/ip/dhcp-server/lease/print — leases",
            "/interface/print — interfaces",
            "/interface/wireguard/print — WG tunnels",
            "/interface/wireguard/peers/print — WG peers",
            "/ip/firewall/filter/print — filter rules",
            "/log/print — logs",
            "/system/resource/print — resource usage",
        ]),
        "python": ("PYTHON QUICK REFERENCE", [
            "print('Hello') — output",
            "name = input('Name? ') — string input",
            "value = int('42') — integer conversion",
            "if x > 5: ... — branch",
            "for x in range(5): ... — iteration",
            "items.append(x) — extend a list",
            "len(items) — number of items",
            "def greet(name): return name — function",
            "with open('a.txt', encoding='utf-8') as f: ...",
        ]),
        "csharp": ("C# QUICK REFERENCE", [
            "Console.WriteLine(value);",
            "string name = Console.ReadLine() ?? \"\";",
            "int.TryParse(input, out int number);",
            "var items = new List<int>();",
            "items.Add(42);",
            "foreach (var x in items) { ... }",
            "var evens = items.Where(x => x % 2 == 0);",
            "File.ReadAllLines(\"file.txt\");",
            "class Item { public int Id { get; set; } }",
        ]),
        "electronics": ("ELECTRONICS POCKET MATH", [
            "Ohm: U = I x R",
            "Power: P = U x I = I^2 x R",
            "Series R: R_total = R1 + R2 + ...",
            "Parallel R: 1/R_total = sum(1/Ri)",
            "Series C: 1/C_total = sum(1/Ci)",
            "Parallel C: C_total = C1 + C2 + ...",
            "1 kOhm = 1000 Ohm",
            "1 mA = 0.001 A",
            "Always de-energize before resistance tests.",
        ]),
    },
    "hu": {
        "subnet": ("IPV4 ALHÁLÓZATOK", [
            "/24 = 255.255.255.0 = 254 gép",
            "/25 = 255.255.255.128 = 126 gép",
            "/26 = 255.255.255.192 = 62 gép",
            "/27 = 255.255.255.224 = 30 gép",
            "/28 = 255.255.255.240 = 14 gép",
            "/29 = 255.255.255.248 = 6 gép",
            "/30 = 255.255.255.252 = 2 gép",
            "Jellemző gépszám: 2^(32-prefix)-2; /31 és /32 kivétel.",
            "Privát hálózatok: 10/8, 172.16/12, 192.168/16.",
        ]),
        "windows": ("WINDOWS PARANCSOK", [
            "ipconfig /all — IP- és DNS-adatok",
            "ipconfig /flushdns — DNS-gyorsítótár törlése",
            "ping CÍM — elérhetőségteszt",
            "tracert CÍM — útvonalkövetés",
            "nslookup NÉV — DNS-lekérdezés",
            "whoami — bejelentkezett felhasználó",
            "tasklist — folyamatok",
            "sfc /scannow — rendszerellenőrzés (admin)",
            "Get-NetIPConfiguration (PowerShell)",
        ]),
        "linux": ("LINUX PARANCSOK", [
            "ip a — hálózati címek",
            "ip route — útvonalak",
            "ss -tulpen — figyelő portok",
            "df -h — szabad lemezterület",
            "free -h — memóriahasználat",
            "journalctl -xe — napló",
            "systemctl status NÉV — szolgáltatás",
            "du -sh ÚTVONAL — mappaméret",
            "find ÚTVONAL -type f — fájlok",
        ]),
        "mikrotik": ("MIKROTIK OLVASÓ PARANCSOK", [
            "/ip/address/print — IP-címek",
            "/ip/route/print — útvonalak",
            "/ip/dhcp-server/lease/print — bérletek",
            "/interface/print — interfészek",
            "/interface/wireguard/print — WG-kapcsolatok",
            "/interface/wireguard/peers/print — WG-peerek",
            "/ip/firewall/filter/print — szabályok",
            "/log/print — napló",
            "/system/resource/print — erőforrások",
        ]),
        "python": ("PYTHON PUSKA", [
            "print('Szia!') — kiírás",
            "nev = input('Név? ') — szöveges bemenet",
            "ertek = int('42') — egész szám",
            "if x > 5: ... — elágazás",
            "for x in range(5): ... — ciklus",
            "lista.append(x) — lista bővítése",
            "len(lista) — elemek száma",
            "def koszon(nev): return nev — függvény",
            "with open('a.txt', encoding='utf-8') as f: ...",
        ]),
        "csharp": ("C# PUSKA", [
            "Console.WriteLine(ertek);",
            "string nev = Console.ReadLine() ?? \"\";",
            "int.TryParse(szoveg, out int szam);",
            "var lista = new List<int>();",
            "lista.Add(42);",
            "foreach (var x in lista) { ... }",
            "lista.Where(x => x % 2 == 0);",
            "File.ReadAllLines(\"adat.txt\");",
            "class Elem { public int Id { get; set; } }",
        ]),
        "electronics": ("ELEKTRONIKAI KÉPLETEK", [
            "Ohm-törvény: U = I x R",
            "Teljesítmény: P = U x I = I^2 x R",
            "Soros R: R_össz = R1 + R2 + ...",
            "Párhuzamos R: 1/R_össz = sum(1/Ri)",
            "Soros C: 1/C_össz = sum(1/Ci)",
            "Párhuzamos C: C_össz = C1 + C2 + ...",
            "1 kOhm = 1000 Ohm",
            "1 mA = 0,001 A",
            "Ellenállást csak feszültségmentesítve mérj!",
        ]),
    }
}

LEGAL_SOURCES = (
    "151/2003. (IX. 22.) Korm. rendelet 2-4. §, 3/A. §",
    "10/2024. (VI. 28.) IM rendelet 1. melléklet",
    "Ptk. 6:163. §; 19/2014. (IV. 29.) NGM rendelet",
    "45/2014. (II. 26.) Korm. rendelet 20. §",
)


def _value(data, name, limit, required=False):
    value = data.get(name, "")
    if not isinstance(value, str):
        raise ValueError(f"{name}: text required")
    value = re.sub(r"[\x00-\x1f\x7f]", " ", value).strip()
    if len(value) > limit:
        raise ValueError(f"{name}: too long (max {limit})")
    if required and not value:
        raise ValueError(f"{name}: required")
    return value


def _heading(r, kind, lang):
    h = {
        "qr": ("QR CODE FACTORY", "QR-KÓD GYÁR"),
        "checklist": ("POCKET CHECKLIST", "ZSEBES ELLENŐRZŐLISTA"),
        "note": ("QUICK NOTE", "GYORS EMLÉKEZTETŐ"),
        "cheatsheet": ("POCKET CHEAT SHEET", "ZSEB-PUSKA"),
    }
    en, hu = h[kind]
    # Keep subtitles short enough for the actual 80mm render.
    r.text("THERMAL TOOLBOX", 19, True, "center").rule()
    r.text(hu if lang == "hu" else en, 30, True, "center").rule(True)


def _item(r, value, checkbox=True):
    start = r.y
    if checkbox:
        r.d.rectangle((r.margin, start + 7, r.margin + 27, start + 34),
                      outline=0, width=3)
    old_margin = r.margin
    try:
        r.margin += 45 if checkbox else 4
        r.text(value, 23 if checkbox else 22, False, gap=4)
    finally:
        r.margin = old_margin
    r.y = max(r.y + 10, start + 48)


def _wifi_escape(value):
    # Android/iOS Wi-Fi QR field escaping; backslash must be FIRST.
    return (value.replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace(":", "\\:")
            .replace('"', '\\"'))


def qr_payload(data):
    kind = data.get("qr_type", "url")
    if kind == "url":
        value = _value(data, "qr_value", 1200, required=True)
        if not value.lower().startswith(("https://", "http://")):
            raise ValueError("URL must start with http:// or https://")
    elif kind == "text":
        value = _value(data, "qr_value", 1200, required=True)
    elif kind == "wifi":
        ssid = _value(data, "ssid", 100, required=True)
        password = _value(data, "wifi_password", 100)
        encryption = data.get("wifi_security", "WPA")
        if encryption not in ("WPA", "WEP", "nopass"):
            raise ValueError("Invalid Wi-Fi security")
        if encryption != "nopass" and not password:
            raise ValueError("Wi-Fi password is required")
        hidden = "true" if data.get("wifi_hidden") is True else "false"
        value = ("WIFI:T:" + encryption + ";S:" + _wifi_escape(ssid) + ";"
                 + (("P:" + _wifi_escape(password) + ";") if encryption != "nopass" else "")
                 + "H:" + hidden + ";;")
    elif kind == "contact":
        name = _value(data, "contact_name", 100, required=True)
        phone = _value(data, "contact_phone", 60)
        email = _value(data, "contact_email", 160)
        if not phone and not email:
            raise ValueError("Provide at least a phone or email")
        if email and ("@" not in email or any(ch.isspace() for ch in email)):
            raise ValueError("Invalid email")
        def esc(s):
            return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
        # MECARD is compact enough for reliable thermal QR scanning.
        value = "MECARD:N:" + esc(name) + ";" + ("TEL:" + phone + ";" if phone else "") + (
            "EMAIL:" + email + ";" if email else "") + ";"
    else:
        raise ValueError("Unknown QR type")
    if len(value.encode("utf-8")) > 1450:
        raise ValueError("QR data too long to scan reliably on thermal paper")
    return value


def legal_terms(data):
    """Statutory information; deliberately no personalized legal document."""
    product = _value(data, "product", 110, required=True)
    seller = _value(data, "seller", 115)
    sale_kind = data.get("sale_kind", "unknown")
    if sale_kind not in ("new_eligible", "new_other", "used", "unknown"):
        raise ValueError("Choose a valid product category")
    channel = data.get("sale_channel", "store")
    if channel not in ("store", "distance"):
        raise ValueError("Choose a valid sales channel")
    price = data.get("price_huf")
    if isinstance(price, bool) or not isinstance(price, (int, float, str)):
        raise ValueError("Enter the gross price in HUF")
    try:
        gross = int(price)
    except (ValueError, TypeError, OverflowError):
        raise ValueError("Enter a whole-number HUF price")
    if gross < 1 or gross > 1_000_000_000 or str(gross) != str(price).strip():
        raise ValueError("Enter a positive whole-number HUF price")
    result = {
        "product": product, "seller": seller,
        "price_huf": gross, "sale_kind": sale_kind, "sale_channel": channel,
        "mandatory_years": None, "certificate_required": False,
    }
    if sale_kind == "new_eligible" and gross >= 10000:
        result["mandatory_years"] = 2 if gross <= 250000 else 3
        result["certificate_required"] = gross > 100000
    return result


def draw_utility(kind, data, r, lang):
    """Render into existing Receipt; caller handles cached preview and bottom feed."""
    hu = lang == "hu"
    tx = lambda en, h: h if hu else en
    if kind == "qr":
        payload = qr_payload(data)
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=8, border=4)
        qr.add_data(payload)
        try:
            qr.make(fit=True)
        except qrcode.exceptions.DataOverflowError as e:
            raise ValueError("QR code is too large") from e
        modules = qr.modules_count + 8
        if modules > 130:
            raise ValueError("QR code too dense for reliable thermal scanning")
        image = qr.make_image(fill_color="black", back_color="white").convert("L")
        width = 448 if modules <= 73 else 504
        image = image.resize((width, width), Image.Resampling.NEAREST)
        _heading(r, kind, lang)
        caption = _value(data, "title", 64) or tx("SCAN ME", "OLVASS BE!")
        r.text(caption, 26, True, "center").space(10)
        r.photo(image)
        if data.get("qr_type") == "wifi":
            r.text(tx("Wi-Fi access", "Wi-Fi csatlakozás"), 22, True, "center")
            r.text(_value(data, "ssid", 100), 22, False, "center")
        else:
            hint = _value(data, "qr_value", 120)
            if hint:
                r.text(hint, 17, False, "center")
        return tx("Scannable QR card", "Beolvasható QR-kódos kártya")

    if kind == "checklist":
        title = _value(data, "title", 76) or tx("TODAY'S CHECKLIST", "MAI ELLENŐRZŐLISTA")
        raw = _value(data, "items", 2200, required=True)
        lines = [re.sub(r"^(?:\s*[-*•]|\s*\[\s*\]|\s*\d+[.)])\s*", "", x).strip()
                 for x in raw.split(" | ")] if "|" in raw and "\n" not in str(data.get("items","")) else [
                 re.sub(r"^(?:\s*[-*•]|\s*\[\s*\]|\s*\d+[.)])\s*", "", x).strip()
                 for x in str(data.get("items", "")).splitlines()]
        # Keep exact original newlines for checklists; don't let arbitrary text
        # inject 1000 blank rows or overflow the receipt canvas.
        lines = [x for x in lines if x]
        if not 1 <= len(lines) <= 28:
            raise ValueError("Checklist must have 1 to 28 non-empty lines")
        if any(len(x) > 125 for x in lines):
            raise ValueError("Each task must be at most 125 characters")
        _heading(r, kind, lang)
        r.text(title, 28, True).rule()
        for item in lines:
            _item(r, item)
        r.rule()
        r.text(tx("DONE IS BETTER THAN PERFECT.", "A KÉSZ JOBB, MINT A TÖKÉLETES."), 19,
               False, "center")
        return tx("Printable checklist", "Nyomtatható ellenőrzőlista")

    if kind == "note":
        title = _value(data, "title", 76) or tx("DO NOT FORGET", "NE FELEJTSD EL!")
        message = _value(data, "message", 1100, required=True)
        emphasis = data.get("note_size", "normal")
        if emphasis not in ("normal", "large"):
            raise ValueError("Invalid note size")
        _heading(r, kind, lang)
        r.text(title, 34, True, "center").rule()
        r.text(message, 38 if emphasis == "large" else 29, True)
        if data.get("timestamp") is True:
            r.space(14).text(datetime.now().strftime("%Y-%m-%d %H:%M"), 19, False, "right")
        return tx("Instant desktop reminder", "Gyors asztali emlékeztető")

    if kind == "cheatsheet":
        topic = data.get("sheet", "subnet")
        if topic == "custom":
            title = _value(data, "title", 70) or tx("MY CHEAT SHEET", "SAJÁT PUSKA")
            raw = _value(data, "items", 2000, required=True)
            lines = [x.strip() for x in str(data.get("items", "")).splitlines() if x.strip()]
            if not 1 <= len(lines) <= 30 or any(len(x) > 140 for x in lines):
                raise ValueError("Cheat sheet needs 1–30 lines up to 140 characters each")
        elif topic in CHEATSHEETS[lang]:
            title, lines = CHEATSHEETS[lang][topic]
        else:
            raise ValueError("Unknown cheat sheet")
        _heading(r, kind, lang)
        r.text(title, 26, True).rule()
        for entry in lines:
            _item(r, entry, checkbox=False)
        return tx("Pocket technical reference", "Zsebben hordható műszaki puska")

    if kind == "legal":
        if lang not in ("en", "hu"):
            raise ValueError("Unknown language")
        terms = legal_terms(data)
        # Hungarian statute applies; print customer-facing legal information
        # in Hungarian even if operator is using the English UI.
        r.text("CELLNET // VÁSÁRLÓI TÁJÉKOZTATÓ", 22, True, "center")
        r.rule(True)
        r.text("NEM JÓTÁLLÁSI JEGY", 30, True, "center")
        r.rule()
        if terms["seller"]:
            r.text("Eladó: " + terms["seller"], 20)
        r.text("Termék: " + terms["product"], 21, True)
        r.text("Bruttó vételár: " + f'{terms["price_huf"]:,}'.replace(",", " ") + " Ft", 20)
        r.rule()
        r.text("KELLÉKSZAVATOSSÁG", 24, True)
        if terms["sale_kind"] == "used":
            r.text("Fogyasztói vásárlásnál főszabály szerint 2 év. Használt termék esetén a felek megállapodhatnak rövidebb, de legalább 1 éves időben.", 20)
        else:
            r.text("Fogyasztói vásárlásnál a kellékszavatossági igény főszabály szerint 2 évig érvényesíthető.", 20)
        r.text("Hibás teljesítésnél a vevőt törvény szerinti kijavítási, kicserélési, megfelelő esetben árleszállítási vagy szerződésmegszüntetési jogok illethetik meg.", 20)
        r.rule()
        r.text("KÖTELEZŐ JÓTÁLLÁS", 24, True)
        yrs = terms["mandatory_years"]
        if yrs is None:
            if terms["sale_kind"] == "new_eligible":
                r.text("A megadott ár nem éri el a kötelező jótállás 10 000 Ft-os küszöbét. Ettől a kellékszavatossági jogok megmaradnak.", 20)
            else:
                r.text("Ezen adatlap alapján kötelező jótállási idő nem állapítható meg. A termékkör, az állapot és az esetleges vállalt jótállás külön ellenőrizendő.", 20)
        else:
            r.text("Megjelölt termékkör esetén: " + str(yrs) + " év kötelező jótállás.", 22, True)
            if terms["certificate_required"]:
                r.text("100 000 Ft felett szabályos jótállási jegy átadása szükséges. EZ A NYOMAT NEM AZ.", 20, True)
            else:
                r.text("100 000 Ft-ig külön jótállási jegy nem kötelező; az előírt adatokat a jótállás végéig olvasható formában kell biztosítani. A jogok a fizetési bizonylattal érvényesíthetők.", 19)
        r.text("A jótállás nem érinti a jogszabályból eredő jogokat.", 20, True)
        r.rule()
        r.text("VISSZAVÉTEL / ELÁLLÁS", 23, True)
        if terms["sale_channel"] == "store":
            r.text("Üzletben vásárolt hibátlan terméknél nincs általános, indokolás nélküli 14 napos elállási jog; ez nem korlátozza a hibás teljesítés miatti igényeket.", 19)
        else:
            r.text("Távollévők között / üzlethelyiségen kívül kötött szerződésnél főszabály szerint 14 napos indokolás nélküli elállási jog van, jogszabályi kivételekkel.", 19)
        r.rule()
        r.text("IGÉNYÉRVÉNYESÍTÉS", 23, True)
        r.text("Őrizze meg a számlát vagy nyugtát. A jótállási igény nem tehető az eredeti csomagolás visszaadásától függővé.", 19)
        r.text("Fogyasztói jogvita esetén békéltető testület eljárása is kezdeményezhető.", 19)
        r.rule()
        r.text("KIEGÉSZÍTŐ TÁJÉKOZTATÓ", 19, True, "center")
        r.text("A hőpapír idővel kifakulhat. A jogszabály szerint előírt tartósan olvasható tájékoztatást és az esetleges jótállási jegyet külön kell biztosítani. Ez a lap nem számla, nyugta, jótállási jegy vagy teljes ÁSZF.", 18)
        r.text("Jogszabályok: 151/2003. Korm. r.; 10/2024. IM r.; Ptk. 6:163. §; 45/2014. Korm. r.", 16)
        return "Magyar fogyasztói jogok - kiegészítő tájékoztató (NEM jótállási jegy)"

    raise ValueError("Unknown utility mode")
