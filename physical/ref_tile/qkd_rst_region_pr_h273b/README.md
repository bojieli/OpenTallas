# qkd_rst_region_pr_h273b -- HOLD 273 regional reset root with a dedicated output launch flop (KV-BIND4 10-19)

Native-pin successor of qkd_rst_region_pr_h273. The h273 route CLOSED (qkd_rst_region_pr_h273-h1-a11f46db5, TT +295.88 /
FF +29.67) but its view FAILS the die's native pin audit (check_rst_pin_view.py: pin b launch 223.8 ps TT > 220), so the
GEN9 die (kvs14r-a6998c101-gen9d) bound HOLD128 and the health retirement reset contract (263) stayed UNPROVEN.
Root cause: the core's output flop b also feeds its own hold logic (`if (b) hold <= HOLD_LD`), so the output pin net
(QN -> hold BUF -> INV -> b) also carried the internal loads (_249_ A1, _162_ A) across the tile.
Fix (structural, 0 cycles): core qkd_rst_region_po keeps b_int for the feedback and a KEPT twin b_pin with byte-identical
next-state logic that drives only pin b. Wrapper qkd_rst_region_pr_h273b: dly pin captures (as _pr) + core HOLD 273.
Die: kvsys_prep.sh binds this view first (OT_KV_RST_HOLD_CELL=qkd_rst_region_pr_h273b -> kv_die.py) when its CLOSED view
audits PASS; h273 then HOLD128 remain the fallbacks.

Benches (Verilator 5.050, fleet): h273b_exact H273B_PASS = output identical to h273 on all 675 cycles (POR, release,
re-assert, hold 273, re-release) and to the HOLD128 _pr through the first release; MUT 4 (legacy 8-bit hold truncation)
-> H273B_HOLD_SHORT; MUT 5 (pin twin one edge late) -> H273B_MISMATCH. Witnesses results/arch/kv_bind4_1019/h273b/.

## SAFE-DESIGN checklist
1. Pins: a -> a_q, dly -> 8 kept dly_pin flops, b launched by the dedicated kept b_pin (no other load); por_n -> 2-flop sync. PASS (fixed).
2. Reach: 12.96 um tile. PASS.
3. Fanout: ~42 flops, local; no register > 32 loads. PASS.
4. Depth: counters + compare, h273 worst stage 188 ps. PASS.
5. Storage: counters only. PASS.
6. Floorplan: no macros, full std-cell band, 12.96 square = the closed _pr / h273 die slot. Util ~35 % WAIVED (inherited slot).
7. Clock: one root, h273 spread 1.2 / 0.8 ps TT/FF; io_hold_margin 0.03. PASS.
8. Schedule: release calendar + hold identical to h273 (bench); 0 cycles. PASS.
