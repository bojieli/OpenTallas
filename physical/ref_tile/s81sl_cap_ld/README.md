# s81sl_cap_ld -- static W lane-3 delay leaf (TOK.DS.BENCH.1, LEAD2-S81/TOK2 10-19)

`ot_s81sl_cap_ld #(.D(16))` delays CAP return lane 3 (R01 in the QF vehicle) before the W tree, inside
`ot_s81sl_cap #(.EDLY(24), .WL3DLY(16))`. The W tree carries four frames (L01 L02 L03 R01), so the E-only delay cannot
pack; exact repack s_16_24 + fullsix_l16e24 (results/rtl/s81_qf_producer_1019/cap_ed_calendar): no tree fault, only the
expected reset-CAP F9. Cost +16 edges on R01 words. Bench 5.050 tools/s81_slice/cap_ld_bench.sh: D16 PASS, D15/D17 FAIL.

## SAFE checklist
1 Pins: PASS -- pin input/output registers of the delay line; reset_landing 2 + ot_rst_relay. 2 Reach: PASS -- 43.2 um leaf.
3 Fanout: PASS -- row write enable 70 bits/row via RF decode; reset relay copies only. 4 Depth: PASS -- one 14:1 mux stage.
5 Storage: PASS -- 980 b RF ring, no flop->flop hold chain. 6 Floorplan: gate to confirm (no macros, one band, ~48 % est.).
7 Clock: PASS -- 1,136 sinks, TT/FF ins 114.2/85.8 ps, spread 3.0/3.3 ps; io_hold 0.03. 8 Schedule: PASS -- static, D owned by the compiler (+16 INBOX).
