# Predicted bound-S8 / CROM alignment price

These are analytical predictions. The current token price remains **HELD**;
no released rate is replaced. Clock = 833 ps, all36 layers. The model holds
non-DV transport, tile and closed-head terms at the historical source inputs.
New methodology TP8 LS407 costs are a separate delta.

| Scenario | cycles/token | predicted tok/s | chained layer | cold layer |
|---|---:|---:|---:|---:|
| Historical source2slice reproduction | 271106 | 4428.1 | 7428 | 7941 |
| Bound ages + SC4/ST4 + actual L9 owners + correct stream occupancy | 286726 | 4186.9 | 7862 | 8371 |
| Above + CROM alignment3 cycles/SU op | 288025 | 4168.0 | 7898 | 8410 |

CROM alignment adds **1299 cycles/token = 1.082067 us**: +36 per chained layer,
+39 in the cold layer (35*36+39). First-order rate cost0.453%; exact predicted
cost0.451% against the bound-current scenario. The combined bound/aligned
prediction costs16919 cycles (+6.241%) versus historical source, a5.874% rate
reduction. SU-derived output/retire ages move+3; scalar and station ages and
root-config lead stay unchanged. Historical PRICED SU8/VM8 age deltas are
removed when measured bound ages replace them, avoiding double-charge.

The correct4-hop stream occupancy has the measured SiLU-only cost+4/layer
(+144/36 layers). It also changes residual broadcasts: their analytic spans
fall629->607 each. Example residual stream entries for s10/s11 move578/585
to449/483; last x at E5 falls701->679. The incorrect2-hop occupancy invented
conflicts at those positions. `occupancy_schedules.json` records the actual
compiled entries. Whole-model counterfactual288188->286726 is -1462 cycles
(chained-40, cold-62), but the counterfactual fails RTL and supports no rate-gain
claim. Residual schedules still need current-RTL qualification.

The source reproduction needs the historical attention-return term116 =
98 measured+18 priced successor edges; using98 alone undercounts648 cycles.
Bound predictions use the newly compiled attention-return span, retaining
its unmeasured qualification. No4u throughput prediction is adopted here.

Sources: CROM RTL candidate c1c42f554; compiler candidate f0ef9ad67; fixed-RTL
s8exp_wf3 ages copied under `ages/`; composition engine94cd97b7a. `price.py`
is the actual recipe: a fresh214-MB engine snapshot with BASE_PATHS from
compose_tokfunc.py, historical source input/ages, current compiler sources
under sources/, and the three bound age JSONs alongside the script. It runs
only analytical composes (no RTL simulation). `probe_sched.py` reproduces the
occupancy entry comparison. Raw scenario JSONs and summary are retained here.
