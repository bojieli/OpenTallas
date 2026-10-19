LANDFIX-SQ/F 10-18: frame_l4 bench (tools/s81_dv/frame_bench.sh L4=1; tb TB_FWD_GATE = gated forwarded lanes, LDLY whole-period lane delay)
Root cause of S81-LAND2 fbench FAIL: staged src lacked tools/ (hdc_golden ModuleNotFoundError) -> empty vector set -> pass=0 fail=0,
and the xlane "negative control passed" because nothing ran (bench blind). frame_bench.sh now fails closed on an empty set.
b2 (ot-epyc5) / b3 (ot-epyc4), MUT 0 PASS:
  col_h9   each K2 d0 12/12, each K5 d3 12/12; plan K1 d0, K2 d0, K2 d1, K4 d1, K4 d3, K5 d2, K5 d4, K5 d3 seed 2
  col_h10  each K2 d0 12/12, each K4 d2 12/12; plan K2 d0, K4 d2, K5 d2
  col_h9_MX each K2 d0 12/12; plan K5 d3
  plan = cycle-exact vs frame_return_plan.py --land-e K (x_shift = K - 6): ret independent of the lane delay inside the window.
Negative controls FAIL as expected: xlane (lanes 1/2 swapped) col_h9 / col_h10 / col_h9_MX each 0/12;
  window violation K5 d0 (dL = 0 < (K - D) T): PLAN_MISMATCH (ret 4 edges early) + landing FAULT edges 21-24 (b2/h9_k5_d0).
