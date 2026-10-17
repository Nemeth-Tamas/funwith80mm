"""Fictional most-wanted photo poster content for Thermal Chaos.

No real law-enforcement insignia, warrants, charges or personal information:
all records are plainly whimsical parody for the 80mm printer.
"""
import random
import re

WANTED = {
    "en": {
        "agency": "THERMAL CHAOS // PARODY",
        "heading": "MOST WANTED",
        "file": "FICTIONAL DOSSIER",
        "case_label": "CASE",
        "photo": "SUSPECT IMAGE // 1 BIT",
        "alias": "ALIAS",
        "charges": "WANTED FOR",
        "seen": "LAST SEEN",
        "reward": "REWARD",
        "note": "FIELD NOTE",
        "footer": "ABSURD FICTION // NOT A REAL WARRANT",
        "aliases": [
            "The Cable Goblin", "Adapter Baron", "The Tool Acquirer",
            "Solder Phantom", "The Midnight Debugger", "The Five-Minute Mechanic",
            "Router Whisperer", "The Thermal Menace", "Spare Parts Prophet",
            "Lord of Unfinished Projects", "The Socket Bandit", "The Firmware Gremlin",
            "The USB Archaeologist", "The Bench Goblin", "The Serial Procrastinator",
            "The Invisible Technician", "The Caffeine-Free Disaster",
            "The Last-Minute Engineer", "Captain Sidequest", "The Mystery Connector"
        ],
        "charges": [
            "Aggravated acquisition of completely essential tools",
            "Crimes against innocent cable management",
            "Possession of suspiciously many adapters",
            "Starting projects without finishing the previous twelve",
            "Premeditated hardware tinkering",
            "Unauthorized distribution of USB hubs",
            "Turning a five-minute fix into a three-day incident",
            "Repeated abuse of the words 'quick test'",
            "Possession of a drawer full of unidentified screws",
            "Conspiracy to add Wi-Fi to an ordinary spoon",
            "Reckless firmware flashing before bedtime",
            "Making the printer do things it never consented to",
            "Insufficient resistance to electronics discounts",
            "Illegal levels of confidence near a soldering iron",
            "Unlicensed cable hoarding", "Attempted overclocking of a toaster",
            "Running seventeen unfinished side projects",
            "Destruction of a perfectly normal sleep schedule",
            "Disturbing the peace of a sleeping NAS", "Possession of a cursed USB-C cable"
        ],
        "seen": [
            "At the scene of a suspicious reboot", "Near the Alza checkout",
            "Under a mountain of spare cables", "Beside a blinking MikroTik",
            "At the workbench after midnight", "Near a dismantled laptop",
            "In a drawer marked MISC", "Buying one more screwdriver",
            "Between the NAS and the coffee machine", "At the thermal printer again",
            "Hovering over the firmware upgrade button", "Holding the wrong adapter"
        ],
        "rewards": [
            "8,000 HUF and a coffee", "One slightly used screwdriver",
            "A fresh roll of thermal paper", "Three perfectly sorted cables",
            "Five minutes of uninterrupted sleep", "An authentic mystery screw",
            "One guilt-free tool purchase", "A working USB-C cable",
            "A tiny bag of cable ties", "A completed to-do list"
        ],
        "notes": [
            "Approach with caution. Subject may start a new project.",
            "Known to say: 'I can fix that in five minutes.'",
            "Often armed with zip ties and unearned confidence.",
            "Do not mention discounted oscilloscopes.",
            "Subject becomes evasive when asked about project deadlines.",
            "Do not leave the subject unattended near spare electronics.",
            "Will claim the extra screwdriver was a business necessity.",
            "May pretend to organize cables while buying more of them."
        ],
    },
    "hu": {
        "agency": "THERMAL CHAOS // PARÓDIA",
        "heading": "KÖRÖZÉS",
        "file": "KITALÁLT ÜGYIRAT",
        "case_label": "ÜGY",
        "photo": "GYANÚSÍTOTTI FOTÓ // 1 BIT",
        "alias": "ÁLNÉV",
        "charges": "KÖRÖZÉS OKA",
        "seen": "UTOLJÁRA LÁTTÁK",
        "reward": "NYOMRAVEZETŐI DÍJ",
        "note": "HELYSZÍNI MEGJEGYZÉS",
        "footer": "PARÓDIA // NEM VALÓDI KÖRÖZÉS",
        "aliases": [
            "A Kábelkobold", "Az Adapterbáró", "A Szerszámbeszerző",
            "A Forrasztófantom", "Az Éjféli Hibavadász", "Az Ötperces Szerelő",
            "A Routermágus", "A Hőpapír Réme", "A Pótalkatrész-jós",
            "A Félkész Projektek Ura", "A Konnektorbandita", "A Firmware-manó",
            "Az USB-régész", "A Munkapadkobold", "A Hivatásos Halogató",
            "A Láthatatlan Technikus", "A Koffeinmentes Katasztrófa",
            "Az Utolsó Pillanatos Mérnök", "A Mellékküldetés Kapitánya",
            "A Rejtélyes Csatlakozó"
        ],
        "charges": [
            "Súlyosan indokolatlanul szükséges szerszámok beszerzése",
            "A kábelrendezés elleni bűncselekmények",
            "Gyanús mennyiségű adapter birtoklása",
            "Tizenkét félkész projekt mellé új projekt indítása",
            "Előre kitervelt hardverbabrálás",
            "USB-elosztók engedély nélküli terjesztése",
            "Ötperces javítás háromnapos incidenssé alakítása",
            "A 'gyors teszt' kifejezés rendszeres bántalmazása",
            "Ismeretlen eredetű csavarok halmozása",
            "Egy közönséges kanál Wi-Fi-re kapcsolásának kísérlete",
            "Felelőtlen firmware-frissítés lefekvés előtt",
            "Blokknyomtató rendeltetésellenes szórakoztatása",
            "Kórosan alacsony ellenállás elektronikai akciókkal szemben",
            "Túlzott önbizalom forrasztópáka közelében",
            "Engedély nélküli kábelraktározás",
            "Kenyérpirító túlhajtásának kísérlete",
            "Tizenhét párhuzamos mellékprojekt működtetése",
            "A normális alvási rend módszeres felszámolása",
            "Alvó NAS nyugalmának megzavarása",
            "Elátkozott USB-C kábel birtoklása"
        ],
        "seen": [
            "Egy gyanús újraindítás helyszínén", "Az Alza kosaránál",
            "Tartalék kábelek hegye alatt", "Villogó MikroTik mellett",
            "A munkapadnál éjfél után", "Félig szétszedett laptop mellett",
            "Egy 'VEGYES' feliratú fiókban", "Újabb csavarhúzót vásárolva",
            "A NAS és a kávéfőző között", "Megint a blokknyomtatónál",
            "A firmware-frissítés gombja felett", "Rossz adapterrel a kezében"
        ],
        "rewards": [
            "8 000 Ft és egy kávé", "Egy enyhén használt csavarhúzó",
            "Egy tekercs friss hőpapír", "Három tökéletesen rendezett kábel",
            "Öt perc zavartalan alvás", "Egy eredeti rejtélyes csavar",
            "Egy bűntudatmentes szerszámvásárlás", "Egy működő USB-C kábel",
            "Egy zacskó kábelkötegelő", "Egy befejezett teendőlista"
        ],
        "notes": [
            "Óvatosan közelítendő. Bármikor új projektbe kezdhet.",
            "Gyakori mondata: 'Öt perc alatt megcsinálom.'",
            "Kötegelővel és indokolatlan önbizalommal felfegyverezve.",
            "Leértékelt oszcilloszkópot tilos említeni előtte.",
            "Határidőkről kérdezve terelni kezd.",
            "Pótalkatrészek közelében felügyelet nélkül ne hagyjuk.",
            "Az új csavarhúzót létfontosságú üzleti beszerzésnek nevezi.",
            "Kábelrendezésnek álcázva újabb kábeleket vásárol."
        ],
    }
}


def wanted_profile(lang, alias=None, rng=None):
    if lang not in WANTED:
        raise ValueError("Unknown poster language")
    rng = rng or random
    bank = WANTED[lang]
    raw_alias = alias if isinstance(alias, str) else ""
    supplied = re.sub(r"[\x00-\x1f\x7f]", "", raw_alias).strip()[:48]
    return {
        "case": f"MW-{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}",
        "alias": supplied or rng.choice(bank["aliases"]),
        "charges": rng.choice(bank["charges"]),
        "seen": rng.choice(bank["seen"]),
        "reward": rng.choice(bank["rewards"]),
        "note": rng.choice(bank["notes"]),
    }
