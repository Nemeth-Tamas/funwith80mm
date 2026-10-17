# Thermal Chaos — Windows Receipt Printer Edition

A one-button, local-only 80 mm thermal printer playground for Windows. Ten buttons: **roasts, random side quests, tiny puzzles (Sudoku / cipher / number patterns / riddles), thermal photo booth, haunted transmissions, micro-horror stories, silly certificates, FPV challenges, fictional receipts, and Chaos Roulette** (randomizes the others). English and **Magyar** UI plus bilingual printed content. Choose **bottom paper margin** (12/20/30 mm) before the cutter. No accounts, APIs, databases or internet connection required after the initial dependency install. No adventure game or AI chat.

## Quick start on Windows

1. Install your **Birch CP-Q1UN** as a Windows printer: via USB (`USB001` etc.) at home or on an installed **network/TCP-IP/WSD/shared Windows print queue** at the shop. Check **Settings → Printers & scanners**.
2. Install Python 3.11+ with the Python Launcher (or add Python to PATH).
3. Clone/download this repository, double-click **`start.bat`**.
4. Open **http://127.0.0.1:8765** if it does not open automatically.
5. Choose **English/Magyar**, pick a mode or Chaos Roulette, generate a preview, select your installed Birch printer (USB or network), and **PRINT**. The bottom padding selector defaults to 20 mm.

The launcher installs Flask, Pillow, and pywin32 in an isolated virtual environment on first use.

Command-line alternative:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## Windows USB and network printing

- Supports Windows-installed **USB, TCP/IP, WSD and shared network printer queues** using the Windows spooler. No direct-IP configuration in the app; add the device to Windows first. Obvious PDF/XPS/Fax virtual printers are hidden. Choose an ESC/POS-compatible receipt printer; arbitrary laser or inkjet queues are not appropriate for RAW receipt commands.
- Receipts are rendered to exactly **576 pixels wide** (nominal 80 mm at 203 DPI); text keeps slightly increased font sizing without an extra outline, to prevent neighboring strokes from merging, then converts to 1-bit monochrome and sends **RAW ESC/POS GS v 0 raster mode**, in 128-row chunks. Birch model/firmware/driver compatibility should be confirmed with a small test receipt.
- Each print uses **the exact cached image generated for its preview**, not an independently regenerated random result.
- Cutter command is `GS V 0` (full cut), optional. If your printer driver treats RAW jobs as text or ignores ESC/POS, configure the device with a compatible Windows ESC/POS/raw queue or adapt the backend in `send_usb()`.
- The app binds only to `127.0.0.1:8765` and sends data only to your computer's chosen Windows print queue. No outside web requests, no cloud AI.
- No receipt prints automatically. The app does **not** verify that physical paper emerges after Windows accepts the job.

## Notes

- Photo inputs are processed in memory and limited to 6 MB; upload limit is 8 MB. The printer is black and white so fine gradients will dither.
- Sudoku uses randomized **valid filled boards** and removes clues based on difficulty. It does not check uniqueness of puzzle solutions; treat as a casual puzzle generator.
- Fake receipts are heavily and repeatedly marked **fictional parody**, not real accounting documents.
- FPV cards contain low-risk practice suggestions and explicitly remind you to fly legally and safely.
- Everything generates quickly offline; content is from built-in templates and randomized selections, not live AI-generated text.
- If the shop printer is missing, install/connect it as a Windows printer first. Then use the **Find printers** button.
- If you have both home USB and shop network printers, use the dropdown to select the correct Birch.

## Developer check

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Operation Infinite Nonsense

The library contains **924 authored entries per language**, including **730 new
entries per language** in the expansion packs. Existing entries remain at the
start of their original lists. Products within a shop, random quantities,
Sudoku boards, arithmetic patterns and Caesar shifts are **not** counted as
additional authored entries.

| Category | English | Magyar | New per language |
| --- | ---: | ---: | ---: |
| Insults: gentle | 50 | 50 | 40 |
| Insults: mean | 55 | 55 | 40 |
| Insults: nuclear | 55 | 55 | 40 |
| Insults: existential | 50 | 50 | 40 |
| Quests: easy | 85 | 85 | 70 |
| Quests: medium | 85 | 85 | 70 |
| Quests: hard | 85 | 85 | 70 |
| Pure horror | 130 | 130 | 100 |
| Haunted transmissions | 80 | 80 | 60 |
| Certificates | 75 | 75 | 60 |
| Fictional shops / receipts | 49 | 49 | 40 |
| Riddles | 50 | 50 | 40 |
| FPV: whoop | 25 | 25 | 20 |
| FPV: cinematic | 25 | 25 | 20 |
| FPV: five-inch | 25 | 25 | 20 |
| **Total** | **924** | **924** | **730** |

Content packs live in `content_packs/en/` and `content_packs/hu/`, organised by
category. See [the authoring guide](content_packs/README.md). The loader validates
both languages at startup, appends the packs, and exposes the same `content.BANK`
API as before. No printer, UI or rendering settings are changed by this expansion.

To validate and print the current counts:

```powershell
.\.venv\Scripts\python.exe -m content_library
```

The test suite forces **every entry** through its actual generator, renders its
576-pixel receipt, checks the white bottom padding and side margins, and encodes
it as ESC/POS with a cutter command. It also renders every riddle's answer slip,
tests invalid content, checks preservation of the original lists, and verifies
the new puzzles with arithmetic, exhaustive small logic models and simulated
solution steps. These tests run without a printer; physical Windows printing
still needs a connected receipt printer.

## The five new chaos buttons

Five new bilingual modes are wired into the existing preview and RAW ESC/POS printer pipeline:

| Button | English | Magyar | Style |
| --- | ---: | ---: | --- |
| PSYOPS | 30 | 30 | Fictional cognitive audits, contradictory files and unsettling bureaucratic notices |
| Reality Patch Notes / Valóságfrissítés | 30 | 30 | Bug fixes and release notes for reality |
| Prophecy / Jóslat | 30 | 30 | Uncomfortably precise or ridiculous predictions |
| Cosmic Complaints / Kozmikus Panaszok | 30 | 30 | Formal complaints and absurd official decisions |
| Future Transmission / Üzenet a jövőből | 30 | 30 | Lost messages, future service tickets and temporal mishaps |
| **New authored entries** | **150** | **150** | **300 total** |

The curated packs are in `extra_modes/en.json` and `extra_modes/hu.json`,
loaded and validated by `extra_library.py`. They are *additional* to the
original `content.BANK`, so the original expansion's 924 entries per language
remain unchanged. The whole app now has **1,074 authored entries per language**
(**2,148 across both languages**), excluding algorithmic puzzle variations and photos.

Use one of the five buttons, select English/Magyar, then **Generate preview** and
**Print**. Chaos Roulette can also randomly choose any of the five additions.
No external APIs are required, and no printer transport or bottom margin behavior
was changed for these modes. Existing Windows USB and network printer queues
continue to work.

The tests validate and render all 300 new entries through the actual
576-pixel raster receipt pipeline; run `python -m unittest discover -s tests -v`.


## Paranormal Investigation Bureau and Thermal Bingo

Two more bilingual, fully offline buttons are included in the existing UI:

- **Paranormal Investigation Bureau / Paranormális Nyomozóiroda**:
  **46 authored case reports per language**, each pairing a suspicious observation
  with an unexpectedly mundane (and usually ridiculous) investigation result.
  Reports have an incident ID, a finding and a formal case-closed line.
- **Thermal Bingo / Thermal Bingó**:
  real **5×5 monochrome, printable bingo cards**, with **24 distinct randomized
  event squares and a free center square**. Four independently authored event
  pools are selectable in both languages: **IT repair, customers, household
  chaos, and cosmic incidents**, with **48 unique squares per theme and language**.
  Print one card and mark the squares by hand as things happen; five in a line
  wins. Generating another card changes the arrangement and event selection.

This brings **238 additional authored items per language** (46 reports + 192
bingo prompts), or **476 new items across both languages**, above the existing
content libraries. **The total is now 1,312 entries per language, 2,624 overall**,
counting individual bingo prompts rather than the countless possible cards.

Content lives in `new_modes/en.json` and `new_modes/hu.json`, checked at
startup by `chaos_games.py`. The new rendering integrates with the existing
preview-first pipeline, image cache, 576-pixel ESC/POS raster encoder and Windows
USB/network printer picker. The bottom padding and cutter commands remain
unchanged. Both new buttons are eligible for Chaos Roulette.

Tests cover all 92 authored paranormal reports, all four bingo themes in both
languages, free-center placement, square uniqueness, long Hungarian text
wrapping, 576-pixel image width, blank bottom feed and ESC/POS output.

## Psychological Horror — The Memory Problem

A dedicated **PSYCHO HORROR / PSZICHOHORROR** button adds **89 new original
psychological-horror microstories in English and 89 in Hungarian** (**178 new
entries**). These are separate from the existing PURE HORROR bank, which is
untouched. Stories focus on memory, identity, family, recordings, unreliable
spaces, surveillance and painfully plausible impossible details, not jump scares.

The stories are intentionally short, generally two sentences. The receipt is
minimally styled, without a playful footer to spoil the atmosphere; existing
576-pixel image width, bitmap font weight, 12/20/30 mm selectable bottom feed,
cutter settings, USB/network printing and previews are unchanged.
**Chaos Roulette** can select the new mode as well.

The content lives in `psychological_horror/en.json` and
`psychological_horror/hu.json`. On startup, `psych_horror.py` validates
completeness (at least 80 stories per language), duplicate identities,
string lengths and Unicode. Tests render all **178 stories** through the
actual receipt renderer and verify their ESC/POS output and white bottom feed.

**Total authored content: 1,401 entries per language, 2,802 overall.**
This counts each psychological horror microstory as one authored entry
and excludes procedural bingo arrangements or Sudoku variations.


## Most Wanted Photo Posters

The existing **Thermal Photo / Hőnyomat** mode now includes a fifth effect,
**MOST WANTED poster / KÖRÖZÉS poszter**, alongside Classic dither, Hard B&W,
Newsprint and Inverted. Upload a normal picture, choose the effect, optionally
enter a suspect alias, generate the preview and print on the installed
Windows USB or network receipt printer.

The mock wanted notice is prominently branded **THERMAL CHAOS // PARODY**,
with an entirely fictional case number, an actual center-cropped and
Floyd-Steinberg dithered 448 × 548 pixel mugshot, a thick black title bar,
an outlined portrait, and randomized absurd allegations, aliases, sighting
locations, rewards and field notes in natural English or Hungarian.
This is a joke poster, **not** a real police document or an FBI seal.

A blank suspect alias generates a random fictional one; the custom alias
is trimmed to 48 characters, and control characters are removed.
The poster is rasterized to the same 576-pixel width, cached for an exact
print preview, and sent through the unchanged RAW ESC/POS printer path.
The bottom margin selector and optional cutter still work exactly as before.
No dependency changes.

The content is maintained in `wanted_posters.py`. Tests cover poster generation
in both languages, optional aliases, monochrome raster, preview dimensions,
ESC/POS encoding and compatibility with the four original photo effects.


## Expanded Most Wanted chaos (2026-10-17)

The Photo > **MOST WANTED / KÖRÖZÉS** effect now has a selectable humor
theme: **Surprise / Lepj meg**, **Everyday & shop / Bolti-hétköznapi**, and
**Geek & workshop / Műhely-kocka**. Hungarian defaults to **shop** in the
browser, so its jokes are about pogácsa theft, suspiciously friendly
customers, mysterious biscuits, fake alibis, and excessive confidence—not
technology. English defaults to Surprise. The Python API's omitted-theme
default remains `tech` for compatibility with older callers.

Ten alternative wanted headlines in each language are automatically fitted
to the 80 mm title bar. In addition to alias, charge, last seen, reward and
note, every poster shows **two or three rotating extras** from distinguishing
marks, suspicious behavior, cover story and temperament. The new
`wanted_variations.json` contains hundreds of curated short lines in both
languages, validated by `wanted_posters.py` at startup. It adds **248
original shop jokes and 99 extra tech jokes in Hungarian**, plus **203 shop
jokes and 99 tech jokes in English**, excluding the ten headlines per
language. Original joke pools remain available too.

The dedicated **ÚJ VÁDAK / NEW ACCUSATIONS** control rerolls the fake case
and jokes while reusing the **same selected photo**; a new preview must
still be consciously printed through the regular printer button. Custom
alias overrides remain supported. The original photo effects, 576-pixel
Pillow/ESC-POS renderer, cutter, bottom feed and Windows USB/network queues
are unchanged. No camera is activated.

## EagleEye IV USB: the small shop photo booth

Double-click **`start_eagle_eye.bat`**, then open
**http://127.0.0.1:8765/eagle-eye** in Chrome or Edge. If the regular app is
already running, close its terminal first. Ordinary **`start.bat` always opens
http://127.0.0.1:8765/** and forces camera mode off, even if an old terminal
still has `THERMAL_CHAOS_CAMERA=1`. The separate camera launcher explicitly
passes `--eagle-eye` to opt in. The camera does not open on page load.

To run it in your own visible PowerShell window using the existing environment:

```powershell
cd "C:\Users\User\Desktop\cuccli\funwith80mm"
$env:THERMAL_CHAOS_CAMERA = "1"
.\.venv\Scripts\python.exe app.py
```

Keep this window open; **Ctrl+C** stops the server. Startup prints the project
folder and camera page URL. Open http://127.0.0.1:8765/eagle-eye in Chrome/Edge.

1. Click **USB-kamerák keresése**, and select **Polycom EagleEye IV USB Camera**.
   Before camera permission, the browser may hide names or offer only its default
   camera. Select it, then verify the active name and live picture after arming.
   If it is the wrong device, cancel, select EagleEye from the now named list and
   arm again. Close other camera applications if USB video is busy.
2. Tell the participant about the souvenir, get their agreement, and manually
   aim at them using the physical remote if needed. Confirm both checkboxes,
   then click **Élesítés / Következő áldozat** and allow camera access. No audio
   permission is requested. A surveillance sign does not replace agreement.
3. Check the live picture: one consenting participant, face inside the portrait
   guide, adequate light. Confirm the picture check and click **Fotózás**.
   A three-second countdown takes one frame, then releases the USB camera.
   A **Kamera expozíciója** slider appears only if the browser exposes a usable
   exposure range and mode. Changes are checked against camera readback; unsupported
   devices show an explanation. Longer manual exposures can blur moving subjects.
4. Review the frozen, Hungarian **shop/everyday** parody poster. **Új szöveg**
   keeps the photo and rerolls the jokes. Optional alias and 12/20/30 mm bottom
   margin changes take effect with that button. **Újrafotózás** discards the old
   photo and requires another deliberate consent/arm step.
   **Fotó világosítása** beside the poster lifts shadows before black/white
   dithering (default 1.6×; range 1.0–2.5). Releasing its slider refreshes the
   exact cached poster with the **same photo and jokes**, without extending
   expiry or printing. Pending alias/margin edits must first be applied with
   **Új szöveg**. This changes the photo raster only, not the text or borders.
5. Choose the installed Birch queue (USB001 at this workstation), set the cutter,
   and click **Nyomtatás**. Only this separate click prints the exact cached
   576-pixel preview. The app clears the photo after Windows accepts the job;
   Windows acceptance does not prove that paper emerged.

**Mégse / Azonnali kikapcsolás** stops the camera and clears the photo and poster.
Arming expires after two minutes. Photos and posters expire after five minutes
from capture, even without further requests; rerolling does not extend this.
Leaving a live-camera tab stops it. Closing the page attempts immediate server
cleanup, with expiry as a fallback. Images stay in browser/server memory, never
in the general one-hour receipt cache or application files. The Windows spooler
and printer manage their own job data. After a printer error, check the queue
and paper before clicking again, because a partial job may have been accepted.

This deliberately small first version uses **USB browser video and manual aim**.
It does not identify people, detect/track faces, move PTZ motors, record video,
contact network camera services, or print on a camera event. Multiple people
must be handled by the operator: cancel and reframe. Very dark/bright frames
are rejected; this is a basic exposure check, not face detection.

Connection research used the owner's EagleEye IV USB handover (VID:PID
`095d:9204`), the connected DirectShow device name, and the sibling EagleCast
project. EagleCast's Pi REST PTZ/multicast system is a different network path,
so this USB booth does not assume RTSP/ONVIF or call the Pi. Camera selection
and lifecycle use the standard browser [getUserMedia API](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).
The app still binds to loopback only; camera API requests reject remote clients,
foreign Host/Origin values and cross-site requests. No extra Python packages
or camera firmware changes are needed.

The booth itself uses external JavaScript/CSS compatible with its CSP. Warnings
pointing to `content.js` may come from an extension trying to insert inline code;
check that source URL or use a browser profile without that extension. The app
does not whitelist unknown injected code to suppress those warnings. Browser
exposure controls follow the [Image Capture specification](https://www.w3.org/TR/image-capture/)
and depend on the camera driver and browser.

Offline checks (no camera or printer required):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test tests/test_camera_ui.cjs
```

Python tests cover consent, one-shot sessions, expiry, frozen-image printing,
reroll invalidation, printer failure and local access. The dependency-free Node
tests cover fake USB tracks, countdown cancellation, late camera permissions,
disconnects, lighting, retakes, unload cleanup and deliberate printing. CI runs
both on pushes to master and pull requests. A real photo and paper check still
need an operator at the booth.


## Thermal Toolbox: useful paper (October 2026)

The normal **start.bat** opens the original Thermal Chaos app, now with
six *additional, printable utility modes* in English and Hungarian:
**QR Factory**, **Pocket Checklists**, **Quick Note**, **Cheat Sheet**,
**Customer Rights**, and **Parts Payment**. Every mode uses the original
cached-preview-then-manual-print flow (576-pixel black/white ESC/POS,
12/20/30 mm bottom feed, installed Windows printer queue and cutter).
Nothing prints unless the operator presses Print.

- **QR Factory:** website links (http/https), Unicode text, properly
  escaped Wi-Fi QR for WPA/WPA2/WPA3, WEP or open networks (including
  hidden networks), and compact MECARD contact details. Square QR
  images retain a white quiet zone. Scan-test on a phone, particularly
  for lengthy codes. QR contents can include sensitive Wi-Fi passwords:
  distribute only to intended recipients.
- **Pocket Checklists:** custom heading and 1–28 newline-separated items
  printed with *real empty squares*, handy for repair checklists and
  shopping. Bullets or leading numbers are optional.
- **Quick Note:** customizable large reminder and optional timestamp.
- **Cheat Sheet:** offline mini-references for IPv4 subnetting, Windows,
  Linux, MikroTik, Python, C# and electronics, plus custom references.
- **Customer Rights / Vásárlói jogok:** a Hungarian-only supplementary
  statutory information slip. Enter seller, description, gross HUF price,
  sale type and sales channel. For a **new product actually within the
  mandatory-warranty product classes**, it reports two years from
  10,000–250,000 Ft, three years above 250,000 Ft. At **100,000 Ft
  or less**, a separate warranty certificate may be omitted, but
  *prescribed information must still be supplied in a durable readable
  format*. Above 100,000 Ft, a compliant warranty certificate is
  required. Also summarizes liability for defects (kellékszavatosság)
  and that the usual 14-day no-reason withdrawal right is **not a general
  entitlement for an ordinary in-store purchase**. This is **not**
  a complete statutory disclosure package, warranty certificate,
  invoice, receipt, ÁSZF or a legal opinion. The operator **must
  verify product category and customer status**; do not assume that
  all replacement parts are listed products. Supply statutory warranty
  information in an appropriately durable form separately; ordinary
  thermal paper may fade.
- **Parts Payment / Alkatrész előleg:** personalized order and payment
  acknowledgment (seller, customer, exact part, optional job reference,
  overall price, amount received, balance, expected arrival and signature
  lines). The operator must choose the **legal nature** of the payment:
    - **ELŐLEG** is an advance against the price. It is **not by default
      non-refundable**. Refund/settlement follows the actual agreement
      and applicable law.
    - **FOGLALÓ** (Ptk. 6:185) is only available after the operator
      confirms a **separately and clearly agreed** earnest-money term.
      Performance credits it to the price; if non-performance is the
      buyer's responsibility, they forfeit it; if the seller is
      responsible, the seller returns *double*; if neither or both
      parties are responsible, it returns. Courts may reduce excessive
      amounts. Consumer statutory remedies and withdrawal rights cannot
      simply be waived by printing a non-refund clause. The app
      intentionally **does not** offer a blanket 'non-refundable deposit'.
      Attach an actual agreed and signed, durable contract.

  **Very important for accounting:** The thermal Parts Payment slip is
  **not an advance invoice, VAT invoice, accounting receipt or fiscal
  cash-register receipt**. Issue the applicable tax documents separately,
  e.g. through the normal Billingo/invoicing setup and fiscal register.
  Do not represent this document alone as proof of all legal terms.

### Primary Hungarian legal sources reviewed

- [151/2003. (IX. 22.) Korm. rendelet](https://njt.jog.gov.hu/jogszabaly/2003-151-20-22):
  mandatory warranty periods, threshold for a separate warranty
  certificate (2. §, 3/A. §).
- [10/2024. (VI. 28.) IM rendelet](https://njt.jog.gov.hu/jogszabaly/2024-10-20-06):
  the enumerated product groups for mandatory warranties. It is the
  **classification of the product**, not merely its price, that controls.
- [2013. évi V. törvény, Ptk.](https://njt.jog.gov.hu/jogszabaly/2013-5-00-00):
  especially 6:163. § (kellékszavatosság), 6:185. § (foglaló).
- [45/2014. (II. 26.) Korm. rendelet](https://njt.jog.gov.hu/jogszabaly/2014-45-20-22):
  distance/off-premises withdrawal rules and exceptions (20. §, 29. §);
  merely ordering an otherwise standard item for a customer is **not
  automatically a made-to-order customization exemption**.
- [2007. évi CXXVII. törvény (Áfa tv.)](https://njt.jog.gov.hu/jogszabaly/2007-127-00-00):
  VAT/advance billing obligations. Verify the specific receipt/invoice
  rules with the accountant.

**Before using the customer-rights or foglaló text as a standard
Cellnet contractual clause, have the exact setup checked by a qualified
Hungarian consumer-law advisor and the tax-document workflow by the
accountant.** The slips are supplementary aids, not substitute legal
documents. All templates run offline and require a manual print action.

Technical checks:
\`\`\`powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test tests/test_camera_ui.cjs tests/test_utility_ui.cjs
\`\`\`
