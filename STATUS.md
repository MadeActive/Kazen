# STATUS — read this first

**Last updated:** 6 Nov 2026 (GitHub + trajectory-fit speed)
**Phase:** display bring-up done on the test board → **sensing tests next**, before cutting strips or building the real panel.

## Where each subsystem is
| Subsystem | State | Detail |
|---|---|---|
| Product / UX | Specified, stable | `docs/product/ux-spec.md`, screen inventory (28 screens / 77 states), Home spec |
| LED display | **Working** on 300-LED test board over USB serial (230400, ~25 fps); renderer in mm coords; mapping verified | `docs/hardware/controller-and-data.md`, `test-board.md` |
| Wi-Fi to controller | **Broken** — controller on LAN at 192.168.1.116 but unreachable from the Mac | `controller-and-data.md` §Wi-Fi |
| Power | 30 W plug pack into the SP805E barrel socket (bench only). 400 W 12 V unit in hand, needs a mains lead → electrician | `led-strip-and-power.md` |
| Impact sensing | **Not started.** Architecture leaning chosen; nothing measured | `docs/hardware/sensing-architecture.md` |
| Kick moment / speed | **Trajectory fit** (gravity model through the tracked flight; range from ball size and post heights): kick and goal-line crossing sub-frame, speed = slope. Six kid kicks on 5 Nov: 50–57 km/h, consistent. Needs ≥3 tracked flight frames; the Mac camera gave only 15 fps at 1080p — use 720p/30 or the phone | `Prototypes/v0.1_SensingDesktop/annotate_clip.py` |
| Camera / pod | **First measurement done** — iPhone 240 fps slo-mo + OpenCV: rest / approach / kick / first-net-contact all detected on one kick; impact at 31.5 cm from post, 89 cm up vs **~30 × 92 measured** (1.5 / 3 cm off); 120 & 60 fps within 3–4 cm of 240, 30 fps fails. No pod hardware yet | `docs/log/2026-11-05-camera-sensing-prototype.md`, `Prototypes/v0.1_SensingDesktop/` |
| Real 13 × 36 panel | Not built; deliberately deferred until sensing decides construction | — |
| App | Spec + Home spec done; v0.1 image-gen explorations; HTML keeper prototype (not live) | `Prototypes/v0.0_KeeperLive`, `Design/Screens` |

## Next tasks (in order)
0. **Camera multi-kick session** (no parts needed): tripod, AE lock, 5 taped targets × 10 kicks, measure kick spot → goal line, export the *unmodified original*. Run `Prototypes/v0.1_SensingDesktop/kick_cam.py` → first tolerance distribution for OQ-2 from the camera alone. Then add trajectory-to-net extrapolation and try a live 30–60 fps loop.
1. **Order sensing parts** — piezos ×6 + Teensy 4.1 (~AU$70), OPS242-A radar (RobotShop), Pi 5 4 GB (long lead). `docs/parts/parts-list.md`.
2. **Email a light-curtain supplier** (AnLyHu / Dadisick): scan cycle ≤ 5 ms? per-beam RS-485 output? Then order one 10 mm / ~1,200 mm pair.
3. **Fix Wi-Fi** (15 min): router AP/client isolation off, untick ESP-NOW in WLED, reserve .116. Unlocks web UI + DDP without USB.
4. **Book an electrician** for the mains lead on the 400 W supply.
5. **Piezo test on the board** when parts land: 4 corner discs + 1 on a batten, µs timestamps on the Teensy, 10 kicks × 5 marked points → tolerance distribution. Then radar, then pod camera, then light curtain (`sensing-architecture.md` §Test plan).
6. **Close the loop**: impact → cross lights on the board. Film it.

## Blocked / waiting on
- Pi Global Shutter Camera: out of stock at every AU seller (4 Nov). Restock notice at Core; Arducam AR0234 (60 fps) is the stand-in.
- OPS243-A: Mouser AU backorder (~6 Nov). OPS242-A is in stock and good enough.
- Electrician availability.

## Decisions pending (see OPEN-QUESTIONS)
**Phone as the MVP sensor** (Ben, 6 Nov): use a phone (240 fps slo-mo, exposure lock, already in every pocket) as the camera for the first product instead of a custom pod; custom camera later. Not yet in DECISIONS — confirm, then it changes the sensing architecture, the app, and the next prototype (`v0.2`: phone-side capture + server analysis, or on-device).
Also: per-panel vs per-goal supplies (OQ-6); panel construction base-sheet vs open-backed (OQ-1, decided by the piezo test).

## Done recently
- 6 Nov: repo on GitHub (MadeActive/Kazen); `Dev/` → `Prototypes/v0.x_*`; speed now from a trajectory fit, not kick/net frames; found the Mac camera delivers 15 fps at 1080p (files said 30) — all 5 Nov live timings were 2× fast until corrected; live tracker now measures and records the real frame rate.
- 5 Nov (pm): camera sensing prototype — `kick_cam.py` (goal-frame fit, ball state machine, events, goal-face output) built and checked against one slo-mo kick; frame-rate sweep 240/120/60/30. Decision: impact = first net motion, not ball deceleration.
- 2–3 Nov: SP805E + 2 × 5 m WS2815 wired and lit; USB serial link characterised (baud gotchas, 921600 dead on Mac); `goal_patterns.py` written; board mapping verified.
- 4 Nov: sensing options worked through; candidate architecture (behind-kicker pod + posts-only light curtain + per-batten piezos, radar as reference); shopping list priced.
- 5 Nov: repo restructured into reference / log / state; Sept summary superseded; numbers reconciled.
