# Sensing architecture

Reference. Distilled from `docs/log/2026-11-04-sensing-architecture-discussion.md` (which has the full reasoning, rejected options and sources). **Status: candidate architecture, nothing measured yet.**

## What has to be sensed
| Need | Used for | Precision |
|---|---|---|
| Kick moment | keeper commit trigger, time-of-flight speed | ≤ 30 ms, ideally ≤ 10 ms |
| Ball speed | Power game, every result | rounded km/h, honest |
| Impact position | every game, impact cross | ≤ 150 mm, ideally ~70 mm (one column) |
| Impact time | result timing, proof the keeper committed first | tens of ms |
| Kicker position | Free Kick, speed distance | ~0.5 m |
| Pre-shot body read | The Reader keeper | hips / plant foot 100–300 ms before contact |
| Misses | MISS without a timeout | binary |
| Hand taps on the face | touch games | zone level |

The two product-killing risks (ux-spec §11): impact tolerance worse than ~150 mm, and kick moment not detectable within ~30 ms. **Measure these first.**

## Current leaning
- **Behind-kicker pod** (launch-monitor style; global-shutter camera at 120 fps, on-device detection, low-latency radio, battery): kick moment (~8 ms), launch speed and direction, pre-shot read, kicker position, trajectory, misses, clips. Weakest reading: impact point from end-of-track on a lit face (~±30–50 mm).
- **In the goal, posts only:** measuring light curtain post-to-post for height (10 mm), per-batten piezos for column (71 mm) and impact time; both serve hand-tap games. Nothing on the crossbar, nothing on the ground, no cameras on the goal.
- **Doppler radar** (OmniPreSense OPS242-A / OPS243-A, 24 GHz, USB text API) on the bench as the speed / kick-time reference instrument; may leave the BOM.
- Microphone dropped unless radar and pod both fail.

## Rejected / parked (see the log for why)
Camera on the goal looking at its own face (sees it edge-on); cameras on arms at the top corners (shake, must survive a 100 km/h ball); ground cones (viable, not preferred); passive light sensors in the channels (fails outdoors); handheld radar guns (closed APIs).

## Why sensing comes before the real panel
Piezo placement (4 corner discs with TDOA on a rigid base sheet vs one disc per batten on open-backed battens) and what lives in the posts dictate how the panel is built. Building the 13 × 36 panel first risks building it twice.

## Test plan on the existing board
1. **Piezos** — 4 corner discs + one on a batten, µs timestamps on a Teensy 4.1. 10 kicks at 5 marked points → tolerance distribution. Also rebound debounce, hard-strike (does the ball reach the strip?), throw vs kick, hand slap.
2. **Radar** — OPS242-A on USB. Does it see a size 4/5 ball at 7 m? Log kick time and peak speed against piezo impact time. Second serial port in `goal_patterns.py`.
3. **Pod camera** — Pi global-shutter camera at 120 fps, tripod 2 m behind and 1 m to the side of the spot. Kick frame and launch speed vs radar; end-of-track impact vs piezos.
4. **Light curtain** — one 10 mm-pitch ~1,200 mm RS-485 pair across the board; log beam frames with piezo timestamps. Ask the supplier first: scan cycle ≤ 5 ms? per-beam states on RS-485?
5. **Close the loop** — impact event → cross lights on the board. The Stage 4 "KICK → burst → number" moment; first thing worth filming.

Parts and prices: `docs/parts/parts-list.md`.
