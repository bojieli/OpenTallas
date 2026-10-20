# hidx_sel_s2a -- L2H-IDXSEL s2 REGIONAL-ROOT successor of hidx_sel_s1a (SAFE fanout successor of the HBM IDX selector (ot_hbm_idx_selector_static), 10-19
Predecessor route hidx_sel_g4p-g4p-90b8aed47 EARLY_FAIL_SETUP: post-CTS TT -578.7 ps, 8,529 endpoints, TNS -1.41 us.
Worst op_r[0] -> core.qfault[3]: 396 ps wire + 896 ps logic. Cause: ONE pin flop per op/pass/addr/k bit fanned out to
all four quadrants and 12 SRAMs (op decodes select 4 x ~2.4k line bits, addr drives 12 SRAM ports + 4 x 64:1 hist read
muxes), the qfault cone OR-ed hazard terms + 16 x 20-bit id compares in one stage, a single threshold register fed
4 x 48 compare inputs, and S2/S4 prefix ranks were 16-step serial chains (gate depth 772 ps / 20 levels).
Structural redesign (rtl/hbm_accel/index/ot_hbm_idx_selector_static.sv, same arithmetic/selection):
- P1: 9 kept relay copies of {addr,pass,op} (2 per quadrant + ctl) and k, in_line relay per quadrant; P2: per-consumer
  KEPT registered one-hot copies in ot_hidx_sel_rep (non-parameterised 16-b register, SYNTH_KEEP_MODULES=ot_hidx_sel_rep;
  keep_module_audit checks it survives): per lane (64) op2 write/hist selects, op1|op7 and op7 line clears, emit and
  pack valid chains; per SRAM (12) re/ing/addr; per 8 hist bins (32) clear + add enables; per 2 hist read bits (28) addr;
  per 4 lanes (16) + hist (4) threshold copies; 2 x 4 fill copies per quadrant for the barrel.
- S2/S3/S4 tie and pack ranks: 4-lane local counts + group bases (log depth). qfault: hazard terms, 16 per-lane id
  compares and count checks registered before the sticky OR (fault +1 edge). out_line valid bit from a registered mask.
- Shell: pin flop per input (P0), output relay + pin flop per output.
Latency / schedule: core inputs +2 (uniform), outputs +1: calendar PIN table sel_in 1->3, sel_out 1->2;
tools/hbm_idx_static_calendar.py frame 1408 -> 1411 edges (+3, +0.21% of the IDX frame); selected stream, link fields and
first TX +3 edges; no selector-relative field edge moves. Full-shape proof run_scheduled.sh launched (pending_results).
Benches: rtl/test/hbm_idx_static/run_selector_vl.sh on Verilator 5.050 (die master SHELL=1): MUT0 PASS; MUT1 ties,
MUT2 emitted id, MUT3 lane-5 write-data select copy one edge late, MUT4 lane-3 emit copy one edge early: all FAIL.
iverilog run_selector.sh SHELL=1 and core (SHELL=0) MUT0 PASS. Witnesses: results/rtl/hbm_idx_static/selector_safe_1019/.
Parallel variants (owner PARALLEL rule): hidx_sel_s1a / hidx_sel_s1b = same RTL, different macro stack height; bind the
first to close, cancel the other.
Geometry (s1a): d4g slot 600 x 450 (exact, FACES_ONLY), macro columns x 86.4 (R0) / 302.4 (MY), macro stack N (y 194.4-440.9), full-width std-cell band S (y 2-194).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every data input and output is a kept pin flop in the die-master shell (outputs: relay + pin flop);
  rst_n -> ot_rst_relay (2 sync + region stage) = 2 registered stages at the face (reset_landing.json).
2 Reach: fixed -- control: pin flop -> P1 relay -> P2 local copy (two hops for the <= ~700 um pin-to-E-column span);
  in_line: pin flop -> in_p1 -> in_p2 (W face to the E column SRAM faces ~480 um in two hops); outputs: core reg ->
  relay -> pin flop (q0/q1 to the E/S faces <= ~500 um in two hops).
3 Fanout: fixed -- per-consumer kept copies (above); no control register drives more than ~40 loads; copies are in a
  non-parameterised kept module (no $paramod rename), verify instance count 172 x ot_hidx_sel_rep in the gate netlist.
  Note: nf>=16 (fill+dcnt) remains a combinational 2 x 592 select net (buffered tree from two local registers).
4 Depth: fixed -- serial 16-step rank chains replaced by log-depth 4-lane groups; qfault cone split; wide line
  selects driven by registered one-hot copies. Gate depth to be confirmed (predecessor 772 ps / 20 levels).
5 Storage: PASS -- 12 SRAM macros 256x256 hold the lines; histogram 64 x 14 b x 4 is a fixed-index counter array
  (each bin a dedicated adder) with a 64:1 registered read: waived as counters, not a runtime-indexed store.
6 Floorplan: fixed -- macros on the 43.2 lattice in x with a 43.2-um centre channel for the wd faces of both columns
  (~5.8 pins/um per face); the 6-high stacks abut at the predecessor's legal 41.088 pitch (y lattice waived: 6 x 41.06-um
  macros); outline = exact d4g slot (util ~0.49 from the predecessor synthesis 0.469 + ~12k relay/copy flops); aspect 1.33.
7 Clock: fixed (s2) -- s1 gates GATE_STALL in CTS hold repair (one clk_ctl root, 42,772 sinks, std-reg insertion 695..998 ps, 18-23k hold endpoints). Five regional roots: clk_q[q] per quadrant (lanes, histogram, pack/emit, its 3 SRAMs, its o1 output relay), clk_ctl for the choose pipeline, reset relay and all pin flops (clk_q pins E face SE corner beside clk_ctl). Data crossings reg->reg (ctl pin flop -> quadrant P1/in_p1, quadrant o1 -> ctl pin flop); logic crossings (ctl threshold/tie copies -> quadrant compare, quadrant histogram read -> ctl sums) under same_pll_fixed_phase (setup 150/210, hold 100 inter-root reserve). Judged per root on pin-flop spread <= 80 TT+FF; io_hold_margin 0.03.
8 Schedule: PASS -- static, no credits/backpressure; +3 edges handed to the IDX calendar compiler and priced above.
