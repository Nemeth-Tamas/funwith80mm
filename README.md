# Thermal Chaos — Birch USB Edition

A one-button, local-only 80 mm thermal printer playground for Windows. Ten buttons: **roasts, random side quests, tiny puzzles (Sudoku / cipher / number patterns / riddles), thermal photo booth, haunted transmissions, micro-horror stories, silly certificates, FPV challenges, fictional receipts, and Chaos Roulette** (randomizes the others). English and **Magyar** UI plus bilingual printed content. Choose **bottom paper margin** (12/20/30 mm) before the cutter. No accounts, APIs, databases or internet connection required after the initial dependency install. No adventure game or AI chat.

## Quick start on Windows

1. Plug the **Birch CP-Q1UN into USB** and install its Windows receipt printer driver. Check that it appears in **Windows Settings → Printers & scanners**, ideally on a port such as `USB001`. Print a Windows test page first.
2. Install Python 3.11+ with the Python Launcher (or add Python to PATH).
3. Clone/download this repository, double-click **`start.bat`**.
4. Open **http://127.0.0.1:8765** if it does not open automatically.
5. Choose **English/Magyar**, pick a mode or Chaos Roulette, generate a preview, select your USB printer, and **PRINT**. The bottom padding selector defaults to 20 mm.

The launcher installs Flask, Pillow, and pywin32 in an isolated virtual environment on first use.

Command-line alternative:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## USB printing details

- **USB only**. Printer selection is restricted to Windows local queues reporting `USB*` or `DOT4*` ports. Network/Wi-Fi printers are never sent jobs. Windows printer spooler is used; no direct USB driver installation or USB VID/PID configuration.
- Receipts are rendered to exactly **576 pixels wide** (nominal 80 mm at 203 DPI); converted to 1-bit monochrome and sent in **RAW ESC/POS GS v 0 raster mode**, in 128-row chunks. Birch model/firmware/driver compatibility should be confirmed with a small test receipt.
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
- If no USB printers appear, check the queue's Windows **Printer properties → Ports**. A `WSD`, `TCP/IP`, or shared network port is intentionally excluded.
- If your computer has multiple USB receipt printers, use the dropdown to select the correct one.

## Developer check

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
