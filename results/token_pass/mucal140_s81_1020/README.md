# S81-MUCAL140 (MU.S81.CAL, 10-20): multi-user static calendar on the 140 physical stage windows

Tool: `tools/s81_dv/dv_mu_calendar_phys.py` (model in its docstring); `--check` reproduces `calendar_phys140_{ar,mtp}.json`.
Map `stage_pick_122/stage_map_f122_140.json` sha f5608b1e5f2a (140 TP4 stages, copy B on the 8 dense-owner stages = 32 dies).
Node cycles = `tools/toksim_s81_compose.py` release-partial composition of record (strict admission; AR 80.3 % / MTP 71.6 % measured),
captured per node from the composer, + cal2 node deltas (XG5 +2/+1, COLL7 +4 a phase, IDX3R +62 = measured rg3 worst pair 41 + 21 W->E)
+ 20 added stage hops x 1008. Not inherited: the 46 AR / 10 MTP of the 59 legacy Sxxx groups.

| | old (legacy 59 groups, RATEFIX cal2 s140) | NEW physical 140 (composer of record) |
|---|---|---|
| AR single user | 1,065.9 tok/s | **815.5 tok/s** (T 1,471,549 cyc) |
| AR users (0 collisions) | 46 | **36** (N=37 FAULT) |
| AR aggregate | 49,032 | **29,357** |
| MTP single user (tau 4.159) | 3,286.0 | **2,509.4** (step 1,988,818 cyc) |
| MTP users | 10 (+1 filler) | **8** (N=9 FAULT; fillers not searched) |
| MTP aggregate | 32,860 | **20,075** |

Checker: brute force over every window of every user mod P on 140 stage copies + 8 copy-B + link copy pairs + head + host:
AR 14,580 windows 0 collisions, MTP 3,240 windows 0 collisions; negative controls N+1 FAULT and injected shift FAULT (both modes).
Bound: dense stage R003 (L0 tail experts + L1 dense + L1 head experts held by one job context): AR 38,804 / MTP step 232,821 cycles;
expert-only stages ~7,150 (median). Copy-B dense stages (R007 61,551) sit under the per-copy bound.

Split of the drop: per-user rate = composer of record (834.0 -> 815.5 with cal2 + hops + forward-x adds, vs RATEFIX 1,065.9);
user count = physical windows (dense stages hold the previous layer's tail experts, the attention and the next layer's head experts).
MODEL items (priced, not measured): static min(6,N) expert-slot reservation per stage, forward-x schedule + partial add 82 cyc
(= measured eng.add), MTP step law 6W-5scan and wave = 5 x worst physical per-position busy (replaces composer wave.busy 235,450 -> 307,445).
Largest lever (next): stop one context holding a dense stage across tail-experts + dense + head-experts (move tails off dense
stages or 2 job contexts): dense windows ~31k -> ~45+ AR users.
