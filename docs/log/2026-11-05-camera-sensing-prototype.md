# 5 Nov 2026 — camera sensing prototype (one kick, iPhone slo-mo, offline OpenCV)

First sensing measurement of the project. Before any piezos/radar/pod hardware, we asked: can a single camera behind the kicker give us *rest → approach → kick → impact* and the impact position on the goal face? Zero-cost test: the backyard 240 × 172 cm goal, Ben's iPhone 15 Plus in Slo-mo (1080p 240 fps), phone propped low behind the kick spot, one kick. Analysis in `Prototypes/v0.1_SensingDesktop/kick_cam.py` (Python 3 + OpenCV, runs on the Mac).

## Result for the one kick (`Photos/ballkick.MOV`)
| Event | Frame (export @30 fps numbering) | Check |
|---|---|---|
| Rest | ≤ 570 | ball on the spot |
| Approach (leg in the ball's zone) | 546 | foot swinging in — 170 ms before contact |
| Kick (ball leaves the spot) | 586–587 | frame shows foot on the ball |
| Impact (first net contact) | 691 | net foreground 460 → 1,650 px in one frame |
| Impact position | **31.5 cm from left post, 89 cm up** (panel cell col 5 / row 7 of 36 × 13) | **Ben measured ~30 × 92 cm on the net** → error 1.5 cm across, 3 cm up; the 60 fps run (34 × 92) is within 4 cm |
| Flight | 104 frames = 0.43 s | kick→goal distance not measured, so no km/h yet |

Frame-rate sensitivity (same recording, frames dropped in software):
| Effective fps | Kick | Impact | Impact position | Δ vs 240 fps |
|---|---|---|---|---|
| 240 | 587 | 691 | (31.5, 89.1) | — |
| 120 | 584 | 694 | (34.2, 88.9) | 3 cm, ±3 frames |
| 60 | 578 | 698 | (34.4, 92.4) | 3–4 cm, ±7 frames |
| 30 | — | — | — | tracker fails (ball jumps 40–60 px/frame, blur) |

Run-to-run variation on the *same* data (different background-model history) moved first-contact by 4 frames and the position by 9 cm — the ball still moves ~2 cm per 240 fps frame when it meets the net, so **the onset frame is the dominant error source**, not pixel resolution (0.6 cm/px at the goal).

## What this says about the open questions
- **OQ-9 (can a camera track the ball from the pod position?)** — yes in daylight against a plain net, with classical CV only (background subtraction ∧ white mask ∧ size gate ∧ state machine). Not yet tested: the animated LED face as background, dusk/night, 8–10 m.
- **OQ-3 (kick moment within ~30 ms?)** — the tracker's rest→flight switch lands on the foot-contact frame ±2 at 240 fps (±8 ms); at 60 fps the same logic is ±2 frames = ±33 ms, i.e. borderline. A 60 fps global-shutter pod (AR0234) is probably enough for impact position but marginal for the kick timestamp; 120 fps would be comfortable.
- **OQ-2 (impact tolerance)** — single-digit cm *repeatability between frame rates* on one kick; the honest tolerance number needs the 5-target × 10-kick session. Expect ±5–10 cm from the onset-frame ambiguity alone unless we extrapolate the trajectory to the net plane rather than reading the centroid at the onset frame.

## How it works (so the next person doesn't re-derive it)
- **Goal frame**: four inner edges (240 × 172 is the inner opening) fitted per frame from a white mask, seeded from `goal.json` corners (`pick_corners.py` to set them). Handles the ~3 px camera drift. A blind wide search was *not* reliable — brick wall, rear top rail and target ropes present several parallel white edges near the crossbar. Homography → goal cm → panel cell.
- **Ball**: MOG2 with shadow detection (the kicker's shadow across the ball was the main false-motion source) ∧ HSV "white" ∧ area/aspect/radius gates. State machine: REST holds an anchor and ignores partial/shaded detections; FLIGHT is gated nearest-neighbour with constant-velocity prediction; LOST re-acquires a ball-sized blob that stays put outside the goal.
- **Events**: rest = 5-frame-median displacement from the anchor stays < 0.25 r; kick = first clear departure (> 1 r, still rising), onset walked back down the rising edge; approach = solid foreground within 4.5 r of the ball exceeds 12 % of the disc; **impact = first frame the net moves** (foreground inside the goal quad, ball excluded, jumps). Ball-velocity discontinuity is kept only as a fallback — the net decelerates the ball over many frames, so "max deceleration" is 5–10 frames late.

## Gotchas
- iPhone Slo-mo shared via Photos/AirDrop arrives as a **30 fps rendered export** (normal-speed head/tail, 8× slow middle). Frames in the slow section are still real 1/240 s samples, so position is fine; timing assumes the analysed window is inside the slow section. For clean timing export the unmodified original (Photos → File → Export → Export Unmodified Original) — that file is 240 fps throughout.
- The laptop webcam would have been the wrong capture device: 30 fps is exactly the rate at which this detector breaks.
- Bare feet in direct sun pass the "white" test; the radius gate and rest anchor are what keep the tracker off them.

## Next
1. **Multi-kick session** (the planned 5 marked targets × 10 kicks) with the phone on a tripod, exposure locked, kick spot → goal line distance measured. Export the unmodified original. This gives the tolerance distribution for OQ-2 from the camera alone, before the piezos even arrive.
2. Trajectory extrapolation to the net plane (fit the last ~10 frames) instead of centroid-at-onset, to take the onset-frame ambiguity out of the position.
3. Live loop: same script on a Continuity-Camera / webcam feed at 30–60 fps to see what breaks in real time; then the pod camera when it lands.
4. Repeat with the test board lit behind the ball (animated background) — the real OQ-9 question.
