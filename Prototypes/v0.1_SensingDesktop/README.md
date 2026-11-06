# Camera sensing prototype

Single camera behind the kicker → rest / approach / kick / impact events and the impact position on the goal face. Offline analysis of recorded video; classical OpenCV, no training. Findings: `docs/log/2026-11-05-camera-sensing-prototype.md`.

## Files
- `kick_cam.py` — the analysis. `python3 kick_cam.py VIDEO --config goal.json [--start N --end N] [--step K] [--render] [--tag NAME] [--out DIR]`
- `goal.json` — goal size, panel grid, capture fps, kick distance (for km/h), fallback resting-ball position, and the four inner goal corners in pixels (TL, TR, BR, BL).
- `pick_corners.py` — click the four inner corners on a frame and save them to `goal.json`. Run in a normal macOS Terminal (needs a window).

## Recording protocol
- iPhone Slo-mo, 1080p **240 fps**; long-press to lock AE/AF on the goal.
- Phone propped 40–60 cm off the grass, 1–1.5 m behind and a little to one side of the kick spot; whole goal and the ball both in frame; don't move it between kicks.
- Targets taped to the net (5 points), 2–3 kicks per target, ball back on the same spot each time.
- Measure kick spot → goal line (set `kick_distance_m`).
- Transfer the **unmodified original** (Photos → File → Export → Export Unmodified Original). AirDrop/Photos exports are rendered to 30 fps with a slowed middle section — usable for position, awkward for timing.

## Outputs (in `--out`, default `<video dir>/out`)
- `<name>_events.json` — per kick: rest/approach/kick/impact frames, impact in goal cm and panel cell, flight time, speed when the distance is known.
- `<name>_track.csv` — per-frame ball position, radius, goal coords, foreground counts.
- `<name>_goalface.png` — goal face with the 36 × 13 grid and impact marks.
- `<name>_frames/` — annotated key frames; `--render` also writes an annotated mp4 of the analysed range.

## Frame-rate test
`--step 2/4/8` drops frames from a 240 fps recording to emulate 120/60/30 fps. On the first kick: 120 and 60 fps within 3–4 cm of 240 fps; 30 fps breaks this tracker.

## Live tracker (`live_tracker.py`)
Same tracker, causal events (READY / APPROACH / KICK / IMPACT / LOST). Run from a normal macOS Terminal (needs a window and camera permission):
```
cd ~/Documents/DEV/AI/Kazen/Prototypes/v0.1_SensingDesktop
python3 -m venv .venv && source .venv/bin/activate && pip install opencv-python numpy   # once
source .venv/bin/activate
python3 live_tracker.py --source 0 --config goal_live.json --surface net
```
Flow: **SETUP** preview (nothing recorded) — set the lid, `g` + click the four inner corners, `s` to save, walk away, place the ball, wait for the bottom line to say *SPACE to arm* → **SPACE** → big **3-2-1** → **ARMED** records `Photos/kick_<date>_<time>.mp4` (+ `.events.jsonl`) and tracks → impact + 1 s (or 12 s timeout) → stops and shows **HIT x × y cm, col/row** large for 5 s → back to SETUP for the next kick. `Esc` cancels a kick, `q` quits. Events seen while not armed (hands at the keyboard) are ignored.
Other keys: `b` click the ball if it isn't found on its own · `r` reset · `w`/`n` wall or net mode. Default camera mode is 1920×1080 @ 30.
Each clip can be re-run offline with `kick_cam.py` (set `capture_fps` 30 and the clip's corners in a config).
Checked on the 5 Nov recording at emulated 30/60 fps: kick within ~3 frames, impact 41×87 / 43×92 cm vs 30×92 measured (net mode).
