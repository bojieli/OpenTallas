# hcoll_gq_issue_k4ia1_1020 (HBM-COLLFUSE2-VME 10-20) -- k4 gq issue leaf #(VM_RT 74, ISSUE_AHEAD 1). NOT GATED, superseded.

Siblings: hcoll_gq_issue_k4bia1_1020 (k4b outline 475.2x388.8 + balance_levels), hcoll_gq_issue_k4v74_1020 (VM_RT 74, IA 0).
STATUS: the first gates (@af944e962) were REFUSED by the mandatory pre-floorplan native32 census (max 108 loads, 16 drivers; most are
k4-BASE combinational drivers: the k4 README census counted register outputs only). gq_issue now belongs to HBM-COLL6, whose k5 line
(claude/coll6-gq-k5-1020, built on af944e962) carries VM_RT + ISSUE_AHEAD and the native32 fanout pass. These kits stay as records.

## PRE-GATE NATIVE CHECK (actual-Liberty mapped netlist, ot-epyc9 ref_gate/hcoll_gq_issue_k4ia1_1020-20261020-024057)
FAIL max 108 > 32, 16 drivers: qbg & iss/iph issue enable 108; sfv/scd decodes 62 / 80 / 106; ev_v[14] | qbg_pr14 plain-read gate 100;
cur_ohc x rf row OR -> qa 70; qa[6][0] 35; u_target commit gate 38 / 34; aq13 u_scale s1_power 34 / 39; aq13 s2a_m -> s2_amax 62 / 62;
VME-owned: vmring filled[6] 34, rg_fslc[0/1] 55 / 52 -> FIXED on claude/hbm-vmearly-k4-1020 after af944e962 (registered kept ready
copies, 4 slot-select copies). Reach / storage / registered pins: not evaluated by the census (floorplan never ran).

## SAFE-DESIGN checklist
1 Pins: PASS (k4 stage table: every input pin-captured, every output a flop; reset_landing 2 stages, relay split <= 32).
2 Reach: not measured (no floorplan); ring macros placed in the S corridor beside the event-pipeline logic.
3 Fanout: FAIL (census above): the VME drivers fixed; the k4-base drivers are COLL6's k5 fanout pass.
4 Depth: VME adds a 2:1 slot mux before each stage-group hold and before ld_desc (registered select copies); not timed.
5 Storage: FIXED vs main's VM_RT form: the 74-edge part of the event / read-expectation / fire pipeline is one SRAM ring
  (ot_hgi_coll_gq_vmring, 2 x ot_sram_1r1w_64x16_m1, D 65, registered in/out), not a 114-deep flop chain; slot banks 2 x 69 b flops.
6 Floorplan: k4 geometry + 2 small ring macros on the 43.2 lattice ((216,43.2) R0 / (259.2,43.2) MY, pin faces outward).
7 Clock: k4 single root + k2 leaves (unchanged).
8 Schedule: static; VM_RT 74 = the die's priced hcollgi round trip; ISSUE_AHEAD 1 = compiler collq_gather_1018.py ia rules (IA_GAP 11,
  slot reuse ND+1, RAW); no credits / ready.

## Evidence (Verilator 5.050, fleet)
COLLQ full default PASS mutants_rejected=8; tb_hgi_coll_gq_ia VM_RT 74: ia0 / ia1 / ia2 PASS bit-exact (exposed 1404 / 617 / 366 =
compiler every pair), +fault=5 FAULT PASS; mutants slot / dep / iaign REJECTED: results/rtl/hbm_vmearly_k4_1020/.
