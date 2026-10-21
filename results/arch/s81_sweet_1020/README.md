# S81-SWEET (10-20): die count vs throughput for the S81 DeepSeek array, with a balanced pipeline

Tools: `tools/s81_dv/s81_sweet_sweep.py` (new) + `dv_mu_calendar_phys.py` (new: `copies` k >= 3 per dense stage, `--dsplit`),
on `claude/s81-mucal140b-1020` @3fe699d4d. Composition = `--compose romopt --alap`, 1 job context (as rb140). Each row = a
min-max re-deal map for that stage count (binary search on the max dense window + DP over layers, exact linear ROM law
q0 + 72 N, calendar rows <= 4096), then the physical calendar: brute-force checker 0 collisions, N+1 FAULT and
injected-shift FAULT on **every** row (AR and MTP). Dies = 4 x stages + 4 x extra copies + 52 other. Rows are MODEL
(capacity by the linear law) unless marked. The 140 row reproduces rb140 exactly (44 x 1,011.0 / 10 x 3,012.1).

## Why the pipeline is unbalanced
* Expert-only stages are **ROM-bound**: 113 experts = 99.3 % of the q words, but only ~3.6 k cycles a token (one 6-slot
  reservation + add). They cannot take more time without more ROM. This sets the all-stage max/mean at >= 2. The balance
  that matters is **across the dense (time-bound) stages**, shown as "dense".
* Dense stages are **time-bound**: attention + pre-expert, A + D, cannot be split. It is 15.4-15.7 k on the light layers,
  19.3 k on L1, 26.5 k on the L24 class, and 42-46 k on L2/8/14/20, where the index top-k on the select engine alone is
  20.8 k. Any experts on a dense stage add 3.5 k for each side.
* Users ~= P / max window, so aggregate AR ~= F / max window. More stages only help until the experts are off the dense
  stages. At that point the floor is (A + D) / copies of the heaviest layer. After that, each extra stage only adds a
  1,008-cycle hop (-0.09 %/stage per user).

## Results (AR; MTP in the same row)
| variant | stages | dies | max/mean stage occ (dense) | bound | AR users x tok/s = agg | AR tok/s/die | MTP users x tok/s = agg | MTP /die |
|---|---|---|---|---|---|---|---|---|
| re-deal (today's copies) | 140 | 644 | 26,041 / 9,182 = 2.84 (1.13) | R028 L8 x2 | 44 x 1,011.0 = 44,483 | 69.07 | 10 x 3,012.1 = 30,121 | 46.77 |
| re-deal | **141** | **648** | 24,688 / 9,127 = 2.71 (1.08) | L14 x2 | **48 x 1,010.1 = 48,486** | **74.82** | 10 x 3,035.1 = 30,351 | 46.84 |
| re-deal | 144 | 660 | 24,366 / 9,058 = 2.69 (1.06) | L4 x1 | 48 x 1,007.3 = 48,353 | 73.26 | 10 = 30,363 | 46.00 |
| re-deal | 148 | 676 | 24,299 / 8,841 = 2.75 (1.07) | L3 x1 | 48 x 1,003.8 = 48,183 | 71.28 | 10 = 30,285 | 44.80 |
| re-deal | 152 | 692 | 24,211 / 8,415 = 2.88 (1.15) | L22 x1 | 48 x 1,001.2 = 48,057 | 69.45 | 10 = 30,387 | 43.91 |
| re-deal | 156 | 708 | 24,144 / 8,308 = 2.91 (1.14) | L21 x1 | 48 x 997.5 = 47,880 | 67.63 | 10 = 30,305 | 42.80 |
| re-deal (floor from 159) | 164 | 740 | 22,944 / 7,909 = 2.90 (1.13) | L14 x2 | 52 x 990.6 = 51,510 | 69.61 | 12 = 36,289 | 49.04 |
| re-deal | 172 | 772 | 22,944 / 7,707 = 2.98 (1.13) | L14 x2 | 52 x 983.5 = 51,142 | 66.25 | 12 = 36,098 | 46.76 |
| re-deal | 180 | 804 | 22,944 / 7,523 = 3.05 (1.13) | L14 x2 | 52 x 976.5 = 50,779 | 63.16 | 12 = 35,909 | 44.66 |
| re-deal | 200 | 884 | 22,944 / 7,128 = 3.22 (1.13) | L14 x2 | 54 x 959.5 = 51,813 | 58.61 | 12 = 35,446 | 40.10 |
| + L2/8/14/20 x3 (c3) | **153** | **712** | 19,303 / 7,885 = 2.45 (1.03) | L1 x1 | **60 x 1,000.9 = 60,054** | **84.35** | 12 x 2,968.3 = 35,619 | 50.03 |
| + dsplit + L2/8/14/20 x3 + L1 x2 | 164 | 760 | 17,825 / 7,542 = 2.36 (1.06) | L4 x1 | 66 x 991.5 = 65,440 | 86.11 | 12 = 36,078 | 47.47 |
| + dsplit + L2/8/14/20 x4 + L1 x2 (dsc4L1) | **195** | **900** | 12,612 / 6,262 = 2.01 (**1.03**) | L4 x1 (light A) | **96 x 966.8 = 92,809** | **103.12** | 14 x 2,951.4 = 41,319 | 45.91 |
| dsc4L1 | 200 | 920 | 12,612 / 6,195 = 2.04 (1.03) | L4 x1 | 96 x 962.5 = 92,403 | 100.44 | 14 = 41,186 | 44.77 |

Full sweep, 74 rows (re-deal 140-200 incl. 141-143 / 157-163; c3, c3L1, ds, dsc3L1, dsc4L1 at each count): `sweep_all.json`.
dsplit is infeasible below ~160 stages because the dense stages then have to carry head experts. Other results: c3L1 at 152
gives 712 dies / 84.42; dsc3L1 at 196 gives 888 / 91.38; ds alone tops out at 58 users, because the heavy layers stay at 21.4 k.

## Sweet spot
* **Max AR tok/s per die: 195 stages, 900 dies, balanced (dsc4L1). 96 AR users x 966.8 = 92,809 tok/s, 103.1 tok/s/die
  (vs 69.1 today, +49 %).** Every dense stage copy is within 3 % of the light-layer attention floor (12.6 k).
* **Knee:** the efficient frontier, taking marginal tok/s per added die against the average:
  644 -> 648: +1,001/die · 648 -> 712 (c3): +181/die · 712 -> 760 (dsc3L1@164): +112/die · 760 -> 900 (dsc4L1@195):
  +196/die. All of these are above the running average (75 / 84 / 86 / 103). Past 900 dies the next floor is the L24 class
  x2 (11.8 k). Reaching it means copying ~28 light dense layers (+112 dies) for ~+7 % (~58/die < 103 average), so **the
  knee is 900 dies**. The 164-192 dsc rows sit below the frontier: the light dense stages still carry tails there. Don't
  pick a count between 165 and 194.
* **Without dsplit (no new compile path): 153 stages + L2/8/14/20 x3 = 712 dies, 60 x 1,000.9 = 60,054, 84.4/die**.
  The best point using only stage count + ROM re-deal is **141 stages = 648 dies (+4 dies), 48 users, 48,486, 74.8/die**.

## Compiler-only vs ROM vs hardware
| move | class |
|---|---|
| ALAP expert slots, user shifts / colouring | compiler only (as rb140) |
| expert re-deal over the stages (min-max DP), tails onto the next dense stage | ROM image re-deal (no RTL); exact capacity run per spec |
| **dsplit**: D (norm, router, top6, shared expert; 3,053 cyc) runs on the first expert stage after the dense stage | compiler + ROM image (shared expert + router words move; same die RTL/engines). **MODEL**: expert-only stages capped at 112 (one expert of q words reserved), D's link/x message unchanged. The exact allocator has no "D on an expert stage" spec yet: tool work needed |
| more stages (+4 dies each) | hardware (die count) |
| extra copies of a dense stage (x3 / x4 / L1 x2, +4 dies each) | hardware (die count). Same die type and ROM image as copy B. The calendar colours users over k copies (new `assign_k`) |
| splitting one layer's attention across stages (projections vs index top-k / KV) | hardware/architecture: the KV and index rows live on the dense stage's dies. Not modelled |
| position-batched MTP verify (6 rows a weight pass) | RTL + compiler (see MTP) |

## (2) Why MTP caps at 10 users
1. The MTP step holds every stage for **6 W - 5 scan**, because the 6 verify positions run back to back in one job context.
   The period is only ~1.40 x the AR period (1,656,896 vs 1,186,972). So MTP users ~= (1.40 / 6) x AR users ~= 0.23 x AR.
   At 140: R003 (L1) step 154,069 and copy-B R028 312,181 / 2 give 1.657 M / 154 k = 10.7, so 10 users.
2. More stages lift MTP only through the same max window: 12 users at the 22.9 k floor, 14 balanced. Then the **head
   dies cap it**. head_mtp = 6 x 10,755 + draft 42,280 = 106,810 cyc, and 1.69 M / 106.8 k = 15.8. Copy colouring (odd
   N on the 2-copy L1) then gives 14. AR head 10,755 is not binding (~116 users).
3. So at every count, multi-user MTP aggregate < AR aggregate (41.3 k vs 92.8 k at the sweet spot). MTP only buys per-user
   speed (2,951 vs 967 tok/s). Lifting the MTP user count needs (a) a verify step below 6 W: field ops issue the 6
   positions in one ROM weight pass (RTL + compiler), and (b) more head capacity or a batched draft head (hardware: head
   dies). Neither is a stage-count change.

## Exact capacity
* Coverage (exact, monotone in N and calendar rows on the same dense layer, from f122_140/148, req201/212 and rb140
  PASS records): s195_dsc4L1 44/44 specs covered (dsplit's moved D words remain MODEL). s153_c3: 30/42 covered, 10 more
  are in the rb140 run still in progress. s141: 17/42 covered, 21 more in rb140.
* LIVE: the 6 specs nobody covers (s141: L12_n106_r3736, L20_n105_r2006, L31_n106_r3736, L38_n82_r3736; s153_c3:
  L13_n106_r1868, L14_n97_r3874) are running on ot-epyc9 at `/srv/opentallas-scratch/claude/s81-sweet` (`run_cap_sweet.sh`,
  `sweet.exact.log`, ot-run oth-ubuntu-3262858-1792563769). Verdict PENDING. s141 and s153_c3 qualify once that run and
  rb140 are all PASS.

Files: `stage_map_*` + `calendar_*` for s140, s141_fine, s153_c3, s164_dsc3L1, s195_dsc4L1. Reproduce any row with
`s81_sweet_sweep.py --out results/arch/s81_sweet_1020 --stages N [--dsplit] [--copies 2=4 8=4 14=4 20=4 1=2] [--tag T]`
(~13 s a count).
