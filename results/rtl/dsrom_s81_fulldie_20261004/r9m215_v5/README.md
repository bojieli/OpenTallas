# S81 v5 die cases (CLAUDE S81-RERUN, 2026-10-06): r9m215 + --vch-interleave + --link-fix + --corr-interleave

Cases EPYC3 `/srv/opentallas-scratch2/claude/s81-rerun/cases/v5` (mk_v5.sh, generator with --corr-interleave).

| die | legality | GRT i50 overflow v4 | v5 |
|---|---|---|---|
| scan (sb) | 0 / 0 | 1,212 | **341** (-72%) |
| layer1 (l1b) | 0 / 0 | 148 | **137** |
| head (hb) | 0 / 0 | 808 | **466** (-42%) |

Design change (not a setting): the v4 hotspot (80% of the scan overflow, x 16.5-17.5 / y 10.5-11.0 mm) was the HC
corridor's lower half, where the 12 corridor chains took lanes 0..11 in order and the heavy return / x chains crossed
the hc_s <-> hc_n hub lanes; `--corr-interleave` strides the corridor lane order (stride 5 of 16).  i5 empty baselines 0.
