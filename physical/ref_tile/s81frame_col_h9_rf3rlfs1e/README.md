# s81frame_col_h9_rf3rlfs1e -- parallel FALLBACK for s81frame_col_h9_rf3rlfs1 (S81-COLLECT/FRAMEFB, 10-21)

Why: the fs1 gate (and siblings rf2/rf3/rf3l) hit GP routability congestion: ~21% overflowed GCells, weighted
congestion 1.41 (h9 fs1 run3), h10 rf2 still oscillating at GP overflow ~0.29 after 24 h. The q-element / bf_col
macro rows block M2-M7 across nearly the full frame width, so all vertical traffic squeezes through a ~20 um centre
gap and the right std-cell column.

Change (owner rule: enlarge, no squeeze): outline width +172.8 um (4 x 43.2), height unchanged.
- centre vertical channel +86.4: every child/macro with x >= 600 shifted +86.4 (gap between q pairs ~20 -> ~106 um);
- right std-cell column +86.4: every child/macro with x >= 1120 shifted +172.8 total.
Everything else identical to s81frame_col_h9_rf3rlfs1 @21b97190e (same RTL, sources, clocks, forwarded soft clocks,
pins/E-face y ranges, children, orientations). Generator: tools/ref_tile from origin/main. 0 overlaps, hard children on
the 43.2 lattice (checked). Std-cell util ~40% at the fs1 post-repair movable area (1.146 mm2 h9) vs ~51% in fs1.

SAFE-DESIGN CHECKLIST (inherited from rf3rlfs1 unless noted):
1 pins: PASS (inherited; pin regs kept, reset landed 2 stages incl. xk receiver re-sync)
2 reach: inherited (landed regions r0/r1/r2, relays); gate native census is the check
3 fanout: gate native census obligation (not claimed)
4 depth: inherited, unchanged RTL
5 storage: PASS (ROM macros, unchanged)
6 floorplan: FIXED -- channels widened (centre + right), util ~40%, lattice kept; aspect ~2.1:1 (h9) / 2.3:1 (h10) tall frame column, die-slot shaped
7 clock: inherited (3 regional roots, landed crossings, io_hold_margin 0.03)
8 schedule: PASS, unchanged (no latency change)
Frame slot: die72 slot must take the new width if this closes first (NOTICE in LEAD-S81).
