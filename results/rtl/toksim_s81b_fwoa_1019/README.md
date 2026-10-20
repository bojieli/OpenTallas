# TOKSIM-S81B/FWOA: attn.wo_b + attn.wo_a measured on the release frame RTL (10-19)

Vehicle: `run_frame_ops.sh` (fleet, ot-epyc9, Verilator 5.050). For one die frame it compiles the multi-phase field of
the layer with the DV placement compiler (`tools/s81_dv/layer_prog/xs_place.py frame/gen`, tools from origin/main
43a1311b7), using the released L0 fixture (real rank-local rows the frame's slice u_s_0S owns, real K, real ROM images),
then runs every wo_b / wo_a phase on:
- **fb**: the frame bench `xs/xs_bench.sh` (frame master `_l4_b` successor + landing + forwarded lanes, w17w10 spine x
  source, `+PH=<phase>`), checked by `xs_place.py check` (lower_xs.check_words: every return word on its planned edge,
  values bit-exact against the golden segment tree; wo_a rows also tied to the layer fixture, 64/64 rows);
- **xb**: the xs-slice bench `xs/xs_slice_bench.sh` (the real slice x streamer ot_s81sl_xs + calendar ROMs drives the
  frame; spine path alongside as lockstep reference), checked by `xs_calendar.py check`.

Legs: g00 = u_f_0L00 (col_h9, LK 5, LDLY 3), g01 = u_f_0L01 (col_h10, LK 2, LDLY 1). Field = 17 phases; wo_b = phases
1-4 (10 rows each, fp8 K 2048, nseg 2), wo_a = phases 5-16 (BF16 pairs, 8 x 6 rows + 4 x 4 rows, shape E2|bseg1024, 4 segments per row).

## Why the 19:35 attempt failed (fixed)
1. The release testbench `tb_s81dv_frame.sv` (blob 69cfc673) has no `+PH`: the spine always ran field phase 0
   (a_proj, nseg 5), so every wo_b/wo_a check failed (BAD_SHAPE n 5, COVERAGE). Fix: the main testbench (be4b5013, adds
   `+PH`, BF word valid in the x word, BF trace probes under ifdef). Testbench only; every DUT file stays release.
2. `tb_s81dv_frame_xs.sv` does not exist at 19bf4121e, so the xs-slice build failed and no run_pN.log was written
   (the FileNotFoundError). Fix: main's tb (9770ed56).

## Results (start = first valid x word at the frame input, edge 67 = spine go 63 + 4; retire = last frame-root RET word)
| op | frame | phases | per phase | serial sum | fb | xb |
|---|---|---|---|---|---|---|
| wo_b | u_f_0L00 col_h9 | 4 x 10 rows | 314 | 1,256 | 4/4 PASS | 4/4 PASS (lockstep D 321, 0 mismatch) |
| wo_b | u_f_0L01 col_h10 | 4 x 10 rows | 316 | 1,264 | 4/4 PASS | 4/4 PASS |
| wo_a | u_f_0L00 col_h9 | 8 x 6 + 4 x 4 rows | 354 / 348 | 4,224 | 12/12 PASS | FAIL (see below) |
| wo_a | u_f_0L01 col_h10 | 8 x 6 + 4 x 4 rows | 347 / 341 | 4,140 | 12/12 PASS | FAIL |

RTL: all 322 DUT source entries the four builds read are blob-identical to release GEN mu4c 19bf4121e
(`blob_vs_release.txt`); the only differences are the two testbenches above.

xb for wo_a: the xs calendar (xs_calendar.py) emits no BF16 window rows, so the streamer's frame word differs from the
reference on 883-890 edges (XSL lockstep FAIL). This is a compiler gap (XS BF window CTL rows, owed: S81-SMWIRE / xs_bf
tier placement), not an RTL fault. wo_a values are bit-exact on the frame bench.

Composition (elements/FWOA.json): per instance = max over frames of the serial phase sum (all frames and slices run
concurrently; phases of one frame run one after another, since no die-wide multi-phase calendar with phase overlap is
compiled yet) + the old DAG's priced wire tail, unchanged (wo_b 146 + 28, wo_a 584 + 28) + CAP edges owed (+1 in, +1
out PINPIPE, +24 on E-column words: +26 once).
Not covered: col_h9_MX frames (third master), other slices (placement shares are equal to +-1 row group).
