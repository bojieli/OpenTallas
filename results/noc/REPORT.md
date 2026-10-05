# Hierarchical NoC sweep

Cycle-approximate static broadcast plus reduction. Payload includes BF16 activations
and FP32 partial sums. Values are architectural estimates, not post-layout timing.

| Model | Batch | Best collective/layer | Topology | Tiles/reticle | Link B/cycle |
|---|---:|---:|---|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 0.291 µs | exchange | 16 | 128 |
| DeepSeek-V4-Flash-0731 | 8 | 1.635 µs | exchange | 16 | 128 |
| DeepSeek-V4-Flash-0731 | 64 | 12.387 µs | exchange | 16 | 128 |
| DeepSeek-V4-Pro-0813 | 1 | 0.435 µs | exchange | 16 | 128 |
| DeepSeek-V4-Pro-0813 | 8 | 2.787 µs | exchange | 16 | 128 |
| DeepSeek-V4-Pro-0813 | 64 | 21.603 µs | exchange | 16 | 128 |
| Kimi-K3 | 1 | 0.435 µs | exchange | 16 | 128 |
| Kimi-K3 | 8 | 2.787 µs | exchange | 16 | 128 |
| Kimi-K3 | 64 | 21.603 µs | exchange | 16 | 128 |
| Qwen3-8B | 1 | 0.291 µs | exchange | 16 | 128 |
| Qwen3-8B | 8 | 1.635 µs | exchange | 16 | 128 |
| Qwen3-8B | 64 | 12.387 µs | exchange | 16 | 128 |

Placement results in `placement.json` use identical per-tile service. MoE cases
apply the p05 correlated-router stress trace; dense controls omit expert-local
placement. They isolate engagement/imbalance penalties, not throughput predictions.
