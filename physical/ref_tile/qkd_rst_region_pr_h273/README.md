# qkd_rst_region_pr_h273 -- regional reset root with HOLD 273 (KV-HEALTH 10-19)

Wrapper of qkd_rst_region_pr (claude/kv-retire-1019 sized core: hold counter HW = max(8, clog2(HOLD)) = 9 bits) with
HOLD 273. Owner 10-19: "size the HOLD counters for 273 (no 8-bit wrap); default-on for the MU release build". The health
retirement contract needs every region held >= 263 edges after a re-assert (source clear + plane depth + 64 skew);
HOLD 128 cannot hold a 183-edge plane (the plane bench's hold128 mutant re-latches a stale fault).
Die: kvsys_prep binds this view for qkd_rst_region when OT_KV_RST_HOLD=273 (kvs14r default) and the view audits PASS;
otherwise HOLD128 stays and RUN/RST_HOLD_DIAGNOSTIC marks the run NOT a die result. Same slot / faces / straps as _pr.
Benches (Verilator 5.050, fleet): H273_PASS (calendar identical to the HOLD128 _pr reference cycle by cycle; re-assert
held exactly 273); MUT4 (legacy 8-bit truncation, HOLD 273 & 255 = 17) -> H273_HOLD_SHORT (witness
results/arch/kv_health_1019/tiles/tb_h273_m4.log).

## Gate (--cts --remote auto): WARN (util only), PNG reviewed by Claude KV-HEALTH
GRT overflow 0; setup WNS +298 ps, hold WNS +51 ps; 41 sinks, TT insertion 55.6 / FF 40.4 ps, spread 1.2 / 0.8 ps.

## SAFE-DESIGN checklist
1. Pins: a -> a_q and every dly bit -> kept dly_pin flop (as _pr); b registered; por_n into the 2-flop synchroniser. PASS.
2. Reach: 12.96 um tile. PASS.
3. Fanout: 41 flops, local; no register > 32 loads. PASS.
4. Depth: 188 ps worst stage. PASS.
5. Storage: counters only (< 2 kb). PASS.
6. Floorplan: no macros, full std-cell band, square 12.96 exact = the closed _pr die slot. Util 35 % WAIVED: exact
   inherited slot of the closed _pr (die reset-relay lattice), +1 hold flop over _pr.
7. Clock: one root, spread 1.2 / 0.8 ps TT/FF; io_hold_margin 0.03. PASS.
8. Schedule: release calendar unchanged (bench cycle-identical to _pr); only the re-assert hold grows (reset path,
   not a token cycle). PASS.
