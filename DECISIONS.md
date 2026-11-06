# Decisions

Append only. Newest at the bottom. Each entry: date · decision · why · what it supersedes. If a decision is reversed, add a new entry — don't edit the old one.

| Date | Decision | Why | Supersedes |
|---|---|---|---|
| Sept 2026 | Addressable LED strip in fence-panel channels, not colour-changing materials or LED cabinets | Only option that is fast, full-colour, impact-tolerant and looks like a garden feature | Thermochromic, PDLC, e-paper, flip-dot, P10/P16 cabinets, pixel nodes |
| Sept 2026 | WS2815 12 V, 30 LEDs/m, black PCB, IP65 (BTF) | Per-pixel IC, backup data line, 12 V survives 1.2–2 m runs | RGBNW (parked) |
| Sept 2026 | Battens vertical; 3 panels side by side | Reads as a goal; keeper can dive to either post | — |
| Sept 2026 | Keeper commits before impact, never computed backwards | Trust is the product (ux-spec §8.1, §11) | — |
| Sept 2026 | App = optional second screen; four screens only; no account until the cloud is needed | ux-spec principles 1, 2, 5 | 35-item feature list |
| Sept 2026 | Impact location by piezo, not camera | Crossbar camera sees the face edge-on | — |
| Sept 2026 | Final per-panel controller Teensy 4.1 + Ethernet; SP805E for bench only | 2,048 px ceiling and Wi-Fi jitter on the SP805E | — |
| Oct 2026 | Panel is 1200 mm tall → 36 rows / 468 per panel / 1,404 full goal | Real fence panel is 1.2 × 0.9 m | 1.8 m / 54 rows / 2,106 (Sept summary) |
| 3 Nov 2026 | USB serial at 230400 as the bench link; always hand baud back to 115200 on exit | 921600 is dead on the Mac CH340 driver; board keeps baud across port opens | 115200 (~12 fps) |
| 3 Nov 2026 | Goal celebration = solid expanding bands ~270 mm thick, not thin rings | Thin rings read as sparse at 67–71 mm column pitch | first goal pattern |
| 4 Nov 2026 | **Sensing tests before building the real panel** | Piezo placement and post contents decide panel construction; avoid building it twice | implied "cut strips next" |
| 4 Nov 2026 | Candidate sensing architecture: behind-kicker pod + posts-only light curtain + per-batten piezos; radar as bench reference; mic dropped | See `docs/log/2026-11-04-sensing-architecture-discussion.md` | corner-camera, ground-cone, in-channel light-sensor options |
| 5 Nov 2026 | Repo split into reference (`docs/product`, `docs/hardware`), log (`docs/log`), state (`STATUS.md`); Sept summary superseded | Each chat was re-reading ~125 KB to find the current state | `Strategy/`, `md/` layout |
| 5 Nov 2026 | Camera sensing prototyped offline first (iPhone 240 fps slo-mo → OpenCV on the Mac), with "impact" defined as the first frame the net moves, not the ball's deceleration peak | Zero-cost while parts are on backorder; the net decelerates the ball over 5–10 frames so deceleration is late; 30 fps webcam capture is exactly where the simple tracker breaks | "pod camera test waits for Pi/AR0234" |
