# hcoll_v5r_ctl_n2s1_v74s -- d4g COLL release leaf n2s1 (VM_RT 74), SAFE successor (LH-SMATT 10-19)
RTL ot_hgi_coll_ctl_v5r_n2s1_safephys (branch claude/hbm-coll-safephys-rst-1019): Codex COLL-SAFE fixed-delay SRAM pipes (6325606c8)
+ 9 KEPT same-age reset copies (77a229559). Replaces hcoll_v5r_ctl_n2s1_v74 (12,136-flop delay pipes; SAFE item 5 FAIL). Same ABI/edges.

SAFE-DESIGN checklist (owner 10-19):
1 Pins: PASS (native) -- every input captured at its pin in RTL (inst_q, hs_q/hb_q, dest_q/rc_*/tkm_*/issue_done_q, vm_raw_valid,
  iter_mul landing), every output a flop Q; synthesis pin_regs OFF as in the approved v74 kits (a stage would add an unscheduled edge).
  Reset: 2-stage face landing (reset_landing.json) then 9 kept D1 copies.
2 Reach: PASS by construction -- 172.8 x 324 outline, longest pin->flop Manhattan < 405 um; gate measures placed reach.
3 Fanout: FIXED -- mapped census results/arch/hbm_coll_safephys_1019/mapped_sizing_rst: reset copies max 32 (was 155/164); all
  functional non-reset nets <= 16 (Codex census); ties are per-sink repaired at floorplan.
4 Depth: PASS -- unchanged V7 logic (field + offset adders between flops); gate STA confirms at TT.
5 Storage: FIXED -- the VM_RT 74 / INJLAT delay pipes are 4 fixed-delay SRAMs (2x 128x256 p192_mir, 2x 32x128 p192_rc) with local
  capture/warm copies; no runtime-indexed flop arrays, no long flop->flop delay chains.
6 Floorplan: macros one deliberately abutted N-S stack (pitch = height + 0.024 um, on track, no pins on N/S macro faces) at x 43.2;
  macro pin faces W/E <= 5.1 pins/um with 41 / 35 um std bands; tile W face 1,661 pins / 324 um = 5.1/um; aspect 1.9.
  WAIVED fill 42% (macro-inclusive; std-only ~10%): pin-bound (fill_reason.pin_bound in spec.json).
7 Clock: single centre-fed root over ~5.4k sinks in a 172.8 x 324 tile; gate must show pin-flop spread <= 80 ps TT and FF.
  io_hold_margin 0.03.
8 Schedule: PASS -- static, no added edge vs v74 (Codex proofs: production 1792 + dense 8192 pairs PASS at LAT 74; mutants FAIL).
Critical prefix (ot_hgi_coll_ctl_v5): gate PNGs go to the coordinator review queue; no REVIEW.json / submit by this lane.
