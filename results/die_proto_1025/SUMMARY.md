# DIE-PROTO 2026-10-25: die-top GRT + die STA summary (collected 08:15 PDT by FLOW-INFRA/DIE-PROTO-COLLECT)

Setup: `die_trial.py` kits on partition abstracts, signals M4-M7 (`set_routing_layers -signal M4-M7`), layer adjustment
0.75 on M4-M7 (only 25 % of tracks offered to die-top feed-through), M8/M9 = clock/PG only (no signal resource; M1-M3
have 0 resource). Image openroad/orfs sha256:16470cea. All five plans have the SAME plan sha256 as main 394765394
(= origin/main at 08:15), so every run is on the current main plan. Plan branches not yet on main (S81 PLAN3, KV per-bit
lattice successor, etc.) are NOT covered.

| die | plan sha256 (= main 394765394) | GRT run | GRT overflow total (Max H / Max V) | M4 H | M5 V | M6 H | M7 V | M8/M9 | usage % | hop check (405 um) | die STA | clock |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| s81_head | 4e6aaa81 | kit/grt, EXIT 0, 06:40 | **0** | 0 | 0 | 0 | 0 | n/a | 1.34 | 0 over | ideal spine PASS (TT setup +669.3, FF hold +36.3 ps); tree no-PHY FAIL TT setup +439.9 / FF hold -154.6 (24420 EP) / pair skew 213.65 TT, 177.04 FF | nophy tree 5.06/3.61 PASS; v1 (with PHY) 2250/1970 FAIL |
| qwen_kvsys | ee1aee20 | kit/grt, EXIT 0, 06:49 | **0** (3 extra iters) | 0 | 0 | 0 | 0 | n/a | 7.46 (M6 10.7, M7 8.7) | 240 slots / 12042 bits over 405 after GRT (plan 0) | sta_ideal + sta_tree TT LIVE (epyc1) | 2.27/2.46 PASS |
| qwen_compute | d27c3788 | kit_it5 (5 congestion iters), EXIT 0, 07:43 | **1,659,581** (121 / 40) | 747 | 170 | 407,499 | 1,251,165 | n/a | 7.30 | 44,005 leg-inst over 405 (33 slots; worst coll_ftc 500.9 um) | kit2 STA TT+FF LIVE (intel1) | (kit clock tree only) |
| s81 | 7f0e38c8 | kit/grt LIVE (epyc1 dtrial-grt-3950895, since 07:00, extra iter 2/50 at 07:47) | pending | - | - | - | - | n/a | - | plan 0 / GRT pending | sta_ideal TT LIVE (epyc1) | 627/539 FAIL |
| hbm (B2n) | f710e18c | kit/grt LIVE (epyc1 dtrial-grt-3616206, since 06:56, extra iter 2/50 at 07:42) | pending | - | - | - | - | n/a | - | 0 slots over 405 | die_sta ideal TT+FF LIVE (intel2, die-proto-hbm/sta) | clk_run30 135.6/135.4 FAIL (seam max 43.9 ps; insertion 18.8 ns) |

Notes
- qwen_compute hot regions (congestion.rpt binned 1 mm, `qwen_compute/kit_it5/grt/congestion_regions_1mm.txt`): ALL in
  one horizontal band y = 10-11 mm, at x = 2-5, 16-17, 19-22, 24-27, 29-30 mm; nets ft_sl_{E0..E5,W4,W5}_su_c / _su_l1
  (slice SU feed-throughs: x_fw_st_a, x_fw_ctl_p2, x_su_l1_ctl, rsn). 82 % of the flagged gcells are horizontal congestion.
  Overflow is on M6/M7 (signals capped at M7): the SU band needs more horizontal FT capacity or a re-placed SU feed-through.
- qwen_compute kit (50 iterations) is still LIVE on intel2 (dtrial-grt-134732, 160 GB, extra iter 7/50 at ~08:10);
  same kit as kit_it5 except iteration count.
- qwen_kvsys: GRT reports 0 overflow but the render (`congestion.png`, window 27 um against the 25 % FT share) peaks
  at 1.86 (M6), 4643 M6 windows > 1.0: two vertical FT trunks at x ~ 3.5 and ~ 7 mm, y 14-26 mm (hg_WN/hg_EN
  columns) and the y 12-13.5 mm cross band. Together with the 240 GRT hops over 405 um this is the KV per-bit lattice problem.
- s81_head render: peak 0.86 (M7) on the centre spine (x ~ 9.1 mm, sp1..sp5); nothing over 1.0.
- s81 / hbm GRT with 50 congestion iterations take > 20 min per iteration; the it5 variant took 34 min on QC.
