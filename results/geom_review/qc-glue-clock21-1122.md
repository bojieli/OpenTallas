# QC Glue clock capacity review · 2026-11-22

PASS-COND for placement and CTS. E9 actual V2 attempt_5 placement is the frozen comparison basis. The viewed layout is `/srv/opentallas-scratch2/claude/fam-qc-cb-r2/nov22_glue_clock/clock21_layout.png` on epyc9. It combines the six actual macro boxes, existing BTerms, formerly overloaded rooted sink coordinates, and exact production-snapped proposed sites.

Nineteen proposed sites follow the central clock load from west to northeast. Two added south-edge taps sit in the clear street below four SRAMs. All 86 shared V2 and V3 tap positions match. The p7c5rt plan retains V3 t86 and adds t87 through t107. The 108-position frozen clock connectivity run capped all 53,070 sinks at 1,000 per tap, including t19 at 979 and t1 at 965. No site intersects a macro halo under the production tap checks.

Obtain an exact place/CTS review on the changed kit before any route decision. The separate Glue timing fixes for ROM response and FDI capture require their own measured placement.
