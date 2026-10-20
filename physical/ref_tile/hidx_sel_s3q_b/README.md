# hidx_sel_s3q_b -- quadrant tile ot_hidx_s3_q (x4) of the landed IDX selector cluster
L2H-IDXSEL s3 (LEAD3-HBM route B, 10-19/20). The HBM IDX selector becomes an lp.py LANDED CLUSTER (die master
ot_hbm_idx_selector_s3, port list == the die's selected-only master ot_hbm_idx_selector_static_sel): ONE hardened quadrant
tile ot_hidx_s3_q used x4 + this ctl tile ot_hidx_s3_ctl, wires-only flat parent ot_hidx_s3_flat ->
rtl/hbm_accel/index/sel_s3/lp/ot_hidx_s3_flat_lp.sv (tools/landed_parent/lp.py, spec tools/landed_parent/specs/hidx_sel_s3.json:
5 regions, 20 landed crossings, D 4 / E 2, +3 edges each, reschedule mode because ctl <-> quadrant is a loop).
Predecessors: s1a/s1b GATE_STALL in CTS hold repair (one clk_ctl root, 42,772 sinks, 18-23k hold endpoints);
s2a/s2b (five roots inside one leaf, ~7k unlanded inter-root crossings) FAIL at floorplan (IO-domain coverage).
Schedule (tools/hbm_idx_static_calendar.py table registered_s3): sel_in 7 (op word: ctl pin flop + ctl out flop + landing 3 +
quadrant pin copies + P2), sel_in_line 2, sel_out 1, sel_choose_rt 8 idle edges after every op5 run (threshold back to the
quadrant 12 edges after the deciding histogram read, ties 13; flat core 3 / 4). IDX frame 1411 -> 1433 edges (+22, +1.56%).
Benches (Verilator 5.050, fleet): rtl/test/hbm_idx_static/run_selector_s3.sh (full shape, crafted margin frame + 3 historical
frames, selected stream exact vs gold): m0 PASS; d1 d3 d5 d6 rt7 dr3 l1 l2 FAIL (witnesses results/rtl/hbm_idx_static/selector_s3/sel);
lp lockstep + audit rtl/hbm_accel/index/sel_s3/lp/ot_hidx_s3_flat_lp_bench.sh (MUT 1 2 4 5 FAIL);
full-shape scheduled proof rtl/test/hbm_idx_static/run_scheduled_s3.sh (IDX_SCHEDULED_GATE_PASS; see results/rtl/hbm_idx_static/selector_s3).

Geometry (b): 259.2 x 216 (aspect 1.2); 3 x ot_sram_1r1w_256x256_m2_r2c2 R0 at x 43.2 (43.2 lattice), stack S
(y 4.32 / 45.408 / 86.496, abutted at the 41.088 pitch as s1), full-width std-cell band N (y 127.56-216); W channel 43.2 (in_line + control pins, pin
flops / relays), E channel 43.2 (macro pin face, selected_line_o pin flops). Pins: W in_line (592) + cw/thr/ties/ret/qfault_o
(70) 3.1/um; E selected_v_o + selected_line_o (593) 3.0/um; clk / rst_n on the N face (band side).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- cw lands in two kept P1 copies (pa/pb, ot_hidx_s3_rep), thr in five kept threshold copies, ties in ties_r,
  in_line in in_p1: every input bit's first stage is a flop; every output is a register (selected_v_o / selected_line_o /
  ret / qfault_o); rst_n -> ot_rst_relay (2 sync + region stage) = 2 registered stages at the face (reset_landing.json).
2 Reach: fixed -- in_line pin flop -> in_p2 -> SRAM wd / lane compares (<= ~260 um per hop); S3 register -> selected_line_o pin
  flop at the E face (<= ~260 um); worst geometric pin-to-corner span 459 um Manhattan (W-top control pins to the E-bottom
  corner): the P2 copies sit beside their consumers, so pa/pb -> copy hops stay inside the band / channels (gate reach check).
3 Fanout: fixed -- per-consumer KEPT copies (non-parameterised ot_hidx_s3_rep, SYNTH_KEEP_MODULES; keep_module_audit): per lane
  the op2 write/hist selects, line clears, pack chain; per SRAM re/ing/addr; per 8 histogram bins; per 2 histogram read bits;
  per 4 lanes a threshold copy; each pin bit drives <= ~12 copies. Known: nf>=16 remains a 2 x 592 select net (buffered tree).
4 Depth: s1 textbook depth 638.5 ps on the same quadrant logic (guidance ~600 ps, ~20 levels): log-depth 4-lane prefix ranks,
  registered qfault terms, registered one-hot line selects; confirm in this gate (any > 600 ps path -> pipeline it).
5 Storage: PASS -- the 3 SRAM macros hold the lines; histogram 64 x 14 b is a fixed-index counter array (each bin a dedicated
  adder, 64:1 registered read): waived as counters, not a runtime-indexed store. No delay line >= 3 deep.
6 Floorplan: PASS -- macros on the 43.2 lattice in x (y abutted at 41.088, waived as s1: 41.064-um macros), 43.2-um channels on
  both pin faces (macro face <= 6 pins/um shared by 3 macros, halo 5.4), outline from ~21.3k um2 macros + ~9-10k um2 std
  (s1 synthesis 43.9k / 4 quadrants incl. shell) = util ~0.55; aspect 1.2; one full-width std-cell band.
7 Clock: PASS -- ONE root per tile (~7.5k sinks + 3 macros, ~1/6 of s1's 42.8k), clk on the band face centre; region clock of
  the cluster (ck_q<n>), every crossing to the ctl is landed in the parent; judged on pin-flop spread <= 80 TT+FF;
  io_hold_margin 0.03.
8 Schedule: PASS -- static, no credits/backpressure; every added edge priced in registered_s3 (frame +22 edges).
