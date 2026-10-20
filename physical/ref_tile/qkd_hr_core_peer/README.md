# qkd_hr_core_peer r6 (KV-HOST/PEER design, committed + benched by KV-HOST4, 10-19)

HOST root cluster child (members u_peer, u_peer_codec, u_root_mux, u_coordinator, u_ctrl; parent qkd_host_root is CRITICAL).
r6 = SAFE item 3/4 structural redesign of r5 (dece9760a: gate WARN 0 fail, but its CTS-stage STA wns -135.2 / tns -142.4 ns,
2,806 endpoints: ctrl u_m.h -> ~17-level accept decode -> 744-flop tk8/kst8 enable, lt -> 93-b status compare -> tx_d,
coordinator grant -> 81-b allocation compare -> TX choice, cohort compare -> dispatch_valid pin flop). Full history: spec.json structural_change.

## Changes
1. Token service inner `_pd2` (generator tools/qwen_kv_die/host_cluster/mk_peer_pd2.py): head flags computed at queue write,
   per-source sequence compares in parallel, status_changed one edge ahead (exact), tk8/kst8/boot8/seen/service_epoch8
   applied one edge later from registered one-hot enables in KEPT copies (<= 31 loads each).
2. Coordinator inner `_pd` (mk_peer_coord_pd.py): class9 codec allocation stage (+1) with a registered allocation-change test.
3. Coordinator dispatch_valid output stage (+1, gen_peer_rr.py STAGE_OUT).
4. Reset copies through the shared reset_relay_split hook (ot_rst_copies, max 256 loads a copy) instead of OT_RST_SPLIT.

Added cycles -> HOST calendar (class9 lifecycle transport, not the per-token compute schedule): tk8/kst8/boot8/seen/service_epoch8 +1,
allocation -> codec +1, dispatch_valid +1 (plus the r5 +1 stages, unchanged).

## Benches (Verilator 5.050, source 8fedfef89, witnesses in results/arch/qwen_split_1014/host_root_cluster/benches/)
cluster lockstep 6/6 PASS; child mutant + rr mutant 0/6 (FAIL as required); peer_pd2_equiv 4/4 PASS, mutant (sc_q from current
values) FAIL 2/4 (the two status-sending die!=0 configs); codec_pd PASS / mutant FAIL; root mux pl2 PASS / mutant FAIL; stage
tp8_coordinator and peer_rank_codec PASS / mutants FAIL. (The 12:01 pd2 'MUTANT_NOT_CAUGHT' run used the previous, tx_v-masked
mutant; the committed mutant is caught.)

## SAFE-design checklist (pre-gate)
1 Pins: pin regs ON; reset_landing 2 on por_n/host_rst_n - PASS (unchanged r4/r5).
2 Reach: 280.8 um square, pin flops at the faces (io_flop_at_pins) - PASS.
3 Fanout: 744-flop enable split into KEPT copies <= 31 loads; reset copies <= 256 (ot_rst_copies) - fixed (verify the gate synth
  OT_RST_COPIES lines and that the dl_*_c copies survive, paramod names).
4 Depth: the r5 classes (-135/-110/-88/-80/-76 ps) each moved behind a register (items 1-3) - fixed; confirm at the CTS gate.
5 Storage: no new runtime-indexed flop arrays (4-entry queues unchanged from r4) - PASS.
6 Floorplan: outline/faces unchanged from r5 (pin-bound, util ~19% fill_reason waiver) - waived (pin-bound).
7 Clock: ck_core at the N-face centre (r5 spread 60.9/59.4 PASS); io_hold_margin 0.03 - PASS (re-measure at the gate).
8 Schedule: static, no credits added; added edges listed above go to the HOST calendar - PASS.
