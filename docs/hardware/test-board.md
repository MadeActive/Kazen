# Test board (Nov 2026)

Reference for the rig all current work runs on. Photo: `Photos/TestBoard_v1.jpg`.

- ~1.2 m × 0.5 m board, 27 mm gutters, 40 mm battens → **67 mm column pitch** (real panel is 71 mm — nothing size-critical should be judged on the board).
- Uncut 300-LED chain (2 × 5 m WS2815), **8 columns × 34 rows** between the marked lines; 7-LED loops top and bottom are off-screen.
- Chain, from the controller end: 1 lead-in, then runs of **34 / 34 / 34 / 26 / 34 / 34 / 34 / 20**, alternating up / down, 7-LED loops between. The 26 on column 4 is the two-strip joiner (dead gap at the bottom, LED 150). Column 8 ends after 20. Total 300.
- Encoded as `LAYOUTS['board']` in `goal_patterns.py`; verified with `identify` and `hold` (bars line up across all columns).

## What reads well at full size
Anything that lights every pixel (bounce, spiral, rainbow). Thin rings looked sparse; the goal celebration was rebuilt as solid expanding colour bands ~270 mm thick with a white leading edge.

## What the board is for next
The sensing tests (`sensing-architecture.md` §5): piezos, radar, pod camera, light curtain, and closing the loop impact → cross on the board.
