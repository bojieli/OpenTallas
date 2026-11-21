# LOCKUP-STATION-R3 handoff (Sonnet, started 2026-11-21 00:xx PST; succeeds LOCKUP-STATION-R2)
Read lanes/handoff/LOCKUP-STATION-R2.md for the form + baselines.
## Done
- 51ab145ab6 gating: the auto latch form was already opt-in (needs clock.zl_lockup.<T> in the plan; no plan in the repo has one; zl_netlist/auto only written then).
  BUT the same-tap/long-hop bypass exports (OT_HOP_LATCH_SAME_TAP=bypass, MAX_UM=200) were default-on for ANY zl_lockup spec. Now opt-in: only auto:true or same_tap:"bypass".
  PUSHED main d8800bd360 (gen_phys.hop_latch_leaf_lines + schema comment + test). ct_latch_restore in clock_taps.tcl still runs on every kit but only touches u_fl_/u_lk_nk_ DFFL cells (a flop where a latch was = function change) ; LATCH-SWAP-0045 (ae39f0a78d4) owns the flow-wide name-free restore + signoff.py check.
- Kits generated with the form: only R2 proofs (proof1-6 t39 under epyc7 .../lockup-station-r2, QC qc_sle_ctl + qc_sle_ctl2 on intel1 scratch3). No die/wave kit.
## Running
- proof6 t39 epyc7 oth-ubuntu-1645995-1795247826 (started 16:2x); QC2 sle_ctl__cl67434795 queued on intel1 (memory wait). Read post-hook: 4_1_cts.log OT_LATCH_RESTORE / bypass counts, pregrt_ff_hold.log, tt_setup_keep.log.
- Baselines: t39 xtap 14,251 / hold cells 47,483 / TT -354.63 tns -16.4k; QC xtap 3,039 / hold cells 48,100 / TT -1.82.
- Rows HELD (S81-J6-ASSEMBLY-R2, J7 after 13:00, QC-PLAN-R8, KV-PLAN-R4/D28) until a proof is no worse than baseline on TNS and hold.
- Cleanup (ot-delete): proof3_t39, proof5_t39, qc_sle_ctl, proof4 after read.

## Note 11-21
- proof6 + QC2 started on main 38faab8511: only the R2 restore (u_fl_/u_lk_nk_ names, clock_taps + hop_latch_leaf) is active, NOT the name-free latch_restore.tcl of e88352084d (LATCH-SWAP-0045). On reading: count DFFLQx4/DFFHQx4 in 4_cts odb (expect 0 u_fl_nl swaps; any other swap = uncovered).

## CODEX notes 11-21 02:22 PST

- t39 proof6 actual post-hook CTS: TT -309.20 / TNS -16,338, FF -220.48 / TNS -260,263.6. TT repair retained at -291.38 / -11,770.78 versus the inherited b05c baseline -354.63 / about -16,400. Pre-GRT FF starts with 9,161 cross-tap ends (-218.14) versus 14,251 baseline (-275), and 2,108 port-out ends versus 1,884 baseline after seam exclusion. Hold repair still active in inherited E7 proof6. Wait for repaired hold and GRT before a plan row. Post-hook ODB census showed 5,146 DLLx2 RVT and zero residual DFFLQx4/DFFHQx4 (E7 sta/codex-p6/census.log). Filter removed 6,354 same-tap and 17,149 far hops, with 5,141 leaf latches connected. QC2 sle_ctl__cl67434795 admitted on intel1, in global placement.

## QC rows (candidate, for QC-PLAN-R9) 11-21 04:xx
Plan row (opt-in form on main d8800bd360): clock.zl_lockup["<QC type>"] = {"auto": true, "max_um": 200}  (same_tap bypass implied by auto; reset relays + SRAM excluded by default; leaf form + latch restore on).
Proven so far on: sle_ctl__cl67434795 only (QC2, intel1 oth-ubuntu-2255653-1795247355, running 3.5 h, CTS not reached). Baseline xtap 3,039 / hold cells 48,100 / TT -1.82.
STATUS: NOT RELEASED. Rule: rows go to a die lane only after a proof no worse than baseline on TNS and hold. R9 may stage the row but must not apply it. I post PROOF-PASS here + to QC-PLAN-R9 the moment QC2 reads post-hook.

## VERDICT 11-21 ~05:4x (log reads; proof6 still in GRT, no post-hook STA yet)
- QC2 sle_ctl (restore: R2 names only): FAIL. cross_tap 3,039->1,728, same_tap 199->472, TT -1.82 -> -133.98 (TNS -3,980; tt_setup_keep -243.95->-133.98). Bypass: 37,483 same tap, 33,345 far. QC rows HELD.
- proof6 S81 t39 (seams off): pre-repair cross_tap 14,251->9,161, port_out 1,884->2,108(pre-repair, unlatched), same_tap 41->22; hold_cells 47,483->36,145; hold after repair wns -49.61 on 1,732 port_in ends only (cross/same/port_out 0); tt_setup_keep TT wns -291.38 / tns -11,770 (base -354.63 / -16.4k) = better. 4_cts: 872 flops restored to DLLx2, 0 DFFLQx4 left, bypass 6,354 same + 17,149 far. Provisional PASS vs baseline on TNS + hold-cells; confirm on final-GRT TT (job 9:41 h in GRT iter 6/30) before any S81 row.
- Split result: general form helps S81, hurts QC. Next (not run): measured-endpoint form + skip legs with < +50 ps setup slack for QC.
