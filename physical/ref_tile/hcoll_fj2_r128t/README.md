# hcoll_fj2_r128t -- ot_hgi_coll_fj_q2_r128 (SAFE q2 COLL parent hard child u_fj, ROWS 128) -- FALLBACK (evidence; NOT submitted)

Owner: LEAD3-HBM / HBM-COLLFJ2 (10-19). Branch claude/collfj-1019. Structural successor of hcoll_fj2_r128w (LEAD3-HBM rejected its
~300-load rst_q waiver; SAFE items 1/3 binding) -- same top name / ports / pin faces, so the q3/q2 lp_ars parents bind it unchanged.
RTL: body ot_hgi_coll_fj_core_s128 + ot_hgi_coll_static_program_target_s128 (rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_safe_leaves.sv);
the closed ot_hgi_coll_fj_core / ot_hgi_coll_static_program_target stay unchanged for every other user and as the lockstep reference.
Geometry: 103.68 x 71.28 um (1.45:1); macro ot_sram_1rw_128x64_m2_r2c2_p192_mir (u.u_program.u_flow) at [43.2, 23.76].
Benches (Verilator 5.050, results/rtl/hbm_coll_fj_1019): q2 parent EQ PASS (s128 body == old fj every output every cycle) + 3 EQ mutants
REJECTED; fj mutants LATE_SPC + LA_STALE REJECTED (parent EQ); random beyond-contract miter programme_target_s128 == programme_target
#(ROWS 128) PASS 956,173 cycles (300 configured / 387 starts / 2,668 faults / 8 drain-edge forwards), mutants LDH_NOFWD + LA_STALE REJECTED.
Gate (claude/collfj-1019 @8c8113b7a, --cts --remote auto): PASS 0 fail 0 warn; std area 1551 um2 + macro 899, util 31% (std density 31.2%);
flops 2,560; TT/FF insertion 199.2/166.6 ps, pin-flop spread 33.5/32.0 ps; placement setup WNS +81.7 ps (r128w +1.2/+4.7),
hold +50.3 ps; GRT overflow 0 (M2 31.62%); no high_fanout finding; reset family as r128s (ot_rst_copies.tsv), 12 kept DFF cells in 1_2_yosys.v.

SAFE-DESIGN checklist:
1 Pins: PASS -- every input registered at its pin in RTL (fj_core_s128 = fj_core capture rung), every output flop Q; rst_n landed in 2 registered
  stages at the face (reset_landing, 1 sink), then the RTL copy stage.
2 Reach: PASS -- tile < 105 um on a side, no wire near 405 um.
3 Fanout: FIXED -- the ~300-load rst_q is now 12 KEPT copies rst__ot_rlv (same release edge), loads re-pointed by region by ot_rst_copies.tcl
  (reset_relay_split max_loads 32): as r128s; yosys kept all 12 (cells ot_rrs__u_ot_pr_core_u_rst__ot_rlv__c0..c11). Frame-accept enable
  no longer fans into 2k flow flops (flow store in SRAM).
4 Depth: FIXED -- r128w worst endpoints were assembly / flow / fault D behind addr_q -> loaded[a_row] 128:1 + OR192 spare check + target compare;
  these are now registered one edge early from the captured inputs (tm_q, seg_q one-hot, ahb_q, dsp_q, dbad_q, ldh_q with the drain forward):
  textbook depth 378 ps (was ~520), setup +81.7 ps.
5 Storage: FIXED -- flow table 128 x 16 b (2 kb runtime-indexed flops) -> ot_sram_1rw_128x64 (read = scan lookahead, write registered);
  assembly 1.5 kb stays flops (< 2 kb, read by the fixed drain step counter, written once per segment).
6 Floorplan: FAIL (util 31% < 40%; the 43.2-lattice x origin forces width >= 103.7 um) -> fallback NOT submitted -- macro >= 20 um from every core edge on both pin faces (W addr/wd, E rd), on the track lattice;
  util 31% (std density 31.2%); aspect 1.45:1; one connected std-cell band around the macro; pins on full faces <= 6/um.
7 Clock: PASS -- one scalar clk, centre-fed tree, pin-flop spread 33.5/32.0 ps TT/FF (<= 80), io_hold_margin 0.03.
8 Schedule: PASS -- static; 0 port edges moved (parent EQ every output every cycle; the SRAM write lands 1 internal edge later, >= 54 edges before
  the only reader) -> 0 cycles/token DS and Qwen.
