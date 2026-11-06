# Kazen — interactive LED goal

A goal-shaped LED display built from slatted batten fence panels. Players kick a ball at it; sensors detect where and how hard; the face shows a keeper, targets, scores. The Goal is the screen; the phone app (Kazen) is an optional second screen. Prototype first (one 13 × 36 panel), then ~100–200 units/year.

## How to start a chat
1. Read **`STATUS.md`** — where things are and the next tasks. That is the only file a new chat must read.
2. Open whichever reference doc the task needs (map below). Don't re-read everything.
3. At the end of a working session: add a dated file to `docs/log/`, append any decisions to `DECISIONS.md`, update `STATUS.md`.

## Map
| Path | What it is | Handling |
|---|---|---|
| `STATUS.md` | Current state per subsystem, next tasks, blockers | **Overwritten** every session |
| `DECISIONS.md` | Decision log: date, decision, why, what it supersedes | Append only |
| `OPEN-QUESTIONS.md` | Single register of unknowns and risks, with how each will be answered | Edit in place; close items, don't delete them |
| `docs/product/` | UX spec, screen inventory + Figma prompt, Home screen spec | Reference, stable |
| `docs/hardware/` | Geometry, strip + power, controller + data, test board, sensing | Reference; edit in place when facts change |
| `docs/parts/parts-list.md` | Everything to buy, with status | Edit in place |
| `docs/log/` | Dated session notes and superseded docs | Frozen; never edited after the day |
| `Prototypes/` | Every prototype, one folder each, versioned: `v0.0_KeeperLive` (Sept HTML keeper), `v0.1_LedTestBoard` (bench scripts), `v0.1_SensingDesktop` (camera sensing: `kick_cam.py`, `live_tracker.py`, `annotate_clip.py`) | Code |
| `Design/` | Brand (wordmark), screen explorations (v0.1 image-gen), research and marketing references | Assets |
| `Photos/` | Fence panel references, test board photo | Assets |
| `Strategy/`, `md/` | Empty — contents moved to `docs/` on 5 Nov 2026. Delete when convenient | — |

## Conventions
- Names in docs: **the Goal** (hardware), **Kazen** (app). Real product names TBD.
- Log files: `YYYY-MM-DD-topic.md`. Reference docs: lowercase-hyphenated, no dates.
- Numbers: the canonical geometry is `docs/hardware/geometry.md` (13 × 36 per panel, 39 × 36 full, 71 × 33 mm pitch, 1,404 LEDs). Anything else is wrong or superseded.
