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
