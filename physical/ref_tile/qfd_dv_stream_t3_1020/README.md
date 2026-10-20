# qfd_dv_stream_t3_1020 -- Q.SAFE.STREAM native-32 successor (QW-STREAM3, LEAD4-QW, 10-20)

Top `qfd_dv_stream_tile` (rtl/qwen_dv/qfd_dv_stream_tile.sv), same ports / pin plan as t2. Spec generator
tools/ref_tile/specs_qw_stream_1019/mk_specs.py; parallel compact fallback kit qfd_dv_stream_t3c_1020 (259.2 x 380.16,
same RTL). Branch claude/qw-stream3-1020.

## Why (failed census)
Both CLOSED t2 routes (qfd_dv_stream_t2_1019-s2-49ac29c7e / t2c-c2-49ac29c7e) FAIL the actual mapped native census
(Codex packet 0017710ea, results/rtl/qw_stream_mapped_census_1020): 211 drivers > 32, max 69, 33,987 roots. Classes:
32-bit select groups at 2 mux pins per bit (cm_c 64, te_c / xe_c / xw_c 40-66, pe_c / pw_c 33-34, cv_c[4] 56), raw
valid pins sw_v / se_v 37, combinational tap predicates 33, the complete AND driving 69 copies, write-any 36, lane-1
decode wa_q[26] 36 / hi_hit 33, wa1_c[32] 37. A CLOSED route does not release a failing source topology.

## Structural fix (no squeezing)
- Every wide select is a kept 14-bit LEAF (2 mapped pins per bit -> <= 28 loads); side controls (valid, tw_we, xt_v /
  conflict, fault terms) are separate leaves.
- Pass side: face ROOT bank (3 kept copies per leaf family of v / kind / dst / sid; tw / x-tap / ubad roots) -> select
  LEAF bank one edge later (<= 27 leaves per root, predicate per root) -> relay / tap registers. Payload carried one
  extra edge (sw_q0 -> sw_q1) so header and payload stay coherent.
- Own writes: two decoder copies (slots 0..31 / 32..63) with a two-level digit decode; P1 = BF16 RNE into 4 kept lane
  copies (16 loads), registered one-hot select (16 loads), slot-hit copies per tree; P2 = assembly xb plus NK = 9
  independent complete trees, each on its own kept copy of the mask xm / open bit (3 copies) / slot hit, each driving
  <= 27 kept P2 leaves (insertion E / W with the direction copy of that tree, eword enables, ebeat, x-tap emit). No
  write-any term is needed in the leaves: complete can only be 1 on a write edge (op = 1 holds a not-complete mask).
- Insertion reads the assembly xb on the edge after completion (eword only holds the x-tap fall-back word), so the
  own path is one edge shorter than t2.
- Config: 3 cv roots (east dirs / west dirs / tag), direction copies per tree, tag in two 14-bit halves.

## Mapped census (pre-gate, yosys 0.68 with the ot_keep_regs.tcl keep steps, ASAP7 RVT TT, results/rtl/qw_stream3_1020/census)
39,042 roots, zero role errors, max 30 apart from rst_n (397 drivers at 28 = the 14-bit leaves); rst_n 725 loads ->
reset landing 28 kept copies (<= 26 each). 16,480 flops (725 reset), 7,077 um2 cells. The gate re-runs the mandatory
census on the ORFS netlist (authoritative).

## Priced schedule (static; no credits, no backpressure) -- reference qfd_dv_stream inputs delayed
| path | edges vs t2 | t3 delay vs qfd_dv_stream |
|---|---|---|
| sw_i / se_i / sid / cfg -> relay so_e / so_w, fault | +1 per tile | DP = 2 (face root + leaf) |
| sw_i / se_i -> table tap tw_*, x tap xt_* (pass words) | +1 per tile | DP + 1 (interior tap relay) |
| SU own x writes xw_* -> emitted beat, own x tap, beat fault | -1 | DX = 2 (face + P1; pbad combinational at P2) |
| reset | 0 | +2 (landing) |
II unchanged (one 8-lane write per edge, one beat per 8 edges, continuous). The SU issues own x writes DX = 2 edges
ahead of the reference slot; the stream schedule adds one edge per stream tile hop. Handed to TOKSIM-QW / QW-GRT4 /
QW-SLICE4 (u_stm bind in qfd_dv_slice2) and the die schedule.

## Benches (Verilator 5.050, fleet ot-epyc6; witnesses results/rtl/qw_stream3_1020/bench/)
Reference = qfd_dv_stream with sw/se/sid/cfg delayed 2 edges, xw_* 2 edges, taps one more. m0 PASS (946 emits, 2,511
table taps, 1,992 x taps, 4,298 relay edges, 3,691 fault-cause edges; every output bit and bad / pbad per edge, two
resets, continuous full beats, random subsets, duplicates, abandoned beats, config changes). Mutants FAIL: m2 xt c40,
m21 xt c261, m22 bad c205, m31 so_e c34, m32 tw c56, m33 so_e c5039, m34 so_w c2824, m35 xt c40, m37 xt c40,
m38 so_w c2824.

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | pin regs + reset landing | PASS: every input registered at its face (payload + root banks), every output a register; rst_n 2-stage landing, 28 kept copies |
| 2 | reach <= 405 um | PASS by plan (t2 measured 290.5 um, same outline); CHECK at the gate |
| 3 | fanout <= 32 | FIXED: mapped census max 30 apart from rst_n (landed copies); 14-bit leaves, root banks, 9 complete trees, decoder copies |
| 4 | depth | PASS: P1 decode + priority, P2 AND-OR8 / 64-AND tree + 2 gates, relay 2:1 / 3:1 muxes; checked at the gate |
| 5 | storage | PASS: no runtime-indexed array; 1,024-bit assembly + 1,024-bit held word, 2-deep payload carry (no delay line >= 3) |
| 6 | floorplan | WAIVED pin-bound (as t2): 6,946 pins, 302.4 x 380.16, W/E 5.85 / S 5.0 / N 3.8 pins/um, no macros, one std-cell band |
| 7 | clock | single ck centre of S, TritonCTS leaf; spread <= 80 ps TT+FF checked at the gate; io_hold_margin 0.03 |
| 8 | schedule | static; pass/tap +1 edge per tile, own write -1 edge vs t2, priced above and handed to the compiler / die schedule |
