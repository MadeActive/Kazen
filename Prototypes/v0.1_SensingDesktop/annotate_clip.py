#!/usr/bin/env python3
"""
annotate_clip.py — re-run a recorded kick through the live tracker, work out the ball speed properly, and write a
small H.264 copy next to the raw clip with a frame counter and the speed in the top-right corner.

  python3 annotate_clip.py ../../../Photos/kick_20261105_171334.mp4 --config goal_1713.json [--surface net]
                           [--fps 15] [--focal-px 1150] [--crf 28] [--scale 1280]

How the speed is measured
  Each tracked flight frame gives a 3-D ball position: range from the ball's apparent radius (Ø 22 cm), direction from
  its image position, via the camera focal length (--focal-px, ~1150 px at 1920 wide for the MacBook camera).  A straight
  line is fitted through those positions against time.  Its slope is the speed.  Where that line passes the resting
  position is the kick time; where it reaches the goal plane (range of the posts from their pixel heights, interpolated at
  the impact column) is the goal-line crossing.  Both are sub-frame.  If fewer than 3 flight frames were tracked (very
  fast kick, blur) it falls back to the tracker's kick frame and net-contact frame, with half-frame corrections.

Frame rate
  Timing uses the clip's TRUE frame rate: the <stem>.times.csv sidecar the live tracker now writes, else the wall-clock
  stamps in <stem>.events.jsonl, else --fps.  (The Mac camera delivered ~15 fps at 1080p on 5 Nov although the files say 30.)
"""
import argparse, json, os, subprocess, sys, csv
import cv2
import numpy as np

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
from kick_cam import load_cfg  # noqa: E402
from live_tracker import true_fps_of  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("--config", required=True); ap.add_argument("--surface", default="net")
ap.add_argument("--fps", type=float, default=None, help="true frame rate (default: sidecar / events / container)")
ap.add_argument("--focal-px", type=float, default=None, help="focal length in px at the clip's width (default 1150 @ 1920)")
ap.add_argument("--crf", type=int, default=28); ap.add_argument("--scale", type=int, default=1280)
ap.add_argument("--out", default=None, help="output mp4 (default <video>_annotated.mp4)")
a = ap.parse_args()

cfg = load_cfg(a.config)
stem = os.path.splitext(os.path.basename(a.video))[0]
work = os.path.join(os.path.dirname(os.path.abspath(a.video)), "out", stem)
os.makedirs(work, exist_ok=True)

# ---- true frame rate
fps = a.fps or true_fps_of(a.video)
if not fps:
    fps = cv2.VideoCapture(a.video).get(cv2.CAP_PROP_FPS) or 30.0
    print(f"WARNING: no measured frame rate for {stem}; using container value {fps:.1f} fps — pass --fps if you know better")

# ---- 1. tracker pass (headless) → work/live_annotated.mp4, file_events.json, file_track.csv
cmd = [sys.executable, os.path.join(here, "live_tracker.py"), "--source", a.video, "--config", a.config, "--surface", a.surface,
       "--headless", "--out", work, "--fps-override", str(fps)]
subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
events = json.load(open(os.path.join(work, "file_events.json"))) if os.path.exists(os.path.join(work, "file_events.json")) else []
ready = next((e for e in events if e["type"] == "READY"), None)
kick = next((e for e in events if e["type"] == "KICK"), None)
imp = next((e for e in events if e["type"] == "IMPACT"), None)
track = list(csv.DictReader(open(os.path.join(work, "file_track.csv")))) if os.path.exists(os.path.join(work, "file_track.csv")) else []

cap = cv2.VideoCapture(os.path.join(work, "live_annotated.mp4"))
W, H = int(cap.get(3)), int(cap.get(4))
f_px = a.focal_px or 1150.0 * W / 1920.0
cx, cy = W / 2, H / 2
R = cfg["ball_diameter_cm"] / 2

def p3(u, v, r):
    z = f_px * R / r
    return np.array([(u - cx) * z / f_px, (v - cy) * z / f_px, z])

# ---- 2. physics: trajectory fit  P(τ) = P_rest + V τ + ½ g τ² ŷ   (camera frame, cm, τ seconds after the kick)
G = 981.0            # cm/s², along camera +Y (image down); camera pitch ignored (small)
DIL = 3.0            # px the tracker's mask dilation adds to every in-flight radius
SIG_UV, SIG_R = 2.0, 3.0

def predict(theta, frames):
    Vx, Vy, Vz, tk = theta
    tau = (frames - tk) / fps
    X = p_rest[0] + Vx * tau; Y = p_rest[1] + Vy * tau + 0.5 * G * tau ** 2; Z = p_rest[2] + Vz * tau
    Z = np.maximum(Z, 30.0)
    return cx + f_px * X / Z, cy + f_px * Y / Z, f_px * R / Z + DIL, np.stack([X, Y, Z], 1)

def residuals(theta, frames, u, v, r):
    pu, pv, pr, _ = predict(theta, frames)
    return np.concatenate([(pu - u) / SIG_UV, (pv - v) / SIG_UV, (pr - r) / SIG_R])

def fit_traj(theta0, frames, u, v, r):
    theta = np.array(theta0, float); lam = 1e-2
    cost = float(np.sum(residuals(theta, frames, u, v, r) ** 2))
    for _ in range(60):
        res = residuals(theta, frames, u, v, r)
        J = np.zeros((len(res), 4))
        for k in range(4):
            d = np.zeros(4); d[k] = 1e-3 * max(1.0, abs(theta[k]))
            J[:, k] = (residuals(theta + d, frames, u, v, r) - res) / d[k]
        A = J.T @ J + lam * np.diag(np.diag(J.T @ J) + 1e-9); g = J.T @ res
        step = np.linalg.solve(A, -g)
        new = theta + step; new_cost = float(np.sum(residuals(new, frames, u, v, r) ** 2))
        if new_cost < cost:
            theta, cost, lam = new, new_cost, lam * 0.3
            if np.linalg.norm(step) < 1e-6: break
        else:
            lam *= 10
            if lam > 1e6: break
    return theta, cost

result = None
if kick and ready:
    c = np.array(cfg["corners"], float)
    h_l, h_r = np.linalg.norm(c[3] - c[0]), np.linalg.norm(c[2] - c[1])
    z_l, z_r = f_px * cfg["goal_h_cm"] / h_l, f_px * cfg["goal_h_cm"] / h_r              # range of each post, cm
    mid_l, mid_r = (c[0] + c[3]) / 2, (c[1] + c[2]) / 2
    post_l = np.array([(mid_l[0] - cx) * z_l / f_px, z_l]); post_r = np.array([(mid_r[0] - cx) * z_r / f_px, z_r])   # XZ
    r0 = kick["rest_r"] if "rest_r" in kick else ready["r"]
    p_rest = p3(kick["anchor"][0], kick["anchor"][1], r0)

    def side(xz):                      # which side of the goal line (XZ plane) a point is on
        d = post_r - post_l; return (xz[0] - post_l[0]) * d[1] - (xz[1] - post_l[1]) * d[0]

    rows = [row for row in track if row["state"] == "flight" and row["det"] == "1" and int(row["frame"]) >= kick["frame"]]
    # first run of frames whose range keeps increasing and that are in front of the goal line
    samples, z_prev, prev_uv, prev_step, contact_f = [], None, None, None, None
    for row in rows:
        fr, u, v, r = int(row["frame"]), float(row["x"]), float(row["y"]), float(row["r"])
        P = p3(u, v, max(r - DIL, 4))
        if side(np.array([P[0], P[2]])) * side(np.array([p_rest[0], p_rest[2]])) < 0 and P[2] > min(z_l, z_r) - 60:
            break                                                     # past the goal line
        if z_prev is not None and P[2] < z_prev - 40:
            break                                                     # coming back: bounced / in the net
        if prev_uv is not None:
            step = float(np.hypot(u - prev_uv[0], v - prev_uv[1]))
            if prev_step is not None and prev_step > 15 and step < 0.4 * prev_step:
                contact_f = fr - 0.5                                  # sudden stop: it hit something (net, target pocket)
                break
            prev_step = step
        prev_uv = (u, v)
        samples.append((fr, u, v, r)); z_prev = P[2]
    if len(samples) >= 3:
        F = np.array([s_[0] for s_ in samples], float); U = np.array([s_[1] for s_ in samples]); Vv = np.array([s_[2] for s_ in samples]); Rr = np.array([s_[3] for s_ in samples])
        # initial guess from the radius-only linear fit
        Zs = f_px * R / np.maximum(Rr - DIL, 4); Ps = np.stack([(U - cx) * Zs / f_px, (Vv - cy) * Zs / f_px, Zs], 1)
        A = np.vstack([F, np.ones_like(F)]).T; coef, *_ = np.linalg.lstsq(A, Ps, rcond=None)
        V0 = coef[0] * fps; tk0 = float(np.dot(p_rest - coef[1], coef[0]) / np.dot(coef[0], coef[0]))
        theta, cost = fit_traj([V0[0], V0[1], V0[2], tk0], F, U, Vv, Rr)
        # drop anything the fit says is already past the line, refit once
        _, _, _, Pp = predict(theta, F)
        keep = np.array([side(np.array([p[0], p[2]])) * side(np.array([p_rest[0], p_rest[2]])) > 0 for p in Pp])
        if keep.sum() >= 3 and keep.sum() < len(F):
            F, U, Vv, Rr = F[keep], U[keep], Vv[keep], Rr[keep]
            theta, cost = fit_traj(theta, F, U, Vv, Rr)
        Vx, Vy, Vz, tk = theta
        # crossing: first τ where the XZ track crosses the post-to-post line
        taus = np.linspace(0, 3.0, 3001); _, _, _, Pt = predict(theta, tk + taus * fps)
        s0 = side(np.array([p_rest[0], p_rest[2]])); sides = np.array([side(np.array([p[0], p[2]])) for p in Pt])
        idx = np.nonzero(sides * s0 < 0)[0]
        if len(idx):
            k = idx[0]; tau_c = taus[k] if k == 0 else taus[k - 1] + (taus[k] - taus[k - 1]) * abs(sides[k - 1]) / (abs(sides[k - 1]) + abs(sides[k]))
            if contact_f is not None and (contact_f - tk) / fps < tau_c:
                tau_c = max(0.05, (contact_f - tk) / fps)                 # it stopped before reaching the line plane
            _, _, _, Pc = predict(theta, np.array([tk + tau_c * fps]))
            dist_m = float(np.linalg.norm(Pc[0] - p_rest)) / 100
            rms = float(np.sqrt(cost / (3 * len(F))))
            if rms < 3.0:                                   # a trajectory that doesn't explain the track is not reported
                result = dict(method="trajectory fit", n=int(len(F)), kick_f=float(tk), cross_f=float(tk + tau_c * fps), flight_s=float(tau_c),
                              dist_m=dist_m, v_ms=dist_m / tau_c, v0_ms=float(np.linalg.norm([Vx, Vy, Vz])) / 100, resid_cm=rms)
            else:
                print(f"{stem}: trajectory fit rejected (rms {rms:.1f}σ over {len(F)} pts)")
    if result is None and imp and imp.get("flight_s"):
        gx_imp = float(np.clip(imp["goal_cm"][0], 0, cfg["goal_w_cm"]))
        z_goal = z_l + (z_r - z_l) * gx_imp / cfg["goal_w_cm"]
        net_depth = cfg.get("net_depth_cm", 60) / 100
        t_kick = kick["frame"] - 0.5
        t_net = imp["frame"] - 0.5
        # if the tracked ball was seen past the goal line well before the net registered, the net reading is late:
        # use the first frame past the line instead
        past = [int(row["frame"]) for row in rows if side(np.array([p3(float(row["x"]), float(row["y"]), max(float(row["r"]) - DIL, 4))[0],
                                                                         p3(float(row["x"]), float(row["y"]), max(float(row["r"]) - DIL, 4))[2]])) * side(np.array([p_rest[0], p_rest[2]])) < 0]
        if past and imp["frame"] - past[0] > 3:
            t_net = past[0] - 0.5                               # crossed between the previous frame and this one
            net_depth = 0.0
        dist_line = float(np.linalg.norm(np.array([(imp["px"][0] - cx) * z_goal / f_px, (imp["px"][1] - cy) * z_goal / f_px, z_goal]) - p_rest)) / 100
        v_ms = (dist_line + net_depth) / max(1e-3, (t_net - t_kick) / fps)
        t_cross = t_net - (net_depth / v_ms) * fps
        result = dict(method="kick/net frames" if net_depth > 0 else "kick/first-past-line frames", n=0, kick_f=t_kick, cross_f=t_cross,
                      flight_s=(t_cross - t_kick) / fps, dist_m=dist_line, v_ms=v_ms, v0_ms=None, resid_cm=None)
    if result and (kick["frame"] <= 4 or result["flight_s"] < 0.08):
        print(f"{stem}: kick at frame {kick['frame']} — the kick happened before or as recording started; no speed")
        result = None

if result:
    rr = "-" if result["resid_cm"] is None else f"{result['resid_cm']:.1f}σ"
    print(f"{stem}: {result['method']} ({result['n']} pts, rms {rr})  kick f{result['kick_f']:.1f} → line f{result['cross_f']:.1f}  "
          f"flight {result['flight_s']:.2f} s  {result['dist_m']:.1f} m  avg {result['v_ms']*3.6:.0f} km/h"
          + (f"  (launch {result['v0_ms']*3.6:.0f} km/h)" if result.get("v0_ms") else "") + f"   @ {fps:.1f} fps")
else:
    print(f"{stem}: no speed (events: {[e['type'] for e in events]})")

# ---- 3. overlay pass → temporary mp4 (frame counter is already drawn by the tracker)
tmp = os.path.join(work, "overlay_tmp.mp4")
wr = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
i = 0
show_from = int(round(result["cross_f"])) if result else None
kick_i = (kick["frame"] - 1) if kick else None
s = W / 1100.0
while True:
    ok, fr = cap.read()
    if not ok: break
    frame_no = i + 1
    if result and frame_no >= show_from:
        l1 = f"~{result['v_ms']*3.6:.0f} km/h"
        l2 = f"{result['dist_m']:.1f} m in {result['flight_s']:.2f} s"
        l3 = f"kick f{result['kick_f']:.1f}  line f{result['cross_f']:.1f}  @ {fps:.0f} fps"
        (tw, th), _ = cv2.getTextSize(l1, cv2.FONT_HERSHEY_DUPLEX, s * 1.6, 3)
        (dw, dh), _ = cv2.getTextSize(l3, cv2.FONT_HERSHEY_DUPLEX, s * 0.6, 2)
        bw = max(tw, dw) + 40; bh = th + 2 * dh + 70
        x0, y0 = W - bw - 20, 20
        ov = fr.copy(); cv2.rectangle(ov, (x0, y0), (x0 + bw, y0 + bh), (0, 0, 0), -1)
        fr = cv2.addWeighted(ov, 0.55, fr, 0.45, 0)
        cv2.putText(fr, l1, (x0 + 20, y0 + th + 15), cv2.FONT_HERSHEY_DUPLEX, s * 1.6, (0, 200, 255), 3, cv2.LINE_AA)
        cv2.putText(fr, l2, (x0 + 20, y0 + th + dh + 35), cv2.FONT_HERSHEY_DUPLEX, s * 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(fr, l3, (x0 + 20, y0 + th + 2 * dh + 55), cv2.FONT_HERSHEY_DUPLEX, s * 0.6, (200, 200, 200), 2, cv2.LINE_AA)
    elif kick_i is not None and i >= kick_i:
        cv2.putText(fr, f"flight {(i - kick_i) / fps:.2f} s", (W - 300, 50), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    wr.write(fr); i += 1
cap.release(); wr.release()

# ---- 4. compress (H.264, CRF, downscale) at the true frame rate
out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.video)), stem + "_annotated.mp4")
vf = f"scale={a.scale}:-2" if a.scale and a.scale < W else "null"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-vf", vf, "-r", f"{fps:.3f}", "-c:v", "libx264", "-preset", "slow",
                "-crf", str(a.crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", out], check=True)
try: os.remove(tmp)
except OSError: pass
print(f"wrote {out}  ({os.path.getsize(out)/1e6:.1f} MB, {fps:.1f} fps)")
