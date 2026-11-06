#!/usr/bin/env python3
"""
kick_cam.py — Kazen camera-sensing prototype (single camera behind the kicker).

From a video of one or more kicks it detects, per kick:
  REST      ball stationary at the kick spot
  APPROACH  foot/leg moving in close to the ball ("moment before kick")
  KICK      ball leaves the spot
  IMPACT    ball meets the net/goal plane, and WHERE on the goal face (cm + panel cell)

Goal corners are found automatically every frame by fitting straight lines to the
white posts / crossbar / ground bar inside a band around an initial guess, so a
slowly drifting (handheld) camera is fine.  Everything else is classical OpenCV:
MOG2 background subtraction ∧ "white" colour mask → blob → gated track.

Usage
  python3 kick_cam.py VIDEO --config goal.json [--start N] [--end N] [--step K]
                       [--render] [--out DIR] [--tag NAME]

  --step K   analyse every K-th frame (frame-rate sensitivity: K=2,4,8 from 240 fps
             gives 120/60/30 fps).  Timing is reported in captured-frame units and
             seconds (capture_fps / K).

Outputs (in --out, default <video dir>/out):
  <name>_events.json       all events, per-kick, with pixel + goal-cm positions
  <name>_track.csv         per-frame ball track (frame, x, y, r, speed, goal x/y)
  <name>_goalface.png      240x172 goal face with the panel grid and impact marks
  <name>_frames/           key frames (rest / approach / kick / impact) annotated
  <name>_annotated.mp4     (with --render) annotated clip of the analysed range
"""
import argparse, json, math, os, sys, csv
import cv2
import numpy as np

# ----------------------------------------------------------------------------- config
DEFAULT_CFG = {
    "goal_w_cm": 240.0, "goal_h_cm": 172.0,
    "panel_cols": 36, "panel_rows": 13,          # WS2815 @ 15 LED/m → 6.67 cm; 13 rows → 13.2 cm
    "capture_fps": 240.0,                          # real sample rate of the analysed frames
    "kick_distance_m": None,                       # kick spot → goal line, for ball speed
    "ball_diameter_cm": 22.0,
    "rest_ball_px": None,                          # [x, y, r] fallback if the ball is shaded/occluded in the first frame
    # inner goal corners (px): TL, TR, BR, BL — set per camera position (pick_corners.py / live_tracker g key)
    "corners": None,
    "band_px": 10,                                 # half-width of the tracking band around each bar
    # colour thresholds (HSV, OpenCV ranges H 0-179, S/V 0-255)
    "white_s_max": 75, "white_v_min": 160,
    # tracking
    "ball_area_px": [120, 60000],                  # upper bound: a ball 1.5 m from a 1080p camera is ~12-15k px²
    "rest_speed_px": 1.2, "kick_speed_px": 4.0,
}


def load_cfg(path):
    cfg = dict(DEFAULT_CFG)
    if path:
        with open(path) as f:
            cfg.update(json.load(f))
    if cfg.get("ball_area_px") and cfg["ball_area_px"][1] < 60000:      # old configs saved a cap tuned for the phone
        cfg["ball_area_px"] = [cfg["ball_area_px"][0], 60000]
    return cfg


# ----------------------------------------------------------------------------- goal frame tracker
def _intersect(l1, l2):
    """l = (vx, vy, x0, y0) from cv2.fitLine → intersection point."""
    (a1, b1, x1, y1), (a2, b2, x2, y2) = l1, l2
    A = np.array([[a1, -a2], [b1, -b2]], float)
    if abs(np.linalg.det(A)) < 1e-9:
        return None
    t = np.linalg.solve(A, np.array([x2 - x1, y2 - y1], float))[0]
    return (x1 + a1 * t, y1 + b1 * t)


class GoalTracker:
    """Fits the 4 white bars of the goal each frame; returns corners + homography."""
    ORDER = [("top", 0, 1), ("right", 1, 2), ("bottom", 2, 3), ("left", 3, 0)]

    def __init__(self, cfg):
        self.cfg = cfg
        self.corners = np.array(cfg["corners"], float)      # TL TR BR BL
        self.band = cfg["band_px"]
        W, H = cfg["goal_w_cm"], cfg["goal_h_cm"]
        # goal coords: x right from left post (0..W), y UP from ground (0..H)
        self.dst = np.array([[0, H], [W, H], [W, 0], [0, 0]], np.float32)
        self.H = None
        self.ok = False
        self.alpha = 0.5                                     # EMA on corners

    def white_mask(self, bgr):
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        m = cv2.inRange(hsv, (0, 0, self.cfg["white_v_min"]), (179, self.cfg["white_s_max"], 255))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))   # kills net strands
        return m

    def _inner_edge_points(self, m, x0, y0, p, q):
        """Rectify the band around bar p→q into a strip (rows = across the bar, outer→inner),
        and return, per column, the innermost white pixel of the bar.  Corners are ordered
        clockwise in image coords, so the inward normal is n = (-uy, ux)."""
        d = q - p; L = float(np.linalg.norm(d)); u = d / L; n = np.array([-u[1], u[0]])
        s = np.arange(0.08 * L, 0.92 * L, 2.0)                       # along-bar samples
        t = np.arange(-self.band, self.band + 1, 1.0)                 # across-bar, outer → inner
        S, T = np.meshgrid(s, t)                                      # (rows=t, cols=s)
        X = (p[0] + u[0] * S + n[0] * T - x0).astype(np.float32)
        Y = (p[1] + u[1] * S + n[1] * T - y0).astype(np.float32)
        strip = cv2.remap(m, X, Y, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0) > 0
        # per column: the inner end of every white run >= 3 px (bar is ~8-12 px thick).
        # There can be several (crossbar + a second rail, net rope...), so return all candidates
        # and let the fit pick the consistent one.
        run = strip.astype(np.uint8)
        ends = (run[:-1] == 1) & (run[1:] == 0)                       # row j white, j+1 not → run ends at j
        run3 = np.zeros_like(run, bool); run3[2:] = (run[2:] & run[1:-1] & run[:-2]) > 0
        cols, cands = [], []
        for c in range(strip.shape[1]):
            js = [j for j in np.nonzero(ends[:, c])[0] if run3[j, c]]
            if run[-1, c] and run3[-1, c]:
                js.append(len(t) - 1)
            for j in js:
                cols.append(c); cands.append(p + u * s[c] + n * t[j])
        return np.array(cols, int), np.array(cands, np.float32), len(s)

    @staticmethod
    def _fit_bar(cols, cands, p, q, tols=(6, 3, 2.5, 2.5)):
        """Fit a line to one edge candidate per column, seeded by the prior line p→q and
        re-picking the candidate nearest the current line with a shrinking tolerance.
        Seeding from the prior (rather than 'innermost') keeps the fit on the crossbar when a
        rear rail / rope shows just inside it."""
        if len(cands) == 0:
            return None, 0
        d = q - p; L = float(np.linalg.norm(d)); vx, vy = d / L; cx, cy = p
        sel = cands
        for tol in tols:
            resid = np.abs((cands[:, 0] - cx) * vy - (cands[:, 1] - cy) * vx)
            best = {}
            for k in range(len(cands)):
                c = cols[k]
                if resid[k] < tol and (c not in best or resid[k] < resid[best[c]]):
                    best[c] = k
            sel = cands[list(best.values())]
            if len(sel) < 10:
                return None, len(sel)
            vx, vy, cx, cy = cv2.fitLine(sel, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
        return (vx, vy, cx, cy), len(sel)

    def update(self, bgr):
        x0 = int(max(0, self.corners[:, 0].min() - 60)); x1 = int(min(bgr.shape[1], self.corners[:, 0].max() + 60))
        y0 = int(max(0, self.corners[:, 1].min() - 60)); y1 = int(min(bgr.shape[0], self.corners[:, 1].max() + 60))
        roi = bgr[y0:y1, x0:x1]
        m = self.white_mask(roi)
        lines, good, self.counts = {}, True, {}
        for name, i, j in self.ORDER:
            cols, cands, ncol = self._inner_edge_points(m, x0, y0, self.corners[i], self.corners[j])
            line, used = self._fit_bar(cols, cands, self.corners[i], self.corners[j])
            self.counts[name] = (used, ncol)
            if line is None or used < max(15, 0.25 * ncol):
                good = False; break
            lines[name] = line
        moved = 0.0
        if good:
            new = [_intersect(lines["left"], lines["top"]), _intersect(lines["top"], lines["right"]),
                   _intersect(lines["right"], lines["bottom"]), _intersect(lines["bottom"], lines["left"])]
            if all(c is not None for c in new):
                new = np.array(new, float)
                moved = float(np.linalg.norm(new - self.corners, axis=1).max())
                if moved < 3 * self.band:                                    # sanity: no jumps
                    self.corners = self.alpha * new + (1 - self.alpha) * self.corners
                    self.ok = True
        self.H = cv2.getPerspectiveTransform(self.corners.astype(np.float32), self.dst)
        return self.corners, self.H

    def initialise(self, bgr, iters=8):
        """Settle the configured corner guesses onto the bars' inner edges.  The guesses need
        to be within ~5 px (use pick_corners.py); a blind wide search is not reliable because
        walls, rear rails and ropes present several parallel white edges near the crossbar."""
        start = self.corners.copy()
        for k in range(iters):
            before = self.corners.copy()
            self.update(bgr)
            if self.ok and np.linalg.norm(self.corners - before, axis=1).max() < 0.2:
                break
        self.init_shift = np.linalg.norm(self.corners - start, axis=1).round(1).tolist()
        return self.ok

    def to_goal(self, pt):
        p = cv2.perspectiveTransform(np.array([[pt]], np.float32), self.H)[0, 0]
        return float(p[0]), float(p[1])

    def inside(self, pt, margin_cm=15):
        gx, gy = self.to_goal(pt)
        return (-margin_cm <= gx <= self.cfg["goal_w_cm"] + margin_cm) and (-margin_cm <= gy <= self.cfg["goal_h_cm"] + margin_cm)


# ----------------------------------------------------------------------------- goal auto-detection
def auto_goal(bgr, cfg):
    """Find a white goal frame automatically from its bars: two tall thin white posts (same height,
    tops level), a crossbar between their tops and, if visible, a ground bar between their feet.
    Returns inner corners TL,TR,BR,BL or None.  Robust to the frame touching a white wall and to
    hanging target nets, because only long thin vertical / horizontal structures are considered."""
    H, W = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    white = cv2.inRange(hsv, (0, 0, cfg["white_v_min"]), (179, cfg["white_s_max"], 255))
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    L = max(31, int(0.04 * H))
    vert = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((L, 1), np.uint8))       # keeps only tall structures
    horz = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((1, L), np.uint8))       # keeps only wide structures
    vert = cv2.morphologyEx(vert, cv2.MORPH_CLOSE, np.ones((15, 3), np.uint8))      # bridge grass over the post foot
    n, lab, st, cen = cv2.connectedComponentsWithStats(vert)
    posts = []
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if h < 0.10 * H or w > 0.04 * W or h < 4 * w or area < 0.35 * w * h:
            continue
        ys, xs = np.nonzero(lab == i)
        vx, vy, cx, cy = cv2.fitLine(np.stack([xs, ys], 1).astype(np.float32), cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
        if abs(vx) > 0.35:                                   # more than ~20° off vertical: not a post
            continue
        t = area / max(h, 1)                                 # mean thickness
        posts.append(dict(x=x, y=y, w=w, h=h, t=t, line=(vx, vy, cx, cy), top=y, bot=y + h))
    def x_at(p, y):
        vx, vy, cx, cy = p["line"]
        return cx + vx * (y - cy) / (vy if abs(vy) > 1e-6 else 1e-6)

    def bar_rows(y_from, y_to, xa, xb, min_frac=0.45):
        """Rows in [y_from, y_to) whose horizontal-structure fill between xa..xb exceeds min_frac;
        returned as runs [(y0, y1), ...]."""
        y_from, y_to = max(0, int(y_from)), min(H, int(y_to))
        if y_to <= y_from or xb - xa < 10:
            return []
        frac = horz[y_from:y_to, int(xa):int(xb)].mean(axis=1) / 255.0
        runs, start = [], None
        for k, v in enumerate(frac):
            if v > min_frac and start is None:
                start = k
            if (v <= min_frac or k == len(frac) - 1) and start is not None:
                end = k if v <= min_frac else k + 1
                if end - start >= 3:
                    runs.append((y_from + start, y_from + end))
                start = None
        return runs

    best, best_score = None, 0
    ratio = cfg["goal_w_cm"] / cfg["goal_h_cm"]
    for i in range(len(posts)):
        for j in range(len(posts)):
            a, b = posts[i], posts[j]
            if a["x"] >= b["x"]:
                continue
            span = (b["x"] + b["w"] / 2) - (a["x"] + a["w"] / 2)
            hmean = 0.5 * (a["h"] + b["h"])
            if span < 0.08 * W or abs(a["h"] - b["h"]) > 0.55 * hmean:     # a target net can hide half a post
                continue
            # the two posts must overlap vertically for most of the shorter one
            ov = min(a["bot"], b["bot"]) - max(a["top"], b["top"])
            if ov < 0.6 * min(a["h"], b["h"]):
                continue
            t = 0.5 * (a["t"] + b["t"])
            xa, xb = x_at(a, a["top"]) + t, x_at(b, b["top"]) - t
            # crossbar: lowest horizontal run just above the post tops (targets may have cut the tops off)
            top = min(a["top"], b["top"])
            runs = bar_rows(top - 0.45 * hmean, max(a["top"], b["top"]) + 2 * t, xa, xb, min_frac=0.3)
            if not runs:
                continue
            cross = runs[-1]                                 # lowest run = the crossbar (wall boards sit higher)
            if cross[1] - cross[0] > 4 * t + 6:              # a thick white band, not a bar
                continue
            full_h = max(a["bot"], b["bot"]) - cross[1]
            asp = span / max(full_h, 1)
            if not (0.6 * ratio < asp < 2.3 * ratio):
                continue
            score = span * full_h
            if score > best_score:
                best, best_score = (a, b, cross, t), score
    if best is None:
        return None
    a, b, cross, t = best

    def edge_line(y0, y1, xa, xb, which):
        """Per column, the top-most ('top') or bottom-most ('bottom') horizontal-structure pixel in rows
        [y0, y1); robust line fit with residual rejection.  Returns y(x) or None."""
        y0, y1 = max(0, int(y0)), min(H, int(y1)); xa, xb = max(0, int(xa)), min(W, int(xb))
        band = horz[y0:y1, xa:xb] > 0
        if band.size == 0:
            return None
        has = band.any(axis=0)
        idx = band.argmax(axis=0) if which == "top" else (band.shape[0] - 1 - band[::-1].argmax(axis=0))
        xs = np.nonzero(has)[0]
        if len(xs) < 0.3 * (xb - xa) or len(xs) < 20:
            return None
        pts = np.stack([xs + xa, idx[xs] + y0], 1).astype(np.float32)
        vx, vy, cx, cy = cv2.fitLine(pts, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
        for _ in range(2):
            resid = np.abs((pts[:, 0] - cx) * vy - (pts[:, 1] - cy) * vx)
            keep = pts[resid < 4]
            if len(keep) < 20:
                break
            vx, vy, cx, cy = cv2.fitLine(keep, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
        return lambda x: float(cy + vy * (x - cx) / (vx if abs(vx) > 1e-6 else 1e-6))

    # bars slope in the image: fit their inner edges and evaluate at each post
    xa, xb = x_at(a, cross[1]) + 2 * t, x_at(b, cross[1]) - 2 * t
    cl = edge_line(cross[0], cross[1] + 2, xa, xb, "bottom")                 # crossbar underside
    ytl = cl(x_at(a, cross[1])) if cl else float(cross[1])
    ytr = cl(x_at(b, cross[1])) if cl else float(cross[1])
    bot = max(a["bot"], b["bot"])
    runs = bar_rows(bot - 0.3 * max(a["h"], b["h"]), bot + 0.1 * max(a["h"], b["h"]), x_at(a, bot) + t, x_at(b, bot) - t, min_frac=0.2)
    gl = None
    if runs:
        r0 = max(runs, key=lambda r: r[1] - r[0])            # the thickest run: a sloping bar spreads over many rows
        gl = edge_line(r0[0] - 2, r0[1] + 2, x_at(a, bot) + 2 * t, x_at(b, bot) - 2 * t, "top")   # ground bar top
    if gl:
        ybl, ybr = gl(x_at(a, bot)), gl(x_at(b, bot))
    elif runs:
        ybl = ybr = float(runs[0][0])
    else:
        ybl, ybr = float(a["bot"]), float(b["bot"])
    tl = (x_at(a, ytl) + t / 2, ytl); tr = (x_at(b, ytr) - t / 2, ytr)
    br = (x_at(b, ybr) - t / 2, ybr); bl = (x_at(a, ybl) + t / 2, ybl)
    return np.array([tl, tr, br, bl], float)


# ----------------------------------------------------------------------------- ball detection
def find_resting_ball(bgr, goal: GoalTracker, cfg):
    """White, roundish blob sitting on grass, outside the goal, in the lower part of frame."""
    H, W = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    white = cv2.inRange(hsv, (0, 0, cfg["white_v_min"]), (179, cfg["white_s_max"], 255))
    green = cv2.inRange(hsv, (18, 40, 40), (95, 255, 255))     # includes the yellow-green of sunlit / dry grass
    white[: int(0.55 * H)] = 0
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))     # drop bright grass specks first
    white = cv2.morphologyEx(white, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))  # then bridge the ball's black panels
    cnts, _ = cv2.findContours(white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, best_score = None, 0
    for c in cnts:
        a = cv2.contourArea(c)
        if not (cfg["ball_area_px"][0] < a < cfg["ball_area_px"][1]):
            continue
        (x, y), r = cv2.minEnclosingCircle(c)
        if r < 10 or goal.inside((x, y), margin_cm=40):
            continue
        fill = a / (math.pi * r * r + 1e-6)
        ring = np.zeros(white.shape, np.uint8)
        cv2.circle(ring, (int(x), int(y)), int(r * 1.8), 255, -1)
        cv2.circle(ring, (int(x), int(y)), int(r * 1.15), 0, -1)
        g = cv2.countNonZero(cv2.bitwise_and(green, ring)) / (cv2.countNonZero(ring) + 1)
        score = fill * g * r                       # the ball at the kick spot is the biggest white round thing on the grass
        if fill > 0.35 and g > 0.4 and score > best_score:
            best, best_score = (x, y, r), score
    if best is None:
        return None
    # refine: erode the blob to detach bright-grass bridges, keep the core nearest the centre, re-measure
    x, y, r = best
    x0, y0 = int(max(0, x - r - 4)), int(max(0, y - r - 4))
    patch = white[y0:int(y + r + 4), x0:int(x + r + 4)]
    core = cv2.erode(patch, np.ones((9, 9), np.uint8))
    n, lab, stats_, cents = cv2.connectedComponentsWithStats(core)
    if n > 1:
        d = [np.hypot(cents[i][0] + x0 - x, cents[i][1] + y0 - y) if stats_[i, cv2.CC_STAT_AREA] > 30 else 1e9 for i in range(1, n)]
        k = int(np.argmin(d)) + 1
        if d[k - 1] < 1e9:
            comp = (lab == k).astype(np.uint8)
            comp = cv2.dilate(comp, np.ones((9, 9), np.uint8))          # undo the erosion on the kept core
            cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if cnts:
                (cx, cy), cr = cv2.minEnclosingCircle(max(cnts, key=cv2.contourArea))
                if 0.4 * r < cr <= r + 2:
                    x, y, r = cx + x0, cy + y0, cr
    return (x, y, r)


class BallTracker:
    """Three states.
    REST   : the ball sits at an anchor.  Shadow edges and feet make the background model fire on
             and around it, so only ball-sized blobs within ~1 r of the anchor are even considered,
             and they do not move the anchor.  Two consecutive frames > 0.5 r away → FLIGHT.
    FLIGHT : gated nearest-neighbour tracking with constant-velocity prediction; coast ≤ 20 frames.
    LOST   : wait for a resting ball to be put back anywhere outside the goal (reacquire())."""
    REST, FLIGHT, LOST = "rest", "flight", "lost"

    def __init__(self, cfg, init, step=1):
        self.cfg = cfg; self.stride = step
        self.bg = cv2.createBackgroundSubtractorMOG2(history=250, varThreshold=20, detectShadows=True)   # shadows → 127
        self.k = np.ones((7, 7), np.uint8)
        self.r0 = float(init[2]); self.pending = None; self.pending_n = 0
        self.goal_dir = None                                 # set_goal() gives the departure direction test
        self._anchor(init)

    def set_goal(self, corners):
        """Unit vector from the current anchor toward the goal centre (image space)."""
        c = np.mean(np.asarray(corners, float), axis=0) - self.anchor
        self.goal_dir = c / (np.linalg.norm(c) + 1e-6)

    def _anchor(self, init):
        self.pos = np.array(init[:2], float); self.r = float(init[2]); self.vel = np.zeros(2)
        self.state = self.REST; self.missing = 0; self.away = 0; self.away_pos = self.pos.copy(); self.kick_lag = 0
        if hasattr(self, "rest_frac"): del self.rest_frac
        self.anchor = self.pos.copy(); self.anchor_r = self.r

    @property
    def lost(self):
        return self.state == self.LOST

    def reacquire(self, bgr, goal, cfg):
        """While lost, look for a ball at rest anywhere outside the goal (ball put back on the spot).
        Accept only a ball-sized blob that stays put across three consecutive checks."""
        rb = find_resting_ball(bgr, goal, cfg)
        if rb is None or not (0.6 * self.r0 < rb[2] < 1.5 * self.r0):
            self.pending = None; return False
        if self.pending is not None and np.hypot(rb[0] - self.pending[0], rb[1] - self.pending[1]) < 10:
            self.pending_n += 1
        else:
            self.pending, self.pending_n = rb, 1
        if self.pending_n >= 3:
            self._anchor(rb); self.pending = None
            return True
        return False

    def _candidates(self, m, centre, gate, r_ref, r_lo=0.5, r_hi=1.6, white=None, min_white=0.25):
        x0, y0 = int(max(0, centre[0] - gate)), int(max(0, centre[1] - gate))
        x1, y1 = int(min(m.shape[1], centre[0] + gate)), int(min(m.shape[0], centre[1] + gate))
        sub = m[y0:y1, x0:x1]
        out = []
        if not sub.size:
            return out
        cnts, _ = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            a = cv2.contourArea(c)
            if not (self.cfg["ball_area_px"][0] < a < self.cfg["ball_area_px"][1]):
                continue
            (x, y), r = cv2.minEnclosingCircle(c)
            x += x0; y += y0
            bx, by, bw, bh = cv2.boundingRect(c)
            if not (0.25 < bw / max(bh, 1) < 4.0):               # motion blur turns the ball into a streak at 30 fps
                continue
            if not (r_lo * r_ref < r < r_hi * r_ref):            # legs, hair, whole-ball shadows
                continue
            d = np.hypot(x - centre[0], y - centre[1])
            if d > gate:
                continue
            if white is not None:                                 # a ball is mostly white inside its circle
                disc = np.zeros((2 * int(r) + 3, 2 * int(r) + 3), np.uint8)
                cv2.circle(disc, (int(r) + 1, int(r) + 1), int(r), 255, -1)
                yy0, xx0 = int(y) - int(r) - 1, int(x) - int(r) - 1
                patch = white[max(0, yy0):yy0 + disc.shape[0], max(0, xx0):xx0 + disc.shape[1]]
                dd = disc[:patch.shape[0], :patch.shape[1]]
                frac = cv2.countNonZero(cv2.bitwise_and(patch, dd)) / max(1, cv2.countNonZero(dd))
                if frac < min_white:
                    continue
            out.append((d + 0.6 * abs(r - r_ref), x, y, r, d))
        return sorted(out)

    def step(self, bgr):
        fg = self.bg.apply(bgr)
        fg = cv2.compare(fg, 200, cv2.CMP_GT)           # solid foreground only; the kicker's shadow is dropped
        self.fg = fg
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        white = cv2.inRange(hsv, (0, 0, self.cfg["white_v_min"]), (179, self.cfg["white_s_max"], 255))
        m = cv2.bitwise_and(fg, white)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        m = cv2.dilate(m, self.k)                       # merge the ball's white patches across its black ones

        if self.state == self.LOST:
            return (*self.pos, self.r, False)

        if self.state == self.REST:
            # is there still a white ball at the anchor?  A sudden disappearance right after foot activity
            # is a kick too fast to track frame to frame (30 fps); a long absence means it was picked up.
            ar = int(self.anchor_r); ax, ay = int(self.anchor[0]), int(self.anchor[1])
            patch = white[max(0, ay - ar):ay + ar, max(0, ax - ar):ax + ar]
            frac = cv2.countNonZero(patch) / max(1, patch.size)
            if not hasattr(self, "rest_frac"):
                self.rest_frac, self.gone = frac, 0
            self.rest_frac = 0.9 * self.rest_frac + 0.1 * frac if frac > 0.12 else self.rest_frac
            self.gone = self.gone + 1 if frac < 0.35 * self.rest_frac else 0
            if self.gone >= 1 and self.goal_dir is not None:
                # the spot just emptied: look for a ball-sized moving white blob anywhere goalward of the spot.
                # Finding one is a confirmed departure — no need to wait three frames.
                allc = self._candidates(m, (m.shape[1] / 2, m.shape[0] / 2), 1e6, self.anchor_r, 0.3, 1.2, white=white)
                best = None
                for c in allc:
                    d = np.array([c[1], c[2]]) - self.anchor
                    along = np.dot(d, self.goal_dir); off = abs(d[0] * self.goal_dir[1] - d[1] * self.goal_dir[0])
                    if along > 1.5 * self.anchor_r and off < 0.6 * along + 2 * self.anchor_r:
                        score = off - 0.3 * along
                        if best is None or score < best[0]:
                            best = (score, c)
                if best is not None:
                    _, (_, x, y, r, d) = best
                    self.state = self.FLIGHT; self.pos = np.array([x, y]); self.r = r; self.missing = 0
                    self.vel = (self.pos - self.anchor) / self.gone
                    self.kick_lag = self.gone; self.gone = 0; self.search_all = 6
                    return (x, y, r, True)
            if self.gone == 3:                           # 3 frames with the ball gone from the spot: it was kicked
                self.state = self.FLIGHT; self.pos = self.anchor.copy(); self.vel = np.zeros(2); self.missing = 1
                self.r = self.anchor_r; self.gone = 0; self.search_all = 12      # look for it anywhere for 12 frames
                self.kick_lag = 3                        # the spot emptied 3 frames ago: back-date the kick
                return (*self.anchor, self.anchor_r, False)
            # at low frame rates a real departure always empties the spot in the same frame; a candidate
            # moving goalward while the ball is still sitting there is the kicker's leg, not the ball
            if self.stride >= 4 and frac > 0.35 * self.rest_frac:
                self.away = 0
                return (*self.anchor, self.anchor_r, True)
            # look a little beyond one radius so the first frames of the kick are caught
            gate = (1.0 * self.anchor_r + 30.0) * self.stride
            # near the anchor the ball may be half-hidden by the foot: no whiteness test there
            cands = self._candidates(m, self.anchor, 2.0 * self.anchor_r, self.anchor_r, 0.6, 1.4)
            cands += [c for c in self._candidates(m, self.anchor, gate, self.anchor_r, 0.6, 1.4, white=white) if c[4] > 2.0 * self.anchor_r]
            cands.sort()
            if self.goal_dir is not None:                      # the ball leaves toward the goal, feet don't
                cands = [c for c in cands if c[4] < 0.5 * self.anchor_r or
                         np.dot((np.array([c[1], c[2]]) - self.anchor) / c[4], self.goal_dir) > 0.0]
            if not cands:
                self.away = 0
                return (*self.anchor, self.anchor_r, False)
            _, x, y, r, d = cands[0]
            if d > 0.5 * self.anchor_r:
                self.away += 1
                if self.away >= 2:                       # it really left: switch to flight
                    self.kick_lag = 1                    # first seen away one frame ago
                    self.state = self.FLIGHT
                    self.vel = np.array([x, y]) - self.away_pos      # one-frame delta, not distance from anchor
                    self.pos = np.array([x, y]); self.r = r; self.missing = 0
                    return (x, y, r, True)
                self.away_pos = np.array([x, y])
                return (*self.anchor, self.anchor_r, True)
            self.away = 0
            return (*self.anchor, self.anchor_r, True)   # shaded / nudged, still at rest

        # ---- FLIGHT
        pred = self.pos + self.vel
        gate = max(45.0, 3.5 * np.linalg.norm(self.vel) + 2 * self.r) * (1 + 0.5 * min(self.missing, 2))
        cands = self._candidates(m, pred, gate, self.r)          # prediction gating is enough in flight
        if not cands and getattr(self, "search_all", 0) > 0:
            # ball left the spot faster than we could follow: find a moving white ball anywhere, preferring
            # candidates near the line from the kick spot to the goal
            self.search_all -= 1
            allc = self._candidates(m, (m.shape[1] / 2, m.shape[0] / 2), 1e6, self.anchor_r, 0.3, 1.2, white=white)
            if allc and self.goal_dir is not None:
                def off_line(c):
                    d = np.array([c[1], c[2]]) - self.anchor
                    return abs(d[0] * self.goal_dir[1] - d[1] * self.goal_dir[0]) - 0.5 * np.dot(d, self.goal_dir)
                cands = [min(allc, key=off_line)]
                if np.dot(np.array([cands[0][1], cands[0][2]]) - self.anchor, self.goal_dir) < 0:
                    cands = []                           # behind the kick spot: not the ball
            if cands:
                self.search_all = 0
                x, y, r = cands[0][1], cands[0][2], cands[0][3]
                self.vel = (np.array([x, y]) - self.anchor) / max(1, self.missing + 1)
                self.pos = np.array([x, y]); self.r = r; self.missing = 0
                return (x, y, r, True)
        if not cands:
            self.missing += 1
            if self.missing > 20:                        # lost: stop coasting, wait to re-acquire
                self.state = self.LOST; self.vel *= 0
            else:
                self.pos = pred
            return (*self.pos, self.r, False)
        _, x, y, r, d = cands[0]
        new = np.array([x, y])
        self.vel = 0.6 * (new - self.pos) + 0.4 * self.vel if self.missing == 0 else (new - self.pos) / (self.missing + 1)
        self.pos = new; self.r = 0.5 * r + 0.5 * self.r if abs(r - self.r) < max(8, 0.4 * self.r) else self.r
        self.missing = 0
        return (x, y, r, True)

    def fg_near(self, mask_fg, pt, rad):
        """foreground pixel count (any colour) in a disc around pt — for 'foot approaching'."""
        x, y = int(pt[0]), int(pt[1]); rad = int(rad)
        x0, y0, x1, y1 = max(0, x - rad), max(0, y - rad), min(mask_fg.shape[1], x + rad), min(mask_fg.shape[0], y + rad)
        return int(cv2.countNonZero(mask_fg[y0:y1, x0:x1]))


# ----------------------------------------------------------------------------- event detection (post-hoc on the track)
def smooth(a, k=3):
    a = np.asarray(a, float)
    if len(a) < k:
        return a
    ker = np.ones(k) / k
    return np.convolve(np.pad(a, (k // 2, k - 1 - k // 2), mode="edge"), ker, mode="valid")


def detect_events(track, goal: GoalTracker, cfg, step):
    """track: list of dicts with frame, x, y, r, det, gx, gy, foot, net.
    Returns list of kick dicts."""
    n = len(track)
    xy = np.array([[t["x"], t["y"]] for t in track])
    rr = np.array([t["r"] for t in track])
    v = np.vstack([np.zeros((1, 2)), np.diff(xy, axis=0)])
    speed = smooth(np.linalg.norm(v, axis=1), 3)
    foot = np.array([t["foot"] for t in track], float)
    # "at rest" = stays within 0.25 r of where it is for the next ~40 ms (shadow jitter tolerated)
    win = max(3, int(10 / step))
    rest_mask = np.zeros(n, bool)
    lost_mask = np.array([t["lost"] for t in track], bool)
    for j in range(n - win):
        rest_mask[j] = (not lost_mask[j]) and np.linalg.norm(xy[j + 1:j + win + 1] - xy[j], axis=1).max() < 0.25 * rr[j]
    kicks, i = [], 0
    while i < n:
        # ---- find a rest period (>= 25 frames at 240 fps ≈ 0.1 s)
        while i < n and not rest_mask[i]:
            i += 1
        rest_start = i
        while i < n and rest_mask[i]:
            i += 1
        rest_end = i - 1
        if i >= n:
            break
        if rest_end - rest_start < max(3, 25 // step):
            continue
        anchor = np.median(xy[rest_start:rest_end + 1], axis=0); r0 = float(np.median(rr[rest_start:rest_end + 1]))
        if goal.inside(tuple(anchor), 25):                 # resting in/at the goal (after a shot): not a kick spot
            continue
        disp_raw = np.linalg.norm(xy - anchor, axis=1)
        disp = np.array([np.median(disp_raw[max(0, j - 2):j + 3]) for j in range(n)])   # 5-frame median: kills jitter
        # ---- kick: ball has clearly left the spot (> 1 r) and keeps going; onset = last frame within 0.15 r
        k, found = rest_end + 1, False
        while k < n - 6:
            if lost_mask[k]:                              # track lost before any kick: no kick from this rest
                break
            if track[k]["det"] and disp[k] > 1.0 * r0 and np.all(np.diff(disp[k:k + 6]) > -1.0):
                found = True; break
            k += 1
        if not found:
            if k >= n - 6:
                break
            i = k; continue
        # onset: walk back down the rising edge of displacement until it stops rising
        kick = k
        while kick > rest_start + 1 and disp[kick - 1] < disp[kick] + 1.0 and disp[kick - 1] > 0.1 * r0:
            kick -= 1
        # ---- approach: a leg-sized foreground mass next to the ball shortly before the kick
        disc = math.pi * (4.5 * r0) ** 2
        approach = None
        for j in range(max(rest_start, kick - int(120 / step)), kick):
            if foot[j] > 0.12 * disc and np.all(foot[j:j + 3] > 0.12 * disc):
                approach = j; break
        if approach is None:
            approach = kick
        # ---- impact: inside the goal quad, biggest velocity discontinuity (ball meets net)
        # flight window: from the kick until the track is lost or 2 s of capture time
        j1 = min(n - 2, kick + int(2.0 * cfg["capture_fps"] / step))
        lost = 0
        for j in range(kick + 3, j1 + 1):
            lost = lost + 1 if not track[j]["det"] else 0
            if lost >= 10:
                j1 = j - 10; break
        impact_net, impact_dec = None, None
        # (a) net motion onset: foreground inside the goal quad (ball excluded) jumps
        net = np.array([t["net"] for t in track], float)
        nb = np.median(net[kick:kick + max(3, 20 // step)])
        for j in range(kick + 3, j1 + 1):
            if net[j] > nb + max(300, 4 * nb) and net[j + 1] > nb + max(300, 4 * nb):
                impact_net = j; break
        # (b) biggest velocity discontinuity of the ball (deceleration / rebound in the net)
        acc = np.zeros(n)
        for j in range(kick + 3, j1):
            acc[j] = np.linalg.norm(v[j + 1] - v[j - 1])
        if j1 > kick + 4:
            impact_dec = int(np.argmax(acc[kick + 3:j1])) + kick + 3
        # first net contact is the moment we want; deceleration peak is the fallback
        impact = impact_net if impact_net is not None else impact_dec
        if impact is not None and not goal.inside((track[impact]["x"], track[impact]["y"]), 40):
            impact = None                                    # ball nowhere near the goal: a miss
        end = j1
        # transverse launch speed from the first ~4 frames after onset; scale from the ball's apparent
        # radius at rest (11 cm).  Lower bound only: motion away from the camera is not seen.
        px_per_frame = float(np.mean(np.linalg.norm(np.diff(xy[kick + 1:kick + 6], axis=0), axis=1)))
        cm_per_px = (cfg["ball_diameter_cm"] / 2) / r0
        kd = {
            "rest_frame": track[rest_end]["frame"],
            "approach_frame": track[approach]["frame"],
            "kick_frame": track[kick]["frame"],
            "kick_px": [float(anchor[0]), float(anchor[1])], "rest_r_px": round(r0, 1),
            "launch_speed_px_per_frame": round(px_per_frame / step, 2),
            "launch_speed_transverse_m_s": round(px_per_frame / step * cm_per_px * cfg["capture_fps"] / 100, 2),
        }
        if impact is not None:
            t = track[impact]
            gx, gy = t["gx"], t["gy"]
            W, Hh = cfg["goal_w_cm"], cfg["goal_h_cm"]
            col = int(np.clip(gx / W * cfg["panel_cols"], 0, cfg["panel_cols"] - 1)) + 1
            row_from_top = int(np.clip((Hh - gy) / Hh * cfg["panel_rows"], 0, cfg["panel_rows"] - 1)) + 1
            flight = (t["frame"] - track[kick]["frame"])
            kd.update({
                "impact_frame": t["frame"],
                "impact_net_frame": track[impact_net]["frame"] if impact_net is not None else None,
                "impact_decel_frame": track[impact_dec]["frame"] if impact_dec is not None else None,
                "impact_px": [t["x"], t["y"]], "impact_r_px": t["r"],
                "impact_goal_cm": {"x_from_left_post": round(gx, 1), "y_from_ground": round(gy, 1)},
                "on_target": bool(0 <= gx <= W and 0 <= gy <= Hh),
                "panel_cell": {"col_from_left": col, "row_from_top": row_from_top},
                "flight_frames": int(flight),
                "flight_s": round(flight / cfg["capture_fps"], 4),
            })
            if cfg.get("kick_distance_m"):
                sp = cfg["kick_distance_m"] / (flight / cfg["capture_fps"])
                kd["avg_speed_m_s"] = round(sp, 2); kd["avg_speed_km_h"] = round(sp * 3.6, 1)
        kicks.append(kd)
        i = end + 1
    return kicks, speed


# ----------------------------------------------------------------------------- drawing
def draw_goal(img, corners, color=(0, 255, 255)):
    c = corners.astype(int)
    cv2.polylines(img, [c.reshape(-1, 1, 2)], True, color, 2)
    for p, nm in zip(c, ["TL", "TR", "BR", "BL"]):
        cv2.putText(img, nm, tuple(p + np.array([4, -4])), 0, 0.5, color, 1)


def goal_face_png(cfg, kicks, path):
    W, Hh = cfg["goal_w_cm"], cfg["goal_h_cm"]; s = 4
    img = np.full((int(Hh * s) + 80, int(W * s) + 80, 3), 30, np.uint8)
    ox, oy = 40, 40
    cols, rows = cfg["panel_cols"], cfg["panel_rows"]
    for c in range(cols + 1):
        x = int(ox + c * W / cols * s); cv2.line(img, (x, oy), (x, oy + int(Hh * s)), (70, 70, 70), 1)
    for r in range(rows + 1):
        y = int(oy + r * Hh / rows * s); cv2.line(img, (ox, y), (ox + int(W * s), y), (70, 70, 70), 1)
    cv2.rectangle(img, (ox, oy), (ox + int(W * s), oy + int(Hh * s)), (255, 255, 255), 2)
    for k, kd in enumerate(kicks):
        if "impact_goal_cm" not in kd:
            continue
        gx, gy = kd["impact_goal_cm"]["x_from_left_post"], kd["impact_goal_cm"]["y_from_ground"]
        px, py = int(ox + gx * s), int(oy + (Hh - gy) * s)
        cell = kd["panel_cell"]
        x0 = int(ox + (cell["col_from_left"] - 1) * W / cols * s); y0 = int(oy + (cell["row_from_top"] - 1) * Hh / rows * s)
        cv2.rectangle(img, (x0, y0), (int(x0 + W / cols * s), int(y0 + Hh / rows * s)), (0, 140, 255), -1)
        cv2.circle(img, (px, py), int(cfg["ball_diameter_cm"] / 2 * s), (255, 255, 255), 1)
        cv2.circle(img, (px, py), 4, (0, 0, 255), -1)
        cv2.putText(img, f"#{k+1} ({gx:.0f},{gy:.0f}) cm", (px + 12, py - 8), 0, 0.5, (255, 255, 255), 1)
    cv2.putText(img, f"goal face {W:.0f}x{Hh:.0f} cm, kicker's view, {cols}x{rows} panel cells", (ox, oy - 12), 0, 0.5, (200, 200, 200), 1)
    cv2.imwrite(path, img)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("--config"); ap.add_argument("--out")
    ap.add_argument("--start", type=int, default=0); ap.add_argument("--end", type=int, default=-1)
    ap.add_argument("--step", type=int, default=1); ap.add_argument("--render", action="store_true", help="write annotated mp4")
    ap.add_argument("--stride", type=int, default=None, help="tracker gate scaling (default = step; use 8 for a native 30 fps clip)")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    cfg = load_cfg(a.config)
    if not cfg.get("corners"):
        sys.exit("config has no goal corners — run pick_corners.py (or live_tracker.py, press g then s) first")
    name = os.path.splitext(os.path.basename(a.video))[0] + (f"_{a.tag}" if a.tag else "") + (f"_step{a.step}" if a.step > 1 else "")
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.video)), "out")
    os.makedirs(out, exist_ok=True); fdir = os.path.join(out, name + "_frames")
    if os.path.isdir(fdir):
        for fn in os.listdir(fdir):
            try: os.remove(os.path.join(fdir, fn))
            except OSError: pass                        # read-only / no-delete mounts: stale frames stay
    os.makedirs(fdir, exist_ok=True)

    cap = cv2.VideoCapture(a.video)
    N = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); end = N - 1 if a.end < 0 else min(a.end, N - 1)
    cap.set(cv2.CAP_PROP_POS_FRAMES, a.start)
    ok, f0 = cap.read()
    if not ok:
        sys.exit("cannot read video")
    goal = GoalTracker(cfg)
    if not goal.initialise(f0):
        print("WARNING: goal frame fit did not converge on the first frame; bar point counts:", goal.counts)
    print(f"corner shift from config (px): {goal.init_shift}  (if > ~5 px, re-pick corners with pick_corners.py)")
    rest = find_resting_ball(f0, goal, cfg)
    if rest is None and cfg.get("rest_ball_px"):
        rest = tuple(cfg["rest_ball_px"]); print("resting ball not found in first frame; using rest_ball_px from config")
    if rest is None:
        sys.exit("no resting ball found in first frame — check white thresholds / start frame, or set rest_ball_px in the config")
    print(f"goal corners: {goal.corners.round(1).tolist()}  fit_ok={goal.ok}")
    print(f"resting ball at px ({rest[0]:.0f},{rest[1]:.0f}) r={rest[2]:.1f}")
    stride = a.stride or a.step
    bt = BallTracker(cfg, rest, stride); bt.set_goal(goal.corners)
    bt.bg.apply(f0)

    writer = None
    if a.render:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(os.path.join(out, name + "_annotated.mp4"), fourcc, 30, (f0.shape[1], f0.shape[0]))

    track = []
    fi = a.start
    cap.set(cv2.CAP_PROP_POS_FRAMES, a.start)
    while fi <= end:
        ok, f = cap.read()
        if not ok: break
        if (fi - a.start) % a.step:
            fi += 1; continue
        corners, _ = goal.update(f)
        x, y, r, det = bt.step(f)
        if bt.lost and (fi - a.start) % (5 * a.step) == 0 and bt.reacquire(f, goal, cfg):
            x, y, r = bt.pos[0], bt.pos[1], bt.r; bt.set_goal(goal.corners)
            print(f"  frame {fi}  re-acquired resting ball at ({x:.0f},{y:.0f}) r={r:.1f}")
        fgm = bt.fg                      # foreground mask from this frame, for the two auxiliary cues
        foot = bt.fg_near(fgm, (x, y), 4.5 * r)
        gm = np.zeros(fgm.shape, np.uint8); cv2.fillPoly(gm, [corners.astype(np.int32)], 255)
        cv2.circle(gm, (int(x), int(y)), int(2.5 * r), 0, -1)
        net = int(cv2.countNonZero(cv2.bitwise_and(fgm, gm)))
        gx, gy = goal.to_goal((x, y))
        track.append(dict(frame=fi, x=float(x), y=float(y), r=float(r), det=bool(det), lost=bool(bt.lost),
                          gx=gx, gy=gy, foot=foot, net=net, corners=corners.copy()))
        if writer:
            vis = f.copy(); draw_goal(vis, corners)
            for t in track[-40:]:
                cv2.circle(vis, (int(t["x"]), int(t["y"])), 2, (0, 255, 0) if t["det"] else (0, 0, 255), -1)
            cv2.circle(vis, (int(x), int(y)), int(r), (0, 255, 0) if det else (0, 0, 255), 2)
            cv2.putText(vis, f"f{fi}  goal({gx:.0f},{gy:.0f})cm", (20, 40), 0, 1, (255, 255, 255), 2)
            writer.write(vis)
        if (fi - a.start) % (200 * a.step) == 0:
            print(f"  frame {fi}  ball ({x:.0f},{y:.0f}) r={r:.1f} det={det} fit_ok={goal.ok}")
        fi += 1
    cap.release()
    if writer: writer.release()

    kicks, speed = detect_events(track, goal, cfg, a.step)

    # ---- per-frame csv
    with open(os.path.join(out, name + "_track.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["frame", "x", "y", "r", "det", "speed_px", "goal_x_cm", "goal_y_cm", "foot_fg", "net_fg"])
        for t, s in zip(track, speed):
            w.writerow([t["frame"], f"{t['x']:.1f}", f"{t['y']:.1f}", f"{t['r']:.1f}", int(t["det"]), f"{s:.2f}", f"{t['gx']:.1f}", f"{t['gy']:.1f}", t["foot"], t["net"]])

    # ---- key frames
    by_frame = {t["frame"]: t for t in track}
    cap = cv2.VideoCapture(a.video)
    for k, kd in enumerate(kicks):
        for key in ["rest_frame", "approach_frame", "kick_frame", "impact_frame", "impact_decel_frame"]:
            fr = kd.get(key)
            if fr is None: continue
            cap.set(cv2.CAP_PROP_POS_FRAMES, fr); ok, f = cap.read()
            if not ok: continue
            t = by_frame[fr]; vis = f.copy(); draw_goal(vis, t["corners"])
            cv2.circle(vis, (int(t["x"]), int(t["y"])), int(max(t["r"], 6)) + 4, (0, 255, 0), 2)
            cv2.putText(vis, f"kick {k+1} {key} f{fr}", (20, 40), 0, 1.1, (255, 255, 255), 3)
            cv2.imwrite(os.path.join(fdir, f"k{k+1}_{key}_{fr}.jpg"), vis)
            if key.startswith("impact"):
                c = t["corners"]; x0, y0 = int(c[:, 0].min() - 40), int(c[:, 1].min() - 40); x1, y1 = int(c[:, 0].max() + 40), int(c[:, 1].max() + 40)
                crop = vis[max(0, y0):y1, max(0, x0):x1]
                cv2.imwrite(os.path.join(fdir, f"k{k+1}_{key}_{fr}_zoom.jpg"), cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
    cap.release()

    goal_face_png(cfg, kicks, os.path.join(out, name + "_goalface.png"))
    res = {"video": os.path.abspath(a.video), "frames_analysed": [a.start, end], "step": a.step,
           "effective_fps": cfg["capture_fps"] / a.step, "goal_corners_px": goal.corners.round(1).tolist(),
           "resting_ball_px": [round(rest[0], 1), round(rest[1], 1), round(rest[2], 1)], "kicks": kicks}
    with open(os.path.join(out, name + "_events.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print(json.dumps(res["kicks"], indent=2))
    print("wrote", os.path.join(out, name + "_events.json"))


if __name__ == "__main__":
    main()
