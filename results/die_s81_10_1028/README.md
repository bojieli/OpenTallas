# DIE-S81-10 (2026-10-28) S81 plan event, pre-F1 part

1. Shared gen_phys change: tap_window applies to types with early core taps -> branch claude/die-s81-10-tapwin-1028@607f28bcec (READY ROOT-MERGE).
2. COLLECT: FLOW joint4 (intel2 pid 1373618, codex-relay-roads-1028/joint4, run_alloc.py, 1 h+ at 100 % CPU, no output) and col_h9 DRT trial (container 5e76e626cac4, GRT extra 22/30) are both still LIVE. Not touched.
3. Plan event plan_s10 (scripts/plan_event_s10.py; intel2:/srv/opentallas-scratch2/claude/die-s81-10/plan/plan_s10.json, sha 5f014a8d3554):
   plan_s5 d29050658673 + CORELAT early taps (1338 re-tap + 374 new placements; 225 ve/vn taps placed at the pins_file clk pin) + clock.tap_window 180 + clock.seam_hold {sender 0, seam 40} (legacy-equivalent; S81 has 0 seam pairs).
   119 early-tap types / 309 of 398 partitions. NO F1 relays (joint4 still running).
   SDC + sdc_lint OK on all 205 types (CHECKED, scripts/lint_all.py).
4. Gate on the packed-G proof (tree built on the plan_s5 taps, so the core-tap part is a what-if):
   - intra FF kit-contract hold +70.32 at W 180 (needed 109.68 nominal), 0 neg pairs (CHECKED data/sta_intra.log). With OCV, UNCHECKED: about +20, extrapolated from the DIE-S81-9 W165 +5.16.
   - CA-OCV-1 planner (--sta-clock-ocv table, shared droop) + start-skew-clean: 2262/2306 pass (D4 2192 / D8 70), min margin lo 105.4 / hi 107.5.
     **44 nontree crossings in 11 region pairs FAIL**: their path ambiguity is 3-7 cycles because OCV-widened tree edges become ambiguous (82/397 edges vs 0 before).
     L_hi is up to 7673 ps, above the D8 bound of 6141 (7.5T-ap). All 44 fit DEPTH 16 (bound 12807). Own interval width 511-2862 ps.
     So bind fails closed, and there is NO die-STA CA row on the OCV plan. Per-crossing data: data/ca_ocv_plan_fail.json.
5. Kits not regenerated (no per-type hold-buffer count): F1 changes 216/398 instances, so kits wait for F1.
