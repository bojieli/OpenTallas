# Qwen vector decode at 512 positions

The parameterized vector reducer supports `SW × 2^LV` elements per segment. With `SW=16`, the earlier `LV=4` configuration covered 256 positions. The [512-position gate](../results/rtl/hdc_qwen_context_512.json) sets `LV=5`, expands the generated ISA image and VM/KV geometry, and executes a token at position 511 after 511 golden prefill positions. The independent arithmetic oracle and ISA machine agree before RTL execution.

| Measure | Result |
| --- | ---: |
| Input → next token | 271 → 1509, exact |
| Token core cycles | 321,363 |
| Logit, VM, KV, fault mismatches | 0, 0, 0, 0 |
| Physical 32-byte HBM KV reads | 6,024 |
| Physical HBM KV writes / committed writes | 8 / 8 |
| Committed HBM byte mismatches | 0 |
| Pre-token physical K-tail boot reads | 128 |
| HBM ACT / refresh events | 1,308 / 320 |

The core uses synchronous ROM weights in this gate. K/V traffic uses the timed four-pseudo-channel behavioral HBM model, including request arbitration, 32-byte physical sectors, and refresh. The token cycle count starts after pre-token K-tail boot. `PC_RDY=1` and this run has zero request backpressure; it does not establish a production bandwidth, latency, throughput, energy, or physical timing result.

## Window and lead condition

The initial `LWIN=8` (256-line) [diagnostic run](../results/rtl/hdc_qwen_context_512_lwin8_diagnostic.json) did not complete. At core PC 13, the fetch and completion pointers were 144 lines while the consumer had advanced 256 lines. The 17-bit occupancy counter therefore held 130,960, the modular representation of −112; allocation could no longer resume. The streamer already records a sticky underflow fault, but the counter wrap turns this condition into a persistent wait. The diagnostic was terminated and is not an RTL token result.

The passing configuration uses `LWIN=10` (1,024 lines) and a conservative `cfg_lead=2048` cycles. A testbench assertion checks on every cycle that the consumer never overtakes allocated fetch lines. It did not fire. The result demonstrates this configuration for one position-511 token; it does not prove that an arbitrary HBM schedule or longer sequence can sustain the no-stall matrix interface. The 1,024-line window corresponds to 128 KiB of BF16 data across four groups before metadata and banking overhead.

## Route to an 8K context gate

The current ISA count and address fields can represent 8,192 positions, but that is only a width check. The next source-pinned gate needs these block changes and checks:

1. Parameterize the image and memory geometry for `TMAX=8192`: VM region bases, KV K/V sector capacity, CROM depth, and prefill state. Verify the generated ISA program against the independent arithmetic oracle before RTL.
2. Set `LV=9` for up to 8,192 score elements and `LOG_TW=9` for 512 position tiles per KV head. Audit reducer intermediate storage, tail-bank address slicing, and the physical HBM sector mapping at the highest address.
3. Prove the KV fetch/consume invariant under the larger request stream. A fully prefetched functional gate would need a window sized for its largest KV operation and the in-flight fetch block. A bounded on-chip window instead needs a valid/ready stall path through the matrix engine and its accumulation pipeline; the current engine assumes one KV word each active cycle. Add an occupancy underflow guard in that production path rather than relying on modular wrap.
4. Run at least one exact vector token with the timed physical HBM model and compare token, all logits, VM, KV, and committed sectors. Then exercise consecutive tokens across a K tile close and V read-after-write.

The 512-position gate is the first full-system proof beyond the earlier 256-position reducer setting. No 8K result is claimed here.
