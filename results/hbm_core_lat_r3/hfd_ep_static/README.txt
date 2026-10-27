HBM-CORE-LAT-R3 hfd_ep_static (B2o outline 250.56 x 375.84; 2026-10-27 ~00:05-01:05 PDT). ALL PREDICTIONS = PLAN MODEL, UNCHECKED.

Interface kept: B2o pin tables exactly (variant A pins sha256 916cfe0a1db9.. = sorted-tuple sha8 7e1768be, 5 inst; variant B
81698133efff.. = 0d2c6a1d, u_host_ep). Only change: clock pin clk M5 (2.328, 0.019) -> outline centre (125.28, 187.92) via
a trial core slice (inputs/slice1_hfd_ep_static.json, master_plan_sha256 TRIAL-no-frozen-master-plan; HBM master plan not frozen).

Kits (intel2:/srv/opentallas-scratch2/claude/hbm-core-lat-r3-ep/kits/, gen_core_kit_hbm.py --sigmax M5 --master-slice --trial):
  hfd_ep_static_916cfe0a1db9-_p1  (A, RTLMP macros)       synth + sdc_lint PASS, face_guard PASS 2286/2286, port_bind PASS
  hfd_ep_static_81698133efff-_p1  (B, RTLMP macros)       same gates PASS
  *_p1m (A/B, aligned SRAM column inputs/macro_place_ep.json, same netlist)   floorplan+place only
  LEC (tools/die_plan/lec.py, in run_kit): NOT EQUIVALENT 2/16312 points (A and B identical): u_bout_fault_cause.q[3:4];
  synthesis removed u_fcore.fault_cause[3:4] (D = bd_cause[3:4] = OR of ot_hep_rx_store.fault_cause[3:4] of both banks:
  async-reset-0 bits that the RTL never writes -> constant 0 after reset, but LEC does not prove the constant). B2n kit
  (codex-hbm-face 57f33b92) had face_shell const_out fault_cause[3:4]=0; the init-safe shell (f90c555daf) no longer does.
  Fix belongs to the RTL owner (write the bits or narrow the store fault_cause) -- not done here. lec_A_p1.json.
  run_kit stops at the LEC preflight -> floorplan+place via scripts/place_only.sh (STOPS before CTS).

Phase-1 placement (no tree, centre clock pin): 4 x ot_sram_1r1w_64x512_m1_r2c2 (171.288 x 77.784, pins W+E edges, OBS
M1-M4, PG M4) = 60 % of the core; 9977 clock sinks (incl. 4 SRAM CK) form a RING: S band (S-face 1477 M5 pin regs),
W and E strips beside the SRAM column, a mid band at the entry; N band ~empty.  Std-cell fill ~13 %.

Plan (core_infra_htree, 12.8b equal structure, centre entry) -> phys_gate OT_PHYS_FIT=uf_phys3_v1 (sweeps/*.tsv):
  NO structure meets 12.3/12.9d.  Best A (RTLMP place, 2,2,4,8 smax 70): TT rise 327.2 w24.2 / FF early 251.7 w20.6 FAIL;
  lowest TT 285.7 (2,2,4,8 smax100) has window 65.6.  B best: 323.9 w30.1 / 250.1 w25.5 FAIL.  Aligned centred column
  (p1m): 396-530 TT (worse: W/E strips cut apart).  Root cause: equal-structure level lengths ~168/94/87/62 um = 410-430 um
  path wire (entry -> farthest S-band corner sink Manhattan ~305 um); leaf nets spread along 1-D strips -> windows.
  core_plan_to_infra/core_infra refuse the build ("unequal-count tree model target FAIL") -> no phase-2 kit, no CTS.
  12.8b: core cannot meet 250+-20 TT with a centre entry -> restructure (internal H-tree + in-core islands first; COORD:
  the parent brief says islands none needed).

Tool change (claude/hbm-core-lat-r3-ep-1027, test tools/die_plan/test_core_infra_htree_vpass.py, 3/3 PASS run directly,
no pytest on intel2): core_infra_htree.py --macro-vertical-pass (macros with OBS below M5 = node keep-outs crossed
vertically only) and minimax_site radius widening (was a crash with a centred macro column).  Default output byte-identical
(plan.tcl sha e0b69661 before/after on the A geo).
Renders (viewed): r_p1_s2248m70.png, r_p1m_s2444m100.png -- plan edges drawn as L shapes, not maze paths.
