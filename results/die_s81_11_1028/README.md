# DIE-S81-11 (2026-10-28) S81 CA crossings under METHODOLOGY 12.16 / 12.16e

Base: claude/die-s81-10-1028@05e4f82600 (CA-OCV-1 + tap window merged in). Gate form = die-s81-10 gate_s10.sh
(CA-OCV-1 hull: spice, cppr-lca, clock_ocv table, shared droop, start-skew-clean 46.9/79.4) on the packed-G proof and plan_s10.
Data: intel2:/srv/opentallas-scratch2/claude/die-s81-11. CHECKED = own run/log read; UNCHECKED = estimate.

## Order change
COORD 07:20 asked for per-pair tree-parent overrides first. OWNER 12.16 (07:29) and 12.16e then changed this: overrides are
residuals only, and the S81 primary path is the local clock form from CLK-LOCAL-EST-1 (~09:00). The override search was
stopped after 1 step (svc_7 re-parent: 44 -> 37 FAIL; data/tp_search_stopped.log). It is NOT adopted.

## (3) Unshared clock per failing pair (before) and structural estimates (CHECKED rows, estimates UNCHECKED)
Rows = CA-OCV-1 hull rows (rows_hull.json). Unshared = max(unshared_a, unshared_b) of the worst crossing of the pair.

| pair | crossings | unshared ns | LCA | direct dist mm | hull width ps | path amb cycles | hop chain over existing crossings (<=3.4 ns/hop) | late-split est ns / width ps |
|---|---|---|---|---|---|---|---|---|
| seqhost<->s_4S_L4 | 9 | 12.1 | b8 | 6.4 | 2862 | 3 | 19 hops, 44 mm | 2.1 / 492 |
| s_4S_L3<->s_4S_x06 | 2 | 12.0 | b0 | 8.3 | 2572 | 3 | 33 hops, 65-72 mm | 2.4 / 515 |
| s_5N_L2<->s_5S_L4 | 2 | 12.0 | b0 | 10.3 | 2633 | 3 | 33 hops, 67-73 mm | 2.7 / 603 |
| s_3S_C<->s_4S_C | 4 | 11.1 | b8 | 7.0 | 2706 | 3 | 21 hops, 48 mm | 2.2 / 535 |
| s_7S_x110<->s_7S_x111 | 3 | 9.1 | b0 | 13.2 | 1881 | 3 | 35 hops, 75-83 mm | 3.2 / 670 |
| iqf<->phy_hbm | 2 | 4.5 | b38 | 6.6 | 1070 | 6 | 4 hops | 2.1 / 509 |
| phy_hbm<->svc_2 | 2 | 4.1 | b74 | 5.6 | 989 | 6 | 2 hops | 2.0 / 476 |
| svc_6<->svc_8 | 4 | 2.7 | b226 | 2.5 | 776 | 6 | - | - |
| svc_5<->svc_7 | 5 | 2.7 | b116 | 2.3 | 804 | 6 | - | - |
| svc_2<->svc_4 | 4 | 2.0 | b74 | 2.4 | 534 | 7 | - | - |
| svc_4<->svc_5 | 7 | 1.6 | b116 | 2.5 | 511 | 7 | - | - |

Two classes:
* A (first 5 pairs, 20 crossings): crossings between distant tree branches across the root split (LCA b0/b8, 182-221 stages).
  Unshared 9-12 ns. This is exactly what 12.16 b(i) forbids. A hop chain over the existing region graph needs 19-35 hops
  (44-83 mm of path), so it is rejected (same as DIE-S81-5 Form R). The late-split estimate assumes the two regions share the
  clock up to a split near the pair: 0.34 ns/mm routed x dist/2 + 1.0 ns region insertion, with the hull width scaled at the
  pair's own 0.21-0.24 ps/ps. It gives 2.0-3.2 ns unshared and 0.48-0.67 ns width, which is D4/D8 with no path ambiguity.
  This is a property of the clock form (12.16e local form), not of the CA planner.
* B (6 svc pairs, 24 crossings): unshared only 1.6-2.7 ns and width 0.5-0.8 ns. They fail ONLY on start-tree path ambiguity
  (6-7 cycles), because the min-ambiguity start tree is unrelated to the clock tree. 12.16 b(iv): reset release follows the same
  model. ESTIMATE (est_cstree.py): start tree = minimum-bottleneck tree on crossing unshared clock (derived from the clock tree).
  Result: 44 -> 34 FAIL; all svc pairs pass; start-edge unshared max 8.9 -> 1.8 ns (0 > 3.4 ns). But 85 ambiguous edges and depth
  49, so 4 new class-A-like pairs fail (s_6S_L3/x06, s_7N_L2/s_7S_L4, phy_hbm/svc_12; data/plan_cstree_summary.json).
  Whole-die count: 83 of 2306 crossings have > 3.4 ns unshared (p50 0.86, p90 1.87, p99 8.9, max 12.1 ns); 63 of them pass today
  only through D8 / clean start paths.

## (2) DEPTH 16: RTL proof + opt-in planner (D16.md)
* Verilator lag sweep of ot_dp_clk_landing_ca (unchanged RTL; same bench, horizon 140 T because ARM = 36 at D16), K in
  {-2,1,2,5} x DEPTH 16, L = +-33 T at 2 ps: clean window [419, 12911] ps = [0.503, 15.499] T, contiguous, silent-wrong 0 of
  27490 each (includes the 1-bit lap alias at L-32T). D8 control: [0.503, 7.499] T. Mutants at D16: NO_TAG caught (4304
  silent-wrong), K caught (0 clean, 4165 wrong), NO_GUARD caught by the window check only (clean window grows to [0.004, 15.998] T,
  0 silent-wrong in this no-metastability bench). Strap form ot_dp_clk_landing_cas DEPTH 16 W 64 (strap 8 bits) elaborates.
  Formal k-induction at D16 NOT run.
* Cell cost per crossing (yosys + abc, ASAP7 RVT TT, 64 bits, K 2): D4 190.9 um2 / 1632 cells, D8 345.3 / 2918,
  D16 657.0 / 5753. D16 - D8 = +311.6 um2 / +2835 cells per 64-bit crossing.
* count_align_plan --max-depth {8,16} (default 8 = byte-identical output fields apart from depth16/max_depth in the summary);
  count_align_bind depth_hist counts 16; clock_landings accepts DEPTH 16. New test_count_align_depth16.py (4 tests incl. an MC
  mutant). Related suites: 74 pass.
* WHAT-IF (not a primary fix under 12.16): current tree + --max-depth 16 -> 0 FAIL (D4 2192 / D8 70 / D16 44), min lo 105.4 /
  hi 107.5, cost 44 x 311.6 = 0.0137 mm2 vs D8.

## (5) F1 / col_h9 COLLECT
* FLOW joint4 (codex-relay-roads-1028/joint4) terminal 07:04 exit 0: PACKING_PROPOSAL 7032 cells (1085 DFFASRHQNx1 + 5947
  buffers/inverters), PRICED_FAIL 0, 3268/3268 roads pass, wire p50 361.3 / max 402.9 um (limit 405). FF placement vs the v3
  bank targets: L1 max 5.02 um, 0 > 8.64 um (CHECKED). Cell move from the pre-F1 placement p50 153 / max 565 um (the intended
  bank moves). Render data/f1_joint4.png VIEWED: FFs packed into the central macro channel (x ~560-600) and an east cluster
  (x 1080-1210, y 540-760); roads drawn as straight legs. It is a proposal: Codex's own review (image/reach/clock/reset/tie and the
  1096 reset/tie control targets) is still open, so it is not applied to a kit here.
* col_h9 DRT trial (container 5e76e626cac4): GRT extra iteration 24/30 at 07:4x, still live, not touched.
