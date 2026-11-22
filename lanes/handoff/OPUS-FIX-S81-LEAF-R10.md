# OPUS-FIX-S81-LEAF-R10 handoff (Opus; succeeds FABLE-FIX-S81-LEAF-R9 at 23:1x 11-21; owns ot_s81sl_leaf__t* + kv_leaf t1 t3 t4 (+t2 split, J9))
Lane dir intel2 /srv/opentallas-scratch2/claude/opus-fix-s81-leaf-r10. R9 dir (gate trees, clone) = /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r9. Read R9 handoff for background.

## COORD 23:25 stop list
kv_leaf t2 28-piece split is NOT J8 (goes to J9). Focus: gate c leaf re-grid (incl kv_leaf t1 t3 t4) -> J8 rows to S81-J6-ASSEMBLY-R5 by 11-22 14:00. t2 split draft only after the hand-off.

## Gate c (plan c 8c21a4c06257, unit oth-ubuntu-2637398-1795324543) DONE 23:17
ELAB_RC=0 BIND_RC=0 (873 crossings, 0 errors) LAT PASS 873/873 with the expected 4 lane deltas, PRE PASS.
G0: 1 NEW error vs J7 (2 gone): t62 ft0 stage 0 bit cells (123) hit u_lf.u_vp.g_ln[6].u_l after R9 nudge (0,-43.2) of lanes 7,6.
Fix = plan d: ft_nudge.py --no-snap allocator, ONLY t62 ft0 bit_sites spliced (script r10_t62fix.sh, out rgd/). Then G0+PRE re-check on plan d.

## t2 split (parked for J9)
R9/t2s: census done; type_split patches in R9/clone (ts_patch.py, ts_patch2.py by R9; tmp/ts_patch3.py by R10: band_fixed_um follows landing bands, insertion_target_override copied; spec drops landing_reader/writer_start). Next failure: reset_tree wf_solve "added tap clk_t82 violates outline/halo/tap spacing" in _reset_trees on the piece plan.

## t39 proof (R8 chain b1, epyc7): geom PASS, route started 23:03 (kit epyc7 kw43-wave-1109n/.../private/FABLE-FIX-S81-LEAF-R8/ot_s81sl_leaf__t39_1121220439/gen/ot_s81sl_leaf__t39, log otrun_route.log). Chain process on intel2 (waiter PID 3546224 tree) posts as FABLE-FIX-S81-LEAF-R8.

## 23:4x update
- Plan d 19d389f9e9b7 (rgd/plan_h2_2249.json; only t62 ft0 bit_sites differ from plan c, 123 bits <= 18.09 um). Gate d unit oth-ubuntu-3457055-1795332181 (script r10_gated.sh = R9 gate in the SAME tree R9/g68b_src, plan swapped in place; log g68d.otrun.log, markers G68D_*, R10_GATE68D_DONE). Waiter armed.
- Draft J8 delta j8_leaf_rg9_delta.json (r10_delta.py J7 -> plan d): 68 types, 4 lanes fixed_cycles, 4 latency rows. Rebuild it from the final plan before the hand-off.
- Intake item 3 (leaf raw reset rows): reach_rules check on plan d leaf types (plan path must be inside the tree!) = 59 edge_reach + 24 start_raw_net (J7: 52 + 15). All on clock.landing_local_resets raws (rst_rl_*), which reach_rules fix --rules 1 skips by design (0 types changed). The bind re-picks them by anchor site (RESET_ANCHOR lines, moves up to 203 um). Fix tool r10_rawfix.py SRC PLAN BIND_DIR OUT REP TYPE_RE [--check]: bound tree (bind rtl), bind anchor + LOCAL-RESET-RAW-1 receipts written back, over-limit (180 half-cycle negedge / 405) -> nearest same-depth bound rst_rl (0 cycles), anchor re-recorded. Run it on gate d bind out (R9/g68b_src/.../native_bind/out) once gate d bind is done -> plan e -> gate e.
- t39: CTS on epyc7 (23:35); waiter on R8/t39spec/chainB.log.
