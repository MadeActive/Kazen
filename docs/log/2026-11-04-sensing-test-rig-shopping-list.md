# Goal Sensing Test Rig — Hardware Shopping List

Nov 4, 2026 · @Ben

Parts to buy for the sensing tests on the existing 300-LED test board, grouped by the test each serves. Prices are AUD inc. GST as shown on supplier pages on 4 Nov 2026 unless marked USD. Companion to `docs/log/2026-11-04-sensing-architecture-discussion.md`.

## 1. Impact sensing — piezos (do first, \~AU$70)

Cheapest ground truth for impact time and zone-level position; build this before anything else. Start on the Teensy, since it is the planned per-panel controller and the piezo code then carries forward.

| Part | Price | Stock | Link |
| --- | --- | --- | --- |
| Piezo element ×6 | $2.95 ea | In stock | [Core Electronics](https://core-electronics.com.au/piezo-element.html) |
| or 27 mm piezo discs with leads, 10-pack | \~$10–15 | — | [eBay AU](https://www.ebay.com.au/shop/piezo-disc?_nkw=piezo+disc) |
| Teensy 4.1 | $52.95 | In stock (55) | [Core Electronics](https://core-electronics.com.au/teensy-4-1.html) |
| 1 MΩ resistors + 3.3 V clamp diodes for the piezo inputs | a few dollars | — | Jaycar / Core |

## 2. Kick moment + speed reference — Doppler radar (\~AU$300–350)

Buy one, not both. The OPS242-A if you want it this week; the OPS243-A if the Mouser date holds and you'd rather have the longer range. Either plugs into the Mac over USB and streams speed readings as text (OmniPreSense [AN-29](https://omnipresense.com/wp-content/uploads/2026/06/AN-029-A_OPS243-for-Sports_260621.pdf) gives the soccer settings).

| Part | Beam | Price | Stock | Link |
| --- | --- | --- | --- | --- |
| OmniPreSense OPS242-A | 76° (AN-29 tested to ≥6 m on a soccer ball) | US$189 + shipping | 3 in stock | [RobotShop](https://www.robotshop.com/products/omnipresense-ops242-a-doppler-speed-radar-sensor) |
| OmniPreSense OPS243-A | 20° × 24°, rolling buffer | $324.80 | Backorder, 133 due \~6 Nov | [Mouser AU](https://au.mouser.com/ProductDetail/OmniPreSense/OPS243-A-CW-RP?qs=T3oQrply3y%252B5pADMfiP69Q%3D%3D) |

## 3. Behind-kicker pod camera test (\~AU$150 camera + compute)

The Pi Global Shutter Camera is the right sensor (true global shutter, 120 fps with cropping) but is out of stock at every AU seller today — sign up for the Core restock notice. The Arducam is a workable stand-in at 60 fps. Order the Pi 5 now: it has the longest lead time, and ball blob-tracking at 60–120 fps runs on its CPU alone. The AI HAT only matters once pose estimation starts.

| Part | Price | Stock | Link |
| --- | --- | --- | --- |
| Raspberry Pi Global Shutter Camera (IMX296) | $88–92.55 | Out of stock everywhere | [Core](https://core-electronics.com.au/raspberry-pi-global-shutter-camera.html) · [Pi Australia](https://piaustralia.com.au/products/raspberry-pi-global-shutter-camera) · [Pakronics](https://www.pakronics.com.au/products/raspberry-pi-global-shutter-camera-rpi-sc0715) |
| 6 mm C/CS-mount lens for it | $43.60 | — | listed on the Core camera page |
| Alternative: Arducam AR0234 global shutter (1920×1200, 60 fps at 720p) | $179.95 | Supplier stock | [Core](https://core-electronics.com.au/arducam-full-hd-color-global-shutter-camera-for-raspberry-pi.html) |
| Raspberry Pi 5, 4 GB | $178.42 | Lead time, dispatch \~30 Nov–9 Dec | [Core](https://core-electronics.com.au/raspberry-pi-5-model-b-4gb.html) |
| Raspberry Pi AI HAT+ 2 (Hailo 10H, 20 TOPS) — only for pose detection | $289 | In stock, 1 per customer | [Core](https://core-electronics.com.au/raspberry-pi-ai-hat-plus-2.html) |
| 850 nm IR illuminator board, 12 V | \~$15–30 | — | generic CCTV illuminator, e.g. [Fruugo listing](https://www.fruugo.us/850nm-infrared-led-illuminator-array-board-for-security-camera-30m-night-vision-range-8pcs/p-466099424) |

## 4. Height sensing — measuring light curtain (\~US$230–300 per pair)

Ask the supplier two things before paying: the scan cycle time (want ≤5 ms) and confirmation that the RS-485 protocol reports individual beam states, not just a count.

| Part | Price | Notes | Link |
| --- | --- | --- | --- |
| RS-485 measuring light curtain, 10 mm pitch, \~1,200 mm, IP65 | US$230–1,370 per pair, MOQ 1 | Emitter bar + receiver bar, one cable each | [AnLyHu (Made-in-China)](https://anlyhu.en.made-in-china.com/product/KwSGWMiuXmrg/China-RS485-Measuring-Light-Curtains-Sensor.html) · [Dadisick range](https://www.dadisick.com/blog/What-Is-a-Measuring-Light-Curtain_b21864) |
| USB-to-RS-485 adapter to read it from the Mac or Teensy | \~$10–15 | — | Core / Jaycar |

## 5. Power — lead-time item (\~AU$95 + electrician)

348 W covers the full goal's \~280 W realistic draw with headroom. If you'd rather have the 400 W the bring-up notes mention, the RSP-500-12 is the next step up at roughly double the price. Either way the mains lead needs a licensed electrician.

| Part | Price | Stock | Link |
| --- | --- | --- | --- |
| Mean Well LRS-350-12 (12 V, 29 A, 348 W) | $92.35 | 49 in stock, VIC | [Power Supplies Australia](https://www.power-supplies-australia.com.au/mean-well-lrs-350-12-enclosed-power-supply) |

## 6. Suggested order of purchase

Rough total for the full test rig: about AU$1,000–1,200 excluding the electrician, with the radar and light curtain making up half of it.

- [ ] Today: piezos + Teensy (\~$70), OPS242-A from RobotShop (\~US$190), Pi 5 4 GB (long lead time), LRS-350-12
- [ ] This week, after the supplier replies: light curtain pair
- [ ] When restocked: Pi Global Shutter Camera + 6 mm lens
- [ ] Only when pose estimation starts: AI HAT+ 2
