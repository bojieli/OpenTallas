# qfd_dv_stream_t2c_1019 -- Q.SAFE.STREAM structural successor, COMPACT FALLBACK (QW-STREAM2, LEAD3-QW, 10-19)

Fallback outline 259.2 x 380.16 (aspect 1.47; W/E 5.85, S 5.9, N 4.4 pins/um; relay 259 um). Same top `qfd_dv_stream_tile` (rtl/qwen_dv/qfd_dv_stream_tile.sv) and pin plan as qfd_dv_stream_t_1019, packer rebuilt.
Spec generator tools/ref_tile/specs_qw_stream_1019/mk_specs.py; parallel fallback kit qfd_dv_stream_t2c_1019 (compact
outline 259.2 x 380.16, same RTL). Branch claude/qw-stream2-1019.

## Why (failed route)
qfd_dv_stream_t_1019-s1-2c97be786 NEEDS_RTL: TT -47.54 ps (1,125 endpoints, all reg->reg; i2r +13.3, out +89.2), FF +11.97,
DRC 0. Classes (path_summary SS view of the same cone): u_ot_pr_core.wa_q -> eword[*] (366 paths, 17 levels), wa_q -> em_c,
wa_q -> xm. Classification: LOGIC DEPTH + COMBINATIONAL FANOUT in one edge -- SU address decode -> slot x lane hit ->
highest-lane priority -> 8-way AND-OR -> &nm over 64 slots -> a ~1,100-load combinational enable on the 1,024-bit eword,
plus the BF16 RNE adder ahead of the AND-OR. Not reach (290 um), not arbitration.

## Structural fix (no squeezing, no LVT)
Packer in three registered stages:
- P1: BF16 RNE of the 8 lanes into two KEPT lane copies (slots 0..31 / 32..63, <= 32 loads per bit); slot x lane
  registered ONE-HOT select (decode + priority, 512 b), slot hit (64 b), duplicate / beat-consistency partial faults.
- P2 (state edge): xb / xm / op / xbeat from the one-hot select (AND-OR 8 + mux, ~5 levels); complete = &nm into 69 KEPT
  copies cm_c (32 eword groups, 34 emit groups, 2 x tap, 1 ebeat); beat fault registered (pbad_r).
- P3 (emit edge): eword[g] <= xb[g] on its own copy cm_c[g] (32 loads); em_c / emx_c from their copies; ebeat <= xbeat.
Relay, taps, cfg, face decode and fault-cause logic unchanged.

## Priced schedule (static; no credits, no backpressure)
| path | edges vs previous tile | vs qfd_dv_stream |
|---|---|---|
| SU own x writes xw_* -> emitted beat (so_e/so_w own word), x tap own word, beat fault | +2 | +3 |
| sw_i / se_i / sid -> relay, table / x taps (pass words), cfg | 0 | as before (+1 face, taps +2) |
| reset | 0 | +2 (landing) |
The SU issues own x writes 3 edges ahead of the slot the emitted beat must take (II unchanged: one 8-lane write per edge,
full beat per 8 edges). Handed to the slice2 bind (lanes/QW-SLICE4.md) and the die schedule (lanes/QW-GEN3.md).

## Benches (Verilator 5.050, fleet ot-epyc5; witnesses results/rtl/qw_stream2_1019/bench/)
Reference = qfd_dv_stream with sw/se/sid/cfg delayed 1 edge and xw_* 3 edges, taps one more. m0 PASS (945 emits, 2,511
table taps, 1,983 x taps, 4,302 relay edges, 3,688 fault-cause edges, every output bit and bad/pbad per edge).
Mutants FAIL: m2 xt c41, m21 xt c262, m22 bad c206, m31 so_e c33, m32 tw c55, m33 so_w c2825, m34 xt c41.

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | pin regs + reset landing | PASS (as s1): every input face-registered, every output a register; reset 2-stage landing, 20 kept copies (~545 control loads incl. cm_c, <= 28 each) |
| 2 | reach <= 405 um | PASS by plan (s1 measured 290.5 um); CHECK at the gate |
| 3 | fanout <= 32 | FIXED: the 1,100-load combinational complete now feeds 69 kept copies + 64 xm + 4 op (buffered tree, then each copy <= 34 loads); lane data in 2 kept copies (32 loads); one-hot select bits 16 loads; slot hit 18 |
| 4 | depth | FIXED: packer split P1 / P2 / P3 (decode+priority+RNE | AND-OR+&nm | enable), each well under 20 levels |
| 5 | storage | PASS: no runtime-indexed array; P1 adds 512 + 64 + 256 + 36 + 19 flops, wa1_c is a 1-deep copy |
| 6 | floorplan | WAIVED pin-bound: 6,946 pins, 259.2 x 380.16, W/E 5.85 / S 5.9 / N 4.4 pins/um, no macros, one std-cell band |
| 7 | clock | single ck centre of S, TritonCTS leaf; spread <= 80 ps TT+FF checked at the gate; io_hold_margin 0.03 |
| 8 | schedule | static; +2 edges on xw_* priced above and handed to slice2 / GEN3 |
