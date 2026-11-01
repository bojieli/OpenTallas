# Proposed existing reset delivery FF relocation

Personally viewed planned.png; recorded 2026-11-01 13:25:53 PST. PASS conditional for applying the one-cell move to an owned continuation and checking actual legality/geometry. No source/netlist/cells/ports/stages changed. Original FAIL retained.

Exact ODB confirms both stages PLACED, not FIRM face cells. Predecessor rst_s[0] stays at E, D of internal rst_s[1] comes from predecessor QN through INV _095586_. Vacant ROW_291/MX target centre168.210,83.025 retains exact master/orientation and has zero overlaps in the original database. Incoming registered hop238.788um; all4583output-tree edges <=217.026um; all4324captures <=254.502um. Projected global r2r353.75um, zero captures above405. Pin p90/max unchanged9.09/32.93.

Existing output buffers remain near E; the figure explicitly shows those return legs. This is a legal bounded-edge prototype, not a reset timing PASS. Actual corrected geometry, normal whole-kit EQ, reset recovery/removal and CTS/GRT gates must pass. The prior column estimate0.64, aspect2.25 and GRT NOT RUN failures are retained without waiver. No physical ODB changed at this review.
