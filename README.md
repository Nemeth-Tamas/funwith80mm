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
