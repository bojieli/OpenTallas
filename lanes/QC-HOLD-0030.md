# QC-HOLD-0030 (11-20): 27 QC kits that failed sign-off on hold, 11-19

Source: tools/route_results.py window 11-19 00:00-23:59 (since-epoch 1795075200), signoff.json + signoff/ff/ep_ff.tsv + 5_1_grt.log + eco_*/eco_loop.json, read-only.
Gate (profile minimal): the hold gate is INTERNAL FF hold only; port-start hold is advisory/parent (two kits with FF hold -171/-23 signed through the ECO).

| type | host | wave | FF hold (all) | internal hold ps / ends | TT setup | late ECO | kit dir |
|---|---|---|---|---|---|---|---|
| sle_hc0__cl05696ed1 | epyc9 | s29q103S4Q9N4 | -187.13 | -15.1 / 28 | -9.65 | EXHAUSTED | <kw43>/s29q103S4Q9N4/items/sle_hc0__cl05696ed1/attempt_8/gen/sle_hc0__cl05696ed1 |
| sle_hc0__cl929603c0__cl4baa7c9c | epyc7 | s29q103S4Q9N4 | -186.4 | -41.41 / 308 | -13.06 | EXHAUSTED | <kw43>/s29q103S4Q9N4/items/sle_hc0__cl929603c0__cl4baa7c9c/attempt_5/gen/sle_hc0__cl929603c0__cl4baa7c9c |
| sle_hc0__cl929603c0__cl38badc56 | epyc7 | s29q103S4Q9N4 | -183.79 | -21.86 / 157 | -16.05 | EXHAUSTED | <kw43>/s29q103S4Q9N4/items/sle_hc0__cl929603c0__cl38badc56/attempt_3/gen/sle_hc0__cl929603c0__cl38badc56 |
| sle_stm_v3 | epyc8 | s29q103S4Q9N41Q | -179.85 | -23.43 / 67 | -24.06 | PASS | <kw43>/s29q103S4Q9N41Q/items/sle_stm_v3/gen/sle_stm_v3 |
| slw_hc0__cl1bc59e1c | epyc9 | s29q103S4Q9N4 | -177.67 | -13.26 / 97 | -15.79 | EXHAUSTED | <kw43>/s29q103S4Q9N4/items/slw_hc0__cl1bc59e1c/attempt_4/gen/slw_hc0__cl1bc59e1c |
| slw_su_l0__cl1a1c1f8f | epyc2 | s29q103S4Q9N41Q | -173.76 | -15.68 / 58 | 83.59 | EXHAUSTED | <s2>/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N41Q/items/slw_su_l0__cl1a1c1f8f/gen/slw_su_l0__cl1a1c1f8f |
| coll_s | epyc9 | s29q103S4Q9N4 | -171.72 | -3.33 / 2 | -9.73 | PASS | <kw43>/s29q103S4Q9N4/items/coll_s/attempt_8/gen/coll_s |
| sle_st_b_v2__cl14c98df5__pv41c959f3 | intel2 | fable-fix-qc | -168.53 | -24.32 / 169 | -41.28 | n/a (job dir) | <s2>/fable-fix-qc/kit/p3/gen/sle_st_b_v2__cl14c98df5__pv41c959f3 |
| sle_st_b_v1__pvc5a85fd4__pv7b7fafb4 | epyc9 | s29q103S4Q9N3 | -163.36 | -12.57 / 81 | -18.37 | ERROR | <kw43>/s29q103S4Q9N3/items/sle_st_b_v1__pvc5a85fd4__pv7b7fafb4/attempt_7/gen/sle_st_b_v1__pvc5a85fd4__pv7b7fafb4 |
| slw_st_b_v1__cl6357f1cc__pvffd43fdc | epyc2 | s29q103S4Q9N3 | -154.64 | -17.04 / 108 | 8.5 | ERROR | <s2>/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N3/items/slw_st_b_v1__cl6357f1cc__pvffd43fdc/attempt_6/gen/slw_st_b_v1__cl6357f1cc__pvffd43fdc |
| sle_st_b_v1__pvc5a85fd4__pv38472fb8 | epyc2 | s29q103S4Q9N3 | -151.5 | -20.46 / 146 | 20.99 | ERROR | <s2>/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N3/items/sle_st_b_v1__pvc5a85fd4__pv38472fb8/attempt_6/gen/sle_st_b_v1__pvc5a85fd4__pv38472fb8 |
| slw_st_b_v2__pvc2ec5bfb | epyc8 | s29q103S4Q9N4 | -149.59 | -6.73 / 23 | -28.73 | EXHAUSTED | <kw43>/s29q103S4Q9N4/items/slw_st_b_v2__pvc2ec5bfb/attempt_6/gen/slw_st_b_v2__pvc2ec5bfb |
| slw_hc1__cl3449ea95 | epyc9 | s29q103S4Q9N4 | -145.73 | -16.04 / 143 | -32.99 | EXHAUSTED | <kw43>/s29q103S4Q9N4/items/slw_hc1__cl3449ea95/attempt_5/gen/slw_hc1__cl3449ea95 |
| slw_hc1__cl68f9248e__cle683a076 | epyc2 | s29q103S4Q9N4 | -144.65 | -39.01 / 272 | -11.79 | EXHAUSTED | <s2>/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N4/items/slw_hc1__cl68f9248e__cle683a076/attempt_3/gen/slw_hc1__cl68f9248e__cle683a076 |
| sle_sc_v2 | epyc9 | ot-jobs | -125.01 | -8.34 / 23 | -6.31 | n/a (job dir) | /srv/opentallas-scratch/claude/ot-jobs/sle_sc_v2-route-renewed-glider-3472379-1795109634/work |
| slw_sc_v1__cl64543eaf__cl4590432d | intel1 | s29q103S4Q9N3 | -122.5 | -11.43 / 4 | -28.83 | ERROR | <kw43>/s29q103S4Q9N3/items/slw_sc_v1__cl64543eaf__cl4590432d/attempt_2/gen/slw_sc_v1__cl64543eaf__cl4590432d |
| sle_st_b_v2__cl14c98df5__pvcd986c42 | epyc10 | ot-jobs | -121.54 | -12.73 / 93 | 72.2 | n/a (job dir) | /srv/opentallas-scratch/claude/ot-jobs/sle_st_b_v2__cl14c98df5__pvcd986c42-route-civil-redfish-2246191-1795117214/work |
| sle_su_l1__clc6d66f5b | epyc7 | s29q103S4Q9N42 | -101.73 | -17.26 / 19 | 28.82 | EXHAUSTED | <kw43>/s29q103S4Q9N42/items/sle_su_l1__clc6d66f5b/gen/sle_su_l1__clc6d66f5b |
| slw_sc_v2 | epyc2 | s29q103S4Q9N3 | -101.36 | -20.53 / 23 | -24.54 | ERROR | <s2>/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N3/items/slw_sc_v2/attempt_2/gen/slw_sc_v2 |
| sle_sc_v3 | intel1 | s29q103S4Q9N3 | -95.87 | -17.82 / 3 | 29.77 | ERROR | <kw43>/s29q103S4Q9N3/items/sle_sc_v3/attempt_3/gen/sle_sc_v3 |
| sle_hc1__cl7d360508 | intel2 | ot-jobs | -95.54 | -28.76 / 164 | -32.59 | n/a (job dir) | <s2>/ot-jobs/sle_hc1__cl7d360508-route-tolerant-swine-2138988-1795115380/work |
| sle_sc_v1__cl7479a5ec | intel1 | s29q103S4Q9N3 | -92.12 | -1.38 / 2 | -27.64 | ERROR | <kw43>/s29q103S4Q9N3/items/sle_sc_v1__cl7479a5ec/attempt_2/gen/sle_sc_v1__cl7479a5ec |
| sle_sc_v2 | epyc2 | s29q103S4Q9N3 | -90.15 | -7.02 / 6 | -23.03 | ERROR | <s2>/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N3/items/sle_sc_v2/attempt_3/gen/sle_sc_v2 |
| slw_sc_v1__cl64543eaf__cl5e017c6f | intel1 | s29q103S4Q9N3 | -47.97 | -6.87 / 1 | -36.33 | ERROR | <kw43>/s29q103S4Q9N3/items/slw_sc_v1__cl64543eaf__cl5e017c6f/attempt_2/gen/slw_sc_v1__cl64543eaf__cl5e017c6f |
| slw_hc1__cl68f9248e__cl144ee7b3 | epyc9 | s29q103S4Q9N3 | -30.66 | -30.66 / 104 | -32.99 | ERROR | <kw43>/s29q103S4Q9N3/items/slw_hc1__cl68f9248e__cl144ee7b3/attempt_6/gen/slw_hc1__cl68f9248e__cl144ee7b3 |
| slw_hc0__cl4f54b7a3 | epyc9 | s29q103S4Q9N3 | -28.85 | -28.85 / 136 | -29.21 | ERROR | <kw43>/s29q103S4Q9N3/items/slw_hc0__cl4f54b7a3/attempt_4/gen/slw_hc0__cl4f54b7a3 |
| sle_hc0__cl05696ed1 | intel1 | s29q103S4Q9N3 | -13.97 | -13.97 / 60 | -16.45 | ERROR | <kw43>/s29q103S4Q9N3/items/sle_hc0__cl05696ed1/attempt_4/gen/sle_hc0__cl05696ed1 |

epyc8 note: sle_stm_v3 and slw_st_b_v2__pvc2ec5bfb are in the table (27 total).  Plan event = the wave token in the kit path (s29q103S4Q9N*, fable-fix-qc, ot-jobs routes).

## Findings

1. GRT hold repair ran in every kit (hold_guard_grt, margin 40, 200-buffer chunks) and ended at GRT-RC hold ws +1..+27 with 0 violators (or 'stalled'),
   yet routed internal FF hold is -1.4..-41 ps: the GRT RC to routed RCX gap, not a cap.  Stop reasons: 0 violators / margin chase stalled (20 kits),
   OT_HOLD_STALL (2), OT_HOLD_SETUP_GUARD stop (4; 3 of them left hold ws -4.4..-9.2 and landed the worst internal hold, -24..-39 ps on 164-272 ends).
   The guard floor was 0 (min(before,0)): fixed, see below.
2. Port-start hold (500-3800 ends, -90..-187 ps: start_i, arst_n, cws3_i, x_fe_*, b_hw_i, cland_*start_in) is advisory under R-MINIMAL; it is the parent/input window.  Not a gate.
3. Post-route late ECO (eco_loop, one iteration, reg2reg scope, target 10 ps) ran in 23 of 27: 12 ERROR 'prd_mk.sh failed (pass dir not staged)', 9 EXHAUSTED, 2 PASS (sle_stm_v3, coll_s).

## Classes

A. ECO never ran (12 kits, ERROR): 5_2_route.odb (and 4_1_cts.odb) deleted by STAGE-CAP; the ECO bundles of those runs (tools sha d68702ce / 753c2a9b) predate the prd_mk fallback to 6_final.odb
   (main 8f3d1679753 11-18 22:01 UTC, 7e9768a9388 11-19 23:37 PST).  All 12 still hold 5_1_grt.odb + 6_final.odb + 6_final.spef.  Verified read-only on intel1: current prd_mk.sh
   (OT_PRD_FROM=route, variant b10) stages sle_hc0__cl05696ed1 attempt_4 cleanly (falls back to 6_final.odb, GRT identity from 5_1_grt.odb).  Owner: flow (already on main).
   ACTION: re-run the late ECO on the 12 (sle_st_b_v1__pv38472fb8, slw_st_b_v1__pvffd43fd, slw_sc_v2, sle_sc_v2, slw_hc0__cl4f54b7a3, slw_hc1__cl144ee7b3, sle_st_b_v1__pv7b7fafb4,
   sle_sc_v1__cl7479a5ec, slw_sc_v1__cl4590432d, sle_sc_v3, slw_sc_v1__cl5e017c6f, sle_hc0__cl05696ed1 intel1).  Expectation from the 11 post-fix ECOs: ~2 sign, ~6 land within 2.2 ps.
B. ECO left 1-2 ends within 0.07-2.1 ps (6 kits: sle_su_l1__clc6d66f5b -0.07/1, sle_hc0__cl4baa7c9c -0.13/2, slw_st_b_v2__pvc2ec5bfb -0.2/1, sle_hc0__cl05696ed1 e8 -0.48/1,
   slw_hc1__cl3449ea95 -0.24/1, slw_hc0__cl1bc59e1c -2.12/2): MAX_ITER = 1 (OWNER 11-07 05:3x).  A residual-only second pad pass (same prd_mk on the pass dir; hold_eco_internal_run
   limits: worst >= -15 ps, <= 100 ends) would sign them.  Owner decision: COORD / OWNER (lifts a 11-07 rule); not changed here.
C. ECO left larger residue (sle_hc0__cl38badc56 -10.2/2, slw_su_l0__cl1a1c1f8f -8.73/9, slw_hc1__cle683a076 272 ends, no after record) and the unrepaired GRT-guard kits: internal ends are
   zero-logic flop->flop (QN->D, <=1 inverter): xl write-data chains (u_xl*.wd[] -> g_t[].g_e[].m[], 66-242 ends per kit), lpad/ist pad chains (u_lpad_*.r[] -> r[]),
   hi_pad/rd_pad lines (st_b).  Fix: KV lockup-latch form on those chains; rows to QC-PLAN-R3.  In-tap spread (launch/capture leaves of one tap differ 20-35 ps, seen on the rrl->RESETN
   path of sle_hc0): DIE-CORETAP-1119.  Same-tap vs cross-tap per end is NOT resolved here (ep_ff.tsv carries no clock pins; a per-end STA via ot-run was not run).
D. Port windows (class 2): QC-PLAN-R3, advisory.

## Flow fix made (main 503558b280b4f14a71bc478c32a54f554de18d3d)

tools/die_plan/hold_margin_family.py SETUP_GUARD_PS 0 -> -30 (test_hold_margin_family.py updated, ot-push-main tests passed).  Applies to NEW kits (config.mk value); the 3 setup-guard kits need a GRT re-run.
Not changed: eco_loop MAX_ITER (owner rule).  Local helper outputs: scratchpad of the lane (not committed).

- 2026-11-20 09:26 PST RESULT [QC-HOLD-0030 -> QC-HC-STM, QC-PLAN-R3, COORD] Four exact epyc9 outcomes are R-MINIMAL SIGNED with complete internal FF 0 ps/0 violators and final DRC/antenna 0/0. N3 slw_hc1__cl68f9248e__cl144ee7b3 a6 i1 TT -33.00 ps (internal FF -30.66/104 before), and N3 slw_hc0__cl4f54b7a3 a4 i1 TT -29.22 ps (before -28.85/136). N4 slw_hc0__cl1bc59e1c a4 residual/i2r TT -15.79 ps (before -2.12/2), and N4 sle_hc0__cl05696ed1 a8 residual/i2r TT -9.68 ps (before -0.48/1). All four records remain NEEDS_PARENT with no matching real-parent PASS. Exact final-netlist LEC is queued independently on epyc9 under qc-hold-0030-kits/results/<type>_<i1-or-i2r>_final_lec, with original route and signoff preserved. These older event rows do not release current V0E review holds. Exact signoff paths and terminal receipts are in intel2:/srv/opentallas-scratch2/claude/qc-hold-0030-logs/{rerun_epyc9_slw_hc1__cl68f9248e__cl144ee7b3,rerun_epyc9_slw_hc0__cl4f54b7a3,resid_epyc9_slw_hc0__cl1bc59e1c,resid_epyc9_sle_hc0__cl05696ed1}.log
- 2026-11-20 09:28 PST RESULT [QC-HOLD-0030 -> QC-HC-STM, COORD] N3 sle_sc_v3 a3 Intel1 ECO i1t stopped by the measured host no-progress watchdog at 08:45:34 PST, exit 143, exact scope oth-ubuntu-1649262-1795163644 and container prd-eco_20261120_003409_1651933-i1t-1681241. The last meaningful line was 6.7 hours earlier after GRT metrics and TT vclk setup. The next PRD operation is removing filler cells from the 6_final fallback seed, before the first PRD marker. Exact final DEF counts 3,336,185 filler/decap placements out of 3,807,748 components. No new 5_1 ODB or signoff. Isolated pre-STA filler-removal timing probe queued on the immutable seed, without GRT/route or a same-input retry. Evidence intel1:/srv/opentallas-scratch2/claude/qc-hold-0030-kits/results/sle_sc_v3_n3_final_seed/fill_probe.client.log
