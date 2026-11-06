# Open questions and risks

One register, merged 5 Nov 2026 from ux-spec §11, the Sept summary §11 and the sensing discussion §7. Edit in place: when something is answered, fill in the answer and date, and move the row to **Closed**. Don't delete rows.

## Open
| ID | Question | What it affects | How we'll answer it |
|---|---|---|---|
| OQ-1 | Fence panel construction: rigid base sheet or open-backed battens? Timber or aluminium? | Piezo layout (4 corner TDOA vs 26 per panel), pulse quality, how the panel is built | Ask the supplier; piezo test on the board; decide after OQ-2 |
| OQ-2 | **Measured impact-position tolerance** on the real batten/backing | Minimum target size in every game; whether Darts is viable; whether the impact cross is an asset or a liability (>150 mm = redesign around zones) | Piezo test: 10 kicks × 5 points (STATUS task 5); camera multi-kick session first (STATUS task 0). *5 Nov: camera repeatability across frame rates 3–4 cm on one kick; onset-frame ambiguity worth ±5–10 cm until trajectory extrapolation is added* |
| OQ-3 | **Can the kick moment be detected within ~30 ms?** | km/h vs power bar; keeper commit-before-impact | Radar on the bench, then pod camera; compare to piezo impact time. *5 Nov: from video, kick frame = foot contact ±2 frames at 240 fps (±8 ms); ±33 ms at 60 fps — borderline* |
| OQ-4 | Does Doppler (OPS242-A) see a size 4/5 ball at 7 m in a garden? | Whether radar is a usable reference / BOM item | First radar test; AN-29 claims ≥ 6 m |
| OQ-6 | One supply per panel (self-sufficient modules) or one per goal? | Product BOM, junction box, certification | Decide with the manufacturing/module decision |
| OQ-7 | Real tiled panel width: 13 × 71 = 923 mm vs quoted 900 mm | Frame width 2.70 vs 2.77 m; seam-column ownership | Measure a real panel |
| OQ-8 | Does a ball compressing into the 27 mm gap ever reach the strip? | Channel depth; protective cover | Hard-strike test on the board during the piezo session |
| OQ-9 | Pod camera: can a blob tracker find the ball against the animated face from 8–10 m, day and night? | Impact point from the pod; whether light curtain / piezos are still needed for position | Pod camera test. *5 Nov: yes in daylight against a plain net with classical CV (one kick, 31.5/89 cm, matches by eye). Untested: lit LED face as background, dusk, 8–10 m* |
| OQ-10 | Light curtain: scan cycle time on affordable units; per-beam RS-485 output; survives inside a post that takes hits; alignment tolerance over 2.7 m | Height sensing; touch games | Supplier questions before ordering, then board test |
| OQ-11 | Which side of the kicker does the pod sit, and how is the parent told to move it for left-footers? | Setup UX, Stage 3/5 | After pod test |
| OQ-12 | Are hand/touch games a big enough pillar to justify beam-level precision over piezo zones? | Whether the light curtain stays in the BOM | Product call after OQ-2 and OQ-10 |
| OQ-13 | Camera performance at dusk/night; background subtraction in a real garden | Keeper and Free Kick in the evening; Mirror / Freeze / Hole-in-the-Wall | Pod test with IR illuminator |
| OQ-14 | Controller processing: clips rendered on the Goal or the phone; LEDs animated at 30+ fps | Share flow; brain box spec | Decide once the pod/brain compute is chosen |
| OQ-15 | Speaker? Microphone? | Colour Call, Beat scene, keeper taunts | Product call |
| OQ-16 | Weather rating of sensors and camera | "Leave it out all year" claim | After parts are chosen |
| OQ-17 | Wake-on-approach false triggers (pets, foliage) | Default height threshold; wake on by default? | Pod test |
| OQ-18 | Seam-column ownership between panels | Mapping identical per module | Decide with OQ-7 |
| OQ-19 | Brightness cap and per-panel power derating in an AU summer | Visible brightness; supply sizing | Measure on the first panel with the big supply |
| OQ-20 | RGB vs RGBNW final call | Strip order for production | RGB for prototype; revisit at production |
| OQ-21 | Certification path for a mains-powered product in AU (EMC/electrical safety, $10–30k) | Manufacturing plan | Later |
| OQ-22 | Wi-Fi: is the Mac → controller block router isolation, ESP-NOW, or something else? | DDP over Wi-Fi, web UI, no USB tether | STATUS task 3 |
| OQ-23 | Does 460800 baud work on the Mac CH340? | ~50 fps on the bench | Try `--baud 460800` once |

## Closed
| ID | Question | Answer | Date |
|---|---|---|---|
| OQ-5 | Which 12 V supply for the bench / first panel? | The 400 W 12 V screw-terminal unit is in hand; no LRS-350-12 needed. Still needs a mains lead fitted by an electrician. Bench meanwhile runs on the 30 W plug pack into the SP805E barrel socket | 5 Nov 2026 |
| — | Can the Mac drive the strip from code? | Yes: Adalight over USB at 230400 (~25 fps/300 LEDs); DDP once Wi-Fi works | 3 Nov 2026 |
| — | Does the test-board chain mapping match the physical board? | Yes, `LAYOUTS['board']` verified with `identify` / `hold` | 3 Nov 2026 |
| — | Does 921600 baud work on the Mac? | No — CH340/macOS driver; power-cycle to recover | 3 Nov 2026 |
