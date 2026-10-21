# S81-MUCAL140B (MU.S81.CAL, 10-20): ROMOPT recompose + dense-stage hold on the 140 physical stages

Tools: `tools/s81_dv/dv_mu_calendar_phys.py` (new flags `--compose romopt`, `--alap`, `--contexts {1,-1,2}`, `--map`, `--unqualified`)
and `tools/s81_dv/mucal_stage_rebalance.py` (expert re-deal over the same 140 stages). The record outputs of S81-MUCAL140
(`../mucal140_s81_1020/calendar_phys140_*`) still reproduce (`--check` SAME; only metadata keys added).

## (1) Recompose with the merged compiler / ROM gains (pinned map f5608b1e5f2a, unchanged)
`--compose romopt` = `toksim_s81_compose.py --scenario calpipe` + the S81-ROMOPT-C o3mix compiled spans (O1 GU_MERGE + O2 12 q pairs
+ O3 gu k2 / down k3), substituted exactly as `results/rtl/s81_romopt_1020/c/compose_c.py`; composer T asserted equal to the committed
`o3mix_prop_compiled` (1,040.4 AR / 3,193.4 MTP), substitution counts equal (160 per op).

| | composer | physical per user | users | aggregate | bound |
|---|---|---|---|---|---|
| record (MUCAL140) AR | 834.0 | 815.5 | 36 | 29,357 | R003 38,804 |
| **ROMOPT AR** | 1,040.4 | **1,011.7** | **42** | **42,490** | R003 28,168 |
| record MTP | 2,649.1 | 2,509.4 | 8 | 20,075 | |
| **ROMOPT MTP** | 3,193.4 | **3,024.3** | **8** | **24,194** | R003 169,005 |

Files: `calendar_romopt140_{ar,mtp}.json`, `romopt140.log`.

## (2) Dense-stage hold (R003: L0 tail experts + add + combine, L1 attention + pre-expert, L1 head experts)
* Moving the experts OFF the dense stages is impossible at 140 stages: the 100 expert-only stages are full (113 = 8,136 / 8,192 q
  words), so the 40 dense stages must hold 15,360 - 11,300 = 4,060 experts (101.5 avg; caps 97-106). Fully off needs ~176 stages.
* Exact capacity is LINEAR: worst q pair = dense intercept (dense_L*_n0 probe: 480 / L1 1,024 / L2-class 576 / L14 1,120) + 72 N.
  This matches all 140 f122_140 stages exactly (asserted), and the new run's L1_n54 = 4,912.
* What is possible: re-deal the experts so the dense windows are balanced (minimax DP, `mucal_stage_rebalance.py`): two-sided
  stages go on the light layers, the heavy copy-B layers (L2/8/14/20, A+D 42-46k) get one side, L1 gets a 2-expert head.
  Plus ALAP expert slots (`--alap`, compiler only): the slots start so they end as the upstream partial lands, with the same output
  edge and zero latency cost. Map `stage_map_rb140.json` (same 140 stages / dies / dense order / copy-B; max fill 99.32 % = base).
* 2 job contexts: the RTL already has them (`ot_dsdv_fixed_issue`: `active[1:0]`, "two contexts may execute the same immutable
  calendar", and a duplicate engine issue is fault 9). `--contexts 2` checks engine-class exclusivity: field / su / coll / hbm /
  select / embed, each one engine (conservative); expert slots hold field+su; un-engined priced terms block all. It also checks
  <= 2 holders per stage copy, with greedy first-fit shifts. Result: **no extra user** (base 42/9, rebalanced 44/10, = the
  1-context searched-shift numbers). With one global shift per user, the forbidden-difference sets of the 40 dense stage patterns
  cover almost every offset. A gain would need per-stage start slips (static landing buffers), a separate design item.

| map (ROMOPT, ALAP) | AR users x tok/s | AR agg | MTP users x tok/s | MTP agg | bound | capacity |
|---|---|---|---|---|---|---|
| pinned f5608b1e5f2a | 42 x 1,011.7 | 42,490 | 8 x 3,026.5 | 24,212 | R003 28,004 | PASS |
| **rebalanced rb140** | **44 x 1,011.0** | **44,483** | **10 x 3,012.1** | **30,121** | R003 25,679 / copy-B R028 52,082 | exact run (see below) |
| rb148_MODEL (f122_148 base, +8 stages = +32 dies) | 48 x 1,003.8 | 48,183 | 10 x 3,028.5 | 30,285 | R014 24,299 | model only |

The 44-user limit is the copy-B colouring on R028 / R007 (L8 / L2 at ~51-52k per copy pair). The single-copy bound would admit
46. ~47 users (the owner's earlier target) needs more stages: 148 stages give 48 (model; f122_148 exact base PASS, rebalance re-run owed).
This is a die-count change, so it is a COORD/owner call.

Checker on every row: brute force over every window mod P (stages / copy pairs / links / head / host); 0 collisions; N+1 FAULT;
injected shift FAULT. Grades: as MUCAL140 (node cycles = composer grades, 69.7 % / 61.2 % measured for ROMOPT; stage split /
reservation / forward-x / ALAP / MTP law = MODEL).

Exact capacity of rb140: ot-epyc9 `/srv/opentallas-scratch/claude/s81-mucal140b` (same frozen root / fixtures / env as f122_140:
QPAIRS 12, PAIR_ROTATE 0, 122 frames), 41 specs (40 new). Verdict PENDING (10-20 22:30: 9/41 specs PASS, all linear-law exact; run live, ot-run oth-ubuntu-1024772-1792557829). rb140 rows are UNQUALIFIED until `rb140.merge.log` reads all_pass.
