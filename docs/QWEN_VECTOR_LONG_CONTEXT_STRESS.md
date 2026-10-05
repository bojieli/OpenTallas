# Qwen vector context-256 HBM queue-pressure gate

The source-pinned [stress record](../results/rtl/hdc_qwen_long_context_256_stress.json)
executes the same reduced Qwen3 vector ISA token at position 255 as the
[uncontended control](QWEN_VECTOR_LONG_CONTEXT_CONTROL.md). The 255 earlier
positions are seeded from the arithmetic golden model. Both runs use G4/SW16,
FP8 physical K/V sectors, the four-pseudo-channel timed behavioral HBM model,
and synchronous ROM weights. The RTL produced token **1561** in both runs,
with zero logit, VM, KV, fault, and committed physical HBM byte mismatches.

| Check | Uncontended control | Tagged stress |
| --- | ---: | ---: |
| Core cycles, excluding K-tail boot | 192,856 | 192,856 |
| Core KV HBM read sectors | 2,952 | 2,952 |
| Committed KV HBM writes | 8 of 8 | 8 of 8 |
| Physical K-tail boot reads | 128 | 128 |
| HBM model request backpressure cycles | 0 | 27 |
| Core request stalls from HBM model | 0 | 26 |
| Deliberate injector hold cycles | 0 | 5 |
| Injected read sectors accepted/completed | 0 | 64 / 64 |

The stress test uses a deterministic, seedless schedule. At the first pending
core HBM request after token start, it offers one 16-sector read per cycle to
scratch sectors 2048–2063, outside the 0–2047 KV image. The injected requests
carry an extra high tag bit and cannot return to the KV controller. The test
holds that first core request for five cycles while the real HBM queues fill;
four synthetic requests are accepted. It stops injecting when the HBM model
first lowers its raw ready signal, then releases the pending core request to
that signal. **The five deliberate holds are separate from the 26 subsequent
cycles in which the released core request waited on HBM model ready.**

The testbench checks each injected request's 16 beat indices and data in a
unique request-tag scoreboard. All 64 injected beats returned exactly once;
the scoreboard found zero duplicate, missing, or wrong-data responses. Core
reads also conserved 2,952 accepted and 2,952 completed beats. The JSON
contains the complete raw simulator output, source/image/model/binary SHA-256
pins, queue settings, and injector policy.

The unchanged core cycle count shows that this short pressure episode fell
within slack or overlap for this reduced workload. It does not establish a
rate improvement or immunity to sustained contention. This gate stops at the
current 256-element vector reduction limit. An 8K exact token requires a
redesigned chunked reducer and larger VM, RoPE, and KV geometry. The timing
model is behavioral and is not a calibrated production throughput, bandwidth,
energy, or physical timing result.
