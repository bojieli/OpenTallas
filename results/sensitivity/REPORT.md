# Sensitivity and provisional-claim audit

Primary ranking: DeepSeek V4 Pro, 200k context, batch 8. Ratio is ROM
per-user speed divided by the fastest feasible B200/B300 configuration.

| Rank | One-factor input | Low ratio | High ratio | Span |
|---:|---|---:|---:|---:|
| 1 | ROM low-precision peak compute (op/s/wafer; higher-precision roof scales proportionally) | 0.419× | 1.012× | 0.593× |
| 2 | ROM array bandwidth (B/s/wafer) | 0.322× | 0.810× | 0.488× |
| 3 | pipeline efficiency | 0.573× | 0.863× | 0.290× |
| 4 | defect-repair efficiency | 0.669× | 0.859× | 0.191× |
| 5 | load-balance efficiency | 0.707× | 0.844× | 0.137× |
| 6 | collective injection bandwidth (B/s) | 0.810× | 0.857× | 0.047× |
| 7 | weight encoding: released vs uniform MXFP4 | 0.768× | 0.810× | 0.042× |
| 8 | ROM capacity (bytes/wafer) | 0.822× | 0.843× | 0.021× |
| 9 | collective floor (s/layer) | 0.794× | 0.811× | 0.018× |
| 10 | GPU shared-KV reread amplification | 0.810× | 0.825× | 0.015× |
| 11 | index-cache bytes: FP4 to BF16 | 0.809× | 0.819× | 0.010× |
| 12 | main-KV bytes: production to BF16 | 0.810× | 0.811× | 0.001× |
| 13 | ROM HBM bandwidth (B/s/wafer) | 0.810× | 0.810× | 0.000× |
| 14 | ROM HBM capacity (bytes/wafer) | 0.810× | 0.810× | 0.000× |
| 15 | ROM shared-KV reread amplification | 0.810× | 0.810× | 0.000× |

## Claimed Pro/200k tiers

The table below asks what *per-wafer* array bandwidth and peak compute are
needed while retaining midpoint capacity, HBM, NoC, derates, and six stages.

| Batch | Brief target | Collective/pipeline ceiling | First grid point reaching target |
|---:|---:|---:|---|
| 1 | 7,000 tok/s | 26,843 tok/s | 1.0 PB/s + 5 POP/s |
| 8 | 5,500 tok/s | 4,450 tok/s | not reached; grid max 1,921 tok/s (kv_beachfront_C8) |
| 32 | 2,250 tok/s | 1,153 tok/s | not reached; grid max 488 tok/s (kv_beachfront_C8) |

The ceiling is not a silicon prediction: it removes weight, compute, KV, and
thermal service time to isolate static collective, pipeline, and cross-stage delay.
