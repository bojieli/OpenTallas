# ROM frontend coupon port access review

2026-11-21 16:33 PST, ROM-WEIGHTS-1119. Verdict PASS-COND.

I read the candidate image at E10 `/srv/opentallas-scratch2/claude/romw-1119/array_frontend_1121/placed_r4/frontend_placement.png`. The reordered 100-cell placement keeps the worst vertical cut at 14 and the placed extent at 1.188 × 18.630 µm. The previous route reduced the count from 552 to 40 markers. Its 25 M4 markers cluster at access against the signed power-stripe edges. Three M3 shorts touch the supply-riser obstruction from the left side.

The new internal input pins sit on the logic side of both risers and each port row is at least 132 nm from the center of a signed power stripe. The image shows the 17 inputs away from the two supply risers and the 41 outputs along the right access edge. The external LEF pins are still the fixed same package; this private vehicle stops at internal access points. The remaining small M3 signal-to-signal cluster must close in this detailed route before any claim of physical readiness.
