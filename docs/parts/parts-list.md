# Parts list

One table for everything to buy. Prices AUD inc. GST as seen 4 Nov 2026 unless marked USD. Update the **Status** column (todo / ordered / arrived / rejected). Full reasoning and links: `docs/log/2026-11-04-sensing-test-rig-shopping-list.md`.

## In hand
| Item | Qty | Note |
|---|---|---|
| BTF SP805E WLED controller | 1 | bench controller |
| BTF WS2815 12 V 30/m 5 m, IP65 | 2 | on the test board (300 LEDs) |
| 30 W 12 V plug pack | 1 | bench only |
| 400 W 12 V screw-terminal supply (33 A) | 1 | no mains lead yet — electrician |
| Test board | 1 | 8 × 34, 67 mm pitch |

## Sensing test rig
| Test | Item | Price | Source | Status |
|---|---|---|---|---|
| Piezo | Piezo element ×6 (or 27 mm discs 10-pk from eBay) | $2.95 ea / ~$12 | Core Electronics | todo |
| Piezo | Teensy 4.1 | $52.95 | Core Electronics (55 in stock) | todo |
| Piezo | 1 MΩ resistors, 3.3 V clamp diodes | a few $ | Jaycar / Core | todo |
| Radar | OmniPreSense OPS242-A (76° beam) | US$189 + ship | RobotShop (3 in stock) | todo — buy this one |
| Radar | OmniPreSense OPS243-A (20° beam, rolling buffer) | $324.80 | Mouser AU, backorder ~6 Nov | alternative, not both |
| Pod | Raspberry Pi 5, 4 GB | $178.42 | Core, dispatch ~30 Nov–9 Dec | todo — longest lead |
| Pod | Raspberry Pi Global Shutter Camera (IMX296) | $88–93 | Core / Pi Australia / Pakronics — **all out of stock** | waiting |
| Pod | 6 mm C/CS lens | $43.60 | Core | todo with camera |
| Pod | Arducam AR0234 global shutter (60 fps) | $179.95 | Core | stand-in if Pi cam stays out |
| Pod | 850 nm IR illuminator board, 12 V | ~$15–30 | generic CCTV | todo |
| Pod (later) | Raspberry Pi AI HAT+ 2 | $289 | Core (1 per customer) | only when pose estimation starts |
| Curtain | RS-485 measuring light curtain, 10 mm pitch, ~1,200 mm, IP65, 1 pair | US$230–300 | AnLyHu / Dadisick | ask scan time + per-beam output first |
| Curtain | USB → RS-485 adapter | ~$10–15 | Core / Jaycar | todo |
| Power | Mean Well LRS-350-12 (348 W) | $92.35 | Power Supplies Australia | rejected — 400 W unit already in hand |
| Power | Electrician — mains lead | — | — | todo |

Rough rig total: AU$1,000–1,200 excluding electrician; radar + curtain are half of it.

## First real panel (from the Sept plan, quantities corrected)
| Item | Qty | Note |
|---|---|---|
| WS2815 12 V 30/m black IP65, 5 m rolls | 4 (10 for 3 panels) | 15.6 m per panel |
| 12 V rain-proof supply (BTF IP65 range) | 1 per panel or 1 per goal | OQ-6 |
| 12 V → 5 V buck, 5 A | 1 | controller / Pi |
| Teensy 4.1 + Ethernet kit, 74HCT245, 33–100 Ω resistors | 1 set | per panel |
| Piezo discs | 4 or 26 | depends on OQ-1 |
| Fused distribution block, 5 A blade fuses, IP68 bulkhead connectors, BTF 4-pin waterproof cable | — | |
| 3 mm frosted polycarbonate strip 26 mm wide, neutral-cure silicone, heat-shrink | 13 × 1.2 m | |
| Later: Pi 5 8 GB, PoE switch, IP65 enclosure | 1 per goal | brain box |

AU stockists checked (Core, Maker Store, Zaitronics, 99Tech, PMD Way) carry 5 V only; BTF ships DHL/FedEx to AU in 4–6 days, free over $200.
