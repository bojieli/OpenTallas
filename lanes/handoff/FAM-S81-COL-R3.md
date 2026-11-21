# FAM-S81-COL-R3 handoff (successor of FAM-S81-COL-R2; started 11-21 03:4x PST)
## Goal
One coherent J7 col row set (relay_depth adds + joint seats + Codex v3 FT delta fc763d2a07c9 + lever-7 pin-bank rows), proven on representative col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f (strict bind + LATCHECK + G0 0 new, then kit to sign-off), handed to S81-J6-ASSEMBLY-R2 for J7.
## State
- Lane clone intel1 /srv/opentallas-scratch2/claude/fam-s81-col-r3/lane (main ad29913002). Work dir intel1 /srv/opentallas-scratch2/claude/fam-s81-col-r3.
- relay_depth.py --limit 405 on rep (J5 plan, R2 src2 tree) gives 0 rows: the tool misses the 15 failing groups. xo0-3 = partition port x_i0_q -> 2 relays -> u_bout_xo_o0 (port-to-port feed-through, one 1104-bit bus -> must share one D, +2 each); lpl_11/lpl_12 = slices of frame_int_i0 (seam leaves ot_pl_seam_r_plq); so_1/so_3 = u_t1/u_t3.so -> core .si; rr_1 = rg0.o -> relay; es_p0 = bn0.d_st -> t0.e0.
- Codex E8 unit 2930371 = col_h9_r0_p1 pv697f40c9 three-moves place proof (not h10); waiter live.
- OWNERS-SWEEP 5 FAILED rows: deliberate holds posted 03:5x (coord bcbdda3dc5).
## Next
1. Find why relay_depth misses the core-to-core chains (q2 trace, rd1/q2.log); build rows (sink rows on head relay input, aligned per source bus).
2. Private plan = J5 + rows; strict bind + LATCHECK + G0 on intel1; kit.
