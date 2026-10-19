# S81-BALANCE 2026-10-18: a work-balanced S81 chain, a balanced Qwen ROM point, and apples-to-apples area vs the A100

Owner request (10-18, item 0ik): build a balanced S81 chain and recompute every comparison apples-to-apples, counting HBM
area on both sides. The coordinator added two Qwen ROM items: balance it too, and grow the KV-die attention service until
the KV die stops being the limit.

This is a design study. There is no RTL change, no fleet job and no release-closure change.
- `compute.py` writes `summary.json` and reads only the `inputs_*` files beside it.
- `expert_load.py` produces `inputs_expert_load_holdout.json` from the real router captures (torch plus the MTP-STATS
  capture).

**Grades.**
- **composed:** `token_path_1018` single-user rates.
- **measured:** a committed bench or a real-capture statistic.
- **priced:** an analytic price of record.
- **modelled:** this file's arithmetic.
- **published:** a datasheet constant.
- **stale:** power. No current die has a power figure, so every per-W number is stale (±50%).

The A100 rows are the repo roofline, so they are an upper bound for the A100.

## 0. Two corrections found on the way

1. **SCANCHK: p4l has one HBM3E stack a die** (`s81_dv_1016/SPEC.md` 0b-p4g).
   - The die has 16 regional controllers `dsfd_ctrl_rg2` of 2 pseudo-channels each, which is 32 PCs, behind one PHY with
     an 8.5 mm face.
   - The 10-18 composition charges the 10-09 index-scan rate instead: 5,987 cycles for 71.3 MB on 4 dies, which is
     3.76 stacks a die.
   - Corrected, the current S81 single-user rate is **AR 1,189 / MTP 3,461 tok/s** (modelled), against 1,243 / 3,808 as
     composed. The reindex layers are score-bound, so they do not move.
   - Lane S81-SCANCHK had not reported when this ran. This is this lane's own check; confirm it when that lane reports.
2. **DeepSeek-V4.1-Flash has 384 routed experts** (MTP-STATS router capture), not the 256 that ROM-MULTIUSER and
   TPUT-RECHECK assumed.
   - On the A100 roofline that raises batch-1 AR from 406 to **438**, MTP from 778 to **962**, max AR to 3,523 and max
     MTP to 9,011.

## 1. Balanced S81 chain (same die; chain re-plan + compiler only)

The model unit is the stage group: one layer's FFN plus the next layer's attention (59 groups from the 10-09 record,
scaled by K = 1.0575 to the 10-18 composition, as in ROM-MULTIUSER).

- **Occupancy** is the busy cycles a stage spends on one position with 1 job context (conservative).
- **Single-user change** = the summed span change. The MTP wave term = 5 x the worst stage's own span.
- **Multi-user** uses the ROM-MULTIUSER shift calendar: users = floor(T / II).

| step | what changes | II (cyc/pos) | AR / MTP single-user | AR users -> aggregate | MTP users -> aggregate | dies + stacks | die+HBM mm² | AR agg / mm² (die+HBM) |
|---|---|---|---|---|---|---|---|---|
| as composed (wrong scan rate) | – | 37,188 | 1,243 / 3,808 | 25 -> 31.1k | 5 -> 19.0k | 440 + 440 | 404,888 | 0.077 |
| **current, corrected** (1 stack/die, contiguous experts) | – | 54,722 | **1,189 / 3,461** | 18 -> 21.4k | 4 -> 13.8k | 440 + 440 | 404,888 | 0.053 |
| B1 hot/cold experts spread | expert -> stage placement (ROM content map) | 53,527 | 1,189 / 3,461 | 18 -> 21.4k | 4 -> 13.8k | same | same | 0.053 |
| B2 index shards on the layer's own dies | index keys of each scan layer striped over the ~10 dies (10 stacks) that already hold that layer; per-die local top-k + merge | 38,900 | **1,224 / 3,724** | 25 -> 30.6k | 5 -> 18.6k | same | same | 0.076 |
| **B3** MTP read sharing | one index read scores the 6 verify queries | 38,900 | **1,224 / 3,829** | 25 -> **30.6k** | 6 -> **23.0k** | **440 + 440** | **404,888** | **0.076** |
| **B4 knee** = B3 + the 10 heaviest groups x2 | users alternate copies; reserved user on copy A | 20,753 | 1,224 / 3,829 | **47 -> 57.5k** | 10 -> 38.3k | 540 + 540 | 496,908 | **0.116** |
| B4 max per mm² (greedy, 128 copies) | | 5,414 | 1,224 / 3,829 | 181 -> 221.5k | 40 -> 153.2k | 1,720 + 1,720 | 1,582,744 | 0.140 |
| B5 = B3 + TP width +4 dies on the 8 field-heaviest groups | single-user lever | 38,900 | **1,285 / 3,970** | 24 -> 30.8k | 6 -> 23.8k | 472 + 472 | 434,334 | 0.071 |
| ALT (die change) 2 stacks a die, no sharding | PHY shoreline | 41,621 | 1,225 / 3,689 | 23 -> 28.2k | 5 -> 18.4k | 440 + 880 | 458,128 | 0.062 |
| sensitivity: B3 with 2 job contexts a die (unmeasured) | overlap 2 positions in a stage | 19,450 | 1,224 / 4,102 | 50 -> 61.2k | 11 -> 45.1k | 440 + 440 | 404,888 | 0.151 |

**Single-user rate.** Against today's real (corrected) chain, B3 is +2.9% AR and +10.6% MTP. Against the over-stated
composition it is −1.5% AR and +0.6% MTP. B5 adds +5% AR / +3.7% MTP for +32 dies, which brings AR above the composed
1,243.

**Expert load (measured on real captures, `inputs_expert_load_holdout.json`).**
- Source: 120 agentic traces, 9,455 decode positions, top-6 of 384 experts, 40 layers. The placement is fitted on 60
  traces and scored on the other 60.
- The hottest expert in a layer gets up to 38x the uniform share.
- Per-group load max/mean, worst layer:

  | expert groups | contiguous placement | balanced placement |
  |---|---|---|
  | 3 | 1.29 | 1.13 |
  | 8 | 1.69 | 1.20 |
  | 12 | 2.09 | 1.30 |

  At 12 groups the hot experts also need replicas.
- S81 row-shards every matrix over all 128 frames of a TP4 stage, so routing cannot unbalance dies inside a stage. Only
  the split of a layer's experts over its ~2.4 stages matters. **For S81 this lever is small:** −2% II and nothing on
  single-user.

**Why B4 saturates.** After the 10 heaviest groups are doubled, the next 20.8k groups (L5/L6/L9/L10 FFN-field-bound)
are numerous. Each further copy buys less: 269 tok/s per added die up to the knee, about 140 after it.

**Top-down sizing for a per-user floor of 1,000 tok/s.**
- Every AR and MTP user of B3/B4 is at 1,224 / 3,829 tok/s, so all of them clear the floor.
- The AR fillers inside an MTP calendar run at 915 tok/s, so they are excluded.
- **Recommended point: B4 knee.** 540 dies + 540 stacks, 47 AR users, 57.5k tok/s aggregate, 0.116 tok/s per mm²
  (die+HBM). That is +88% aggregate for +23% area over B3.
- **Max aggregate per mm²:** B5 + greedy replication, 1,842 dies, 247k, 0.146. That is only +25% per mm² over the knee
  for 3.4x the area.
- With 2 job contexts (unmeasured), B3 + replication reaches 0.238 per mm² at 1,190 dies.

**Latency-throughput design points (S81).**

| point | per-user | users | aggregate | mm² |
|---|---|---|---|---|
| MTP B3 | 3,829 | 6 | 23.0k | 0.40 M |
| MTP knee | 3,829 | 10 | 38.3k | 0.50 M |
| AR B5 | 1,285 | 24 | 30.8k | 0.43 M |
| AR knee | 1,224 | 47 | 57.5k | 0.50 M |
| AR max | 1,224 | 181 | 221k | 1.58 M |

The full curves are in `summary.json` `s81.curve`, `curve_tp` and `curve_ctx2`.

**Chain plan / compiler changes (no die change for B1-B5).**
1. **B1:** expert -> stage placement by measured load (LPT, equal expert count a stage) is a ROM content map. Add hot
   replicas only if a layer splits into 8 or more groups.
2. **B2, the index stripe.** The compiler places each scan layer's index-key entries round-robin across the HBM of the
   layer's ~10 dies.
   - Each die's `svc_sx` scans its shard and runs a local top-512.
   - A merge tree returns the result over the existing stage links: about 2 hops (2,012 cycles) plus 150 per doubling,
     charged in the model.
   - New compiler work: the q broadcast to the shard dies and the merge order, which must be deterministic and the
     golden's top-k tie rule.
   - RTL check owed: the `svc_sx` top-k must accept a merge input. Today it merges TP4 partials only.
3. **B3:** the MTP verify job word carries 6 query slots per scan job. Sharing needs 6 score accumulators in `svc_sx`.
   If it has one, the score is time-multiplexed: 6 x score against one read, as the model charges.
4. **B4:** a replicated stage group is a rack/chain re-plan. The upstream stage's lep needs a second tx port (A/B), and
   the reuse layers read the owner copy by user (ROM-MULTIUSER item 5).
5. **B5:** TP width +4 on a field-heavy group is a chain re-plan with an 8-die collective. Its cost is modelled as coll x
   (1 + 0.25 log2(8/4)).
6. Stacks per die (ALT) **is** a die change, and it is worse per mm² than B2. It is not recommended.

## 2. Qwen ROM balance (coordinator additions)

Per-layer occupancy per user, in cycles of the 6,886-cycle layer period. Users = floor(6,886 / binding).

| unit | cycles | users | grade |
|---|---|---|---|
| all-reduce, one in flight | 2,184 | **3** | measured windows |
| KV-die attention service (one instance) | 1,555 | 4 | measured-old-RTL |
| **compute-die tile field (ROM read, 1 MAC/lane/cycle)** | **1,476** | **4** | measured windows |
| KV HBM floor (2.10 MB a KV die a layer at 4 x 512 B/cycle) | 1,024 | 6 | modelled |
| compute-die SU/VM | 275 | 25 | composed |
| all-reduce, pipelined issue (payload 1.9% + issue) | 170 | 40 | modelled |
| D2D q + out (2 KB over a 512-b lane, assumed width) | 32 | 215 | modelled |

| option | users | binding | aggregate | added die mm² (system) | single-user |
|---|---|---|---|---|---|
| today | 3 | all-reduce | 14.0k | 0 | 4,769 |
| **pipelined all-reduce** (compiler + collective sequencer) | **4** | KV service 1,555 (tile field 1,476 just behind) | **18.4k** | 0 | unchanged |
| 2 distributed KV services, all-reduce unchanged | 3 | all-reduce | 14.0k | +66 | unchanged |
| 2 or 4 distributed KV services + pipelined all-reduce | 4 | **compute-die tile field** | 18.4k | +66 / +199 | unchanged |
| + ROM 2-user lanes on the compute die (DIE CHANGE) | 6 | KV HBM 1,024 | 27.8k | +66 + unpriced compute-die | unchanged if the paired users are co-slotted |
| + 4 services + KV HBM ports 820 B/cycle a stack + ROM 2-user lanes | 9 | tile field 738 | 41.0k | +199 + unpriced | unchanged |
| + ROM 4-user lanes | 10 | KV service / HBM 640 | 46.4k | +199 + unpriced | unchanged |

**Answer to the coordinator.**
- More attention service alone buys nothing. **The compute die supports 4 users before it saturates**: 4 x 1,476 =
  5,904 of 6,886 cycles. Saturated, its cap is 21.4k tok/s, the same as the single KV service's cap (21.4k).
- The balanced no-die-change point is therefore a **pipelined all-reduce with the KV die unchanged: 4 users, 18.4k tok/s,
  1.35 tok/s per mm² (die+HBM)**.
- Growing the KV die (distributed per-HBM-channel services; about +8.3 mm² a service, the PV16 delta as a proxy) pays
  only after the compute die reads each ROM weight once for P users (P accumulators a lane). That is a die change on the
  near-reticle 841 mm² die. Its area is unpriced; the HBM-MTP analogue is about 33 mm² a lane on a 642 mm² die.
- Next bottlenecks, in order, once the compute die has P lanes:
  1. KV HBM port (1,024 -> 6 users);
  2. KV service (with 4 services: 389 -> HBM again);
  3. tile field (738 at P=2);
  4. compute SU (25 users);
  5. pipelined all-reduce (40);
  6. D2D (215).

## 3. Apples-to-apples vs the A100 80GB (area = logic die + HBM stack footprint, both sides)

**HBM footprints (published).**
- **HBM3E: 11 x 11 mm = 121 mm²** (Micron HBM3E product brief: 11 x 11 x 0.72 mm; JSSC Jan 2023: HBM3 maximum
  package 11 x 11 mm). This applies to every one of our stacks.
- **HBM2e: 10 x 11 mm = 110 mm²** (SK hynix at Hot Chips 2026, as reported by ServeTheHome: pre-HBM4 base 10 x 11 mm,
  HBM4 12.4 x 11 mm).
- **A100 80GB:** 826 mm² die + 5 active stacks = **1,376 mm²** (8x = 11,008 mm²). The 6-site sensitivity (1,486 mm²) is
  in `summary.json`.
- **Interposer:** no sourced A100 figure was found. The P100's 1,200 mm² is a different part. It is excluded on both
  sides.

**Ratio key.** Ratios are ours / A100. "per mm² d" = die only, "d+H" = die + HBM. Per W is stale.

**A100 baselines (modelled roofline):**

| | b1 AR | b1 spec | max AR | max spec |
|---|---|---|---|---|
| DS, 8x A100 | 438 | 962 | 3,523 (62 users) | 9,011 |
| Qwen, 1x A100 | 173 | 643 | 2,105 (103 users) | 8,632 |

**At a per-user floor of 1,000 tok/s the A100 has no point at all**, in either model, with or without speculation. All
"at floor" ratios are therefore unbounded for every one of our designs whose single-user rate is ≥ 1,000. That is every
design except the two HBM Qwen dies.

**DeepSeek-V4.1 (vs 8x A100):**

| system | die / +HBM mm² | b1 AR (x sys, d, d+H, W) | b1 MTP (x sys, d+H) | max AR (ours, x sys, d, d+H, W) | max spec (ours, x d+H) |
|---|---|---|---|---|---|
| S81 current, corrected, 1 user (today) | 351.6k / 404.9k | 1,189: 2.71, 0.051, 0.074, 0.23 | 3,461: 3.60, 0.098 | 1,189: 0.34, 0.006, 0.009 | 3,461: 0.010 |
| S81 current + calendar | same | same | same | 21.4k: 6.07, 0.114, **0.165**, 0.51 | 13.8k: 0.042 |
| **S81 balanced B3** | same | 1,224: 2.79, 0.052, 0.076, 0.23 | 3,829: 3.98, 0.108 | 30.6k: 8.68, 0.163, **0.236**, 0.73 | 23.0k: **0.069** |
| **S81 balanced B4 knee** | 431.6k / 496.9k | same, 0.062 | 3,829: 0.088 | 57.5k: 16.3, 0.250, **0.362**, 1.11 | 38.3k: **0.094** |
| S81 B4 max per mm² | 1.37M / 1.58M | – | – | 221.5k: 62.9, 0.302, **0.437**, 1.35 | 153k: 0.118 |
| HBM d4g DS (1 job in flight) | 123.2k / 169.7k | 1,994: 4.55, 0.244, **0.295**, 1.16 | 3,259: 3.39, **0.220** | 1,994: 0.57, 0.030, 0.037 | 3,259: 0.024 |
| HBM next die P=2 DS | 129.9k / 176.3k | 1,905: 4.35, 0.221, 0.271, 1.05 | 3,143: 3.27, 0.204 | 3,060 (2 users): 0.87, 0.044, 0.054 | 3,143: 0.022 |

**Qwen3-8B (vs 1x A100):**

| system | die / +HBM mm² | b1 AR (x sys, d, d+H, W) | b1 vs A100 spec (x d+H) | max AR (ours, x sys, d, d+H, W) | max vs A100 spec (x d+H) |
|---|---|---|---|---|---|
| Qwen ROM today | 9,749 / 13,621 | 4,769: 27.6, 2.34, **2.78**, 1.81 | 0.75 | 4,769: 2.27, 0.19, 0.23 | 0.056 |
| **Qwen ROM balanced** (pipelined all-reduce) | same | same | same | 18.4k: 8.75, 0.74, **0.88**, 0.57 | **0.215** |
| HBM d4g Qwen | 5,135 / 7,071 | 931: 5.38, 0.87, **1.05**, 0.82 | 0.28 | 931: 0.44, 0.07, 0.09 | 0.022 |
| HBM next die P=2 Qwen | 5,411 / 7,347 | 946: 5.47, 0.84, 1.02 | DFlash 865: 0.25 | 1,734: 0.82, 0.13, 0.15 | 0.019 |

The Qwen ROM 0.75 is our AR against the A100's spec, so it is shown against the spec column.

**Reading.**
- Counting HBM on both sides raises every ratio by about 1.4x for DS and 1.2x for Qwen. That is because the A100 is 40%
  HBM by footprint, while S81 is 13% (1 stack per 799 mm² die).
- **Per system and per user we win everywhere above ~1,000 tok/s per user.**
- **Per mm² at saturation the A100 still wins:**
  - DS AR: 0.24-0.44x (B3 to B4-max); DS spec: 0.07-0.12x.
  - Qwen AR: 0.88x; Qwen spec: 0.22x.
  - The A100 spec numbers are roofline upper bounds. Measured large-batch spec gains are smaller.
- Batch 1 per mm²:
  - Qwen ROM: **2.8x** the A100 (AR vs AR), 0.75x vs the A100 with spec.
  - HBM d4g DS: 0.30x.
  - S81: 0.074-0.108x. S81 is 0.4 M mm²; the ROM holds all 510 GB of weights in logic-die area.
- HBM d4g today and the P=2 next die are 1-2 users, so their saturated per-mm² is 0.02-0.06x.

## 4. Die changes this needs

- **None for S81 B1-B5.** The chain plan, ROM content map and compiler change. The owed RTL checks are `svc_sx` top-k
  merge input and 6 score slots, and the lep second tx port (ROM-MULTIUSER item list).
- **Qwen balanced point: none.** It needs only the collective sequencer issue rate (check owed: overlapping epochs).
  Going past 4 users needs a compute-die change (ROM P-user lanes) plus KV-die services and HBM ports, and the KV die may
  grow to the reticle.

## Files

- `compute.py`: the model; every constant has its source inline.
- `summary.json`: all rows, curves and comparisons, with grades.
- `inputs_s81_stages_1009.json`: 10-09 stage-group classes (same as ROM-MULTIUSER).
- `inputs_expert_load_holdout.json` and `expert_load.py`: measured routing load.
- `inputs_hbm_mtp_next.json`: HBM-MTP D1 table (claude/hbm-mtp-next-1018 043140ff1).
