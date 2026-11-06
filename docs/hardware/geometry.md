# Panel and goal geometry

Reference. Reconciled 5 Nov 2026 from `docs/product/ux-spec.md` §2.1 and the bring-up notes. These are the numbers every other document and every renderer must use.

## The panel
- Slatted batten fence panel, **1200 × 900 mm** nominal, battens running along the 1200 mm length.
- 13 battens × 44 mm, 27 mm channels between → **71 mm column pitch**. (13 × 71 = 923 mm, not 900 — measure a real panel; see OPEN-QUESTIONS.)
- Battens vertical. LED strip in each channel at 30 LEDs/m → **33 mm row pitch**, **36 LEDs per channel**.
- **468 LEDs per panel** (13 columns × 36 rows).
- Battens take the ball; strips never see it. Strip sits on the channel floor behind a recessed frosted polycarbonate diffuser (see `led-strip-and-power.md`).

## The goal
| | Prototype (1 panel) | Full goal (3 panels) |
|---|---|---|
| Face | 0.9 × 1.2 m portrait | 2.7 × 1.2 m (2.77 m if true pitch is 923 mm/panel) |
| Grid (W × H) | 13 × 36 | **39 × 36** |
| Pixel pitch | 71 × 33 mm | 71 × 33 mm |
| LEDs | 468 | **1,404** |
| Text per line, 5-col font | 2 chars | 6 chars |
| Text per line, 3-col font | 3 chars | 9 chars |

- Pixels are **non-square** (71 mm across, 33 mm down). The renderer works in mm coordinates and corrects once, centrally — `Prototypes/v0.1_LedTestBoard/goal_patterns.py` already does this. No game may assume square pixels.
- Seam between panels: decide which panel owns a shared edge column so each panel stays 13 columns and the mapping is identical per module.
- Posts and crossbar are a separate white steel/aluminium frame (~60 mm tube) around the panels; ball loads go to the frame, not the display. Frame houses sensors/camera and the one physical button.

## Superseded figures (do not use)
1.8 m panels, 54 LEDs/column, 702/panel, 2,106 total, 630 W — from the Sept 2026 summary, now in `docs/log/`.
