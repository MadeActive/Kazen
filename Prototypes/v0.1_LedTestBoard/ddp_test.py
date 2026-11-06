#!/usr/bin/env python3
"""
Drive a WLED controller pixel-by-pixel from your laptop, over DDP (UDP port 4048).

No installs needed: plain Python 3. Your laptop must be on the same Wi-Fi as the
controller (either your home network, or join WLED-AP and use 4.3.2.1).

Over USB instead of Wi-Fi (needs: pip3 install pyserial):
  python3 ddp_test.py usb chase                 # finds the controller's USB port itself
  python3 ddp_test.py /dev/cu.usbserial-110 chase --baud 115200

Usage:
  python3 ddp_test.py <wled-ip> chase           # one dot runs the full length
  python3 ddp_test.py <wled-ip> marks           # white every 10 LEDs, red every metre (30)
  python3 ddp_test.py <wled-ip> pixel 149       # light just LED #149 (0-based)
  python3 ddp_test.py <wled-ip> kick            # press Enter = a "ball impact" burst
  python3 ddp_test.py <wled-ip> fps             # how fast can we push frames?

Options:
  --leds 300         number of LEDs (default 300 = two 5 m strips)
  --bright 0.3       0..1 brightness scale applied in this script (default 0.3)

While this script is sending, WLED switches into "realtime" mode and ignores its own
effects. Stop the script (Ctrl+C) and WLED goes back to normal after ~2.5 seconds.
"""
import argparse, random, socket, sys, time, threading

PORT = 4048
MAX_PAYLOAD = 480 * 3   # 480 RGB pixels per UDP packet


class DDP:
    def __init__(self, host, n):
        self.addr = (host, PORT)
        self.n = n
        self.seq = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, frame: bytes):
        """frame = n*3 bytes of R,G,B."""
        self.seq = (self.seq % 15) + 1
        for off in range(0, len(frame), MAX_PAYLOAD):
            chunk = frame[off:off + MAX_PAYLOAD]
            last = off + MAX_PAYLOAD >= len(frame)
            flags = 0x41 if last else 0x40          # v1, PUSH on the last packet only
            header = bytes([flags, self.seq, 0x01, 0x01]) + off.to_bytes(4, "big") + len(chunk).to_bytes(2, "big")
            self.sock.sendto(header + chunk, self.addr)


class Serial:
    """WLED's built-in Adalight receiver over the USB cable."""
    def __init__(self, port, n, baud):
        try:
            import serial, serial.tools.list_ports
        except ImportError:
            sys.exit("USB mode needs pyserial. Run:  pip3 install pyserial")
        if port == "usb":
            ports = [p.device for p in serial.tools.list_ports.comports()
                     if any(k in (p.device + str(p.description)).lower()
                            for k in ("usbserial", "wchusb", "ch34", "cp210", "usbmodem", "slab"))]
            if not ports:
                sys.exit("No USB serial port found. Is the cable plugged into the controller's bottom port? "
                         "Run  ls /dev/cu.*  to see what's there.")
            port = ports[0]
            print(f"Using {port}")
        self.ser = serial.Serial(port, baud, write_timeout=2)
        time.sleep(2)                       # opening the port can reboot the ESP32; let it start
        cnt = n - 1
        hi, lo = cnt >> 8, cnt & 0xFF
        self.header = b"Ada" + bytes([hi, lo, hi ^ lo ^ 0x55])
        self.min_gap = (len(self.header) + n * 3) * 10 / baud   # don't outrun the cable
        self.last = 0.0

    def send(self, frame: bytes):
        wait = self.min_gap - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        self.ser.write(self.header + frame)
        self.last = time.time()


def connect(target, n, baud):
    if target == "usb" or target.startswith("/dev/") or target.upper().startswith("COM"):
        return Serial(target, n, baud)
    return DDP(target, n)


def blank(n):
    return [(0, 0, 0)] * n


def pack(pixels, bright):
    out = bytearray()
    for r, g, b in pixels:
        out += bytes((int(r * bright), int(g * bright), int(b * bright)))
    return bytes(out)


def run(args):
    d = connect(args.ip, args.leds, args.baud)
    n, br = args.leds, args.bright
    fps = 40

    if args.mode == "chase":
        i = 0
        while True:
            px = blank(n)
            for t in range(6):                                   # little fading tail
                if i - t >= 0:
                    px[i - t] = (0, int(255 * (1 - t / 6)), int(120 * (1 - t / 6)))
            d.send(pack(px, br))
            i = (i + 1) % n
            time.sleep(1 / fps)

    elif args.mode == "marks":
        px = blank(n)
        for i in range(n):
            if i % 30 == 0:
                px[i] = (255, 0, 0)       # every metre (30 LEDs/m)
            elif i % 10 == 0:
                px[i] = (255, 255, 255)   # every 10 LEDs
        px[n - 1] = (0, 0, 255)           # last LED = blue
        while True:
            d.send(pack(px, br)); time.sleep(0.5)

    elif args.mode == "pixel":
        px = blank(n)
        px[args.index] = (255, 255, 255)
        print(f"Lighting LED #{args.index}. Ctrl+C to stop.")
        while True:
            d.send(pack(px, br)); time.sleep(0.5)

    elif args.mode == "kick":
        hits = []                                                 # (centre, start_time)
        def listen():
            print("Press Enter to 'kick' (Ctrl+C to quit)")
            for _ in sys.stdin:
                hits.append((random.randrange(n), time.time()))
        threading.Thread(target=listen, daemon=True).start()
        while True:
            now = time.time()
            px = [[0, 0, 0] for _ in range(n)]
            for c, t0 in list(hits):
                age = now - t0
                if age > 1.2:
                    hits.remove((c, t0)); continue
                radius = age * 60                                # LEDs per second
                fade = 1 - age / 1.2
                for i in range(n):
                    dist = abs(i - c)
                    if dist < 2 and age < 0.15:                  # bright flash at impact
                        px[i] = [255, 255, 255]
                    elif abs(dist - radius) < 2:                 # expanding ring
                        v = int(255 * fade)
                        px[i] = [max(px[i][0], v), max(px[i][1], int(v * 0.6)), px[i][2]]
            d.send(pack(px, br))
            time.sleep(1 / fps)

    elif args.mode == "fps":
        frames, t0 = 0, time.time()
        while time.time() - t0 < 5:
            v = frames % 256
            d.send(pack([(v, 0, 255 - v)] * n, br))
            frames += 1
            time.sleep(0.002)
        print(f"Sent {frames / 5:.0f} frames/s from this laptop. "
              f"(Over USB at {args.baud} baud the cable allows ~{args.baud / 10 / (6 + n * 3):.0f} fps. "
              f"The strip itself tops out around {1_000_000 / (n * 30):.0f} fps for {n} LEDs on one data line.)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("ip", help="controller IP address, or 'usb'")
    p.add_argument("mode", choices=["chase", "marks", "pixel", "kick", "fps"])
    p.add_argument("index", nargs="?", type=int, default=0)
    p.add_argument("--leds", type=int, default=300)
    p.add_argument("--bright", type=float, default=0.3)
    p.add_argument("--baud", type=int, default=115200, help="USB speed; must match WLED's serial baud setting")
    a = p.parse_args()
    try:
        run(a)
    except KeyboardInterrupt:
        try:
            if not (a.ip == "usb" or a.ip.startswith("/dev/")):
                DDP(a.ip, a.leds).send(bytes(a.leds * 3))   # leave the strip dark
        except Exception:
            pass
        print("\nStopped.")
