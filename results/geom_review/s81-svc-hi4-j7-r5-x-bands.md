# S81 hi4 J7 service split with landing reserves

Viewed `s81-svc-hi4-j7-r5-x-bands.png` for the 570.24 µm seam and the enlarged south and west landing view. The 154 hard boxes preserve their original dimensions and orientations, including 12 new 160×256 landing SRAMs. The two existing 562-bit FT chains retain five internal site groups each. The longest original FT0 and FT1 hops after the move are 367.045 and 324.610 µm, within 405 µm. The proposed cut still needs its own added stage priced.

All seven landing reserves fit in single rectangles within their owning pieces. Each keeps at least the old total reserve area. The max pin-to-band hop is 338.962 µm at attn_i2 versus the 402.84 µm search bound. Geometry checks covered hard boxes, all band pairs and FT bit sites. The retained pre-SRAM bind estimates 6,896 wires across the seam at 2.51 wires/µm.

Verdict **PASS-COND** for the private geometry draft. Remaining conditions are output from exact-parent elaboration, the new net-level local hop and pin capacity check, source and dead-input contracts, clock/reset sites with loaded taps, and split cycle accounting. Inputs and solver result are on epyc10 at `/srv/opentallas-scratch2/claude/opus-fix-s81-svc-r5/split-hi4-band-test`, unit `oth-ubuntu-1996905-1795259611`.
