# HBM-MTP sizing statistics (MTP-STATS, 2026-10-18)

These are the P-lane sharing statistics for the next HBM die variant, taken from real DeepSeek-V4.1-Flash captures. The run used the released checkpoint dba1be0a on 2026-10-03, with `tools/v41_dspark_onpolicy`: 120 greedy agentic traces across 5 workloads, a teacher-forced router capture of top-6 of 384 experts on all 40 layers, and the real DSpark drafts at every generated position. There are 9,455 decode positions, at contexts from 214 to 8,555 tokens (median 2,221).

The source SHA-256 values are in `summary.json` under `sources`. The tools are `tools/hgi_sim/mtp_union_stats_1018.py`, which writes `moe_union.json`, and `tools/hgi_sim/mtp_stats_summary_1018.py`, which writes `summary.json`.

## (a) MoE expert union per layer

The model routes to the top 6 of 384 experts, plus 1 shared expert.

| P | consecutive, actual verify walk (decorrelated est.) mean / p90 / max | verify bounds [exact-lanes lower, strict upper] mean | greedy continuation mean / p90 | independent users (mixed) mean / p90 / max | same workload mean / p90 | uniform random |
|---|---|---|---|---|---|---|
| 1 | 6 | 6 | 6 | 6 | 6 | 6 |
| 2 | 10.4 / 12 / 12 | [10.1, 10.5] | 10.4 / 12 | 11.6 / 12 / 12 | 11.3 / 12 | 11.9 |
| 4 | 18.0 / 21 / 24 | [15.9, 18.8] | 17.7 / 21 | 21.9 / 24 / 24 | 20.6 / 23 | 23.4 |
| 6 | **24.7 / 30 / 36** | [19.2, 27.6] | 23.9 / 29 | **31.1 / 34 / 36** | 28.8 / 33 | 34.6 |
| 8 | (no gamma-7 drafts) | – | 29.3 / 36 | 39.7 / 44 / 48 | 36.0 / 41 | 45.5 |

How the verify columns are built:

- **Exact lanes.** In the actual DSpark walk the verify lanes are the pending token plus P−1 drafts. The pending lane and the accepted drafts are the trace's own inputs, so their routing is exact.
- **Rejected lanes.** The routing of the rejected draft lanes and every lane after them was not captured. On average that is 1.41 of the 6 lanes at P=6.
- **Estimates for those lanes.** The table gives a lower bound that uses the exact lanes only, and a strict upper bound that adds 6 new experts for each unknown lane. Between the bounds are two estimates: the continuation proxy, which is the old 23.9 held figure, and a decorrelated estimate, which uses the routing of a random other position of the same trace.
- **Recommendation.** Size for the decorrelated estimate: P=6 gives a mean of 24.7 and a p90 of 30. The 23.9 proxy is about one expert optimistic.

Per-layer means vary between 21.9 and 30.6 at P=6 verify. Layers 0, 19 and 39 are the highest; the arrays are in `summary.json`.

Per-expert lane-count histogram (fraction of union experts served by n lanes) at P=6:

| n lanes | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| verify (decorrelated) | 0.717 | 0.176 | 0.062 | 0.027 | 0.013 | 0.006 |
| continuation | 0.697 | 0.182 | 0.068 | 0.031 | 0.015 | 0.008 |
| independent users (mixed) | 0.873 | 0.105 | 0.018 | 0.004 | 0.001 | 0.0001 |

On average a union expert serves 1.46 lanes in the verify walk and 1.16 lanes for independent users. Grouped GEMM over the union is therefore mostly single-row work: per-expert weight reads scale with the union size, not with P.

The DSpark greedy-walk tau on these traces, by gamma, is 1.94, 2.78, 3.51, 4.11 and 4.59 for gamma 1 to 5. The composition default stays 4.159, the owner's 6-class blend.

## (b) Sparse attention: KV-line union

The model selects the indexer top-512 on the 8 index-source layers [2, 8, 14, 20, 24, 28, 32, 36]. Each selection is reused until the next index-source layer, so a token makes 8 distinct selection sets. The compress ratio is 2 on layers 2–19 and 1 on layers 20–39. From layer 20 on, layers draw from the 16,384-line candidate pool built at layer 20. Each token also has a 128-token window.

- **Independent users:** the union is exactly P × single, because users have disjoint KV caches.
- **Consecutive positions: what is exact.** The window union is 128 + P − 1 lines. Whenever the compressed lines number 512 or fewer, every lane selects all of them, so the union equals one lane's set plus at most P − 1 new block lines. That holds for 44% of the decode positions on ratio-2 layers and 31% on ratio-1 layers.
- **Consecutive positions: what was not measured.** The selection overlap at longer contexts, and at the 1M design point, is not measured. No indexer top-k capture exists. The real selection needs the full-model forward, which only runs on the CUDA tool `v41router.py`. The CPU golden `hdc_golden_v41.py` uses the reduced 40 MB model and gives no real attention statistics.
- **What to price at 1M until a capture exists:** the upper bound, P × 512 selected lines + 128 + P − 1 window lines.
- **Follow-up (needs coordinator OK, localhost GPU):** add an Indexer hook to `v41router.py` and re-run phase R1 on the same 120 traces, about 1.6 h, then on synthetic 64K–1M contexts.

## (c) Qwen3-8B DFlash, block 16

Qwen3-8B is a dense model with 36 layers, 8 KV heads and no MoE.

- **Weights:** fully shared across the B verify lanes, and across independent users too.
- **KV, consecutive positions:** fully shared up to the causal offset. The union is pos + B − 1 lines, against pos for a single lane.
- **KV, independent users:** disjoint.

Measured tau (direct run at each block size, cycle-weighted over the 9 primary workloads; block sizes below 16 are out of the drafter's training distribution):

| Block | 2 | 3 | 4 | 5 | 6 | 8 | 12 | 16 |
|---|---|---|---|---|---|---|---|---|
| Tau | 1.74 | 2.27 | 2.63 | 2.86 | 3.03 | 3.30 | 3.49 | 3.66 |

The block-16 workload mean is 4.66. The DFlash rows in `tools/hgi_sim/dflash_timing.py` use a published tau of 8.01 for block 16 and a scaled 5.585 for block 8, against measured values of 3.656 and 3.296. The composition default from third-party data is 3.1445.
