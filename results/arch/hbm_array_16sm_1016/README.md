# HBM array: 16 SM / 2 stack die vs 32 / 4 (owner question 10-16 ~21:40)

The model is `tools/hgi_sim/ds_die_split.py`. It re-runs the S2 schedule (command processor, wait masks, per layer segment) on the native DeepSeek-V4.1 programme: the AR token, the MTP design point (verify P=6, the R-row DSpark draft and the seed), and Qwen3-8B AR.
- **Relay stages:** each die's H-DIE per-class `stages_bw` relative to v5carry (`stages.json`, from `claude/hdie-d4c-g2`).
- **Split transform:** described in the module docstring.
- **Runs:** fleet `ot-run` on EPYC4. Round 1 is `die_split_r1.json` and round 2 is `die_split_r2.json`. `census_ar_r1_premergefix.json` is the per-record census taken before the TOPK_MERGE byte fix.
- **Grade:** schedule model (relay-only stages plus the split transform). These are not measured rates.

## Results (1M context; DS MTP = the design point, τ 4.159)

| System | DS AR tok/s | DS MTP tok/s | Qwen AR tok/s | mm²/SM |
|---|---:|---:|---:|---:|
| 96 x d4c, 32 SM / 4 stacks, TP-96 (824.8 mm²) | 2,006.8 | 3,485.5 | 940.2 (TP-4) | 25.8 |
| **192 x d4f, 16 SM / 2 stacks, TP-192, full core (618 mm² stages; 674 mm² widened)** | **1,777.7 (-11.4%)** | **3,040.9 (-12.8%)** | 934.1 (TP-8, -0.7%) | 38.6 / 42.1 |
| same, SU at half width (512 lanes) | 1,776.8 (-11.5%) | 3,039.9 | 934.1 | |
| same, VM-ring fill of the SE/NE hubs (option a, upper proxy) | 1,725.2 (-14.0%) | 2,944.7 (-15.5%) | 931.0 | |
| 192 x A2P as drawn (470 mm²): 2 COLL lanes, half SU | 1,651.2 (-17.7%) | 2,749.8 (-21.1%) | 935.2 | 29.4 |
| 192 x A2P with 4 COLL lanes | 1,834.7 (-8.6%) | 3,139.9 (-9.9%) | 938.2 | |
| 2 x TP-96 groups of d4f (DP=2), 4 lanes | 1,835.5 (-8.5%) | 2,997.1 (-14.0%) | 524.9 (TP-4, -44%) | |
| 2 x TP-96 groups of d4f (DP=2), 2 lanes | 1,731.8 (-13.7%) | 2,722.1 (-21.9%) | 524.1 | |
| 192 x d4f on a 2-tier switch (+2 crossings) | 1,009.3 (-49.7%)* | 1,778.9 | — | |
| 128 x 24 SM / 3 stacks, TP-128 (B24a geometry, 779 mm²) | 1,965.4 (-2.1%) | 3,417.4 (-2.0%) | 749.3 (TP-4, -20%); 1,272.7 (TP-8, +35%) | 32.5 |

\* The 2-tier row was priced on the A2P stages.

**Where the d4f loss comes from**
- The split alone, on d4c stages, costs -7.6% AR. The A2P relay stages alone cost -1.2%; the d4f relay stages alone cost -4.3%.
- The split loss has three parts:
  - Head work (wq_b, the wo_a K-split, and option-B attention, all on 64 head dies at half the SMs and bandwidth): about +20k cycles per token.
  - Each collective's delivery term grows from (G-1)·f/lanes at G=96 to G=192: +24 cycles a gather, and +1.5k cycles per index merge (192 x 512 candidates).
  - ROW_GATHER padding.
- Row-split SM work, routed experts and IDX key scans do not change: half the rows run on half the SMs at half the bandwidth.

## Capacity, links, blockers

- **Capacity: not a blocker.**
  - Each stack is 22.5 GB (`STACK_BYTES`), so 45 GB per die.
  - Weights are 510 GB / 192 = 2.66 GB per die.
  - KV at 1M is 4.9 MB/user/die (sharded) plus 2.7 MB/user/die (window rows, replicated).
  - That gives about 4,900 users per 192-die array, against about 6,000 for 96 x d4c. The replicated window costs about 18% of users, far above any saturated batch.
- **Switch: a one-tier fabric is mandatory (a 2-tier switch costs -50%).** It is feasible: at 32 x 100G lanes per die (4 x 800G), 192 dies need at least 12 Tomahawk-Ultra-class 512-lane chips. Eight 800G ports per die would need at least 24 chips.
- **SerDes: 5 links (4 switch + 1 host/spare) are enough.** Ingress is 4 x 720 Gb/s = 360 GB/s, above the 4-lane delivery bound of 307 GB/s.
- **Core requirements, from S2:**
  - 4 COLL delivery lanes: REQUIRED. 2 lanes cost a further ~9%.
  - VM 2^18 words: REQUIRED. The map is about 261.7k words of replicated D-wide buffers, so no TP split shrinks it.
  - SU: 512 lanes is enough (cost 0.04%).
  - SE/NE hubs filled over the VM ring (option a): OK. The upper proxy costs ≤2.6%, and the compiler should keep SM operands in the SW/NW banks.
- **Routing, Sinkhorn and expert placement:** no change.
  - HC/Sinkhorn is replicated per die and costs the same.
  - Top-6 routing is local.
  - Experts stay TP-row-split: each die holds 1/192 of every expert. EP at batch 1 loses, per the MICROARCH audit.
  - The index top-k merge doubles its candidates (192 x 512): about +12k cycles per token, included above. A 2-die pre-merge would recover it.
- **Saturated throughput:** a TP group's saturated rate is set per die, and the replicated SU/HC/COLL work does not divide over more dies. So 192 small dies in one TP group give at most the throughput of 96 large dies, times the ~0.89 chain ratio: per die it halves, and per array it is unchanged at best. DP=2 (2 x TP-96 small groups) restores the engine parallelism but costs Qwen 44% and DS MTP 14% per user.

## Verdict

16 SM / 2 stacks works functionally for both models (capacity OK, one-tier switch feasible, no new blocker). It is not a significant gain:
- DS loses 11–13% (AR 1,778, MTP 3,041) against 32/4.
- Qwen is flat (TP-8).
- Silicon per SM rises 50–63% (38.6–42.1 vs 25.8 mm²/SM), because the full core is needed on every die.

24 SM / 3 stacks (TP-128) costs only about 2% DS, but it needs Qwen at TP-8 to avoid -20%, and it adds ~26% silicon per SM.

**Recommendation:** keep 32 / 4 as the rate- and silicon-optimal point. If reticle squeeze or closure demands a smaller die, take 24 / 3 (or B24a) before 16 / 2. If 16 / 2 is taken for closure, d4f with a half-width SU and VM-ring fill is the right core. Its price is about -11 to -14% DS.
