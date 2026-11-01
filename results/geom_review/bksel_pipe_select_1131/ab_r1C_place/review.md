# Actual one-existing-FF reset correction

Personally viewed auto_geom.png; recorded 2026-11-01 13:35:39 PST. The owned clone moves exactly one existing internal reset delivery FF; check_placement passed, zero other instances moved and no netlist/source/port/cycle change. Original canonical placement FAIL remains in ab_r1_place.

Actual corrected hard-reach metrics: max register-to-register353.75um and zero captures over405 (original479.25/680). Counts remain140354standardcells/25659FF, outline388.8x172.8, fill.2614, empty.2802. Pin p90/max9.09/32.93 and zero unregistered pins are unchanged. Density image has the same face rows and internal clusters, with no new island or wall.

AUTO remains FAIL on aspect2.25, column estimate.64 at240/72.5 and GRT NOT RUN. Clock reach511.79 is preCTS INFO with zero fixed clock cells. No overall geometry PASS or capacity/timing closure is claimed. Native official source proof remains pending.
