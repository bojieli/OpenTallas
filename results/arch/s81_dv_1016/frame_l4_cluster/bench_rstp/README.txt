AD-S81-FRAME 10-18: frame _l4 benches (tools/s81_dv/frame_bench.sh L4=1, Verilator 5.050, ot-epyc5) on claude/ad-s81-frame-1018
d5813f144 + 5d6de16e0 (q RSTP=1 on the crs4 xl0..xl3 die base; topology record sha refresh). Scripts run_bench.sh / run_plan.sh.
MUT 0 PASS: col_h9 each K2 d0 12/12; col_h9 plan K2; col_h10 plan K2; col_h9_MX plan K5 d3.
Negative control: col_h9 MUT=xlane each 0/12 -> NEGATIVE_CONTROL_FAILED_AS_EXPECTED (fail witness out_h9_xlane.txt).
(first plan runs failed only on the stale topology sha; re-run after 5d6de16e0: out_h9_plan / out_h10_plan / out_h9mx_plan.)
