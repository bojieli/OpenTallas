# METH-ALIGN lane (tool/doc alignment with METHODOLOGY section 10 rulings)

2026-10-24 22:34 PDT METH-ALIGN: branch claude/methodology-align-1024@5173eb8e3a2a (worktree /home/ubuntu/wt/meth-1024r, sparse). Implemented 9.1 (AGENTS merge), 9.3 (signals <= M7, m89_signals ERROR, reach 405, no over-the-top ft), 9.4 (ft_station_max_um 405 ceiling), 9.10 (README R2), 9.13 (README signable scope). Not touched: reset wavefront (RESET), signoff pair-skew (CLOCK), signoff.py (README-only for 9.13).
2026-10-24 22:34 PDT METH-ALIGN: tools/die_plan pytest 284 passed. Plan impact table + requests: see COORD-REVIEW-QUEUE READY line; requests in S81 / S81-HEAD / QC-A0 / KV-G3 / HBM-ARCH lane files.
2026-10-24 22:34 PDT METH-ALIGN: notes -- G0C reach margin stays 0.9 x 405 = 364.5 um; examples changed station counts (tiny mid 3, s81_pair 4) so example latencies changed (x 4->8, r 5->9); gen_phys die assembly MAX_ROUTING_LAYER M9 and g2 spine probe (-signal M8-M9 for clock/reset spine nets) left as is (clock/reset only).

## PARKED 2026-10-24
- branch claude/methodology-align-1024@5173eb8e3a2a, pushed; READY posted. No live jobs (all checks were seconds-long python on rtx-pro; no fleet jobs).
- Next: ROOT-MERGE review/merge; lanes re-plan their dies (requests posted). Merge order note: clean merge-tree vs main and claude/reset-1024.
- OWNER?: none.
