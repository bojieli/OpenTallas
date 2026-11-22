# Reordered ROM frontend coupon placement review

2026-11-21 16:24 PST, ROM-WEIGHTS-1119. Verdict PASS-COND for the private M2–M4 coupon.

I reviewed the updated placement image at E10 `/srv/opentallas-scratch2/claude/romw-1119/array_frontend_1121/placed_r3/frontend_placement.png`. The grouped floorplan sent 34 live nets across its worst row boundary and the first route stalled at 552 DRT violations. Reordering the same 100 locked RVT instances drops the worst cut to 14 and total cut crossings from 749 to 344. Exposing one empty row between active rows gives each group a local horizontal routing channel. The resulting 35 active rows fill 18.630 µm of the upper 30.552 µm slit, with the same 1.188 µm cell width. The native signed M4 stripes and both vertical supply risers stay blocked.

The updated DEF exposes the same 58 exact internal ports. Input and output accesses use opposite edges. The planned worst local route extent is under 19 µm and every shape remains under the current M4 obstruction boundary. Candidate is eligible for the private coupon route test. The production macro still requires the external pin and phase distributions.
