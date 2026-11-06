# LED strip, mounting and power

Reference. Carried over from the Sept 2026 summary with quantities recomputed for the 1.2 m / 36-row geometry (5 Nov 2026).

## Strip (chosen)
**BTF-LIGHTING WS2815 RGB, DC 12 V, 30 LEDs/m, black PCB, IP65, 5 m rolls** — https://www.btf-lighting.com/products/ws2815-rgb-addressable-led-strip-dc12v
- WS2815 = one IC per LED, dual data line (one dead LED doesn't kill the chain), 12 V. Cuttable every LED.
- Colour order **GRB**. Wires: red +12 V, white GND, green data, blue backup data (BI).
- IP65 silicone coat, 10 × 3 mm, adhesive backing kept. (IP67 sleeve is 12 mm, no adhesive.)
- Why 12 V: 5 V drops too much over 1.2–2 m runs; 24 V per-pixel is rare.
- RGBNW parked: only per-LED 12 V RGBW at 30/m found was SuperLightingLED SK6812-RGBW-30IA-12V. 12 V WS2814 is one IC per 3 LEDs — not per-pixel. RGB is fine at 5–20 m viewing.
- In hand: 2 × 5 m WS2815 (300 LEDs), on the test board.

## Quantities
| | Per panel | Full goal |
|---|---|---|
| Strip length | 13 × 1.2 m = 15.6 m | 46.8 m |
| Rolls (5 m) | 4 (20 m) | 10 (50 m) + spares |
| Peak draw, full white (~0.2 W/LED, ~30 W per 5 m measured) | ~94 W (~8 A at 12 V) | ~280 W (~23 A) |
| Realistic average at a brightness cap | 40–60 W | 120–180 W |

## Mounting in the channel
- 10 mm strip centred on the channel floor, 3M tape + silicone bead every 300 mm.
- 3 mm frosted polycarbonate strip ~26 mm wide, seated 5 mm below the batten face, stopped 10 mm short of the bottom rail so channels drain. Open channel foot; vertical channels self-drain.
- Strain-relieve every solder joint within 30 mm; heat-shrink + neutral-cure silicone over joints.
- Unverified: a ball compressing into the 27 mm gap must not reach the strip. Test with a hard strike before fixing channel depth (OPEN-QUESTIONS).

## Power supplies
- **Now (bench):** 30 W 12 V plug pack into the SP805E barrel socket (4 A max). WLED brightness limiter 2000 mA. Daytime visibility marginal at brightness 0.3 on this supply.
- **Next:** the **400 W 12 V (33 A) screw-terminal supply already in hand** (L, N, earth, 3× V−, 3× V+) for the 300-LED board at full brightness and later the first panel. It has no mains lead yet — **in AU fitting one is a licensed-electrician job.** When it goes in: feed the strips from it directly (power injection), controller on its own 12 V feed, never through the SP805E's terminals.
- **Product:** either one supply per panel (self-sufficient modules, ~94 W peak → a 150–200 W rain-proof unit at ~50% load) or one ~400 W unit per goal. Undecided; depends on the panel-as-module manufacturing decision. BTF 12 V IP65 rain-proof range (180–240 V, fanless, no UL) or BTF aluminium-case UL 350 W as the boxed alternative. Derate ~75% outdoors.
- Keep 230 V entirely at the supply; only 12 V / 5 V leaves it. RCD-protected outdoor socket; terminals down; drip loops; silicone over the mains boot; 50 mm air gap around fins.

## Distribution
- **Inject power every ~5 m directly from the supply, never through the controller's terminals.**
- Per panel: fused block, one 5 A blade fuse per group of ~4 columns + one for electronics; 12 V → 5 V buck (5 A) for controller / Pi.
- Mains to 3 panels: one RCD feed → IP66 junction box on a post → 3 fused outputs on IP68 quick-connect cables.
- Software brightness cap (WLED / renderer) so full-face white stays inside the supply with no visible loss at 5–20 m.
