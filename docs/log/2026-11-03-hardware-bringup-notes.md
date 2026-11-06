# Interactive LED Goal — hardware bring-up notes

Spec lives in the repo at `docs/product/ux-spec.md`. Scripts in `Prototypes/v0.1_LedTestBoard/`.

## Target geometry (from spec)
- One slatted panel = 13 columns × 36 rows = 468 LEDs, 1.2 m vertical channels, 33 mm LED pitch, 71 mm column pitch.
- Full goal = 3 panels = 39 × 36 = 1,404 LEDs.
- Pixels are non-square (71 mm across × 33 mm down); every renderer must correct for this.

## Hardware
- Controller: BTF-Lighting SP805E (ESP32, WLED build **2508020**). 5–24 V, 12 A through the controller, barrel socket 4 A max. USB-C shows as `/dev/cu.usbserial-3130` (CH340 chip, Apple's built-in driver). mDNS `wled-c085e8`.
  - Left: VCC, GND, GND, IO33 + barrel. Right: GND, GND, DATA2 (GPIO 2), DATA1 (GPIO 16), PWM, 3× VCC.
- LEDs: 2× BTF WS2815 12 V, 5 m, 30 LEDs/m (150 each, 300 total, chained). Red +12 V, white GND, green data, blue backup data.
- Power now: 30 W 12 V plug pack via barrel. Later: 400 W 12 V (33 A) screw-terminal supply — needs a licensed electrician in AU to fit the mains lead.

## Wiring (working)
Strip red → VCC, white → GND, blue → GND, green → DATA1 (GPIO 16). Strip 2 chained off strip 1.

## WLED settings
WS281x, GPIO 16, GRB. Brightness limiter 2000 mA. Segment currently reads 330 LEDs — tidy to 300. (Gotcha: default length is 30 and the segment stop must also be changed.) AudioReactive usermod is on.

## Wi-Fi — unresolved
Joined "Triangle" at 192.168.1.116 but Mac (192.168.1.114) can't ping it. To try: disable router AP/client isolation, untick "Enable ESP-NOW" in WLED WiFi settings, reserve .116. Fixing this also unlocks the web UI and DDP at 30+ fps with no USB tether.

## USB serial link — what we learned (3 Nov 2026)
- WLED answers `v` with its version and `{"v":true}` with JSON over the same cable; useful as a liveness check.
- WLED changes baud on a single byte: 0xB0=115200, 0xB1=230400, 0xB2=460800, 0xB3=500000, 0xB4=576000, 0xB5=921600, 0xB6=1M, 0xB7=1.5M. It replies `Baud is now N` *before* switching. Not persisted — but
- **this board does not reset when the USB port is opened**, so it keeps the last baud across runs. Always put it back to 115200 on exit, or scan rates on start-up (goal_patterns.py does both).
- **921600 does not work from the Mac** (CH340 + macOS driver): the controller switches but nothing gets through either way after that, and only a power-cycle recovers it. 230400 works (~25 fps for 300 LEDs); 460800 untested.
- Never send data at a rate the controller isn't confirmed to be on: WLED reads the garbage and random 0xB0–0xB7 bytes re-baud it to something unknown.
- Mac-side backlog causes "jumps": generate frames no faster than the link carries and `flush()` each one.

## Control from code
- `ddp_test.py usb <chase|marks|pixel N|kick|fps>` — original bring-up script.
- `goal_patterns.py usb <pattern>` — grid renderer in mm coordinates (circles stay round). `usb live` switches patterns by key (g goal, t target, a KICK attract loop, d countdown, b bounce, l spiral, w rainbow, q quit). `usb probe` = serial diagnostics. `--layout panel` for the real 13×36 column. Default `--baud 230400`, auto-negotiated and handed back on exit.

## Test board (Nov 2026) — mapping confirmed
Uncut 300-LED chain on a ~1.2 m × 0.5 m board: 27 mm gutters, 40 mm battens (67 mm column pitch). 8 columns × 34 rows between the marked lines; loops of 7 LEDs top and bottom are off-screen.
Chain: 1 lead-in, then runs of 34/34/34/26/34/34/34/20 (up, down, up, down…) with 7-LED loops between. The 26 on column 4 is the two-strip joiner (dead gap at the bottom, LED 150); column 8 ends after 20. Total 300. Encoded in `LAYOUTS['board']`. Verified with the `hold` pattern: bars line up across all columns.

## Pattern feedback at full size
- Read well: bounce, spiral, rainbow (anything that lights every pixel).
- Thin rings (first goal version) looked sparse at 67 mm column pitch; goal rebuilt as solid expanding colour bands ~270 mm thick with a white leading edge.
- Daytime visibility is marginal at brightness 0.3 on the 30 W supply; revisit with the 400 W supply.

## Power and scaling
- ~30 W (2.5 A) per 5 m strip at full white. 400 W supply ≈ 10 strips / 1,500 LEDs ≈ full goal (~280 W).
- Inject power every ~5 m straight from the supply, not via the controller.
- Full goal: split across DATA1/DATA2 (~700 each) → ~45 fps instead of 24. Controller max 2,048 LEDs.

## Next
1. Fix Wi-Fi (router isolation / ESP-NOW / reserve .116) → DDP over Wi-Fi, web UI access.
2. Decide the celebration / attract / hit-feedback behaviours against the spec and refine those patterns.
3. Cut strips and build the first real 13×36 panel; switch to `--layout panel`.
