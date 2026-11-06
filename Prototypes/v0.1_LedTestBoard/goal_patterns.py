#!/usr/bin/env python3
"""
goal_patterns.py - pattern tester for the interactive-goal LED test board.

Drives a WLED controller with raw pixel data (DDP over Wi-Fi, or Adalight over
the USB serial port) and renders patterns onto the board treated as an
8-column x 34-row "screen" with non-square pixels (16.7 mm tall, 67 mm wide).

Requirements:  python3, numpy, pyserial   (pip3 install numpy pyserial)
Optional:      tkinter for --preview      (bundled with python.org Python; Homebrew: brew install python-tk)

Usage:  python3 goal_patterns.py <target> <pattern> [options]
  <target>   usb              Adalight over the SP805E's USB port (auto-finds /dev/cu.usbserial-*)
             192.168.1.116    DDP over Wi-Fi (UDP 4048) once the controller is reachable
             none             no hardware (combine with --preview)
  <pattern>  see `python3 goal_patterns.py list`, or demo / live

Examples:
  python3 goal_patterns.py usb identify           # one white pixel walks the whole chain - check the mapping first
  python3 goal_patterns.py usb goal               # goal celebration
  python3 goal_patterns.py usb live               # keyboard-driven: g = GOAL, t = target, d = countdown ... q = quit
  python3 goal_patterns.py usb text --text KICK   # scrolling text
  python3 goal_patterns.py usb demo --baud 460800 # faster link (~50 fps) if your USB chip/driver can do it; default 230400 (~25 fps)
  python3 goal_patterns.py none goal --preview    # just a window
  python3 goal_patterns.py usb goal --layout panel   # the real 13 x 36 panel once the strips are cut

Test-board mapping (from the photo: START bottom-left, data snakes left to right):
  LED 0              lead-in below the bottom line         (off screen)
  LEDs 1-34          run 1 going UP        -> column 0
  LEDs 35-41         loop over the top                     (off screen)
  LEDs 42-75         run 2 going DOWN      -> column 1
  ...
  LEDs 124-149       run 4 DOWN, 26 LEDs   -> column 3 rows 0-25, then the joiner between the two strips (dead gap)
  LEDs 280-299       run 8 DOWN, 20 LEDs   -> column 7 rows 0-19, strip ends
"""

import argparse
import math
import random
import select
import socket
import sys
import time

import numpy as np

# --------------------------------------------------------------------------------------
# Physical layout
# --------------------------------------------------------------------------------------
LED_PITCH_MM = 1000.0 / 30.0     # WS2815, 30 LEDs per metre

# The chain, in data order.  ('skip', n) = n LEDs that are not on the screen (loops / lead-in).
# ('up', n, col) = n LEDs running from the BOTTOM row upwards in that column.
# ('down', n, col) = n LEDs running from the TOP row downwards in that column.
# A short run (n < rows) just leaves the remaining rows dark - e.g. the joiner on run 4.
LAYOUTS = {
    # the uncut test board: 27 mm gutters + 40 mm battens, loops top and bottom
    'board': dict(
        rows=34, cols=8, col_pitch_mm=27.0 + 40.0, gutter_mm=27.0,
        chain=[
            ('skip', 1),
            ('up', 34, 0), ('skip', 7),
            ('down', 34, 1), ('skip', 7),
            ('up', 34, 2), ('skip', 7),
            ('down', 26, 3), ('skip', 7),      # 26 live LEDs then the strip-to-strip joiner (dead) at the bottom
            ('up', 34, 4), ('skip', 7),
            ('down', 34, 5), ('skip', 7),
            ('up', 34, 6), ('skip', 7),
            ('down', 20, 7),                   # second strip ends after 20
        ]),
    # one real fence panel per the spec: 13 columns x 36 rows, 71 mm across, cut strips zig-zagging
    'panel': dict(
        rows=36, cols=13, col_pitch_mm=71.0, gutter_mm=27.0,
        chain=[('up' if c % 2 == 0 else 'down', 36, c) for c in range(13)]),
}

GAMMA = 2.2
DEFAULT_BRIGHTNESS = 0.3    # WLED's 2000 mA limiter also applies; 300 WS2815 at full white is ~5 A at 12 V
FPS = 30


# --------------------------------------------------------------------------------------
# Build the mapping once
# --------------------------------------------------------------------------------------
ROWS = COLS = COL_PITCH_MM = GUTTER_MM = None   # set by Layout() from the chosen preset


class Layout:
    def __init__(self, name='board'):
        global ROWS, COLS, COL_PITCH_MM, GUTTER_MM
        spec = LAYOUTS[name]
        ROWS, COLS = spec['rows'], spec['cols']
        COL_PITCH_MM, GUTTER_MM = spec['col_pitch_mm'], spec['gutter_mm']
        self.name = name
        self.led_to_rc = []                       # led index -> (row, col) or None
        self.grid_to_led = -np.ones((ROWS, COLS), dtype=int)
        for seg in spec['chain']:
            kind, n = seg[0], seg[1]
            if kind == 'skip':
                self.led_to_rc.extend([None] * n)
                continue
            col = seg[2]
            rows = range(ROWS - 1, ROWS - 1 - n, -1) if kind == 'up' else range(0, n)
            for r in rows:
                self.grid_to_led[r, col] = len(self.led_to_rc)
                self.led_to_rc.append((r, col))
        self.n_leds = len(self.led_to_rc)
        self.mask = self.grid_to_led >= 0                       # live pixels
        # physical coordinates of every grid cell (mm), row 0 at the top
        cs, rs = np.meshgrid(np.arange(COLS), np.arange(ROWS))
        self.X = cs * COL_PITCH_MM
        self.Y = rs * LED_PITCH_MM
        self.width_mm = (COLS - 1) * COL_PITCH_MM
        self.height_mm = (ROWS - 1) * LED_PITCH_MM
        self.cx = self.width_mm / 2
        self.cy = self.height_mm / 2
        self.D = np.hypot(self.X - self.cx, self.Y - self.cy)    # distance of every cell from the centre
        live_rows, live_cols = np.nonzero(self.mask)
        self.live_rc = list(zip(live_rows.tolist(), live_cols.tolist()))
        self.live_leds = self.grid_to_led[self.mask]
        self.gamma_lut = np.array([int(round(255 * (i / 255.0) ** GAMMA)) for i in range(256)], dtype=np.uint8)

    def dist_from(self, x_mm, y_mm):
        return np.hypot(self.X - x_mm, self.Y - y_mm)

    def frame_to_bytes(self, frame, brightness, gamma=True):
        """frame: float array (ROWS, COLS, 3) in 0..1 -> bytes for the whole chain (RGB)."""
        out = np.zeros((self.n_leds, 3), dtype=np.uint8)
        vals = np.clip(frame[self.mask] * brightness, 0, 1)
        vals8 = (vals * 255 + 0.5).astype(np.uint8)
        if gamma:
            vals8 = self.gamma_lut[vals8]
        out[self.live_leds] = vals8
        return out.tobytes()

    def describe(self):
        print(f"layout '{self.name}': {self.n_leds} LEDs, screen {COLS} cols x {ROWS} rows, "
              f"{self.width_mm:.0f} x {self.height_mm:.0f} mm centre-to-centre, "
              f"{int(self.mask.sum())} live pixels")
        for c in range(COLS):
            leds = self.grid_to_led[:, c]
            live = leds[leds >= 0]
            print(f"  col {c}: LEDs {live.min()}-{live.max()}  ({len(live)} rows live)")


# --------------------------------------------------------------------------------------
# Transports
# --------------------------------------------------------------------------------------
class DDPSender:
    """DDP (Distributed Display Protocol) - WLED listens on UDP 4048, no setup needed."""
    MAX_PIXELS_PER_PACKET = 480

    def __init__(self, host, port=4048):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq = 1

    def send(self, data):
        n_pix = len(data) // 3
        offset_px = 0
        while offset_px < n_pix:
            chunk_px = min(self.MAX_PIXELS_PER_PACKET, n_pix - offset_px)
            last = offset_px + chunk_px >= n_pix
            flags = 0x40 | (0x01 if last else 0x00)         # version 1, push on last packet
            hdr = bytes([flags, self.seq & 0x0F, 0x01, 0x01]) \
                + (offset_px * 3).to_bytes(4, 'big') \
                + (chunk_px * 3).to_bytes(2, 'big')
            self.sock.sendto(hdr + data[offset_px * 3:(offset_px + chunk_px) * 3], self.addr)
            offset_px += chunk_px
        self.seq = (self.seq % 15) + 1

    def close(self):
        self.sock.close()


class SerialSender:
    """Adalight over USB serial.  In WLED: Settings -> Sync Interfaces -> Serial = 115200 (default)."""

    @staticmethod
    def find_port(port):
        if port in (None, 'auto'):
            import glob
            ports = sorted(glob.glob('/dev/cu.usbserial*') + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/cu.SLAB*'))
            if not ports:
                sys.exit("no USB serial port found - is the controller plugged in?  (expected /dev/cu.usbserial-3130)")
            port = ports[0]
        return port

    def __init__(self, port, baud=115200, boot_baud=115200, blind=False):
        try:
            import serial  # pyserial
        except ImportError:
            sys.exit("pyserial is needed for usb:  pip3 install pyserial")
        self.port = port = self.find_port(port)
        self.baud = boot_baud
        # WLED boots at the baud set in Config -> Sync Interfaces (115200 unless changed).  Opening the port
        # resets the ESP32, so always open at the boot baud, then ask WLED to switch with its one-byte command.
        self.boot_baud = boot_baud
        self.ser = serial.Serial(port, boot_baud, timeout=0, write_timeout=2.0)
        if baud not in self.BAUD_CODES:
            sys.exit(f"--baud must be one of {sorted(self.BAUD_CODES)} (WLED's supported rates)")
        # WLED answers 'v' with its version.  This board does not reset when the port opens, so the
        # controller may still be at whatever rate the previous run left it on: listen at the boot
        # rate first, then scan the others until something answers.
        version = self._wait_for_wled(timeout=3.0)
        if not version:
            for rate in [baud] + [r for r in sorted(self.BAUD_CODES) if r not in (baud, boot_baud)]:
                self.ser.baudrate = rate
                self.baud = rate
                time.sleep(0.1)
                version = self._wait_for_wled(timeout=0.8)
                if version:
                    print(f"(controller was still at {rate} baud from the last run)")
                    break
            else:
                self.ser.baudrate = boot_baud
                self.baud = boot_baud
        if version:
            print(f"controller answered: {version}")
        else:
            print("no reply from WLED at any rate (still booting, or this firmware does not talk back)")
        if baud != self.baud:
            if blind:
                self.ser.write(bytes([self.BAUD_CODES[baud]]))
                self.ser.flush()
                time.sleep(0.3)
                self.ser.baudrate = baud
                self.baud = baud
                print(f"--blind: sent the switch byte and moved to {baud} baud without confirmation.")
            elif not version:
                print(f"can't confirm anything with a silent controller - staying at {self.baud}")
            else:
                was = self.baud
                ok, why = self._switch(baud)
                if ok:
                    print(f"WLED switched to {baud} baud for this session")
                else:
                    print(f"{baud} baud failed: {why}")
                    if why.startswith("no reply at"):
                        # WLED *did* switch, so talk to it at the new rate to bring it back down
                        back, why2 = self._switch(was)
                        if back:
                            print(f"returned the controller to {was}; running at that rate. "
                                  f"Try a lower rate next time, e.g. --baud 230400")
                        else:
                            sys.exit(f"could not return the controller to {was} ({why2}). "
                                     f"Power-cycle the controller before running again.")
                    else:
                        print(f"staying at {was}")
        self.ser.reset_input_buffer()

    def _switch(self, new_baud):
        """Ask WLED to change baud and follow it. Returns (ok, reason). Only leaves the two sides
        mismatched if something is badly wrong, and then says so."""
        self.ser.reset_input_buffer()
        self.ser.write(bytes([self.BAUD_CODES[new_baud]]))
        self.ser.flush()
        reply = self._read_for(1.0)
        if b'Baud is now' not in reply:
            return False, f"no acknowledgement from WLED (got {reply[:40]!r})"
        time.sleep(0.3)                        # let WLED finish re-opening its UART
        self.ser.baudrate = new_baud           # changing the rate on an open port does not reset the ESP32
        self.baud = new_baud
        time.sleep(0.3)
        for _ in range(6):                     # a few tries - the first bytes after a rate change can be lost
            self.ser.reset_input_buffer()
            self.ser.write(b'v')
            self.ser.flush()
            if b'WLED' in self._read_for(0.5):
                return True, ""
        return False, f"no reply at {new_baud} after WLED acknowledged the switch"

    @classmethod
    def probe(cls, port, boot_baud):
        """Open the port and show everything the controller says, then try the known queries."""
        import serial
        port = cls.find_port(port)
        print(f"opening {port} @ {boot_baud}; listening for 6 s for a boot log ...")
        ser = serial.Serial(port, boot_baud, timeout=0)
        end = time.monotonic() + 6.0
        got = b''
        while time.monotonic() < end:
            n = ser.in_waiting
            if n:
                got += ser.read(n)
            time.sleep(0.05)
        print(f"  boot output: {got[:400]!r}" if got else "  boot output: (nothing)")
        for label, msg in [("version query 'v'", b'v'),
                           ("JSON query", b'{"v":true}\n'),
                           ("improv/other newline", b'\n')]:
            ser.reset_input_buffer()
            ser.write(msg)
            ser.flush()
            time.sleep(1.0)
            got = ser.read(ser.in_waiting or 0)
            print(f"  {label:<22}-> {got[:300]!r}" if got else f"  {label:<22}-> (no reply)")
        # does Adalight still work?  light the first 10 LEDs white for a second
        data = bytes([80, 80, 80] * 10 + [0, 0, 0] * 290)
        n = 299
        ser.write(b'Ada' + bytes([n >> 8, n & 0xFF, (n >> 8) ^ (n & 0xFF) ^ 0x55]) + data)
        ser.flush()
        print("  sent one Adalight frame: the first 10 LEDs should be white now")
        time.sleep(2.0)
        ser.close()

    def _read_for(self, seconds):
        end = time.monotonic() + seconds
        buf = b''
        while time.monotonic() < end:
            n = self.ser.in_waiting
            if n:
                buf += self.ser.read(n)
                if b'\n' in buf:
                    break
            time.sleep(0.02)
        return buf

    def _wait_for_wled(self, timeout):
        end = time.monotonic() + timeout
        time.sleep(0.5)
        while time.monotonic() < end:
            self.ser.reset_input_buffer()
            self.ser.write(b'v')
            self.ser.flush()
            reply = self._read_for(0.4)
            if b'WLED' in reply:
                line = reply[reply.find(b'WLED'):].split(b'\n')[0].strip()
                return line.decode('ascii', 'replace')
        return None

    BAUD_CODES = {115200: 0xB0, 230400: 0xB1, 460800: 0xB2, 500000: 0xB3,
                  576000: 0xB4, 921600: 0xB5, 1000000: 0xB6, 1500000: 0xB7}

    def max_fps(self, n_leds):
        return self.baud / 10.0 / (n_leds * 3 + 6)

    def send(self, data):
        n = len(data) // 3 - 1
        hi, lo = (n >> 8) & 0xFF, n & 0xFF
        self.ser.write(b'Ada' + bytes([hi, lo, hi ^ lo ^ 0x55]) + data)
        self.ser.flush()                      # block until this frame has actually left the Mac - no backlog
        # WLED talks back occasionally (Improv / JSON); drain it so the input buffer never fills
        if self.ser.in_waiting:
            self.ser.reset_input_buffer()

    def close(self):
        # leave the controller at its boot rate so the next run (or any other tool) finds it
        if self.baud != self.boot_baud:
            try:
                time.sleep(0.1)
                ok, _ = self._switch(self.boot_baud)
                print(f"controller returned to {self.boot_baud} baud" if ok
                      else f"warning: controller may still be at {self.baud} baud (the next run will scan for it)")
            except Exception:
                pass
        self.ser.close()


class NullSender:
    def send(self, data):
        pass

    def close(self):
        pass


class Preview:
    """tkinter window showing the screen at its real aspect ratio (optional)."""

    def __init__(self, layout, scale=0.9):
        try:
            import tkinter as tk
        except ImportError:
            sys.exit("tkinter not available - on Homebrew Python: brew install python-tk")
        self.tk = tk
        self.layout = layout
        self.scale = scale
        pad = 30
        w = int(layout.width_mm * scale) + 2 * pad
        h = int(layout.height_mm * scale) + 2 * pad
        self.root = tk.Tk()
        self.root.title("goal board preview")
        self.canvas = tk.Canvas(self.root, width=w, height=h, bg='#202020', highlightthickness=0)
        self.canvas.pack()
        # draw the gutters
        gw = GUTTER_MM * scale
        for c in range(COLS):
            x = pad + c * COL_PITCH_MM * scale
            self.canvas.create_rectangle(x - gw / 2, pad - 10, x + gw / 2, h - pad + 10, fill='#303030', outline='')
        self.items = {}
        rpx = LED_PITCH_MM * scale * 0.45
        for (r, c) in layout.live_rc:
            x = pad + c * COL_PITCH_MM * scale
            y = pad + r * LED_PITCH_MM * scale
            self.items[(r, c)] = self.canvas.create_oval(x - rpx * 1.6, y - rpx, x + rpx * 1.6, y + rpx,
                                                         fill='#000000', outline='')
        self.alive = True
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _close(self):
        self.alive = False

    def show(self, frame, brightness):
        if not self.alive:
            return
        f = np.clip(frame * min(1.0, brightness * 2.5), 0, 1)   # preview a bit brighter than the LEDs
        for (r, c), item in self.items.items():
            rr, gg, bb = (f[r, c] * 255).astype(int)
            self.canvas.itemconfig(item, fill=f'#{rr:02x}{gg:02x}{bb:02x}')
        try:
            self.root.update()
        except self.tk.TclError:
            self.alive = False


# --------------------------------------------------------------------------------------
# Helpers for patterns
# --------------------------------------------------------------------------------------
def hsv(h, s=1.0, v=1.0):
    """h in 0..1 -> rgb tuple 0..1 (vectorised if h is an array)."""
    h = np.asarray(h) % 1.0
    i = np.floor(h * 6).astype(int)
    f = h * 6 - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    i = i % 6
    r = np.choose(i, [v * np.ones_like(f), q, p, p, t, v * np.ones_like(f)])
    g = np.choose(i, [t, v * np.ones_like(f), v * np.ones_like(f), q, p, p])
    b = np.choose(i, [p, p, t, v * np.ones_like(f), v * np.ones_like(f), q])
    return np.stack([r, g, b], axis=-1)


def blank():
    return np.zeros((ROWS, COLS, 3), dtype=float)


def paint(frame, weight, color):
    """Additively paint `color` (3,) onto frame with per-pixel weight (ROWS, COLS)."""
    frame += weight[..., None] * np.asarray(color, dtype=float)[None, None, :]
    return frame


def ring(layout, x, y, radius, thickness):
    """Soft ring weight mask in mm space."""
    d = layout.dist_from(x, y)
    return np.clip(1 - np.abs(d - radius) / thickness, 0, 1)


def disc(layout, x, y, radius, soft=20.0):
    d = layout.dist_from(x, y)
    return np.clip((radius - d) / soft + 1, 0, 1)


# 3x5 font (rows top to bottom) - scores, countdowns, scrolling words
FONT = {
    '0': ["111", "101", "101", "101", "111"], '1': ["010", "110", "010", "010", "111"],
    '2': ["111", "001", "111", "100", "111"], '3': ["111", "001", "111", "001", "111"],
    '4': ["101", "101", "111", "001", "001"], '5': ["111", "100", "111", "001", "111"],
    '6': ["111", "100", "111", "101", "111"], '7': ["111", "001", "001", "001", "001"],
    '8': ["111", "101", "111", "101", "111"], '9': ["111", "101", "111", "001", "111"],
    'A': ["010", "101", "111", "101", "101"], 'B': ["110", "101", "110", "101", "110"],
    'C': ["111", "100", "100", "100", "111"], 'D': ["110", "101", "101", "101", "110"],
    'E': ["111", "100", "111", "100", "111"], 'F': ["111", "100", "111", "100", "100"],
    'G': ["111", "100", "101", "101", "111"], 'H': ["101", "101", "111", "101", "101"],
    'I': ["111", "010", "010", "010", "111"], 'J': ["001", "001", "001", "101", "111"],
    'K': ["101", "101", "110", "101", "101"], 'L': ["100", "100", "100", "100", "111"],
    'M': ["101", "111", "111", "101", "101"], 'N': ["111", "101", "101", "101", "101"],
    'O': ["111", "101", "101", "101", "111"], 'P': ["111", "101", "111", "100", "100"],
    'Q': ["111", "101", "101", "111", "001"], 'R': ["111", "101", "110", "101", "101"],
    'S': ["111", "100", "111", "001", "111"], 'T': ["111", "010", "010", "010", "010"],
    'U': ["101", "101", "101", "101", "111"], 'V': ["101", "101", "101", "101", "010"],
    'W': ["101", "101", "111", "111", "101"], 'X': ["101", "101", "010", "101", "101"],
    'Y': ["101", "101", "010", "010", "010"], 'Z': ["111", "001", "010", "100", "111"],
    '!': ["010", "010", "010", "000", "010"], '-': ["000", "000", "111", "000", "000"],
    ' ': ["000", "000", "000", "000", "000"],
}


def text_width(text, sx, gap=1):
    return len(text) * 3 * sx + (len(text) - 1) * gap


def draw_text(frame, text, color, sx, sy, gap=1, row0=None, col0=None):
    """Draw text; sx/sy = screen cells per font pixel. Centred unless row0/col0 given (may be off-screen)."""
    text = text.upper()
    glyphs = [FONT.get(ch, FONT[' ']) for ch in text]
    if col0 is None:
        col0 = (COLS - text_width(text, sx, gap)) // 2
    if row0 is None:
        row0 = (ROWS - 5 * sy) // 2
    c = col0
    for g in glyphs:
        for fr, line in enumerate(g):
            for fc, bit in enumerate(line):
                if bit == '1':
                    r0, c0 = row0 + fr * sy, c + fc * sx
                    if c0 + sx <= 0 or c0 >= COLS or r0 + sy <= 0 or r0 >= ROWS:
                        continue
                    frame[max(r0, 0):r0 + sy, max(c0, 0):c0 + sx] = color
        c += 3 * sx + gap
    return frame


# --------------------------------------------------------------------------------------
# Patterns.  Each is a factory: make(layout, cfg) -> render(t, dt) -> frame (ROWS, COLS, 3) floats 0..1
# --------------------------------------------------------------------------------------
PATTERNS = {}


def pattern(name, desc, key=None):
    def deco(fn):
        PATTERNS[name] = (fn, desc, key)
        return fn
    return deco


@pattern('identify', "Walk a single white pixel along the WHOLE chain (loops included) - checks wiring/order", 'i')
def p_identify(layout, cfg):
    speed = 20.0  # LEDs per second
    last = [-1]

    def render(t, dt):
        f = blank()
        idx = int(t * speed) % layout.n_leds
        if idx != last[0]:
            last[0] = idx
            rc = layout.led_to_rc[idx]
            where = f"row {rc[0]:2d} col {rc[1]}" if rc else "off-screen (loop)"
            print(f"\rLED {idx:3d}: {where}      ", end='', flush=True)
        rc = layout.led_to_rc[idx]
        if rc:
            f[rc] = (1, 1, 1)
        return f
    render.raw_index = lambda t: int(t * speed) % layout.n_leds
    return render


@pattern('columns', "Light each column in turn, left to right - checks the column mapping", 'c')
def p_columns(layout, cfg):
    def render(t, dt):
        f = blank()
        c = int(t / 0.6) % COLS
        f[:, c] = cfg.color
        f[0, c] = (1, 1, 1)        # top pixel white so you can see which way is up
        return f
    return render


@pattern('rows', "A bar sweeping top to bottom - checks the row alignment across columns", 'r')
def p_rows(layout, cfg):
    def render(t, dt):
        f = blank()
        r = int(t / 0.12) % ROWS
        f[r, :] = cfg.color
        f[max(r - 1, 0), :] = np.array(cfg.color) * 0.3
        return f
    return render


@pattern('hold', "A fixed still image (bars) - any flicker or shift you see is data corruption on the link", 'h')
def p_hold(layout, cfg):
    f = blank()
    f[::5, :] = (1, 1, 1)
    f[:, ::2] += np.array(cfg.color) * 0.5
    f = np.clip(f, 0, 1)

    def render(t, dt):
        return f
    return render


@pattern('checker', "Checkerboard that swaps every half second", 'k')
def p_checker(layout, cfg):
    def render(t, dt):
        f = blank()
        rows, cols = np.indices((ROWS, COLS))
        phase = int(t * 2) % 2
        m = ((rows // 4 + cols) % 2) == phase
        f[m] = cfg.color
        f[~m] = cfg.color2
        return f
    return render


@pattern('goal', "GOAL celebration: white flashes, then rings bursting from the centre with sparkles", 'g')
def p_goal(layout, cfg):
    period = 5.0
    sparks = np.zeros((ROWS, COLS))

    def render(t, dt):
        nonlocal sparks
        tt = t % period
        f = blank()
        if tt < 0.6:
            if int(tt / 0.1) % 2 == 0:
                f[:] = 1.0
            return f
        age = tt - 0.6
        # Solid expanding waves from the centre: every pixel inside the front is lit, alternating the two
        # colours in bands ~270 mm thick (4 columns / 8 rows) so it reads as a bold burst, not thin rings.
        speed, band = 900.0, 270.0
        phase = (age * speed - layout.D) / band          # >0 once the front has passed this pixel
        inside = phase > 0
        k = np.floor(phase).astype(int)
        col_a = np.asarray(cfg.color)[None, None, :]
        col_b = np.asarray(cfg.color2)[None, None, :]
        f = np.where((k % 2 == 0)[..., None], col_a, col_b) * inside[..., None]
        # bright white leading edge on each band
        edge = np.clip(1 - (phase % 1.0) / 0.25, 0, 1) * inside
        paint(f, edge * 0.9, (1, 1, 1))
        # sparkles on top
        sparks *= math.exp(-dt * 6)
        if age < 3.5:
            for _ in range(3):
                r, c = random.choice(layout.live_rc)
                sparks[r, c] = 1.0
        paint(f, sparks, (1, 1, 1))
        if age > 3.5:
            f = f * max(0.0, 1 - (age - 3.5) / 0.9)
        return np.clip(f, 0, 1)
    return render


@pattern('target', "Bullseye target in the centre, breathing - a 'hit this' zone", 't')
def p_target(layout, cfg):
    def render(t, dt):
        f = blank()
        pulse = 1 + 0.08 * math.sin(t * 3)
        step = layout.cx / 4.2                      # four rings that just fit the width
        for k in range(1, 5):
            w = ring(layout, layout.cx, layout.cy, k * step * pulse, step * 0.42)
            paint(f, w, (1, 0.05, 0.05) if k % 2 == 1 else (1, 1, 1))
        paint(f, disc(layout, layout.cx, layout.cy, step * 0.5 * pulse, 15), (1, 0.05, 0.05))
        return f
    return render


@pattern('ripple', "Ripples spreading from a random 'ball impact' point every 1.5 s", 'p')
def p_ripple(layout, cfg):
    hits = []   # (x, y, t0, color)

    def render(t, dt):
        f = blank()
        if not hits or t - hits[-1][2] > 1.5:
            x = random.uniform(0, layout.width_mm)
            y = random.uniform(0, layout.height_mm)
            hits.append((x, y, t, hsv(random.random())))
            del hits[:-4]
        for (x, y, t0, col) in hits:
            age = t - t0
            r = age * 300
            paint(f, ring(layout, x, y, r, 45) * max(0, 1 - age / 2.0), col)
            paint(f, disc(layout, x, y, 40, 20) * max(0, 1 - age * 2), (1, 1, 1))
        return f
    return render


@pattern('bounce', "A ball bouncing around the screen with a trail (proper round ball despite the odd pixels)", 'b')
def p_bounce(layout, cfg):
    pos = [layout.cx, layout.cy]
    vel = [220.0, 170.0]
    trail = blank()

    def render(t, dt):
        nonlocal trail
        for i, lim in enumerate((layout.width_mm, layout.height_mm)):
            pos[i] += vel[i] * dt
            if pos[i] < 0 or pos[i] > lim:
                vel[i] = -vel[i]
                pos[i] = min(max(pos[i], 0), lim)
        trail *= math.exp(-dt * 4)
        f = trail.copy()
        paint(f, disc(layout, pos[0], pos[1], 90, 30), cfg.color)
        trail = f.copy()
        paint(f, disc(layout, pos[0], pos[1], 35, 20), (1, 1, 1))
        return f
    return render


@pattern('rainbow', "Diagonal rainbow wave scrolling across the board", 'w')
def p_rainbow(layout, cfg):
    def render(t, dt):
        h = (layout.X + layout.Y * 0.6) / 700.0 - t * 0.25
        return hsv(h)
    return render


@pattern('fire', "Fire rising from the bottom of the goal", 'f')
def p_fire(layout, cfg):
    heat = np.zeros((ROWS, COLS))

    def render(t, dt):
        nonlocal heat
        # each row takes most of its heat from the row below, with a little sideways spread
        new = np.zeros_like(heat)
        new[:-1] = heat[1:] * 0.86 + (np.roll(heat[1:], 1, axis=1) + np.roll(heat[1:], -1, axis=1)) * 0.05
        new[-1] = np.clip(np.random.rand(COLS) * 1.4 + 0.3, 0, 1)
        heat = np.clip(new, 0, 1)
        f = blank()
        h = heat
        f[..., 0] = np.clip(h * 3, 0, 1)
        f[..., 1] = np.clip(h * 3 - 1, 0, 1) * 0.6
        f[..., 2] = np.clip(h * 3 - 2.2, 0, 1) * 0.5
        return f
    return render


@pattern('rain', "Drops falling down each gutter with a fading tail", 'n')
def p_rain(layout, cfg):
    drops = []  # [col, y_row(float), speed, hue]
    buf = blank()

    def render(t, dt):
        nonlocal buf
        buf *= math.exp(-dt * 5)
        if random.random() < dt * 6:
            drops.append([random.randrange(COLS), -1.0, random.uniform(25, 45), random.random()])
        for d in drops[:]:
            d[1] += d[2] * dt
            r = int(d[1])
            if r >= ROWS:
                drops.remove(d)
                continue
            if r >= 0:
                buf[r, d[0]] = hsv(d[3])
        f = buf.copy()
        for d in drops:
            r = int(d[1])
            if 0 <= r < ROWS:
                f[r, d[0]] = (1, 1, 1)
        return f
    return render


@pattern('confetti', "Multicoloured sparkles popping and fading - a gentle celebration / idle mode", 'o')
def p_confetti(layout, cfg):
    buf = blank()

    def render(t, dt):
        nonlocal buf
        buf *= math.exp(-dt * 2.5)
        for _ in range(2):
            if random.random() < 0.8:
                r, c = random.choice(layout.live_rc)
                buf[r, c] = hsv(random.random())
        return buf.copy()
    return render


@pattern('pulse', "Whole screen breathing slowly in the team colour - idle / attract mode", 'u')
def p_pulse(layout, cfg):
    def render(t, dt):
        f = blank()
        v = 0.15 + 0.85 * (0.5 + 0.5 * math.sin(t * 1.6)) ** 2
        f[:] = np.array(cfg.color) * v
        return f
    return render


@pattern('scanner', "Horizontal bar bouncing up and down, then a vertical bar left to right", 's')
def p_scanner(layout, cfg):
    def render(t, dt):
        f = blank()
        tt = t % 8
        if tt < 4:
            y = layout.cy + layout.cy * math.sin(tt * 2.2)
            w = np.clip(1 - np.abs(layout.Y - y) / 45.0, 0, 1)
        else:
            x = layout.cx + layout.cx * math.sin((tt - 4) * 2.2)
            w = np.clip(1 - np.abs(layout.X - x) / 70.0, 0, 1)
        paint(f, w, cfg.color)
        return f
    return render


@pattern('spiral', "Rotating pinwheel around the centre", 'l')
def p_spiral(layout, cfg):
    ang = np.arctan2(layout.Y - layout.cy, layout.X - layout.cx)
    d = layout.dist_from(layout.cx, layout.cy)

    def render(t, dt):
        h = (ang / (2 * math.pi) * 3 + d / 400.0 - t * 0.6)
        v = 0.5 + 0.5 * np.cos(h * 2 * math.pi)
        return hsv(h / 3 + t * 0.1, 1.0, 1.0) * v[..., None]
    return render


@pattern('countdown', "3 - 2 - 1 - GO, then the goal celebration", 'd')
def p_countdown(layout, cfg):
    goal = p_goal(layout, cfg)

    def render(t, dt):
        tt = t % 10.0
        f = blank()
        if tt < 3:
            digit = str(3 - int(tt))
            frac = tt % 1.0
            v = 1.0 if frac < 0.6 else max(0.0, 1 - (frac - 0.6) / 0.4)
            draw_text(f, digit, np.array(cfg.color) * v, sx=BIG_SX, sy=BIG_SY)
        elif tt < 4.5:
            draw_text(f, "GO", np.array((0.1, 1.0, 0.1)) * (1 if int(tt * 6) % 2 else 0.3), sx=1, sy=SMALL_SY)
        else:
            f = goal(tt - 4.5, dt)
        return f
    return render


# glyph scales: a 3x5 glyph at (sx, sy) cells covers 3*sx columns x 5*sy rows.
# With 67 mm columns and 33 mm rows, sx=2/sy=4 gives a ~400 x 670 mm digit (looks about right);
# sx=1/sy=3 gives ~130 x 500 mm digits - narrow, but two of them fit in 7 columns.
BIG_SX, BIG_SY = 2, 4
SMALL_SY = 3


@pattern('score', "Show a 1- or 2-digit score (set with --score N), flashing briefly first", 'e')
def p_score(layout, cfg):
    text = str(cfg.score)[-2:]

    def render(t, dt):
        f = blank()
        v = (1 if int(t * 8) % 2 else 0.2) if t < 1.0 else 1.0
        if len(text) == 1:
            draw_text(f, text, np.array(cfg.color) * v, sx=BIG_SX, sy=BIG_SY)
        else:
            draw_text(f, text, np.array(cfg.color) * v, sx=1, sy=SMALL_SY)
        return f
    return render


@pattern('text', "Scroll a word across the board, e.g. --text KICK (one column step at a time)", 'x')
def p_text(layout, cfg):
    word = cfg.text.upper()
    sx, sy = (1, 4) if COLS < 10 else (2, 4)
    width = text_width(word, sx)
    cols_per_sec = 3.0

    def render(t, dt):
        f = blank()
        col0 = COLS - int(t * cols_per_sec) % (width + COLS)
        draw_text(f, word, cfg.color, sx=sx, sy=sy, col0=col0)
        return f
    return render


@pattern('kick', "Attract loop: KICK scrolls past, then the target breathes (in live mode hit g for the GOAL)", 'a')
def p_kick(layout, cfg):
    target = p_target(layout, cfg)
    word = p_text(layout, cfg)

    def render(t, dt):
        tt = t % 9.0
        if tt < 4.0:
            return word(tt, dt)
        return target(tt - 4.0, dt)
    return render


@pattern('demo', "Cycle through all the patterns, ~8 s each")
def p_demo(layout, cfg):
    names = [n for n in PATTERNS if n not in ('demo', 'identify')]
    state = {'i': -1, 'render': None, 't0': 0}
    per = 8.0

    def render(t, dt):
        i = int(t / per) % len(names)
        if i != state['i']:
            state['i'] = i
            state['t0'] = t
            state['render'] = PATTERNS[names[i]][0](layout, cfg)
            print(f"\r  demo -> {names[i]:<12}", end='', flush=True)
        return state['render'](t - state['t0'], dt)
    return render


# --------------------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------------------
class Cfg:
    pass


def parse_color(s):
    parts = [float(p) for p in s.split(',')]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("colour must be R,G,B (0-255)")
    return tuple(p / 255.0 for p in parts)


class KeyReader:
    """Non-blocking single-key reader for 'live' mode (macOS / Linux terminal)."""

    def __enter__(self):
        import termios
        import tty
        self.fd = sys.stdin.fileno()
        self.old = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        return self

    def __exit__(self, *a):
        import termios
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)

    def get(self):
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None


def run(args):
    layout = Layout(args.layout)
    layout.describe()

    cfg = Cfg()
    cfg.color = args.color
    cfg.color2 = args.color2
    cfg.score = args.score
    cfg.text = args.text

    target = args.target
    if target == 'usb' or target.startswith('/dev/'):
        sender = SerialSender(None if target == 'usb' else target, args.baud, args.boot_baud, args.blind)
        link_fps = sender.max_fps(layout.n_leds)
        if args.fps > link_fps * 0.9:
            args.fps = link_fps * 0.9           # never generate faster than the wire can carry
        print(f"sending Adalight over {sender.port} @ {sender.baud} baud "
              f"(link carries ~{link_fps:.0f} fps, running at {args.fps:.0f})")
    elif target in ('none', 'preview'):
        sender = NullSender()
        if not args.preview:
            print("no hardware target: running blind (add --preview to see it)")
    else:
        sender = DDPSender(target, args.port)
        print(f"sending DDP to {target}:{args.port}")

    preview = Preview(layout) if args.preview else None

    live = args.pattern == 'live'
    name = 'pulse' if live else args.pattern
    render = PATTERNS[name][0](layout, cfg)
    keymap = {key: n for n, (_, _, key) in PATTERNS.items() if key}
    if live:
        print("live mode keys:  " + "  ".join(f"{k}={n}" for k, n in keymap.items()) + "   q=quit")

    frame_time = 1.0 / args.fps
    t0 = time.monotonic()
    last = t0
    keys = KeyReader() if live else None
    try:
        if keys:
            keys.__enter__()
        while True:
            now = time.monotonic()
            dt = now - last
            last = now
            if keys:
                k = keys.get()
                if k == 'q':
                    break
                if k in keymap:
                    name = keymap[k]
                    render = PATTERNS[name][0](layout, cfg)
                    t0 = now
                    print(f"\r  -> {name:<12}", end='', flush=True)
            frame = render(now - t0, dt)
            sender.send(layout.frame_to_bytes(frame, args.brightness, gamma=not args.no_gamma))
            if preview:
                preview.show(frame, args.brightness)
                if not preview.alive:
                    break
            if args.duration and now - t0 > args.duration:
                break
            sleep = frame_time - (time.monotonic() - now)
            if sleep > 0:
                time.sleep(sleep)
    except KeyboardInterrupt:
        pass
    finally:
        if keys:
            keys.__exit__(None, None, None)
        # blank the strip on exit
        try:
            sender.send(bytes(layout.n_leds * 3))
        except Exception:
            pass
        sender.close()
        print("\ndone")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target', nargs='?', default='none',
                    help="usb | /dev/cu.usbserial-XXXX | <WLED ip or hostname> | none   (or 'list')")
    ap.add_argument('pattern', nargs='?', default='demo', help="pattern name, 'demo', 'live', or 'probe' (serial diagnostics)")
    ap.add_argument('--layout', choices=sorted(LAYOUTS), default='board', help="board (default) or panel")
    ap.add_argument('--port', type=int, default=4048, help="DDP UDP port")
    ap.add_argument('--baud', type=int, default=230400,
                    help="serial baud to run at (default %(default)s, ~25 fps); WLED is switched to it over the cable. "
                         "460800 (~50 fps) may work; 921600 does not with the CH340 + macOS driver")
    ap.add_argument('--boot-baud', type=int, default=115200,
                    help="baud WLED starts at = Config -> Sync Interfaces -> Serial (default %(default)s)")
    ap.add_argument('--blind', action='store_true',
                    help="switch baud without waiting for WLED to acknowledge (for firmware that never talks back)")
    ap.add_argument('--preview', action='store_true', help="show a tkinter preview window")
    ap.add_argument('--brightness', type=float, default=DEFAULT_BRIGHTNESS, help="0..1 (default %(default)s)")
    ap.add_argument('--fps', type=float, default=FPS)
    ap.add_argument('--color', type=parse_color, default=(1.0, 0.45, 0.0), help="team colour R,G,B 0-255")
    ap.add_argument('--color2', type=parse_color, default=(0.0, 0.4, 1.0), help="second colour R,G,B 0-255")
    ap.add_argument('--score', type=int, default=7)
    ap.add_argument('--text', default='KICK', help="word for the text / kick patterns")
    ap.add_argument('--duration', type=float, default=0, help="stop after N seconds (0 = run until Ctrl-C)")
    ap.add_argument('--no-gamma', action='store_true')
    args = ap.parse_args()

    if args.pattern == 'probe':
        SerialSender.probe(None if args.target == 'usb' else args.target, args.boot_baud)
        return
    if args.target == 'list' or args.pattern == 'list':
        for n, (_, d, k) in PATTERNS.items():
            print(f"  {n:<10} {('[' + k + ']') if k else '   ':5} {d}")
        print("  live        keyboard-driven: press the bracketed key to switch, g for GOAL, q to quit")
        return
    if args.pattern != 'live' and args.pattern not in PATTERNS:
        sys.exit(f"unknown pattern '{args.pattern}' - try: python3 goal_patterns.py list")
    run(args)


if __name__ == '__main__':
    main()
