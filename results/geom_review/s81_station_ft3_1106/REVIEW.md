# S81 t51 FT3 storage form A — 2026-11-06

Actual plan image inspected: station_ft3.png (old and new NW bands, actual N input spans and declared clock taps).

Verdict: PASS-COND for the targeted physical trial. This is not timing or routing sign-off.

The old FT3 bank is a 25.92 x 109.788 um column in the NW crossing. The candidate is east of that crossing at [302.4,1144.8,388.8,1209.228], 86.4 x 64.428 um. Area increases from 2845.705 to 5566.579 um2, above twice the 2636.064 um2 reservation. The gap from the W-band inner edge x77.54 is224.86 um. No other ring band overlaps it. The existing local clock tap is within the new reader bank; forwarded write clock still enters at its existing N pin. No new clock budget or root was introduced.

The full declared FT3 input window to every new band corner is at most351.84 um, below the existing402.84 um planning reach. The previous207.306 um field was replaced with that conservative bound. Actual placement/routed setup, hold, slew, first-hop reach and clock behavior remain to be collected. No DRC/STA result is asserted.

Outline, pins, RTL, reset topology, FT depths, other bands and latency are unchanged. PDN and macro placement are unchanged (this soft station has no hard cores). Estimated functional form remains below150k cells from its approximately55k storage/relay FFs plus local logic; actual synthesis count must be read from the trial. Utilization requested explicitly0.40.

S81 plan owner approved this geometry on2026-11-06 before route. Legacy FREG capture form B is separate and is not enabled here.
