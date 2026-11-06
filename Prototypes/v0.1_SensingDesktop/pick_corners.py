#!/usr/bin/env python3
"""
pick_corners.py — click the 4 INNER goal corners on a video frame and write them to goal.json.

Run this in a normal macOS Terminal (needs a window):
    python3 pick_corners.py ../../../Photos/ballkick.MOV --frame 300 --config goal.json

Click order: top-left, top-right, bottom-right, bottom-left — the inner edges of the posts /
underside of the crossbar / top of the ground bar, i.e. the 240 x 172 cm opening.
Keys: z = undo last click, r = reset, s = save and quit, q = quit without saving.
Mouse wheel / +/- zooms, drag with right button to pan.
"""
import argparse, json, cv2, numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("--frame", type=int, default=0); ap.add_argument("--config", default="goal.json")
a = ap.parse_args()

cap = cv2.VideoCapture(a.video); cap.set(cv2.CAP_PROP_POS_FRAMES, a.frame); ok, img = cap.read()
if not ok:
    raise SystemExit("cannot read frame")
H, W = img.shape[:2]
state = {"pts": [], "zoom": 1.0, "cx": W / 2, "cy": H / 2, "drag": None}
names = ["TL", "TR", "BR", "BL"]


def view():
    z = state["zoom"]; vw, vh = 1400, 800
    x0 = int(state["cx"] - vw / (2 * z)); y0 = int(state["cy"] - vh / (2 * z))
    x0 = max(0, min(W - int(vw / z), x0)); y0 = max(0, min(H - int(vh / z), y0))
    crop = img[y0:y0 + int(vh / z), x0:x0 + int(vw / z)]
    v = cv2.resize(crop, (vw, vh), interpolation=cv2.INTER_CUBIC if z > 1 else cv2.INTER_AREA)
    for i, (x, y) in enumerate(state["pts"]):
        px, py = int((x - x0) * z), int((y - y0) * z)
        cv2.drawMarker(v, (px, py), (0, 0, 255), cv2.MARKER_CROSS, 24, 1)
        cv2.putText(v, names[i], (px + 6, py - 6), 0, 0.6, (0, 0, 255), 2)
    if len(state["pts"]) == 4:
        pts = np.array([[(x - x0) * z, (y - y0) * z] for x, y in state["pts"]], np.int32)
        cv2.polylines(v, [pts.reshape(-1, 1, 2)], True, (0, 255, 255), 1)
    cv2.putText(v, f"click {names[len(state['pts'])] if len(state['pts'])<4 else 'done — press s to save'}   zoom {z:.1f}x", (10, 25), 0, 0.7, (255, 255, 255), 2)
    return v, x0, y0


def on_mouse(ev, x, y, flags, _):
    v, x0, y0 = state["view"]
    z = state["zoom"]
    if ev == cv2.EVENT_LBUTTONDOWN and len(state["pts"]) < 4:
        state["pts"].append((x0 + x / z, y0 + y / z))
    elif ev == cv2.EVENT_MOUSEWHEEL:
        state["zoom"] = float(np.clip(state["zoom"] * (1.25 if flags > 0 else 0.8), 1, 8))
        state["cx"], state["cy"] = x0 + x / z, y0 + y / z
    elif ev == cv2.EVENT_RBUTTONDOWN:
        state["drag"] = (x, y, state["cx"], state["cy"])
    elif ev == cv2.EVENT_MOUSEMOVE and state["drag"] and flags & cv2.EVENT_FLAG_RBUTTON:
        dx, dy, cx, cy = state["drag"]; state["cx"] = cx - (x - dx) / z; state["cy"] = cy - (y - dy) / z
    elif ev == cv2.EVENT_RBUTTONUP:
        state["drag"] = None


cv2.namedWindow("pick corners"); cv2.setMouseCallback("pick corners", on_mouse)
while True:
    state["view"] = view()
    cv2.imshow("pick corners", state["view"][0])
    k = cv2.waitKey(30) & 0xFF
    if k == ord("q"): break
    if k == ord("z") and state["pts"]: state["pts"].pop()
    if k == ord("r"): state["pts"] = []
    if k in (ord("+"), ord("=")): state["zoom"] = min(8, state["zoom"] * 1.25)
    if k == ord("-"): state["zoom"] = max(1, state["zoom"] * 0.8)
    if k == ord("s") and len(state["pts"]) == 4:
        try:
            cfg = json.load(open(a.config))
        except FileNotFoundError:
            cfg = {}
        cfg["corners"] = [[round(x, 1), round(y, 1)] for x, y in state["pts"]]
        json.dump(cfg, open(a.config, "w"), indent=2)
        print("saved", cfg["corners"], "to", a.config); break
cv2.destroyAllWindows()
