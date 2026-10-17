# Authored content packs

Each language has eight UTF-8 JSON files. The original entries remain in
`content.py`; `content_library.extend_bank()` appends these packs to a deep copy.
Callers still use `BANK[language][category]`, and paired entries remain tuples
after loading. There are no runtime API calls or generated template combinations.

| File | Shape | One counted entry |
| --- | --- | --- |
| `insults.json` | Object with `gentle`, `mean`, `nuclear`, `existential` lists | One roast |
| `quests.json` | Object with `easy`, `medium`, `hard` lists | One performable quest |
| `horror.json` | List of strings | One complete story |
| `mysteries.json` | List of strings | One technical incident |
| `certs.json` | List of `[title, description]` | One qualification |
| `shops.json` | List of `[name, [[product, integer_price], ...]]` | One entire shop |
| `riddles.json` | List of `[question, answer_with_explanation]` | One solvable puzzle |
| `flight.json` | Object with `whoop`, `camera`, `five` lists | One flight mission |

Keep each authored entry on its own JSON line to make editorial diffs easy to
review. Use natural language, NFC Unicode and proper Hungarian accents. A new
entry needs a distinct idea, not a swapped noun, price, date or severity label.
Localise jokes when needed; a Hungarian story need not duplicate an English one.

The runtime validator rejects missing categories, unknown JSON keys, repeated
keys, empty lists or strings, control characters, invalid product prices, and
duplicate entry identities. Identities ignore case, whitespace and punctuation;
they are the text for plain entries, question for riddles, title for certificates
and name for shops. The check spans categories within each language. Repeated
answers or products in different shops are allowed. Semantic similarity still
needs editorial judgement.

The ordinary text limit is 500 characters. Certificate titles and shop names
allow 80; certificate descriptions allow 300; product labels allow 48. Shops
contain 1–6 products priced from 0 to 999999 imaginary coins. These are upper
bounds, not length targets. Most entries should be much shorter. Horror pack
entries must be two sentences and 15–45 whitespace-separated words; the original
shorter stories are preserved. Don't add comic footnotes to horror.

Keep quests achievable with mundane materials or an explicitly named simulator.
Use no live mains, battery disassembly, destructive commands or production
network changes. FPV missions should suit the chosen craft and ordinary safe
practice: clear sites, ample separation, comfortable speeds and normal battery
reserves. Simulator missions should say so explicitly.

Riddle answers belong in the pair, never embedded as a question spoiler. State
assumptions when necessary and include a short derivation. Extend the executable
puzzle checks when adding calculable or logic puzzles. Keep generated Sudoku,
number-pattern and Caesar functionality in `app.py`; those outputs do not inflate
the content counts.

Before committing, run:

```sh
python -m content_library
python -m unittest discover -s tests -v
```

The exhaustive renderer test selects every entry deterministically rather than
hoping random sampling will cover it. With the default 20 mm padding and maximum
shop quantities, each content receipt must fit within 2200 raster rows, with
clear side margins and white padding before the cutter. Tests also generate all
riddle answer slips. Actual USB/network spooler acceptance and paper quality need
the Windows printer; the content tests do not claim to exercise physical hardware.
