> **SUPERSEDED — kept for history only (moved here 5 Nov 2026).**
> This Sept 2026 summary describes 1.8 m panels / 54 LEDs per column / 2,106 pixels / 630 W. The product moved to **1.2 m panels / 36 rows / 1,404 pixels** (see `docs/product/ux-spec.md` §2.1). The still-valid material (strip choice, power, control/data, brain box, manufacturing notes) has been carried into `docs/hardware/` with corrected numbers. Do not quote figures from this file.

# LED Goal Display — Project Reference

Summary of design decisions to date (Sept 2026). Prices are estimates from supplier listings at the time, not quotes.

---

## 1. Concept

An interactive, goal-shaped LED display mounted on a batten fence panel. Players kick a ball at it; sensors detect where it hits, a camera watches the player, and the display reacts. Target: prototype first, then manufacture ~100–200 units/year.

**Requirements settled:**
- Colour images/animation, sub-second response
- Survives repeated ball impacts and outdoor weather
- Attractive enough for a garden (no polycarbonate front, no bare LED cabinet)
- Cheap to manufacture in modules

---

## 2. Technology decisions (why LED, not colour-changing material)

Rejected in order:
- **Thermochromic + heater** — too slow at 50 cm+, needs continuous power
- **PDLC over black backing** — fast, but only white/dark-grey, fixed-colour reveal, no arbitrary images
- **Segmented colour e-paper (E Ink Prism 3 type)** — closest "material" option, 6 colours, bistable, cut-to-shape, but ~1 s switching, B2B only, not tough enough for wet/abrasive use
- **Flip-dot** — fast, coarse, mechanical, two fixed colours per dot
- **Stadium LED cabinets (P10/P16)** — cheap and bright but look like a screen; drilled metal plate over P10 fails (60% open area, ±20° viewing angle)
- **12 mm pixel nodes behind drilled plate** — works but ~3× the cost of strip and 9,600 push-fits

**Chosen:** individually addressable ("SPI") LED strip mounted in the channels of a batten fence panel, one strip per channel, behind a recessed frosted polycarbonate diffuser. Battens take the ball hits; strips never see the ball.

---

## 3. Panel geometry

**Fence panel:** 1.8 m × 0.9 m, seamless batten design, 27 mm channels + 44 mm battens → **71 mm pitch**, effectively **13 channels per panel** when joined.

**Layout chosen:** channels vertical, **3 panels side by side → 2.7 m wide × 1.8 m tall**.

| Item | Value |
|---|---|
| Columns | 39 (13 per panel) |
| LEDs per column | 54 (30 LEDs/m × 1.8 m) |
| Total pixels | 2,106 (702 per panel) |
| Pixel spacing | 71 mm horizontal × 33 mm vertical (non-square — set in mapping software; or address every 2nd LED for a square 39 × 27 grid) |
| Strip needed | 70 m total (21.6 m per panel); order 16 rolls of 5 m |
| Peak power (full white) | ~630 W (210 W per panel) |
| Realistic average | 200–250 W |

**Mounting in channel:**
- 10 mm strip centred on channel floor (8.5 mm clearance each side), 3M tape + silicone bead every 300 mm
- 3 mm frosted polycarbonate strip cut to ~26 mm, seated 5 mm below batten face, stopped 10 mm short of bottom rail so channels drain
- Vertical channels self-drain; open channel foot
- Strain-relieve every solder joint (cable tie/clip within 30 mm); heat-shrink + neutral-cure silicone over joints

**Seam handling:** decide which panel owns a shared edge column so each panel stays at 13 columns and mapping is identical per module.

---

## 4. LED strip spec

**Chosen product:** BTF-LIGHTING WS2815 RGB, DC12V
https://www.btf-lighting.com/products/ws2815-rgb-addressable-led-strip-dc12v

- Select: **30 LEDs/m, Black PCB, IP65, 5 m rolls**
- WS2815 = one IC per LED (true per-pixel), dual data line (one dead LED doesn't kill the row), 12 V
- IP65 = silicone coating, 10 × 3 mm, adhesive backing retained. (IP67 sleeve is 12 mm wide, no adhesive.)
- Colour order is **GRB** — set once in controller
- Cuttable every LED

**Why 12 V:** 5 V drops too much over 1.8–2 m rows and needs bus-bar-level current; 24 V per-LED addressable is rare and usually groups 3–6 LEDs per pixel.

**RGBNW option (parked):** natural-white 4th die was wanted. Only stock per-LED 12 V RGBW at 30/m found: SuperLightingLED 12V SK6812 30/m, model SK6812-RGBW-30IA-12V (10 mm, options for RGB+NW 4000K, black PCB, IP65) — https://www.superlightingled.com/12v-sk6812-150-pixels-individually-controlled-rgbw-led-strip-p-5981.html . BTF's 12V SK6812 is 60/m, white PCB only, and was out of stock. **Note: 12 V WS2814 is one IC per 3 LEDs — not per-pixel.** Decided to go RGB (WS2815) for now; RGB white is fine at 5–20 m viewing.

**Strip glossary:**
- PWM SMD = analogue, whole strip one colour — not usable
- SPI SMD = addressable, chip per LED — what we use
- FCOB/COB = continuous chip-on-board line, addressable only in segments — not usable
- RGBWW / RGBNW / RGBCW = 4th white die at warm (~2700–3000K) / natural (~4000K) / cool (~6000–6500K)

**IP ratings:** IP65 = dust-tight + hose jet; IP67 = 1 m immersion 30 min; IP68 = potted. Ratings say nothing about impact/shock — mounting does that.

---

## 5. Power

**Per-panel supply (self-sufficient panels):** BTF 12 V IP65 rain-proof supply, **400 W** version, one per panel
https://www.btf-lighting.com/collections/12v-power-supply/products/ac180v-240v-to-dc12v-24v-ip65-rain-proof-power-supply-transformer-adapter-for-led-strip-lights-60w-100w-400w-600w
- 180–240 V input (suits AU mains), fanless, sealed, no UL listing on page; derate to ~75% outdoors
- Each panel is 210 W peak → supply at ~50% load
- Alternative (boxed, UL): BTF Aluminium Case UL Recognised 12 V 350 W — https://www.btf-lighting.com/collections/12v-power-supply/products/aluminum-power-supply-ul-listed
- Rejected: Mean Well HLG-600H-12 (~AU$400, overkill); generic uncertified silver-box supplies

**Brightness cap:** set a power limit in software (WLED/xLights have it). ~55% brightness keeps full display under 350 W with no visible loss at 5–20 m.

**Mounting rain-proof supplies:** under bottom rail or behind panel, terminals down, drip loops on all cables, silicone over mains terminal boot, 50 mm air gap around fins. Mains from an RCD-protected outdoor socket. Keep 230 V entirely at the supply; only 12 V / 5 V leaves.

**Distribution per panel:** fused block, one 5 A blade fuse per group of 4 columns + one for electronics; 12 V → 5 V buck (5 A) for controller/Pi. Feed strips from the distribution block, **never through the controller's terminals**.

**Mains to 3 panels:** one RCD feed → IP66 junction box on fence post → 3 fused outputs on IP68 quick-connect cables.

---

## 6. Control & data

**Signal amplifier: not needed.** WS2815 regenerates data at every LED; controller-to-first-LED runs are 0.2–0.5 m, top jumpers < 100 mm. Amplifiers only matter past 3–5 m of cable.

**Do need:**
- Level shifter (74HCT245 / SN74AHCT125) if driving from a 3.3 V Teensy; SP805E, Falcon, Advatek have it built in
- 33–100 Ω series resistor on each data line at controller end
- Data run as a pair with ground (BTF 4-pin cable), kept away from 12 V bus
- WS2815 backup data input (BI) of first LED in each chain tied to ground

**Wiring plan per panel:** data snakes bottom→top, jumper across top batten (under removable top rail), top→bottom, etc. Chain 3–4 columns per output. Each column gets its own power feed from the bus.

**Test controller:** BTF **SP805E** (ESP32, WLED, 2 SPI outputs, 2,048 px max, ETL listed, WiFi) — for bench testing colour order, pixel counts, IP65 terminations, and 2D mapping. Not the final controller (WiFi only, 2,048 px ceiling, ~30 fps at that count, unstable latency). SP803E is the same with 1 SPI output.

**Final per-panel controller:** Teensy 4.1 + Ethernet adapter, 4 data outputs (3–4 columns each) via level shifter, also reads impact sensors. Alternative: Falcon F16v5 / Advatek PixLite 16 ($200–300) as a commercial Ethernet pixel controller.

**Software:** Pi streams frames to panels via DDP or sACN/E1.31 (keeps panels in sync). Content tools: xLights (define model with 71 × 33 mm spacing), Madrix, or WLED 2D matrix for testing.

---

## 7. Sensing & processing ("brain box")

**Architecture:** one central brain + self-sufficient panels.

**Brain box (one per goal, ~$300–350):**
- Raspberry Pi 5 (8 GB) in vented IP65 box
- Raspberry Pi AI HAT+ (Hailo) if player recognition / pose / which-foot is wanted
- **Raspberry Pi Global Shutter Camera** with ~6 mm wide lens, centre of crossbar looking out/down at the player. Global shutter avoids ball smear. IR illuminator for night.
- Small PoE-capable Ethernet switch
- Camera → reaction latency 20–40 ms

**ESP32-CAM rejected:** ~10–25 fps at 320×240, no compute headroom; a ball at 60 km/h moves 70 cm between frames at 25 fps.

**Impact location — not by camera** (crossbar camera sees the face edge-on). Use piezo sensors:
- **If battens sit on a rigid continuous base sheet (aluminium ideal):** 4 piezo discs in panel corners, time-difference-of-arrival, ±10 cm, sub-ms latency, ~$30/panel. Test on panel 1.
- **If battens are open-backed on rails:** one piezo top and bottom of each batten (26/panel). Which batten = column (71 mm); top/bottom timing = height (±10 cm). Read via multiplexers on the Teensy.
- Aluminium battens transmit a clean pulse; timber damps and is less precise.
- **Backup:** 4 corner microphones timing airborne impact sound, gated by piezo so shouting doesn't trigger.
- Seam hits fire two panels — brain takes stronger signal or averages.

**Per-panel electronics cost (excl. strip):** ~$40 supply, $50 Teensy + Ethernet, $15 sensors/shifter, $30 connectors/fusing ≈ **$135/panel**.

---

## 8. Goal frame & mounting

- Posts and crossbar as a separate white powder-coated steel/aluminium frame (~60 mm tube) around the panels: reads as a goal, hides panel edges, houses camera, and is the rigid structure that bolts to fence/wall
- Ball loads go through the frame to the posts, not through the display
- Ask fence supplier for: removable top rail or 20 mm service gap (data jumpers); flat continuous channel floor over 1.8 m (no mid-span bracing); how edge half-channels combine at seams

---

## 9. Shopping list (prototype, one panel)

From BTF-LIGHTING:
- WS2815 12V, 30 LEDs/m, black PCB, IP65 — 5 rolls (21.6 m needed; 16 rolls for all 3 panels)
- 12 V IP65 rain-proof supply, 400 W — 1
- 12 V → 5 V step-down module — 1
- SP805E WLED controller — 1 (bench test)
- 4-pin waterproof connectors & cable

Elsewhere:
- Teensy 4.1 + Ethernet kit, 74HCT245 level shifter, 33–100 Ω resistors
- Piezo discs (4 or 26 depending on panel construction), multiplexers if per-batten
- Fused distribution block, 5 A blade fuses, IP68 mains & Ethernet bulkhead connectors
- 3 mm frosted polycarbonate strip (26 mm wide), neutral-cure silicone, heat-shrink
- Later: Pi 5 8 GB, AI HAT+, Global Shutter Camera + 6 mm lens, PoE switch, IP65 enclosure

Australian stockists checked (all 10 mm, 5 V only): Core Electronics, Maker Store, Zaitronics, 99Tech, PMD Way — none carry 12 V per-LED strip in the needed spec. BTF ships DHL/FedEx to AU in 4–6 business days, free over $200.

---

## 10. Manufacturing notes (100–200 units/year)

- Modular panel = the product; tile count varies per customer. Brain box is one-off per goal.
- Levers: custom LED strip or rigid PCB bars at exact pitch (cheaper per pixel than nodes; fewer solder joints), stock extrusions, standard perforation/channel patterns, 2-piece shipping, custom controller board at volume
- One-off costs: EMC/electrical safety certification for mains products ($10–30k), tooling/firmware ($10–20k), 3–5% warranty reserve (connectors fail, not LEDs)
- Ballpark full-goal COGS at volume: $2.5–3.5k; retail positioning $8–12k on design/durability, since an off-the-shelf P16 cabinet set costs the same in hardware and is brighter. The product sells on looking like a garden feature, not a screen.

---

## 11. Open items

- [ ] Confirm fence panel construction: base sheet or open battens; timber or aluminium
- [ ] Piezo TDOA test on panel 1
- [ ] Decide seam-column ownership
- [ ] Confirm brightness cap and per-panel power derating in summer
- [ ] RGB vs RGBNW final call (RGB chosen for prototype)
- [ ] Certification path for mains-powered product in AU
