# s81sl_cap_ed -- CAP-ED static E-column delay leaf (TOK.DS.BENCH.1, LEAD2-S81/TOK2 10-19)

`ot_s81sl_cap_ed #(.D(24))` sits between the E capture tree (`u_te`) and the root (`u_rt`) inside `ot_s81sl_cap #(.EDLY(24), .WL3DLY(16))`.
Why: the CAP root takes one word per edge and the six QF frames never merge (757a340ff); the exact packing
(results/rtl/s81_qf_producer_1019/cap_ed_calendar) gives a legal 12-pair six-frame calendar only with the E column +24 edges plus W lane 3 +16 (s_16_24; E-only cannot pack).
Cost: +24 edges on E return words (latency only); the compiler (retained_xs_program.py --placements s_16_24.json --shifts ...) owns D.

Bench (Verilator 5.050): tools/s81_slice/cap_ed_bench.sh -- base D 24 PASS (204 checks), RTL mutants D 23 / D 25 FAIL
(witnesses results/rtl/s81_qf_producer_1019/cap_ed_calendar/bench_l16e24/ed_m2{3,5}.run.log).

## SAFE checklist
1 Pins: PASS -- every input lands in the delay line's pin input register, every output leaves its pin output register, o_f a
  sticky flop; reset_landing 2 stages (kit) + ot_rst_relay inside.
2 Reach: PASS -- 38.88 x 34.56 um leaf; longest internal wire < 60 um; placed against u_te (W face) / u_rt E port (E face).
3 Fanout: PASS -- write-row decode drives 66 bits per row (row enable through the RF's own decode; no register > 32 loads in
  a critical cone besides the reset relay copies); verify kept copies at gate.
4 Depth: PASS -- one 21:1 read mux per bit, one stage at 833 ps.
5 Storage: PASS -- 1,386 b < 2 kb register-file ring (ot_hdc_delay_rf), no flop->flop hold chain.
6 Floorplan: fixed -- first gate e8bab98ef: std 996 um2 in 1,045 um2 (95 %); outline 51.84 x 47.52 = 48.5 % util; no macros, one std-cell band, aspect 1.13, pins <= 3.1/um.
7 Clock: PASS (gate to confirm) -- one centre root, ~1.55k sinks; io_hold_margin 0.03; pin-flop spread checked at --cts gate.
8 Schedule: PASS -- static; +24 edges handed to the compiler (packD_23) and logged in lanes/LEAD2-S81.md INBOX.
