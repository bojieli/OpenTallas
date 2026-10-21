# qfd_tt_head_static_h16t -- h16s successor (QW-ORPHANS2 10-20), TOK.QW.LAYER.3.SEG head leaf

h16s gate FAIL (3 fail / 6 warn), causes and structural fixes:
1. reset_landing: rst_n reached 5 raw flops (u_ot_pr_core.u_0 + 4) -> kit reset_landing ON (ref_tile rst_l0 -> rst_l1 at
   the face; +2 reset-release edges, a scheduled constant; no data edge).
2. CTS "OT_HYBRID: CTS source ck_pm0 must reach only standard-cell clock pins": ck_pm0/ck_pm1 drive only raw SRAM clock
   pins (5 / 3) -> exact soft_root_macro_bindings (main a74f61f32 multiple_cts_roots leaf form), one per SRAM instance.
3. textbook depth 4449 ps / 138 levels (REFUSE-level, reported WARN): bound_r3 was emitted from `synth -noabc` generic
   gates frozen one-per-kept-cell (ripple compare/select chains, no restructuring possible downstream). bound_r4
   (results/rtl/qw_head_safe32_1020/bound_r4/run_bound_r4.sh) runs ABC gate mapping on the SAME bit_generic.json, then the
   SAME bounding pass (load-cap 16, flags as r3): source depth 153 -> 36 levels, cells 36212 -> 23437, FF 6481 -> 6319.
   Remaining deepest registers (RTL): rom_cmd 37, fixed_issue sched_q 36 / cycle 33, ctrl_me dts_all 32 (57 bits).
   If the gate's TT timing on them is negative, the next step is RTL pipelining of those cones (priced cycles).

## SAFE-DESIGN checklist
1 Pins: flow pin registers ON; reset landed by the kit (2 stages) -- fixed
2 Reach: outline 345.6x302.4, gate measures -- gate
3 Fanout: bound_r4 bounding pass load-cap 16; gate native census (mapped) must PASS <=32 -- gate
4 Depth: 36 source levels (was 153) -- WARN until gate TT timing
5 Storage: FIFO in 6x 32x128 SRAM + 2x 64x512 programme store -- PASS
6 Floorplan: h16s geometry (8 macros on the 43.2 lattice, >=35 um pin-face channels), fill ~40% lattice-bound -- WARN (as h16s)
7 Clock: multiple_cts_roots ck_head / ck_pm0 (5 SRAM) / ck_pm1 (3 SRAM), raw SRAM sinks bound; spread <=80 TT/FF -- gate
8 Schedule: 0 added data edges; reset release +2 (constant) -- PASS
Proof owed: bound_r4 benches img0/imgh + BMUT3 on V5.050 (pending_results); ABC is logic-preserving but r4 is a new
emitted netlist, so the benches (and the formal native-vs-RTL proof still owed from r3) must be rerun on it.
