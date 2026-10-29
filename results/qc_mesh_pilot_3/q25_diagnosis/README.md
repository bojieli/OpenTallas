# QC trial25 refit regression: physical cause

Read-only diagnosis of existing routed artifacts, no build or parameter sweep. All numbers UNCHECKED by NUMBER-CHECK.

Inputs (intel2): die-qc24-1028/{trial24/clock/tree.json,c24_TT/arr_TT.txt}; die-qc25-1028/{trial25/clock/tree.json,c25_TT/arr_TT.txt,fit24.json,val25.json} under /srv/opentallas-scratch2/claude/. `inspect_paths.py RUNROOT` reads copies as RUNROOT/trial{24,25}/{tree.json,arr_TT.txt}; exact raw path trace is in exact_paths.txt.

The calibration changes topology. In worst quad c_E2_bf_10, TT late glue spread rises from 35.481 ps (trial24) to 156.238 ps (trial25). Trial25 chooses a slow branch b9424 -> b9462 with 2,406.4 um of snake wire in ten consecutive 229.8–248.0 um stages. The old fastest/slowest glue paths used snakes of 1,530.9 um/8 stages and 764.2 um/4 stages, with no stage over 225 um. This is a geometry and driver-load change, not simply a new label on the old tree.

The b9462 branch costs 533.202 ps early / 595.816 ps late. The actual build's fit24 early model predicts 478.160 ps: +55.042 ps error on that one leg. The first repeater input rising slew is 112.93 ps; successive values run about 97–129 ps. Ten near-maximum wire loads sustain slow input slew, which the stateless leg model does not include. The opposite branch combines short stacked legs and a shorter snake. Using the same early model on complete paths gives clk_t8 accumulated residual -39.30 ps and clk_t3 +62.23 ps: 101.53 ps differential error, on top of 48.19 ps predicted path difference, produces 149.71 ps measured early spread. The mean glue/core offset can therefore remain close while leaf spread degrades badly.

This isolates a concrete long-stage/slew dependence and asymmetric topology, rather than a core early-offset error or small legalization movement. It does not prove every global-fit residual shares that cause. A new coefficient fit alone is not qualified by this diagnosis. Retaining trial24's passing baseline while applying the independent E crh mapping change avoids adopting this measured regression; future construction should balance stage lengths/depth and propagate slew/load through the planned legs.

`path_geometry.png` was personally viewed: the slow path's long U-shaped snake has ten near-limit segments while the fast path contains several short stacked nodes. This is a diagnostic of the existing plan, not approval for a new route.

SU glue comparison from raw TT T rows, excluding clk_c* core taps: trial24 12 regions median57.57/max93.69 ps; trial25 median59.59/max87.58 ps. The severe regression is concentrated in the A0-quad trees, not a uniform SU glue spread failure.

| region | trial24 TT glue ps | trial25 TT glue ps |
|---|---:|---:|
| sl_E0_su_c | 77.97 | 49.17 |
| sl_W0_su_c | 55.34 | 57.89 |
| sl_E1_su_c | 60.90 | 74.01 |
| sl_W1_su_c | 53.83 | 58.46 |
| sl_E2_su_c | 51.70 | 53.59 |
| sl_W2_su_c | 64.10 | 87.58 |
| sl_E3_su_c | 59.67 | 73.42 |
| sl_W3_su_c | 55.47 | 83.37 |
| sl_E4_su_c | 93.69 | 46.96 |
| sl_W4_su_c | 43.59 | 66.66 |
| sl_E5_su_c | 77.97 | 60.72 |
| sl_W5_su_c | 55.34 | 55.82 |
