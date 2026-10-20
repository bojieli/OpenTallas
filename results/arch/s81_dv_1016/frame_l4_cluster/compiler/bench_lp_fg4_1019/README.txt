S81-FRAME4 10-19: re-bench of the landed frame LP RTL after the no-tie-off fix (bf front roots io_clk/io_n/io_w/io_e on
their region root; frame_lp clock_pins).  Source claude/s81-frame4-1019 @2285c8f2b (git archive staged on ot-epyc5),
Verilator 5.050 (frame_bench.sh FRAME_LP=1, J=16, --mem 64).  try1 failed BENCH_SETUP (staging lacked tools/*.py), the
builds were kept and the vectors re-run with the full tools tree.
  col_h9  MUT0 plan (KK 2048) PASS; each PASS; unland / landread / reset FAIL (NEGATIVE_CONTROL_FAILED_AS_EXPECTED)
  col_h10 MUT0 plan PASS; each PASS; unland / landread / reset FAIL as expected
