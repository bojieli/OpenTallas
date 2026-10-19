# s81lk_kp4_dec_col -- S81 SerDes RX KP4 decoder, landed column cluster (TW7-S81SERDES 10-19, tree S81.STA.OWN.7)

Top `ot_s81_kp4_dec_native_flat_lp` (tools/landed_parent/lp.py from Codex SERDES-NATIVE `ot_s81_kp4_dec_native_flat`,
spec tools/landed_parent/specs/ot_s81_kp4_dec.json with column region centres; record
results/arch/serdes_native_1019/ot_s81_kp4_dec_native_flat_lp_record.json).  Kit spec
tools/ref_tile/specs_s81link_col/s81lk_kp4_dec_col.json.  Level 1 of the column parent `ot_pdie_serdes_col`
(plan results/arch/s81_link_col_1019/serdes_column_plan.json): the outer level (PMA abstracts physical/s81_pma_col +
this cluster + rate_match + enc + TX relay rows, rck/clk asynchronous) needs async regions that lp.py / landed_cluster do
not support (rate_match has wclk + rclk in two regions; a landing across rck/clk is not a valid CDC).

Children (closed column re-pins, routed pin-flop spread TT/FF): dsyn t2-e3dea7351 (43.2, 25.92), ddly col-e7e375bce
73.1/69.3 (25.92, 285.12), dchn col-07c70c35d 46.4/43.4 (25.92, 457.92), dout col-f43086fd3 44.9/41.1 (25.92, 699.84).
Outline 302.4 x 959.04: the plan's 259.2 column cannot hold any child under the 20-um macro-edge rule (dout 248.4 needs
>= 292.7) -> SLOT CHANGE for DIE-S81-LEAD / MU-DIE-S81 (column 302.4 wide).

## SAFE-DESIGN checklist (owner 10-19)
1. Pins: PASS -- every port is a face register (u_face_* ot_pl_pad N 1, in its region); reset lands in RTL (rst_n ->
   u_lpr_root on ck_syn -> regional runs depth 3 -> per-child pads), one sink on the port net (reset_landing disabled
   with that reason).
2. Reach: PASS -- regional reset runs 2 hops to chn/out (reach 405); every child seam is a landing (bank wires are
   multicycle -setup 2 / -hold 3), longest bank ddly N -> dout S ~268 um, syn E -> chn S ~430 um on a multicycle bank.
3. Fanout: per ot_pl_land (the standard landing cell shared with the closed landed parents); judged at the gate.
4. Depth: PASS -- wires-only parent; logic = ring write / 4:1 read select.
5. Storage: waived -- landing rings are D 4 flop ring buffers by the LANDING-CONTRACT (no runtime-indexed array).
6. Floorplan: children on an 8.64-um lattice (WARN vs 43.2; on-track checked by the kit), channels >= 20 um (edges
   23.76, gaps 43.2 / 25.92 / 47.52), pin density <= 4.4/um (p_d 544 on S 4.32-129.6 under the PMA rx q face, q_d 512 on N
   142.56-272.16 under dout's q pins); aspect 3.2:1 waived (die-edge column slot); full-width std-cell bands between the
   children joined by the W (>= 23.76) and E (>= 36.7) channels.
7. Clock: PASS by construction -- 4 regional roots ck_syn (S, under dsyn clk), ck_dly / ck_chn (W, in the gaps beside the
   ddly / dchn clocks), ck_out (W, at dout's W clk pin); landed crossings; io_hold_margin 0.03; pin-flop spread per root
   measured by the gate (TT+FF <= 80).
8. Schedule: PASS -- static; +6 rx edges (outputs q_* +6, n_corr/n_unc +3, reset release +3) in the record's compiler
   block (dv_price KP4_DEC_HW_CYCLES -> q 74, Codex SERDES-NATIVE model).

Benches (Verilator 5.050): tools/s81_link/run_serdes_col_bench.sh col (PASS 6000/6000) + mut1 / mut2 (FAIL, witnesses
results/rtl/s81_link/col_1019/mut{1,2}/run.log).  The lp lockstep bench is not a witness (random p_d never locks: MUT 1 PASSES).
