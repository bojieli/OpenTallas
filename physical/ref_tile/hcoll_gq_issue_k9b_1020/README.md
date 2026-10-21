# hcoll_gq_issue_k9b_1020 (HBM-GQ8, 10-20) -- ot_hgi_coll_gq_issue #(VM_RT 74, ISSUE_AHEAD 1), d4g hcollgi_{NE,NW,SE,SW}

Source: claude/hbm-gq8-1020 = Codex R6 e8956f9d9 (native FAIL 7 roots / max 42) + R9 structural fanout fix (opt-in OT_GQ_N32):
- period-end compare tl==per-1 and lps>1 become REGISTERED flags tl_last / lps_gt1 (12 kept ot_hgi_coll_gq_control_ff copies
  each, one per consumer group); next state from the same tl/per/lps updates (launch: per_rd==1; counting: tl+2==per;
  wrap: per==1). Removes R6's 4 wrap roots (33) and the 8 compare cones R7 replicated (per/tl roots 33..61).
- 5 kept registered one-hot base copies (target16 stored_oh = 1<<base, captured on launch_c[8..12]) feed per lo/hi and fault
  row AND-ORs, b0_oh and cur_oh: removes R6's p_sb decode roots (42/37/36).
- Same edges, same function: invariant check OT_GQ_CHECK_INV ($fatal per copy per cycle) in the IA1/IA2 production benches;
  mutants OT_GQ_MUT_TLLAST (wrap-with-loops case dropped) and OT_GQ_MUT_OH_COPY (period-lo one-hot copy rotated) must FAIL.
Geometry: literal-lattice model 35f39f06c (results/rtl/hbm_coll_gq_k5_1020/lattice_model): 8 x 128x256 p192 macros in two
4-high stacks at y 43.2/172.8/302.4/432 (pitch 129.6, 49.128 um channels, no abutment), 2 VM-ring 64x16 macros at the S edge
of the centre band; outline 518.4x561.6, centre band 164.376 um (parallel fallback; right half +43.2). Pins: N host/ISA, W VM lo, S VM hi, E ring A/B + landing (unchanged from k5).

Safe-design checklist (owner 10-19; rule freeze 10-20 09:35: guidance, die GRT/STA decide):
1 Pins: every input captured by a flop at the pin, every output a flop Q (RTL stage table); reset 2-stage landing x4 -- PASS (k5 unchanged)
2 Reach: tile <= 561.6 um tall; any >405 um net is reported by the gate reach check -- gate decides
3 Fanout: R9 targets 0 drivers >32 (census runs first in the gate; numbers recorded in gate_result) -- PENDING census
4 Depth: tl_last next state = max(per_rd AND-OR, tl+2 incrementer) + 16-bit equality + 2 mux levels (< 20 levels) -- gate TT decides
5 Storage: AQ element lines + VM ring in SRAM macros (8 + 2) -- PASS
6 Floorplan: all macro origins on the 43.2 lattice, channels >= 20 um, pin faces 5.09/um <= 6, aspect <= 1.2 -- PASS (model)
7 Clock: K=8 regional roots (clock_split_km); io_hold_margin 0.03; pin-flop spread <= 80 TT/FF checked by the gate -- gate decides
8 Schedule: no added edge (flags hold the same value the compare produced in the same cycle) -- PASS
Die slot: the d4g manifest grants 237.6x237.6 for collgi_*; this view needs k9b outline -> die floorplan re-grant (DIE owner).
