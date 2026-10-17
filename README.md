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
- Receipts are rendered to exactly **576 pixels wide** (nominal 80 mm at 203 DPI); text has a subtle 1-pixel outline and slightly increased font sizing for sharper thermal output, then converts to 1-bit monochrome and sends **RAW ESC/POS GS v 0 raster mode**, in 128-row chunks. Birch model/firmware/driver compatibility should be confirmed with a small test receipt.
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
