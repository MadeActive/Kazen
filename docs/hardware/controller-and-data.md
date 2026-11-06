# Controller, data and the serial/Wi-Fi link

Reference. Facts established on the bench 2–4 Nov 2026 (`docs/log/2026-11-03-hardware-bringup-notes.md`) plus the architecture from the Sept summary.

## Bench controller: BTF SP805E (ESP32, WLED build 2508020)
- 5–24 V in, 12 A through the controller max, barrel socket 4 A max. 2 SPI outputs, 2,048 px ceiling. mDNS `wled-c085e8`.
- Left terminals: VCC, GND, GND, IO33 + barrel. Right: GND, GND, DATA2 (GPIO 2), DATA1 (GPIO 16), PWM, 3× VCC.
- USB-C (CH340) → Mac as `/dev/cu.usbserial-3130`, Apple's built-in driver.
- WLED: WS281x, GPIO 16, GRB, 300 LEDs (gotcha: default length 30 and the segment stop must both be changed). Brightness limiter 2000 mA. AudioReactive usermod on.
- Not the product controller: Wi-Fi only, 2,048 px, jittery latency.

## Wiring (working)
Strip red → VCC, white → GND, blue (BI) → GND, green → DATA1 (GPIO 16). Strip 2 chained off strip 1. No amplifier needed (WS2815 regenerates data at every LED; runs < 0.5 m). 33–100 Ω series resistor on each data line at the controller; data run as a pair with ground, away from the 12 V bus; BI of the first LED tied to ground.

## USB serial (Adalight) — what we know
- Liveness: WLED answers `v` with its version and `{"v":true}` with JSON on the same port.
- Baud change on one byte: 0xB0=115200, 0xB1=230400, 0xB2=460800, 0xB3=500000, 0xB4=576000, 0xB5=921600, 0xB6=1M, 0xB7=1.5M. Replies `Baud is now N` *before* switching. Not persisted — **but this board does not reset on port open, so it keeps the last baud across runs.** Always return it to 115200 on exit, or scan rates on start (`goal_patterns.py` does both).
- **921600 is dead from the Mac** (CH340 + macOS driver): nothing passes either way, power-cycle to recover. **230400 works (~25 fps / 300 LEDs).** 460800 untested.
- Never send at a rate the controller isn't confirmed on: garbage bytes 0xB0–0xB7 will re-baud it to something unknown.
- Mac-side backlog causes visible "jumps": generate frames no faster than the link carries and `flush()` each one.

## Wi-Fi — unresolved
Joined "Triangle" at 192.168.1.116; Mac at .114 can't ping it. To try: router AP/client isolation off, untick "Enable ESP-NOW" in WLED Wi-Fi settings, DHCP-reserve .116. Unblocks the web UI and DDP at 30+ fps without a USB tether.

## Frame rates and splitting
- 300 LEDs at 230400 ≈ 25 fps. Full goal 1,404 LEDs on one output ≈ 24 fps; split across DATA1/DATA2 (~700 each) ≈ 45 fps.

## Product architecture (from Sept summary, still the plan)
- **Per panel:** Teensy 4.1 + Ethernet, 4 data outputs (3–4 columns each) via 74HCT245 level shifter, also reads that panel's piezos. Alternative: Falcon F16v5 / Advatek PixLite (US$200–300).
- **Per goal:** one brain box (Pi 5 8 GB in a vented IP65 box, small PoE switch, optional AI HAT+) streaming frames to panels by DDP or sACN. Content tools for testing: WLED 2D, xLights with a 71 × 33 mm model.
- Data snakes bottom→top, jumper across the top batten under a removable top rail, top→bottom. Chain 3–4 columns per output; each column gets its own power feed. Ask the fence supplier for a removable top rail / 20 mm service gap and a flat channel floor.

## Scripts (`Prototypes/v0.1_LedTestBoard/`)
- `ddp_test.py usb|<ip> <chase|marks|pixel N|kick|fps>` — first bring-up script.
- `goal_patterns.py <usb|ip|none> <pattern> [--layout board|panel] [--baud 230400] [--preview]` — mm-coordinate renderer. `list` prints patterns; `live` switches by key (g goal, t target, a attract, d countdown, b bounce, l spiral, w rainbow, q quit); `probe` = serial diagnostics; `identify` walks one pixel along the chain to verify mapping. Needs numpy + pyserial.
