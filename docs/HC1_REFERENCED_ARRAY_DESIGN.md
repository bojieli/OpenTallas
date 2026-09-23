# ROM designs referenced to Taalas HC1

Status: analytical design envelope, 2026-09-23. No RTL, workload simulation or
physical implementation. It follows the user's direction to base the ROM design on
the shipping part that already exceeds 10,000 tokens/s on an 8B model.

## The reference design

Taalas HC1 hardwires Llama-3.1-8B into one **815 mm² TSMC N6** die with 53 B
transistors. All weights live in mask ROM on the die, KV lives in on-die SRAM, and
the part runs at **16,960 tokens/s per user at batch 1 per chip** (1K in / 1K out),
with 200–250 W per card. Its weights use a 3-bit base mixed with 6-bit. Its CEO
describes one transistor storing a ≤4-bit weight and doing the associated multiply.
The repository's reconstruction reads that as pre-compute, select and accumulate
([mechanism](COMPUTE_IN_ROM_MECHANISM.md)). All of these figures are Taalas's own,
with no third-party measurement; sources and grades are in
`configs/hardware/technology.json` → `reference_parts.taalas_hc1`.

From those published facts alone, one HC1 die provides:

| Envelope quantity | Value | Derivation |
|---|---:|---|
| Weight cells per die | ≥ 8.03 B | the whole Llama checkpoint is on the die |
| Token time | 58.96 µs | 1 / 16,960 |
| Weight-select rate | ≥ 1.27 × 10¹⁴ /s | 7.50 B active weights per token time |
| Stage latency | ≤ 0.368 µs | token time / (32 layers × 5 dependent stages) |
| Attention MAC rate | ≥ 9.1 × 10¹² /s | QK + AV at 2K context per token time |
| SRAM ceiling | ≤ 0.94 GB | (53 B − 8.03 B transistors) / 6T per bit |
| Power | 200–250 W | published band |

HC1 publishes no microarchitecture, so its token time is read two ways that
bracket the truth: **throughput-bound** (every cycle selects weights at the rate
above) or **latency-bound** (a fixed time per dependent stage). Both are reported.

This does not repair the repository's independent HC1 reconstruction. That one
still fails capacity, because it charges a 1.6× cell **per bit** instead of one
select transistor **per ≤4-bit weight**. Here HC1 is a design reference, not a
validation gate that the reconstruction has passed.

## What HC1 actually demonstrates

Averaged over the whole die, HC1 holds **4.93 MB/mm² of 4-bit weights**. That
average includes SRAM, accumulators and I/O, yet it exceeds the array-only density
of a compiler-generated ROM at N7 (2.73–4.30 MB/mm²,
[register](../configs/architecture/rom_density_evidence.json)). Its per-die select
rate, however, equals about 64 TB/s of FP8 weights. That is comparable to what a
fabricated SRAM organization delivers from ~1.4 GB on one die (GC200 per-byte rate:
76 TB/s).

**HC1's advantage is weight capacity per die at a local rate, not a faster memory.**
It becomes a large speed advantage exactly when a competitor would otherwise fetch
weights from off-die memory.

## Qwen3-8B: one HC1-class die

Qwen3-8B has 8.19 B weights, 2% more than HC1 holds, with 36 layers against 32.
At HC1's 3.5-bit mixture:

| Machine, one 815 mm² die | Tokens/s per user |
|---|---:|
| HC1-class ROM, throughput reading | 16,818 |
| HC1-class ROM, latency reading | 15,076 |
| HBM die, same 3.5-bit weights, 1.44 GB SRAM cache, hardwired dataflow | 1,994 |
| HBM die, shipped BF16 weights | 256 |

At equal die area, ROM is **7.6–8.4× faster than an optimized HBM die with the same
weight format**, and ~60× faster than the BF16 checkpoint as shipped. This is the
several-fold advantage the project is looking for, and it follows from capacity.
The HBM die can cache only 44% of the weights, so 1.87 GB per token must come
from HBM at 3.9 TB/s.

Three conditions come with it:

1. **Numerics.** HC1's format is a 3/6-bit quantization with acknowledged quality
   loss and parallel accumulation. The shipped Qwen capability is BF16 with
   sequential whole-K RNE, which caps *any* machine at 1,125 tokens/s
   ([compact screen](QWEN_COMPACT_RESOURCE_SCREEN.md)). Adopting an HC1-class
   format is a model-quality decision that needs qualification before this row
   becomes a design.
2. **Context.** 2K-context KV (302 MB, BF16) fits. At 8K, KV is 1.21 GB, above
   the 0.94 GB that HC1's transistor count could hold even if nothing else used
   transistors. An 8K Qwen die needs FP8/FP4 KV, attached KV memory or a second die.
3. **Capacity margin.** 2% over HC1's measured content is within the uncertainty
   of an unpublished floorplan, but it is not demonstrated. N5 or a smaller
   embedding store would restore margin.

## DeepSeek-V4.1-Flash: an array of HC1-class dies

V4.1's native formats match the cell well. Routed experts are FP4: one cell per
weight, with the E8M0 scale per 32 applied after each block partial. Dense FP8 is
charged two nibble cells, BF16 four and F32 eight; only the ≤4-bit case has
published support. Both die types reserve 50 mm² of FP8 MACs (B300-derived density)
for attention and index scans. On the ROM die that costs 6% of weight capacity.

**Map.** Two dies per layer: die A holds the layer's dense work plus half the
experts, die B the other half, at 92.6% fill. The head (2.65 B cells) spreads over
spare capacity on eight dies. That is **80 dies, 65,200 mm², ≤20 kW**. Engram
tables stay external and are prefetched from token ids.

**Schedule per layer.** The attention side runs on die A: 6 stages, 8 on index
layers, 7 on Engram layers. The FFN side has die A running shared expert, router
and its experts, while die B runs its experts behind a dispatch and return hop.
The two paths overlap; the next layer is one hop away. At 8K, 0.25 µs links and the
throughput reading, a typical layer spends 2.0 µs selecting 257 M attention cells,
1.7 µs on die A's FFN path and 0.25 µs on the hop.

**The HBM baseline gets the same dataflow.** It uses the same stage latencies, no
kernel launches or software collectives, dense weights cached in on-die SRAM, and
experts striped over up to 64 dies from HBM with an explicit reduction. Its per-die
bandwidth, capacity and system power come from B300 (published, halved per die).
The same-area HBM machine has 80 dies; the same-power machine has 22.

| Context | HC1 reading | Link delay | ROM tok/s (spread / worst route) | HBM equal area (miss / cached) | HBM equal power | ROM ÷ HBM, equal area, miss |
|---|---|---:|---:|---:|---:|---:|
| 8K | throughput | 0.10 µs | 5,111 / 4,366 | 5,265 / 5,644 | 4,722 | 0.97 |
| 8K | throughput | 0.25 µs | 4,952 / 4,250 | 4,668 / 4,964 | 4,236 | 1.06 |
| 8K | throughput | 0.50 µs | 4,577 / 3,970 | 3,926 / 4,133 | 3,616 | 1.17 |
| 8K | throughput | 1.00 µs | 3,578 / 3,196 | 2,978 / 3,096 | 2,797 | 1.20 |
| 8K | latency | 0.25 µs | 4,483 / 4,250 | 4,588 / 4,738 | 4,170 | 0.98 |
| 64K | throughput | 0.25 µs | 4,708 / 4,069 | 4,557 / 4,838 | 4,144 | 1.03 |
| 64K | latency | 1.00 µs | 3,449 / 3,093 | 2,919 / 2,980 | 2,745 | 1.18 |

The full sweep has 16 rows. Across them, **ROM per-user speed is 0.87–1.21× the
idealized HBM array at equal area and 0.96–1.29× at equal power.** Both machines
sit near 3,000–5,000 tokens/s per user. The floor is 40 layers of 12–14 dependent
stages plus hops, and neither weight store removes it.

This is not a several-fold ROM decode advantage for V4.1 against an equally
idealized HBM array. The reasons are specific:

- At array scale, an equal-area HBM machine has 80 dies of SRAM (115 GB). That
  caches all 8.5 GB of dense weights, so it gets the same local rate as ROM for the
  dense 65% of each token. The remaining expert reads are spread over 32 dies of HBM.
- Per-die select rate is comparable on both (see above), so the dense side ties.
- The expert side costs HBM a reduction and a first-access latency. That is why
  the ratio rises above 1 as link delay grows.

ROM's V4.1 advantages that survive are **power and cost at equal speed**. ROM needs
≤20 kW against 72.5 kW for 80 HBM dies, with no HBM stacks. It also keeps its speed
without an interconnect good enough to stripe experts 16–32 ways. Against shipping
GPU systems, which pay kernel-launch and collective-software latency this baseline
omits, the gap is far larger. That comparison measures dataflow, though, not ROM.

## Aggregate throughput

Compute-in-ROM does not amortize a weight across a batch (see mechanism doc §4),
but a layer-dedicated array pipelines users. The 40 die pairs can each hold a
different user's token, so aggregate is roughly 40× the per-user rate
(~140–200 K tokens/s for 40 users) if each stage has KV SRAM for its users. HBM can
batch within a stage as well as pipeline, and the existing roofline study
quantifies that per-stream penalty at up to 20.7× at batch 256. Aggregate
comparisons belong there, not in this per-user envelope.

## Decisions this forces

1. **Qwen compact:** adopt an HC1-class single die as the ROM candidate, with a
   quantized-weight numerical contract to be qualified and a 2K KV scope, or
   FP8/attached KV for 8K. This is the one case with a several-fold per-user win.
2. **V4.1 array:** the per-user limit is the dependency chain, not memory. Further
   ROM gains must come from shorter stages (a pipelined select/accumulate below
   HC1's 0.37 µs, if HC1 is throughput-bound) and fewer hops per layer. Neither is
   evidenced yet. Report the power/cost advantage honestly instead of a speed ratio.
3. **Evidence to seek next:** any Taalas disclosure of clock, stage depth or SRAM
   size would collapse the two readings. HC1's own card power at a V4.1-like 7%
   activity would bound the array's real power.

Reproduce with `python3 tools/audit_hc1_referenced_designs.py`; tests in
`tests/test_hc1_referenced_designs.py`; record with every row, assumption and input
hash in [hc1_referenced_designs.json](../results/architecture/hc1_referenced_designs.json).
