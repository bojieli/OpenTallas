HBM-CORE-LAT-R4 hfd_ep_static (variants A 916cfe0a x5, B 81698133 host_ep x1), 2026-10-27 ~01:15-02:10 PDT. Predictions = PLAN MODEL (uf_phys3_v1), UNCHECKED.

(a) LEC dead bits -- FIXED (commit 62a977d432, RTL rtl/hbm_accel/tu/ep_static_20261015/ot_hep_rx_store.sv):
  ot_hep_rx_block.fault_cause[4:3] are reserved: never written (also never in the H-COLL template ot_hgi_coll_offdie_rx_block),
  only reset to 0 -> reset-only self-holding flops (D=Q). Yosys folds them to constant 0; LEC (no init assumption) cannot prove
  a self-loop flop constant -> 2/16312 NOT EQUIVALENT (u_bout_fault_cause.q[3:4]). Root-cause fix: the reserved bits are
  constant-0 wires (assign fault_cause = {2'b00, fc}; fc[2:0] = the 3 real sticky causes). Port width / pin tables unchanged.
  Declared under the COORD 10-25 dead-inputs/bits rule. No RTL owner fix existed (last change in the dir = H-LKEP route 4;
  no open branch touches it).
  Evidence (CHECKED): kit LEC A and B EQUIVALENT 16318/16318 (lec_A_r4.json, lec_B_r4.json); face_guard 2286/2286, port_bind
  0/0 both; bench tb_hfd_ep_static MUT=0 PASS 768/768 both ways, MUT=1 FAIL (bad 190/186, caught) (bench_r4.txt). The bench
  script file list was stale (KP4 decoder split) -> now the run_pdie_link_gate.sh list.

(b) Re-pack (no CTS): kits intel2:/srv/opentallas-scratch2/claude/hbm-core-lat-r4-ep/kits/hfd_ep_static_{916cfe0a1db9,81698133efff}-_r4
  (= R3 p1m kits + fixed RTL + column shifted W per GEOM-REVIEW-16 01:11: x 38.88 -> 34.56, strips W 30.24 / E 40.39 um;
  centre band y 173.09-202.77 holds the centre entry 125.28,187.92). Synth + LEC + floorplan + place exit 0 (A and B).
  Outline 250.56 x 375.84 kept = the plan slot in all 4 parents (NW_io x2, NE_io, q_spb0, vsN0; B2n core_reshape); SRAM
  4 x 171.288 x 77.784, SYMMETRY X Y (no R90) with M4 pins on the short W/E edges -> one column is forced (2x171 > 250).
  Clock sinks (A, CHECKED from geo): W strip 4162 (SRAM-side fcore regs), S band 2801 (1477 S-face M5 pins: SerDes sd_tx/sd_rx
  512+512, rx_pin), E strip 2153 (798 E-face M4 pins: tx_frame/rx_pin), MID 815, N 46 -> a 1-D RING.
  Islands: 4 fixed level-2 island sets (inputs/isl_sets.txt: I1 strip midpoints per GEOM-REVIEW-16; I2/I4 lower; I3 two S-band
  islands) x splits/smax, shared planner core_infra_htree (plan() and the R6 ring planner), --macro-vertical-pass; the same
  sites serve A and B (same macro placement).
  RESULT: every structure FAILS 12.3 (sweeps/*.txt): best r6_I1_nb8 TT 391.6 w31.8 / FF 305.6 w27.2; best window I3 2,2,8,4
  TT 412.7 w23.7 / FF 317.2 w20.0; no islands TT 491.8 (R3 RTLMP column was 327 w24). Planned path wire 527-709 um against the
  geometric floor (entry -> S corners) ~305 um Manhattan / 360.7 um maze (core_islands.py, inputs/isl_A_k4sym.json).
  Root cause: equal-length levels on a ring. The B level must reach +-130 um along the strips / S band, and every edge of a level
  is padded to that max -> ~1.7x the floor. The floor itself (~305 um) gives ~250-270 TT only for a near-Manhattan tree.
  Render (viewed): r4_A_colW_r6I1nb8.png (+ r4_A_colW_I3s2284.png).
  Structural options (need COORD / plan owner): (1) a delay-balanced (unequal-length, plan-computed per-tap sizing) in-core tree
  near the 305-um floor = new planner mode; (2) plan pin change: pull the S-face SerDes/rx_pin and E-face pins away from the
  corners (HBM plan owner HBM-MU-QUAD-3) to cut the floor. No CTS launched.
