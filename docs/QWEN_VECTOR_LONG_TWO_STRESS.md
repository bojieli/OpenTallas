# Two Qwen vector tokens under physical HBM queue pressure

The source-pinned [stress record](../results/rtl/hdc_qwen_long_two_stress_254_255.json)
uses the same reduced Qwen3 images and position-254/255 ISA program as the
[uncontended two-token gate](QWEN_VECTOR_LONG_TWO_GATE.md). Both tokens again
produce **1561** with zero logit, VM, KV, and fault mismatches after each
token. During position 255, the KV system reads 16 physical V sectors written
before that token. The testbench-only position-256 maintenance pulse closes
K tile 15 after both tokens; 128 K write transactions complete across 64
packed sectors with zero byte mismatches. No third core token executes.

At the first pending HBM request of token 255, a deterministic seedless
injector holds that core request and offers 16-sector reads from scratch
sectors 2048–2063, outside the KV image. An extra high tag bit keeps injected
responses out of the KV controller. Four requests are accepted during five
deliberate hold cycles. The injector stops when the HBM model first lowers
its raw ready signal, and the pending core request then waits **26 cycles on
that real ready signal**. The model records 27 total request backpressure
cycles, including the last offered injector request. Deliberate holds are
tracked separately and do not satisfy the core-stall assertion.

Every injected request and beat is checked against its unique tag, beat
index, and scratch data. All 64 injected beats complete exactly once with
zero response errors. The 5,904 core KV read beats also have matching
accepted and completed counts. Physical KV writes are 144 of 144 committed;
the final physical byte comparison is exact. The JSON includes the raw
simulator output and source, image, model, and binary SHA-256 pins.

| Check | Uncontended | Tagged pressure |
| --- | ---: | ---: |
| Core cycles, positions 254 / 255 | 192,856 / 194,998 | 192,856 / 194,998 |
| Core HBM request stalls | 0 | 26 |
| Deliberate injector holds | 0 | 5 |
| Physical KV reads / committed writes | 5,904 / 144 | 5,904 / 144 |
| Cross-token V read-after-write | 16 | 16 |
| K flush transactions / sector byte mismatches | 128 / 0 | 128 / 0 |

The identical core cycle counts show that this short pressure episode fits
within overlap for this reduced workload. It is not evidence of sustained
contention tolerance or a production performance rate. The vector reducer
still limits this exact attention segment to 256 score elements, so neither
run establishes an 8K context. The HBM model is behavioral and does not
calibrate production bandwidth, energy, or physical timing.
