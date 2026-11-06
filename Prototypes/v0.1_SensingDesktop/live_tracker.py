#!/usr/bin/env python3
"""
live_tracker.py — Kazen live ball tracker (webcam or video file), causal events.

Reuses the goal-frame fitter and the rest/flight/lost ball tracker from kick_cam.py, but the
event logic is causal (decides as frames arrive) so it can drive the panel.

Events it prints / logs:
  READY     ball found at rest (anchor set)
  APPROACH  leg-sized foreground next to the ball
  KICK      ball left the spot          (latency = ms after the frame that showed it)
  IMPACT    wall mode: ball velocity reversed (bounce)  |  net mode: net started moving
            → position in goal cm + panel cell; refined a few frames later by intersecting
              the incoming and rebound trajectories (wall mode)
  LOST      track lost / ball left; waits for a ball at rest again

Flow (camera): SETUP preview (calibrate, place the ball, nothing recorded) → SPACE → big 3-2-1 →
ARMED: records to Photos/kick_<time>.mp4 and logs events → impact + 1 s (or 12 s timeout) → stops,
shows the result large for 5 s → back to SETUP for the next kick.  Esc cancels a kick.

Run on the Mac (needs a window):
  pip3 install opencv-python numpy            (once)
  python3 live_tracker.py --source 0 --config goal_live.json --surface net
  python3 live_tracker.py --source ../../../Photos/ballkick.MOV --emulate-fps 30 --config goal.json --headless

Keys in the window:
  SPACE arm (3-2-1 then record)      Esc  cancel the current kick
  a   auto-detect the goal (also runs at startup); the yellow quad shows what it found
  g   pick the 4 goal corners yourself (click TL, TR, BR, BL; z = undo) — always wins over auto
  b   click the resting ball (if auto-detect doesn't find it)
  r   reset tracker (look for a resting ball again)
  s   save corners (and surface) to the config file
  w/n toggle wall / net surface mode
  q   quit

Options:
  --record-dir DIR    where kick clips go (default: the Photos folder of the repo)
  --annotate          also save kick_<time>_annotated.mp4 (quad, ball, trail, panel) next to the raw clip
  --post-s / --timeout-s   seconds to keep recording after impact / give up without one
  --headless          no window (file source only); writes <out>/live_annotated.mp4 instead
  --width/--height/--fps   camera mode (default 1920x1080 @ 30; the Mac camera also does 1280x720)
"""
import argparse, json, os, sys, time, math
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kick_cam import GoalTracker, BallTracker, find_resting_ball, load_cfg, auto_goal   # noqa: E402

COLS = {"rest": (0, 200, 255), "flight": (0, 255, 0), "lost": (0, 0, 255)}


class CausalEvents:
    """Turns the per-frame tracker state into events with no look-ahead (beyond 2 frames)."""

    def __init__(self, cfg, goal, surface="wall", fps=30.0):
        self.cfg, self.goal, self.surface, self.fps = cfg, goal, surface, fps
        self.reset()

    def reset(self):
        self.prev_state = None
        self.hist = []                 # flight history: (frame_idx, t, x, y, r)
        self.kick = None               # dict
        self.impact = None             # dict
        self.rev_count = 0
        self.net_base = None; self.net_vals = []
        self.approach_n = 0
        self.approach_fired = False
        self.last_net = 0

    def _goal_cm(self, pt):
        gx, gy = self.goal.to_goal(pt)
        W, H = self.cfg["goal_w_cm"], self.cfg["goal_h_cm"]
        col = int(np.clip(gx / W * self.cfg["panel_cols"], 0, self.cfg["panel_cols"] - 1)) + 1
        row = int(np.clip((H - gy) / H * self.cfg["panel_rows"], 0, self.cfg["panel_rows"] - 1)) + 1
        m = self.cfg["ball_diameter_cm"] / 2                       # ball centre is a radius inside the edges when it touches them
        return gx, gy, col, row, bool(-m <= gx <= W + m and -m <= gy <= H + m)

    def update(self, fi, t, bt, x, y, r, det, foot, net, net_ball=None):
        """Returns a list of event dicts emitted this frame."""
        ev = []
        st = bt.state
        if st != self.prev_state:
            if st == bt.REST:
                self.reset(); self.prev_state = st
                ev.append(dict(type="READY", frame=fi, t=t, px=[float(x), float(y)], r=float(r)))
                return ev
            if st == bt.FLIGHT and self.prev_state == bt.REST:
                lag = int(getattr(bt, "kick_lag", 0))
                self.kick = dict(type="KICK", frame=fi - lag, t=t - lag / self.fps, seen_frame=fi,
                                 anchor=[float(bt.anchor[0]), float(bt.anchor[1])], rest_r=float(bt.anchor_r))
                ev.append(self.kick)
            if st == bt.LOST:
                ev.append(dict(type="LOST", frame=fi, t=t))
        self.prev_state = st

        if st == bt.REST and not self.approach_fired:
            disc = math.pi * (4.5 * bt.anchor_r) ** 2
            self.approach_n = self.approach_n + 1 if foot > 0.12 * disc else 0
            if self.approach_n >= 3:
                self.approach_fired = True
                ev.append(dict(type="APPROACH", frame=fi, t=t))

        # quiet-net baseline is measured while the ball is still at rest
        if st == bt.REST:
            self.net_vals.append(net); self.net_vals = self.net_vals[-15:]
        # net mode: the net moving is the impact, whether or not the ball is still being tracked
        if self.surface == "net" and self.kick is not None and self.impact is None:
            if self.net_base is None:
                self.net_base = float(np.median(self.net_vals)) if self.net_vals else float(net)
            if True:
                thr = self.net_base + max(300, 4 * self.net_base)
                if net > thr and self.last_net > thr:
                    # position: tracked ball if it is in the goal, else the white blob found in the net
                    if det and self.goal.inside((x, y), 30):
                        hx, hy = float(x), float(y)
                    elif net_ball is not None:
                        hx, hy = net_ball
                    else:
                        hx, hy = (self.hist[-1][2], self.hist[-1][3]) if self.hist else (float(x), float(y))
                    gx, gy, col, row, on = self._goal_cm((hx, hy))
                    self.impact = dict(type="IMPACT", frame=fi - 1, t=t, seen_frame=fi, px=[hx, hy],
                                       goal_cm=[round(gx, 1), round(gy, 1)], cell=[col, row], on_target=on,
                                       flight_s=round(t - self.kick["t"], 3), latency_ms=round((time.time() - t) * 1000, 1),
                                       refined=True, source="net-motion" + ("" if det else " (ball not tracked)"))
                    ev.append(self.impact)
        self.last_net = net

        if st == bt.FLIGHT and det:
            self.hist.append((fi, t, float(x), float(y), float(r)))
            if self.impact is None:
                hit = None
                # net mode, soft shot: tracked ball inside the goal that stops / reverses is also an impact
                if self.surface == "net" and len(self.hist) >= 4 and self.goal.inside((x, y), 10):
                    h = np.array([(p[2], p[3]) for p in self.hist[-4:]])
                    v_now = np.linalg.norm(h[-1] - h[-2]); v_prev = np.linalg.norm(h[-2] - h[-3])
                    stopped = v_now < 2.0 and v_prev < 4.0                   # px/frame: it has come to rest in the goal
                    rev = np.dot(h[-1] - h[-2], h[-2] - h[-4]) < 0 and v_now > 2.0   # bounced
                    if stopped or rev:
                        hit = self.hist[-2]
                if self.surface == "wall" and len(self.hist) >= 5:
                    # velocity now vs mean velocity over the previous frames: reversal → bounce
                    h = np.array([(p[2], p[3]) for p in self.hist[-6:]])
                    v_now = h[-1] - h[-2]
                    v_prev = (h[-2] - h[0]) / max(1, len(h) - 2)
                    if np.dot(v_now, v_prev) < 0 and np.linalg.norm(v_now) > 1.0:
                        self.rev_count += 1
                    else:
                        self.rev_count = 0
                    if self.rev_count >= 2:
                        k = len(self.hist) - 1 - self.rev_count          # last frame before reversal
                        hit = self.hist[k]
                if hit is not None:
                    gx, gy, col, row, on = self._goal_cm((hit[2], hit[3]))
                    self.impact = dict(type="IMPACT", frame=hit[0], t=hit[1], seen_frame=fi, px=[hit[2], hit[3]],
                                       goal_cm=[round(gx, 1), round(gy, 1)], cell=[col, row], on_target=on,
                                       flight_s=round(hit[1] - self.kick["t"], 3) if self.kick else None,
                                       latency_ms=round((time.time() - hit[1]) * 1000, 1), refined=False)
                    ev.append(self.impact)
            elif self.surface == "wall" and not self.impact["refined"]:
                # refine once we have a few rebound frames: intersect incoming and outgoing lines
                idx = [i for i, p in enumerate(self.hist) if p[0] == self.impact["frame"]]
                if idx:
                    k = idx[0]
                    inc = np.array([(p[2], p[3]) for p in self.hist[max(0, k - 8):k + 1]], np.float32)
                    out = np.array([(p[2], p[3]) for p in self.hist[k + 1:k + 9]], np.float32)
                    if len(inc) >= 3 and len(out) >= 4:
                        l1 = cv2.fitLine(inc, cv2.DIST_L2, 0, 0.01, 0.01).ravel()
                        l2 = cv2.fitLine(out, cv2.DIST_L2, 0, 0.01, 0.01).ravel()
                        A = np.array([[l1[0], -l2[0]], [l1[1], -l2[1]]])
                        if abs(np.linalg.det(A)) > 1e-6:
                            tt = np.linalg.solve(A, np.array([l2[2] - l1[2], l2[3] - l1[3]]))[0]
                            px, py = float(l1[2] + l1[0] * tt), float(l1[3] + l1[1] * tt)
                            if np.hypot(px - self.impact["px"][0], py - self.impact["px"][1]) < 4 * self.hist[k][4]:
                                gx, gy, col, row, on = self._goal_cm((px, py))
                                self.impact.update(px_refined=[px, py], goal_cm=[round(gx, 1), round(gy, 1)],
                                                   cell=[col, row], on_target=on, refined=True)
                                ev.append(dict(self.impact, type="IMPACT_REFINED", seen_frame=fi))
                        else:
                            self.impact["refined"] = True
                    elif len(self.hist) > k + 12:
                        self.impact["refined"] = True
        return ev


def draw_panel(img, cfg, impact, state, origin=(20, 60), cell=10):
    cols, rows = cfg["panel_cols"], cfg["panel_rows"]
    x0, y0 = origin
    cv2.rectangle(img, (x0 - 4, y0 - 4), (x0 + cols * cell + 4, y0 + rows * cell + 4), (40, 40, 40), -1)
    for c in range(cols):
        for r in range(rows):
            col = (70, 70, 70)
            if state == "rest": col = (90, 120, 90)
            if impact and impact["cell"] == [c + 1, r + 1]: col = (0, 140, 255)
            cv2.rectangle(img, (x0 + c * cell + 1, y0 + r * cell + 1), (x0 + (c + 1) * cell - 1, y0 + (r + 1) * cell - 1), col, -1)


def true_fps_of(video_path):
    """Real frame rate of a recorded clip: from its <stem>.times.csv sidecar (per-frame wall clock) if present,
    else from the two most distant events in <stem>.events.jsonl, else None."""
    stem = os.path.splitext(video_path)[0]
    try:
        rows = [l.split(",") for l in open(stem + ".times.csv").read().strip().splitlines()[1:]]
        if len(rows) >= 10:
            f0, t0 = int(rows[0][0]), float(rows[0][1]); f1, t1 = int(rows[-1][0]), float(rows[-1][1])
            if t1 > t0: return (f1 - f0) / (t1 - t0)
    except (OSError, ValueError, IndexError):
        pass
    try:
        ev = [json.loads(l) for l in open(stem + ".events.jsonl") if l.strip()]
        ev = [e for e in ev if "frame" in e and "t" in e]
        if len(ev) >= 2:
            e0, e1 = min(ev, key=lambda e: e["frame"]), max(ev, key=lambda e: e["frame"])
            if e1["frame"] - e0["frame"] >= 10 and e1["t"] > e0["t"]:
                return (e1["frame"] - e0["frame"]) / (e1["t"] - e0["t"])
    except (OSError, ValueError):
        pass
    return None


def big_text(img, txt, color=(255, 255, 255), scale=None, y=None, thick=None):
    """Centred text large enough to read from across the garden."""
    H, W = img.shape[:2]
    scale = scale or (W / 160.0 if len(txt) <= 2 else W / (90.0 + 18 * len(txt)))
    thick = thick or max(3, int(scale * 2.5))
    (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_DUPLEX, scale, thick)
    x = (W - tw) // 2; y = y or (H + th) // 2
    cv2.putText(img, txt, (x, y), cv2.FONT_HERSHEY_DUPLEX, scale, (0, 0, 0), thick + 8, cv2.LINE_AA)
    cv2.putText(img, txt, (x, y), cv2.FONT_HERSHEY_DUPLEX, scale, color, thick, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="0", help="camera index or video file")
    ap.add_argument("--config", default="goal_live.json")
    ap.add_argument("--surface", choices=["wall", "net"], default=None)
    ap.add_argument("--width", type=int, default=1920); ap.add_argument("--height", type=int, default=1080); ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--emulate-fps", type=float, default=None, help="file source: drop frames to this rate")
    ap.add_argument("--record-dir", default=None, help="where kick clips go (default ../../../Photos next to this script)")
    ap.add_argument("--headless", action="store_true"); ap.add_argument("--out", default="out")
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--fps-override", type=float, default=None, help="true frame rate of a file source (default: sidecar / events / container)")
    ap.add_argument("--annotate", action="store_true", help="also save an annotated copy of each kick clip (kick_<time>_annotated.mp4)")
    ap.add_argument("--post-s", type=float, default=1.0, help="keep recording this long after the impact")
    ap.add_argument("--timeout-s", type=float, default=12.0, help="stop a kick clip after this long with no impact")
    a = ap.parse_args()

    cfg = load_cfg(a.config if os.path.exists(a.config) else None)
    surface = a.surface or cfg.get("surface", "wall")
    is_file = not a.source.isdigit()
    here = os.path.dirname(os.path.abspath(__file__))
    rec_dir = a.record_dir or os.path.abspath(os.path.join(here, "..", "..", "..", "Photos"))

    def open_cam(idx):
        c = cv2.VideoCapture(idx, cv2.CAP_AVFOUNDATION) if sys.platform == "darwin" else cv2.VideoCapture(idx)
        if not c.isOpened():
            return None, None
        c.set(cv2.CAP_PROP_FRAME_WIDTH, a.width); c.set(cv2.CAP_PROP_FRAME_HEIGHT, a.height); c.set(cv2.CAP_PROP_FPS, a.fps)
        for _ in range(60):                     # AVFoundation can return empty frames for the first second or two
            ok, fr = c.read()
            if ok and fr is not None and fr.size:
                return c, fr
            time.sleep(0.05)
        c.release()
        return None, None

    if is_file:
        cap = cv2.VideoCapture(a.source); ok, f = cap.read()
        if not ok:
            sys.exit("cannot open video file " + a.source)
    else:
        cap, f = open_cam(int(a.source))
        if cap is None:
            print(f"camera {a.source} gave no frames. Probing indices 0-4 ...")
            found = []
            for i in range(5):
                c, fr = open_cam(i)
                if c is not None:
                    found.append((i, fr.shape[1], fr.shape[0])); c.release()
            if found:
                print("cameras that work:", ", ".join(f"--source {i} ({w}x{h})" for i, w, h in found))
            else:
                print("no camera delivered frames. On macOS: System Settings > Privacy & Security > Camera > allow Terminal, "
                      "then quit and reopen Terminal. Also close other apps using the camera.")
            sys.exit(1)
    H, W = f.shape[:2]
    src_fps = cap.get(cv2.CAP_PROP_FPS) or a.fps
    fps_note = "container"
    if is_file:
        true_fps = true_fps_of(a.source)
        if a.fps_override:
            src_fps, fps_note = a.fps_override, "override"
        elif true_fps:
            src_fps, fps_note = true_fps, "measured (sidecar/events)"
    eff_fps = a.emulate_fps if (is_file and a.emulate_fps) else (a.fps if not is_file else src_fps)
    skip = int(round(cfg["capture_fps"] / a.emulate_fps)) if (is_file and a.emulate_fps) else 1
    stride = max(1, int(round(240.0 / eff_fps)))               # scales the tracker's gates for slow frame rates
    print(f"source {a.source}: {W}x{H} @ {src_fps:.1f} fps ({fps_note}), effective {eff_fps:.1f} fps, surface={surface}, gate stride {stride}")
    print(f"kick clips → {rec_dir}")

    os.makedirs(a.out, exist_ok=True); os.makedirs(rec_dir, exist_ok=True)
    ann = cv2.VideoWriter(os.path.join(a.out, "live_annotated.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), eff_fps, (W, H)) if a.headless else None

    goal_src = "none"

    def set_goal(corners, src):
        """Use these corners as the goal.  They are taken as given; the white-bar fitter only
        refines them if it can see the bars (fit_enabled), otherwise they stay exactly as set."""
        nonlocal goal, have_goal, fit_enabled, goal_src, bt
        cfg["corners"] = [list(map(float, q)) for q in corners]
        goal = GoalTracker(cfg)
        fit_enabled = goal.initialise(f)
        if not fit_enabled:
            goal.corners = np.array(cfg["corners"], float); goal.update(f)
        have_goal, goal_src, bt = True, src, None
        print(f"goal ({src}): {goal.corners.round(0).tolist()}" + ("" if fit_enabled else "  (bars not confirmed; using as given)"))

    goal, have_goal, fit_enabled = GoalTracker(cfg), False, False
    if cfg.get("corners") and all(0 <= c[0] < W and 0 <= c[1] < H for c in cfg["corners"]):
        set_goal(cfg["corners"], "config")          # what you saved last time with s
    else:
        q = auto_goal(f, cfg)
        if q is not None:
            set_goal(q, "auto")
        else:
            print("no saved goal and none found automatically — press g and click the 4 inner corners")
    bt, events, state_txt = None, None, "no goal — press g"
    picking, pick_pts, pick_ball = False, [], False
    clicked = {"pt": None}

    # ---- phases: setup → countdown → armed (recording + events) → done (show result) → setup
    phase = "armed" if is_file else "setup"
    phase_t = time.time()
    rec, rec_path, log, kick_events, result, rec_ann = None, None, None, [], None, None
    times_f, frame_times = None, []                              # camera: wall-clock per frame → measured fps
    cam_fps = eff_fps
    impact_t = None

    def start_clip():
        nonlocal rec, rec_path, log, kick_events, result, impact_t, bt, events, rec_ann
        nonlocal times_f
        stem = time.strftime("kick_%Y%m%d_%H%M%S")
        rec_path = os.path.join(rec_dir, stem + ".mp4")
        rec = cv2.VideoWriter(rec_path, cv2.VideoWriter_fourcc(*"mp4v"), cam_fps, (W, H))      # real rate, so playback is real time
        if a.annotate:
            rec_ann = cv2.VideoWriter(os.path.join(rec_dir, stem + "_annotated.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), cam_fps, (W, H))
        times_f = open(os.path.join(rec_dir, stem + ".times.csv"), "w"); times_f.write("frame,t\n")
        if events is not None: events.fps = cam_fps
        log = open(os.path.join(rec_dir, stem + ".events.jsonl"), "w")
        kick_events, result, impact_t = [], None, None
        if bt is not None and bt.state != bt.REST:
            bt = None                                   # re-find the ball now that the kicker is out of frame
        print(f"--- recording {rec_path}")

    def stop_clip(reason):
        nonlocal rec, log, phase, phase_t, result, rec_ann, times_f
        if rec: rec.release(); rec = None
        if rec_ann: rec_ann.release(); rec_ann = None
        if times_f: times_f.close(); times_f = None
        if log: log.close(); log = None
        imp = [e for e in kick_events if e["type"].startswith("IMPACT")]
        kick = [e for e in kick_events if e["type"] == "KICK"]
        if imp:
            e = imp[-1]
            result = f"HIT  {e['goal_cm'][0]:.0f} x {e['goal_cm'][1]:.0f} cm   col {e['cell'][0]} row {e['cell'][1]}" + ("" if e["on_target"] else "  (off target)")
        elif kick:
            result = "KICK seen, no impact"
        else:
            result = "no kick detected"
        print(f"--- stopped ({reason}): {result}   clip {os.path.basename(rec_path) if rec_path else '-'}")
        phase, phase_t = "done", time.time()

    def on_mouse(e, x, y, flags, _):
        if e == cv2.EVENT_LBUTTONDOWN:
            clicked["pt"] = (x, y)

    if not a.headless:
        cv2.namedWindow("kazen live", cv2.WINDOW_NORMAL); cv2.setMouseCallback("kazen live", on_mouse)

    fi, n_proc, t_last_fit, t0 = 0, 0, 0, time.time()
    proc_ms, impact_show = [], None
    track_f = open(os.path.join(a.out, "file_track.csv"), "w") if is_file else None
    if track_f: track_f.write("frame,t,state,x,y,r,det,net\n")
    while True:
        if fi > 0:
            ok, f = cap.read()
            if not ok: break
        fi += 1
        if is_file and skip > 1 and (fi - 1) % skip: continue
        t_frame = time.time() if not is_file else (fi - 1) / src_fps
        n_proc += 1
        if not is_file:                                          # measure what the camera really delivers
            frame_times.append(t_frame); frame_times = frame_times[-90:]
            if len(frame_times) >= 30:
                cam_fps = (len(frame_times) - 1) / max(1e-3, frame_times[-1] - frame_times[0])
            if n_proc == 60:
                print(f"camera is delivering {cam_fps:.1f} fps at {W}x{H}" + ("  (slow: try --width 1280 --height 720)" if cam_fps < 24 else ""))
        if rec and times_f: times_f.write(f"{fi},{t_frame:.4f}\n")
        if a.max_frames and n_proc > a.max_frames: break
        tp0 = time.time()
        vis = f.copy()
        now = time.time()

        # ---- phase transitions
        if phase == "countdown":
            left = 3.0 - (now - phase_t)
            if left <= 0:
                phase, phase_t = "armed", now
                start_clip()
        elif phase == "armed" and not is_file:
            if impact_t is not None and now - impact_t >= a.post_s:
                stop_clip("impact + %.0fs" % a.post_s)
            elif now - phase_t > a.timeout_s:
                stop_clip("timeout")
        elif phase == "done" and now - phase_t > 5:
            phase = "setup"
        if rec: rec.write(f)

        # ---- corner / ball picking (interactive)
        if clicked["pt"] is not None:
            p = clicked["pt"]; clicked["pt"] = None
            if picking:
                pick_pts.append(p)
                if len(pick_pts) == 4:
                    picking = False
                    set_goal(pick_pts, "clicked")
            elif pick_ball:
                hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
                white = cv2.inRange(hsv, (0, 0, cfg["white_v_min"]), (179, cfg["white_s_max"], 255))
                white = cv2.morphologyEx(white, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
                cnts, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                best = None
                for c in cnts:
                    if cv2.pointPolygonTest(c, p, False) >= 0 or cv2.pointPolygonTest(c, p, True) > -15:
                        (x, y), r = cv2.minEnclosingCircle(c); best = (x, y, r)
                if best:
                    bt = BallTracker(cfg, best, stride); bt.bg.apply(f); bt.set_goal(goal.corners)
                    events = CausalEvents(cfg, goal, surface, cam_fps if not is_file else eff_fps); print(f"ball set at ({best[0]:.0f},{best[1]:.0f}) r={best[2]:.1f}")
                pick_ball = False

        # ---- tracking (runs in every phase so you can see the ball lock during setup; events only count when armed)
        if have_goal:
            if fit_enabled and now - t_last_fit > 1.0:        # refine the goal corners once a second
                goal.update(f); t_last_fit = now
            if bt is None:
                rb = find_resting_ball(f, goal, cfg)
                if rb is not None:
                    bt = BallTracker(cfg, rb, stride); bt.bg.apply(f); bt.set_goal(goal.corners)
                    events = CausalEvents(cfg, goal, surface, cam_fps if not is_file else eff_fps)
                state_txt = "looking for ball at rest"
            if bt is not None:
                x, y, r, det = bt.step(f)
                if bt.lost and n_proc % 5 == 0 and bt.reacquire(f, goal, cfg):
                    bt.set_goal(goal.corners)
                foot = bt.fg_near(bt.fg, (x, y), 4.5 * r)
                gm = np.zeros(bt.fg.shape, np.uint8); cv2.fillPoly(gm, [goal.corners.astype(np.int32)], 255)
                cv2.circle(gm, (int(x), int(y)), int(2.5 * r), 0, -1)
                net = int(cv2.countNonZero(cv2.bitwise_and(bt.fg, gm)))
                net_ball = None
                if events.kick is not None and events.impact is None:
                    hsv_ = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
                    wm = cv2.inRange(hsv_, (0, 0, cfg["white_v_min"]), (179, cfg["white_s_max"], 255))
                    gm2 = np.zeros(bt.fg.shape, np.uint8); cv2.fillPoly(gm2, [goal.corners.astype(np.int32)], 255)
                    m2 = cv2.bitwise_and(cv2.bitwise_and(bt.fg, wm), gm2)
                    m2 = cv2.morphologyEx(m2, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)); m2 = cv2.dilate(m2, np.ones((7, 7), np.uint8))
                    cnts2, _ = cv2.findContours(m2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    best2 = None
                    for c2 in cnts2:
                        a2 = cv2.contourArea(c2)
                        (bx2, by2), br2 = cv2.minEnclosingCircle(c2)
                        if a2 > 60 and br2 > 4 and a2 > 0.3 * math.pi * br2 * br2 and (best2 is None or a2 > best2[0]):
                            best2 = (a2, bx2, by2)
                    if best2: net_ball = (float(best2[1]), float(best2[2]))
                for e in events.update(fi, t_frame, bt, x, y, r, det, foot, net, net_ball):
                    e["wall_ms"] = round((now - t0) * 1000)
                    if phase != "armed":
                        continue                                # setup noise (hands, legs) is not logged
                    kick_events.append(e)
                    if log: log.write(json.dumps(e) + "\n"); log.flush()
                    if e["type"].startswith("IMPACT"):
                        impact_show = e
                        if impact_t is None: impact_t = now
                        print(f"[{e['type']}] frame {e['frame']}  goal ({e['goal_cm'][0]:.0f}, {e['goal_cm'][1]:.0f}) cm  cell col {e['cell'][0]} row {e['cell'][1]}"
                              f"  {'on' if e['on_target'] else 'OFF'} target  flight {e.get('flight_s')} s  seen +{e['seen_frame'] - e['frame']} frames")
                    else:
                        print(f"[{e['type']}] frame {e['frame']}" + (f"  at ({e['px'][0]:.0f},{e['px'][1]:.0f})" if "px" in e else ""))
                if track_f: track_f.write(f"{fi},{t_frame:.4f},{bt.state},{x:.1f},{y:.1f},{r:.1f},{int(det)},{net}\n")
                state_txt = bt.state
                col = COLS.get(bt.state, (255, 255, 255))
                cv2.circle(vis, (int(x), int(y)), int(max(r, 4)), col, 2)
                if events and events.hist:
                    for p in events.hist[-30:]:
                        cv2.circle(vis, (int(p[2]), int(p[3])), 2, (0, 255, 0), -1)
            c = goal.corners.astype(int)
            cv2.polylines(vis, [c.reshape(-1, 1, 2)], True, (0, 255, 255), 2)
        proc_ms.append((time.time() - tp0) * 1000)
        if len(proc_ms) > 60: proc_ms.pop(0)

        # ---- overlay
        draw_panel(vis, cfg, impact_show if phase in ("armed", "done") else None, state_txt)
        cv2.putText(vis, f"{phase.upper()}  |  goal: {goal_src}{' +refined' if fit_enabled else ''}  |  ball: {state_txt}  |  {surface}  |  {np.mean(proc_ms):.1f} ms/frame",
                    (20, 36), 0, 0.8, (255, 255, 255), 2)
        if phase == "setup":
            ready = have_goal and bt is not None and bt.state == bt.REST
            small = ready and bt.anchor_r < 8
            if not have_goal: msg = "no goal: press g and click the 4 corners (a = auto-detect)"
            elif not ready: msg = "waiting for ball at rest (b to click it)"
            elif small: msg = f"ball only {bt.anchor_r:.0f}px - move closer, or SPACE anyway"
            else: msg = "SPACE to arm"
            big_text(vis, msg, (0, 255, 0) if (ready and not small) else (0, 200, 255), scale=W / 900.0, y=H - 40)
        elif phase == "countdown":
            n = int(math.ceil(3.0 - (now - phase_t)))
            big_text(vis, str(max(1, n)), (0, 255, 255))
        elif phase == "armed":
            cv2.circle(vis, (W - 40, 40), 14, (0, 0, 255), -1)
            big_text(vis, "KICK", (0, 0, 255), scale=W / 700.0, y=H - 40)
            if impact_show:
                big_text(vis, f"HIT {impact_show['goal_cm'][0]:.0f} x {impact_show['goal_cm'][1]:.0f} cm", (0, 140, 255), scale=W / 500.0)
        elif phase == "done" and result:
            big_text(vis, result, (0, 140, 255) if result.startswith("HIT") else (0, 200, 255), scale=W / 650.0)
        if picking:
            cv2.putText(vis, f"click corner {['TL','TR','BR','BL'][len(pick_pts)]}  (z undo)", (20, H - 90), 0, 0.9, (0, 255, 255), 2)
            for q in pick_pts: cv2.drawMarker(vis, q, (0, 255, 255), cv2.MARKER_CROSS, 20, 2)
        if pick_ball:
            cv2.putText(vis, "click the ball", (20, H - 90), 0, 0.9, (0, 255, 255), 2)
        cv2.putText(vis, f"f{fi}", (W - 110, H - 20), cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(vis, f"f{fi}", (W - 110, H - 20), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        if ann: ann.write(vis)
        if rec_ann: rec_ann.write(vis)
        if not a.headless:
            cv2.imshow("kazen live", vis)
            k = cv2.waitKey(1) & 0xFF
            if k == ord("q"): break
            if k == ord(" ") and phase in ("setup", "done") and have_goal:
                phase, phase_t, impact_show = "countdown", now, None
                print("--- armed: 3 ...")
            if k == 27 and phase in ("countdown", "armed"):          # Esc cancels a kick
                if rec: stop_clip("cancelled")
                else: phase = "setup"
            if k == ord("g"): picking, pick_pts = True, []
            if k == ord("a"):
                q = auto_goal(f, cfg)
                if q is not None: set_goal(q, "auto")
                else: print("auto-detect found no goal in this view")
            if k == ord("z") and picking and pick_pts: pick_pts.pop()
            if k == ord("b"): pick_ball = True
            if k == ord("r"): bt = None
            if k == ord("w"): surface = "wall"; events and setattr(events, "surface", "wall")
            if k == ord("n"): surface = "net"; events and setattr(events, "surface", "net")
            if k == ord("s"):
                cfg["corners"] = goal.corners.round(1).tolist(); cfg["surface"] = surface
                json.dump({k2: v for k2, v in cfg.items() if k2 in ("goal_w_cm", "goal_h_cm", "panel_cols", "panel_rows", "kick_distance_m",
                                                                      "corners", "surface")},
                          open(a.config, "w"), indent=2)
                print("saved", a.config)
    if rec: stop_clip("quit")
    cap.release()
    if ann: ann.release()
    if track_f: track_f.close()
    if is_file and kick_events:
        imp = [e for e in kick_events if e["type"].startswith("IMPACT")]
        print("file run result:", (f"HIT {imp[-1]['goal_cm']} cell {imp[-1]['cell']}" if imp else "no impact"))
        with open(os.path.join(a.out, "file_events.json"), "w") as fh:
            json.dump(kick_events, fh, indent=1)
    print(f"processed {n_proc} frames, mean {np.mean(proc_ms):.1f} ms/frame")


if __name__ == "__main__":
    main()
