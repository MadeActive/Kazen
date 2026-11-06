# 6 Nov 2026 — GitHub, Prototypes/ layout, trajectory-fit speed, phone-as-sensor direction

## Repo
- Pushed to **github.com/MadeActive/Kazen** (the working folder is the repo). `Dev/` became `Prototypes/` with one versioned folder per prototype: `v0.0_KeeperLive`, `v0.1_LedTestBoard`, `v0.1_SensingDesktop`. Video captures are gitignored (2.7 GB); their `.events.jsonl` / `.times.csv` sidecars are committed.

## Speed measurement, second attempt
Yesterday's numbers were wrong for three stacked reasons, found by stepping frames with a counter:
1. **Frame rate.** The Mac camera delivered ~15 fps at 1920×1080 (wall-clock stamps in the event logs: 52 frames in 3.47 s) but the clips were written as 30 fps, so every live timing was 2× fast. The gravity curvature of the fitted trajectories independently prefers 15 fps (residuals 0.4–0.7σ vs 0.8–1.6σ at 30). `live_tracker.py` now measures the delivered rate, writes clips at it and saves a per-frame timestamp sidecar.
2. **Kick late by ~3 frames** — the "spot empty" trigger waited three frames. Now back-dated, and the whole-frame search for the departing ball starts on the first empty frame.
3. **Impact late by up to 6 frames** — net motion is a poor clock (dull against moving fronds, and the ball is through the line before the net bulges).

New method (`annotate_clip.py`): each tracked flight frame → 3-D position (range from the ball's apparent radius, Ø 22 cm; direction from the pixel; focal ~1150 px @1920). Fit **P(τ) = P_rest + Vτ + ½gτ²** by Gauss-Newton through all observations (u, v, r). Kick = where the fit passes the resting position; goal-line crossing = where it reaches the vertical plane through the two posts (ranges from post pixel heights); a sudden stop in the track ends the flight (ball caught in a target pocket). Speed = path length / flight. Rejected if rms > 3σ; fallback to kick / first-frame-past-line.
Results, 5 Nov 17:13–17:17, the kid, ~5 m: **50, 52, 53, 57, 52 km/h** (one clip started on the kick — no speed). Checks against the frame counter on 171334: foot on ball f40, airborne f41, at the posts f45–46, in net f47 → fit says kick f40.2, line f45.4.
Caveats: 15 fps gives 4–5 flight frames per kick; ±1 frame at each end is still ±15 %. Needs: 720p/30 fps on the Mac or, better, the phone at 240 fps. Ball diameter matters (kid's ball may be Ø 20 cm → ranges 9 % short); focal length matters linearly for distance (Ben's paced 5–5.5 m agrees with the 4.8–5.6 m estimates).

## Direction
Ben: **phone as the MVP sensor** — far cheaper to ship than a pod; custom camera later. Recorded in STATUS as a pending decision. Candidate next prototype `v0.2_SensingPhone`: phone films (240 fps), analysis server-side first (reuse this code), on-device later.
