# Interactive LED Goal — sensing architecture notes (4 Nov 2026)

Summary of a working discussion on what should come after the display bring-up. Companion to `docs/log/2026-11-03-hardware-bringup-notes.md` and `docs/product/ux-spec.md`. Nothing here is decided; it records the options, the reasoning, and what to test.

---

## 1. Where we are and the main recommendation

The display subsystem is de-risked: serial link, mapping, patterns, power maths all work on the 300-LED test board. Nothing has yet touched **impact sensing** or **kick-moment detection**, which the spec (section 11) names as the two risks that can kill the product:

1. Sensor tolerance worse than ~150 mm → target games need redesign, impact cross becomes a liability.
2. Kick moment not detectable within ~30 ms → speed becomes a power bar, keeper can't commit-before-impact.

**Recommendation: do sensing next, on the existing test board, before cutting strips or building the 13×36 panel.** The sensing choice dictates panel construction (rigid base sheet vs open-backed battens, what goes in the posts), so building the panel first risks building it twice.

Parallel lead-time items: order the 400 W supply and book the electrician; spend 15 min on the router (AP isolation / ESP-NOW off / reserve .116).

Doc tidy-up: `docs/log/2026-09-led-goal-project-summary-SUPERSEDED.md` still describes a 1.8 m panel / 54 LEDs per column / 2,106 pixels. Spec and bring-up notes have moved to 1.2 m / 36 rows / 1,404. Mark the summary as superseded. Test board is 67 mm column pitch vs 71 mm on the real panel.

---

## 2. What the system has to sense

| Need | Used for | Precision needed |
|---|---|---|
| Kick moment | Keeper commit trigger, speed by time-of-flight | ≤ 30 ms, ideally ≤ 10 ms |
| Ball speed | Power mode, every result | Rounded whole km/h, honest |
| Impact position | Every game, impact cross | ≤ 150 mm, ideally ~70 mm (one column) |
| Impact time | Result timing, proving keeper committed first | tens of ms is fine |
| Kicker position | Free Kick, speed distance, "strike from anywhere" | ~0.5 m |
| Pre-shot body read | The Reader keeper, honest anticipation | hips / plant foot 100–300 ms before contact |
| Misses / wide shots | MISS without a timeout | binary |
| Hand taps on the face | Reaction / touch games | zone level |

**Keeper commit trigger** = the *moment* the keeper locks his dive. Direction comes separately from his profile, the pre-shot read, and chance. The trigger makes him honest; the read makes him interesting. The Cat barely needs a camera (profile + chance); The Reader depends on one.

---

## 3. Options discussed, with verdicts

### 3.1 Piezo impact sensors (from project summary)
- 4 corner discs with time-difference-of-arrival if battens sit on a rigid base sheet, or one top and bottom of each batten (26/panel) if open-backed. Per-batten gives the **column** directly at 71 mm pitch.
- ~$30/panel, deterministic, weatherproof, works at night, also detects hand slaps.
- Expected ±100 mm; unmeasured. **Still the cheapest ground truth for impact time, and a free training label for the keeper's read.**
- Verdict: build on the test board first regardless of what else is chosen.

### 3.2 Microphone for kick moment
- Wired to the same microcontroller as the piezos (shared clock); wireless adds jitter and a battery. Can sit on the goal rather than at the kicker: speed = d / (Δt + d/343) with the sound-delay term folded into calibration.
- Kick is a soft low-frequency thump; clap is loud broadband; shout is tonal and long. Separable in principle, but signal-to-noise at 7 m outdoors is unknown and must be measured. Never classify in isolation: anchor on the piezo impact and look back ≤ 800 ms for the most recent kick-shaped transient.
- Verdict: cheap fallback only. Superseded by radar or camera if either works.

### 3.3 Doppler radar
- All sports radar guns are CW Doppler at 10.525 GHz (X-band, older) or 24 GHz (K-band). Handhelds (Pocket Radar Smart Coach US$400, TAG One US$300, Stalker Sport 3 Connect US$800, Bushnell) are closed — Bluetooth to their own apps, no API. Sports Radar SR3600 (US$290–320) has RS-232 via a proprietary adapter and a 3 s hold between readings: integrable but clunky.
- **OmniPreSense OPS242-A / OPS243-A**: complete 24 GHz sensor boards, USB/UART, text API, readings at 100–200 Hz. Sports application note AN-29 (June 2026) covers soccer: low-reflectivity ball, range "at least 5–10 m", ≥ 6 m measured on the OPS242-A; settings S2 / 128 samples / km/h / R>3 / M>10; mount so the ball travels straight at the sensor.
  - OPS242-A: 76° beam, 1–25 m, 138 mph, US$189, in stock at RobotShop (3 units at time of writing).
  - OPS243-A: 20°×24° beam, 1–100 m, rolling buffer, US$224 / AUD 325, sold out at Tindie and DigiKey, backordered at Mouser AU (133 due ~6 Nov).
- Gives kick moment (first inbound reading above ~10 km/h) and speed from one part; gives **no position** (radial speed only). Cosine error for off-axis shots. Open question is whether it sees a size 4/5 ball at 7 m at all.
- Module tier for later: RFbeam K-LD7 (UART, speed+distance, but tops out at 100 km/h), ZLY TECH ZLYSR100A (24 GHz, UART/BLE, 40–240 km/h, marketed for soccer goals, price on enquiry). HB100 / CDM324 raw modules not worth the time.
- Verdict: buy one as the **reference instrument** for developing everything else, even if it leaves the BOM later.

### 3.4 Cameras
- Only a camera can do the pre-shot body read, kicker position, trajectory, wake-on-approach and clips.
- Camera-only for everything is hard: frame-rate quantisation (0.37 m per frame at 80 km/h / 60 fps), garden lighting, occlusion by the kicking leg, animated LED face as background, on-device compute (Jetson Orin Nano or Pi 5 + accelerator, US$150–400 on the BOM).
- **Camera placement options discussed:**
  - *On the goal looking at its own face*: can't work — a camera in the plane sees the face edge-on.
  - *On short arms at the top corners, looking down/in*: works (homography on a known plane, impact time by interpolating the approach/rebound reversal, IR illumination + IR-pass filter makes the LED face vanish). Rejected: arm must survive a 100 km/h ball and the panel shakes on impact.
  - *Cones on the ground at the six-yard corners*: isolated from shake, the goal can flash a pattern to re-calibrate them and a sync flash to align clocks. Needs battery + wireless + on-cone detection; gets kicked; can be lost. Viable but not preferred.
  - *Recessed in a deep frame* (LED panel set 300–400 mm behind the front frame, on isolators): no arms, wired, nothing to lose; goal becomes a box.
  - **Pod behind and to one side of the kicker (launch-monitor style) — preferred.** One safe camera sees kicker, ball at launch, flight, face, rebound and wide misses. Kick moment within ~8 ms at 120 fps global shutter; launch speed and direction as launch monitors do it; pose from behind/side gives plant foot, hips, approach angle. Impact point from the end of the ball's pixel track on the face plane (~±30–50 mm, against a lit face from 8–10 m — the weakest reading). Impact time ambiguous by ±2–3 frames (doesn't matter). Latency to trigger the keeper ≈ 40–100 ms total (frame + detect + ESP-NOW-class radio + goal frame) against a ~400 ms flight and a 150–400 ms keeper reaction delay — comfortably fast enough; triggering on the plant foot (~100 ms before contact) gives the budget back. Weaknesses: single viewpoint, pod should sit on the plant-foot side (left-footers flip it), battery device (accepted — brought inside after use, like a golf launch monitor), reads the back of the kicker.

### 3.5 "String of light sensors" in the channels
- Passive shadow sensing fails outdoors: nothing is darker at night, ambient swings 100×, kicker's shadow and clouds look like hits, adjacent LEDs swamp the sensor, 1,404 solder joints in a wet channel.
- Flip to **active modulated IR** (38 kHz, sunlight-immune): either sparse reflective pairs in the channels (~120 points, still a lot of wiring) or an **IR beam grid in the frame**.
- Beam grid geometry: post-to-post horizontal beams give height over the whole face. Left–right position needs beams the other way, and top + posts alone leaves the bottom half of the centre blind (no top-to-post beam passes below mid-height at the centre line); shallow diagonals give hopeless resolution for low balls. So a bottom edge is required for X from beams alone — passive retroreflective tape, or a raised (~50 mm) sheltered rail with blocked-beam self-test.
- **Two-sided hybrid: height from post-to-post IR beams, column from per-batten piezos.** Electronics in the posts only. Hands work the same way.
- The behind-kicker pod can't see a hand on the face (the person blocks it), so touch games need something in the goal: piezos at zone level, or beams for precise height.

### 3.6 Ready-made IR beam bars: measuring light curtains
- Industrial **measuring light curtains** are exactly "a strip of IR beams you embed in a post": one sealed aluminium emitter bar, one receiver bar, one cable each, RS-485 output of which beams are blocked. IP65, −30…+50 °C, modulated IR ignores sunlight, shock-rated for machinery. Pitch 2.5–25 mm; a 10 mm-pitch 1,200 mm bar fits the post and gives height to ±10 mm; range to 10 m covers the 2.7 m goal.
- Speed: cheap units only quote "response < 10 ms". The ball helps: 220 mm deep, it blocks the plane from ~4 ms before contact through ~10 ms of contact and the rebound — ≥ 20 ms per kick. A bar scanning every 3–5 ms is fine; a slow one isn't. Blocked-band width also classifies ball (~220 mm) vs hand (~100 mm) vs body.
- Prices: Chinese RS-485 measuring curtains US$230–1,370 per pair, MOQ 1 (AnLyHu, Dadisick); Banner EZ-ARRAY / Sick / Leuze well over US$1,000 per pair (reference only); IR touch frames US$100–400 but four-sided, indoor, sun-sensitive. At 100–200 units/yr expect US$120–180 per pair.
- Two questions for the supplier before ordering: scan cycle time (want ≤ 5 ms) and whether RS-485 reports individual beam states, not a count.

---

## 4. Candidate architecture (current leaning)

- **Behind-kicker pod** (global-shutter camera, 120 fps, on-device detection, low-latency radio): kick moment, launch speed and direction, pre-shot read, kicker position, trajectory, misses, clips.
- **In the goal, posts only**: measuring light curtain for height (10 mm), per-batten piezos for column (71 mm) and impact time, both also serving hand-tap games. No crossbar sensors, nothing on the ground, no cameras on the goal.
- **Radar** on the test bench as the speed/kick-time reference; leaves the BOM if the pod proves good enough.
- Mic dropped unless both radar and pod fail.

---

## 5. Test plan on the existing board

1. **Piezos** — 4 corner discs + one on a batten, microsecond timestamps on an ESP32/Teensy. 10 kicks at 5 marked points → tolerance distribution. Rebound debounce, hard strike (does the ball touch the strip?), throw vs kick, hand slap.
2. **Radar** — OPS242-A on USB; does it see a size 4/5 ball at 7 m? Kick time and peak speed logged against piezo impact time. Second serial port in `goal_patterns.py`.
3. **Pod camera** — Pi global-shutter camera at 120 fps on a tripod 2 m behind, 1 m to the side of the kicking spot. Prove kick frame and launch speed against radar; end-of-track impact point against piezos.
4. **Light curtain** — one 10 mm-pitch ~1,200 mm RS-485 pair across the board (0.5 m apart); log beam frames alongside piezo timestamps.
5. Close the loop: impact event → cross lights on the board. That is the Stage 4 "KICK → burst → number" moment and the first thing worth filming.

Then decide panel construction (base sheet vs open-backed, what lives in the posts), cut strips, build the 13×36 panel.

---

## 6. Parts to order

| Part | Approx. price | Source |
|---|---|---|
| Piezo discs ×6, 1 MΩ resistors, spare ESP32 or Teensy 4.1 | <AU$50 | any |
| OmniPreSense OPS242-A | US$189 + shipping | RobotShop (in stock) |
| OmniPreSense OPS243-A (backorder) | AUD 325 | Mouser AU |
| Raspberry Pi Global Shutter camera + lens, IR illuminator | ~AU$100–150 | Core Electronics / Little Bird |
| Measuring light curtain, 10 mm pitch, ~1,200 mm, RS-485 | US$230–300 per pair | AnLyHu / Dadisick (confirm scan time + per-beam output first) |
| 400 W 12 V supply + electrician | — | lead-time item |

---

## 7. Open questions

- Does Doppler see a football at 7 m? (AN-29 says ≥ 6 m on the OPS242-A; unverified for our ball/garden.)
- Pod: can a blob tracker find the ball against the animated face from 8–10 m, day and night?
- Light curtain: scan cycle time of the affordable units; survivability inside a post that takes direct hits; alignment tolerance across 2.7 m.
- Piezo tolerance on the real batten/backing construction (the thing that decides everything else).
- Which side of the kicker the pod lives on, and how the parent is told to move it.
- Whether touch/hand games are a big enough pillar to justify beam-level precision over piezo zones.

---

## 8. Sources

- OmniPreSense OPS243-A: https://omnipresense.com/product/ops243-doppler-radar-sensor/
- OmniPreSense OPS242-A: https://omnipresense.com/product/ops242-short-range-radar-sensor/
- AN-29 OPS24x for Sports (PDF): https://omnipresense.com/wp-content/uploads/2026/06/AN-029-A_OPS243-for-Sports_260621.pdf
- OPS243-A Mouser AU: https://au.mouser.com/ProductDetail/OmniPreSense/OPS243-A-CW-RP
- OPS242-A RobotShop: https://www.robotshop.com/products/omnipresense-ops242-a-doppler-speed-radar-sensor
- RFbeam K-LD7 datasheet: https://www.mouser.com/datasheet/2/1565/K_LD7_Datasheet-3446777.pdf
- ZLY TECH ball-speed modules: https://www.zlyradar.com/add-ball-speed-measurement-to-sports-training-gear/
- Pocket Radar Smart Coach: https://www.pocketradar.com/products/smart-coach-radar
- TAG One: https://tagsports.ai/products/tag-one-sports-radar
- Stalker Sport 3 Connect: https://radargunsales.com/stalker-sport-3-connect/
- Sports Radar SR3600: https://www.hittingstore.com/products/sr3600-radar-gun
- Kick-Point Speed Kick: https://www.kick-point.com/speed-kick-with-photo/
- OpenFlight (OPS243-based golf launch monitor): https://github.com/jewbetcha/openflight
- AnLyHu RS485 measuring light curtain: https://anlyhu.en.made-in-china.com/product/KwSGWMiuXmrg/China-RS485-Measuring-Light-Curtains-Sensor.html
- Dadisick measuring light curtains: https://www.dadisick.com/blog/What-Is-a-Measuring-Light-Curtain_b21864
- Banner EZ-ARRAY: https://qviro.com/product/banner/measuring-light-curtain-ez-array-series
- RapidoScan light grid: https://www.ethercat.org/en/products/4C61A1DDF6F24FC4B9D4A3950189EE81.htm
- XinTouch IR touch frames: https://xintouch.com/en/products/ir-touch-frame
