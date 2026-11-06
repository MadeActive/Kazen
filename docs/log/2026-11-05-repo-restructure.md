# 5 Nov 2026 — repo restructure

Reviewed every doc in `Strategy/`, `md/` and `Design/*.md`. Project is coherent; the pain was that current state lived in nobody's file and each chat re-read ~125 KB to find it.

## What changed
- Split into three kinds of document: **reference** (`docs/product`, `docs/hardware`, edit in place), **log** (`docs/log`, dated, frozen), **state** (`STATUS.md`, overwritten each session). Added `DECISIONS.md` (append-only) and `OPEN-QUESTIONS.md` (one register, 23 open / 3 closed).
- `Strategy/` → `docs/product/` (ux-spec, screen-inventory-and-figma-prompt, home-screen-spec).
- `md/` → `docs/log/` with dates in the filenames.
- Sept project summary → `docs/log/…-SUPERSEDED.md` with a banner; its still-valid content rebuilt in `docs/hardware/` with numbers reconciled to 1.2 m / 36 rows / 1,404 LEDs (strip 15.6 m per panel, ~94 W peak per panel, ~280 W full goal).
- `Hardware/` (photos) → `Photos/`.
- Shopping list → `docs/parts/parts-list.md` as one status table.
- `Strategy/` and `md/` are now empty but couldn't be removed from this session — delete by hand.
- Noted `Prototypes/v0.0_KeeperLive` ("Kazen Keeper Live", Sept) in the README: not live, still runs from `index.html`.

## Inconsistencies found and parked as open questions
- Supply: bring-up notes assume a 400 W unit is in hand; the 4 Nov shopping list adds an LRS-350-12. → OQ-5.
- Test board 67 mm vs real 71 mm pitch — documented in `test-board.md`.
- Panel width 923 vs 900 mm — OQ-7 (was already in the spec).

## Habit from here
Start: read `STATUS.md`. End: dated log file, append decisions, update STATUS, mirror STATUS into the Claude project.

## Later the same morning
Ben confirmed the 400 W 12 V supply is in hand; the test board runs on the 12 V mains adapter straight into the SP805E. OQ-5 closed, LRS-350-12 dropped from the parts list.
