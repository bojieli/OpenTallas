# Sensitivity and provisional-claim audit

> **Legacy/superseded sensitivity.** This sweeps the old single-midpoint
> B200/B300 comparison. Use `results/iso-node/` for current conclusions.

Primary ranking: DeepSeek V4 Pro, 200k context, batch 8. Ratio is ROM
per-user speed divided by the fastest feasible B200/B300 configuration.

| Rank | One-factor input | Low ratio | High ratio | Span |
|---:|---|---:|---:|---:|
| 1 | ROM DeepSeek MXFP4-weight x FP8-activation peak compute (op/s/wafer; all format roofs scale proportionally) | 0.198× | 0.956× | 0.758× |
| 2 | pipeline efficiency | 0.272× | 0.410× | 0.138× |
| 3 | defect-repair efficiency | 0.317× | 0.408× | 0.092× |
| 4 | ROM array bandwidth (B/s/wafer) | 0.320× | 0.385× | 0.065× |
| 5 | load-balance efficiency | 0.343× | 0.398× | 0.055× |
| 6 | ROM capacity (bytes/wafer) | 0.357× | 0.392× | 0.035× |
| 7 | weight encoding: released vs uniform MXFP4 | 0.365× | 0.385× | 0.020× |
| 8 | collective injection bandwidth (B/s) | 0.385× | 0.403× | 0.019× |
| 9 | GPU shared-KV reread amplification | 0.385× | 0.391× | 0.007× |
| 10 | index-cache bytes: FP4 to BF16 | 0.384× | 0.389× | 0.005× |
| 11 | collective floor (s/layer) | 0.381× | 0.385× | 0.004× |
| 12 | main-KV bytes: production to BF16 | 0.385× | 0.385× | 0.001× |
| 13 | ROM HBM bandwidth (B/s/wafer) | 0.385× | 0.385× | 0.000× |
| 14 | ROM HBM capacity (bytes/wafer) | 0.385× | 0.385× | 0.000× |
| 15 | ROM shared-KV reread amplification | 0.385× | 0.385× | 0.000× |

## Claimed Pro/200k tiers

The table below asks what *per-wafer* array bandwidth and peak compute are
needed while retaining midpoint capacity, HBM, NoC, derates, and six stages.

| Batch | Brief target | Collective/pipeline ceiling | First grid point reaching target |
|---:|---:|---:|---|
| 1 | 7,000 tok/s | 15,616 tok/s | 2.0 PB/s + 10 POP/s |
| 8 | 5,500 tok/s | 2,278 tok/s | not reached; grid max 1,361 tok/s (collective_floor_C6) |
| 32 | 2,250 tok/s | 580 tok/s | not reached; grid max 344 tok/s (collective_floor_C6) |

The ceiling is not a silicon prediction: it removes weight, compute, KV, and
thermal service time to isolate static collective, pipeline, and cross-stage delay.
