# Qwen3-8B decode core: architecture specification (top-down)

Scope: Qwen3-8B (hidden 4,096, 36 layers, 32/8 heads of 128, FFN 12,288,
vocabulary 151,936), batch 1, greedy, bit-exact against the golden
(`tools/hdc_golden.py`), on two designs:

* **ROM** — the single-reticle Taalas-HC1-class die (N6, 815 mm²): weights in
  ROM, KV in on-die SRAM. The reticle split comes from
  `opentallas.roofline.taalas_hc1_anchor`: ROM 262.0 mm², compute 146.7 mm²,
  SRAM 259.6 mm², interconnect 65.2 mm², overhead 81.5 mm².
* **HBM** — the iso-area comparator: one reticle of logic with **6 HBM3E
  stacks**. 6 is the reticle's beachfront: 2 × (26 + 33) mm × 60% edge use /
  12 mm a stack = 5.9. H200 also carries 6. At 1.0 TB/s a stack × 0.90
  sustained that is 5.4 TB/s.

Everything below is computed by `tools/arch_budget_qwen3.py`, which writes
`results/arch/qwen3_budget.json` and is tested by
`tests/test_arch_budget_qwen3.py`. The test includes the **performance gate**:
the RTL-calibrated sequencer model, replaying the program the core runs at the
shipped shapes, against a ratchet that falls as each block lands and ends at
the budget target. The clock is the slowest routed Qwen3 token-path unit,
1.0986 GHz (`ot_hdc_matvec`; ASAP7 TT).

## 1. Requirement and target

On the ROM design the binding resource is the **weight sweep on the MAC
lanes**. Weights cost nothing to read: a compute-in-ROM cell is read by the
multiply that uses it. Every weight must still pass through a MAC once per
token:

* 7,568,097,280 MACs per token (36 × 193.0 M, plus the lm_head's 622.3 M).
* On 131,072 lanes that is **57,740 cycles**, a ceiling of
  **19,027 tok/s** <!-- figure: 19,027.4 src="results/arch/qwen3_budget.json#budget.ceiling_tokens_s" name="Qwen3-8B ROM weight-sweep ceiling tok/s" -->.

The budget gives the weight sweep 55% of the token:

* **Target: 104,982 cycles per token, 10,465 tok/s per user at 2k context** <!-- figure: 10,465.1 src="results/arch/qwen3_budget.json#budget.target_tokens_s" name="Qwen3-8B ROM budget target tok/s" -->.
* The analytical headline, `decode_critical_path.py`, is 8,680 tok/s.

On the HBM design the binding resource is **bytes over the stacks**. Its
target is 95% of the byte bound:

| format | 2k bound | 2k target | 8k bound | 8k target | MAC lanes (2× margin) |
|---|---|---|---|---|---|
| BF16 | 349.8 | 332.3 | 330.4 | 313.9 | 4,820 |
| FP8 | 686.1 | 651.8 | 615.3 | 584.5 | 9,454 |
| ROM's 3.5-bit format | 1,494.6 | 1,419.9 | 1,195.0 | 1,135.2 | 20,592 |

Bounds and targets are tok/s per user. MAC lanes are sized at 2k.

## 2. Workload per token (from the graph)

| class | 2k | 8k |
|---|---|---|
| weight MACs (qkv 906 M, o 604 M, gate/up 3,624 M, down 1,812 M, lm_head 622 M) | 7.568 G | 7.568 G |
| attention MACs (Q·K and P·V, each 36 × 32 × 128 × T) | 604 M | 2,416 M |
| KV read, BF16, each element once (GQA-shared) | 302 MB | 1,208 MB |
| KV capacity at 24.07 Mb/mm² | 100.4 mm² | 401.6 mm² (**exceeds the 259.6 mm² SRAM**) |
| elementwise element-ops (reference graph: three softmax passes) | 8.75 M | 29.98 M |
| reductions | 73 of 4,096 (sums of squares), 1,440 of 128 (q/k norms), 2 × 1,152 of T (softmax), 1 argmax of 151,936 | same |
| dependent stages a layer | 21 (reference graph), 20 (spec, §5) | same |

At 8k, BF16 KV does not fit the reticle's SRAM. At 8k the ROM design needs
either an FP8 KV cache (604 MB, 200.8 mm²; a golden change) or KV in HBM.

## 3. Roofline per resource (ROM design, spec widths)

| resource | 2k cycles | 8k cycles |
|---|---|---|
| weights on 131,072 lanes | 57,740 | 57,740 |
| attention on 131,072 lanes | 4,608 | 18,432 |
| KV SRAM, one 16-lane BF16 word per group per cycle | 1,152 | 4,608 |
| elementwise (reference graph) on 512 lanes | 34,170 | 117,114 |

The elementwise row is why the spec restructures softmax (§5): three passes
over 32 × T elements per layer is the largest non-weight load.

## 4. Budget and per-block requirements (ROM, 2k)

| share | cycles | resource |
|---|---|---|
| weights 55% | 57,740 | MAC lanes |
| attention 5% | 5,249 | attention lanes and KV banks |
| elementwise 7% | 7,349 | stream unit |
| exposed dependency latency 30% | 31,495 | every dependent stage |
| control 3% | 3,149 | sequencer |

Requirements derived from the budget:

| block | requirement |
|---|---|
| MAC array | 131,072 lanes = **8,192 groups** (a power of two, so every K-split tiles whole rounds: weight tiling 0.9999 of ideal) |
| ROM read | 57,344 B/cycle (one 3.5-bit weight a lane a cycle) |
| attention | ≥ 115,066 lanes busy: Q·K and P·V both K-split over every free group |
| KV SRAM | ≥ 57,533 B/cycle (≥ 1,798 16-lane BF16 banks); 100.4 mm² at 2k |
| stream unit | **512 elements/cycle**; a lane-partial plus 9-level cross-lane pairwise reduction tree |
| dependency | ≤ 44 cycles exposed per dependent stage (31,495 over 36 × 20). This needs tile-granular chaining, never a full-unit drain |
| sequencer | ≤ 3,149 exposed control cycles a token: back-to-back issue from a prefetched decode |
| argmax | a streaming compare tree on the result path (as built) |
| vector buffer | ≥ 65,536 FP32 elements (score rows 32 × T, gate/up 2 × 12,288) |

On area, the lanes are 131,072 × 1,071.8 µm² = 140.5 mm² (routed ASAP7, not
scaled to N6), inside the 146.7 mm² compute share. The spec's 512-lane stream
unit adds about 12.8 mm², estimated at 25,000 µm² a lane: lane 0 has every
SFU, and lanes 1.. carry exp, three multipliers, an adder and a reducer, as in
the V4.1 vector stream unit. That 12.8 mm² exceeds the compute share by
6.6 mm². It is taken from SRAM, which has 125.7 mm² spare after the 2k KV and
the DFlash drafter's ROM.

## 5. Reconciliation: analytical DAG vs calibrated sequencer vs as built

All figures are cycles per token at 2k:

| model | cycles | tok/s | what differs |
|---|---|---|---|
| analytical DAG (`decode_critical_path.py`, SU 256, attention at the full MAC rate, no drains) | ~119,000 | 8,680 | reference |
| dependency chain at spec widths, reference graph (SU 512, K-split attention, as-built unit latencies) | 144,576 | 7,599 | latency 68,148 and three softmax passes |
| dependency chain, spec (one-pass softmax, prefetched issue) | 131,256 | 8,370 | latency 62,532 is now the largest term after weights |
| calibrated model, as built (SU 1, split ≤ 8, 7,680 groups) | **14,499,553** <!-- figure: 14,499,553 src="results/arch/qwen3_budget.json#as_built_calibrated.2048.cycles" name="Qwen3-8B calibrated as-built cycles 2k" --> | 75.8 | everything below |
| the same with the split field ignored (the figure first reported) | 13,714,305 | 80.1 | `me_split` is 2 bits: S ≤ 8 |

Where the as-built 14.5 M cycles go:

* Unit busy:
  * stream unit 8,710,761 (1 element a cycle);
  * P·V 4,718,592 (head_dim on the lanes: 8 of 7,680 groups; positions in order, T × 8 cycles an op);
  * weights 884,736 (split ≤ 8);
  * Q·K 147,456 (1,024 cycles an op);
  * lm_head 8,192.
* Sequencer:
  * barrier drains 13.46 M;
  * chase 269,102;
  * issue gap 22,700 (4,540 instructions at 5 cycles).

At 8k the as-built core takes 49.9 M cycles. The analytical figure hides the
narrow units: at spec widths the gap to the DAG closes to 1.10×, and what
remains is dependency latency, which the DAG prices only partly (its
compute_chain of 77 µs).

## 6. Gap table (requirement vs the RTL as built)

| block | requirement | as built | as-built cycles, 2k |
|---|---|---|---|
| stream unit | 512 elements/cycle | 1 element/cycle | 8,710,761 |
| attention P·V | K-split over positions across free groups | T × 8 cycles an op on 8 groups | 4,718,592 |
| attention Q·K | K-split over head_dim | 1,024 cycles an op on 128 groups | 147,456 |
| dependency | ≤ 44 exposed a stage | full-unit barrier (both units idle) | 13,463,058 |
| sequencer | ≤ 3,149 control cycles | 4,540 × 5 | 22,700 |
| matrix engine | 8,192 groups, split field to 2^13 | 2-bit split on 7,680 groups | 892,928 |
| KV SRAM | ≥ 57,533 B/cycle | 7,680 × 32 B per cycle (meets) | — |

## 7. Microarchitecture of each block that misses

In implementation order: the largest cycles saved first, each bit-exact with
the golden.

1. **Vector stream unit (SW lanes, VI mode).** Lanes take consecutive inner
   indices. Each lane is the scalar datapath: lane 0 is full, lanes 1.. carry
   exp/sigmoid, the multipliers, the adder and a reducer.
   * A segmented SUM reduces in lane-local 8-interleaved partials, then a
     pairwise tree over each lane's partials, then a pairwise tree over the
     lanes. That order is the golden's `reduce_sum` generalised to SW (SW = 1
     is today's order).
   * MAX is order-free.
   * Memory ports are SW elements wide (word access, any alignment through
     SW-way element banking).
   * K writes are transposed: one lane-masked word write per KV bank per
     cycle.
2. **Attention K-split.**
   * Q·K splits head_dim over the free groups (S = 2^s ≤ 128). P·V splits
     positions into S chunks of ⌈T/S⌉. The last chunks may be short or empty,
     and elements past T are masked to +0.
   * The existing split tree adds the chunk sums: ((c0 + c1) + (c2 + c3)).
   * This changes the golden's order to chunked sums plus a pairwise tree. The
     order is fixed by the program (S) and documented.
   * The split field widens to 4 bits (S ≤ 2^13 at shipped shapes; the reduced
     vehicle uses S ≤ G).
3. **Sequencer.** Prefetch and decode the next instruction while the current
   one waits, so issue runs back to back (5 → 1 cycle a gap).
4. **Dependency.** A per-unit barrier: an op waits for the producing unit only,
   and chases element progress across units wherever the write/read orders
   allow (already derived by `chase_threshold`). Full-unit drains remain only
   where a reduction result is read.
5. **One-pass softmax.** Latency and elementwise reductions:
   * The row max is taken by a compare tree on the matrix engine's result path
     as the scores emerge, next to the argmax tree.
   * The stream unit makes one exp-and-sum pass.
   * The 1/Z scale is applied to P·V's 32 × 128 outputs, so the reciprocal
     runs beside P·V (normalise-after-sum: a documented golden change).
6. **Remaining latency (target ≤ 44 a stage, spec chain 87).** The candidates,
   each costed before it is built:
   * the norm scalar applied after the matvec, so rsqrt overlaps the sweep;
   * shorter special-function pipes;
   * a registered 4:1 split tree.

## 8. DFlash (the drafter the user chose for both designs)

One step (block 16) needs 158.9 G MACs:

* draft: 5 layers × 16 slots, plus the target's lm_head × 15;
* verify: 36 layers × 16 slots;
* context projection;
* attention.

**ROM:** the reticle is MAC-bound. At the spec's 131,072 lanes a step's MAC
floor is 1,212,228 cycles. Against the spec's plain token (131,256), DFlash
breaks even only at **τ = 9.24**. At the measured τ 5.18 it gives 4,695 tok/s
against 8,370 plain: it loses.

The lever is lane copies (the multiplier m). At 1,071.8 µm² a lane, not one
extra copy fits in the 125.7 mm² of spare SRAM. The bare pipelined MAC is
509 µm², but that is a lower bound for a lane copy, not a qualified figure;
the qualified figure is `ot_hdc_matvec` routed at m = 2 against m = 1. So m is
a first-class area trade against the KV/SRAM budget, not an add-on.

The smaller-block alternatives were priced as well. Assumptions:

* Tokens a step for block B are E[min(L, B)], from the 561 measured block-16
  acceptance lengths (pooled τ 4.10). This assumes a smaller block keeps the
  first B − 1 drafts.
* Verify is KV-shared and slot-parallel: one plain token's dependency
  latency, and B tokens' MACs.
* The draft's latency is hidden under the verify ("overlapped"). Its MACs
  cannot be hidden, because they bind.

The best ROM configuration is **B = 2** (one draft): 1.70 tokens a step at
221,929 cycles, **8,410 tok/s against 8,370 plain (1.005×)**. B = 4 gives
7,227 and B = 16 gives 3,299. On the ROM reticle speculation is at best
break-even at the spec's lanes. It becomes a gain only if the plain token stays
latency-bound well above its MAC floor, or if lanes are added
(`dflash.rom.block_size_sweep`).

**HBM:** the bytes bind. With m = 16 a step reads the target's and drafter's
weights once for 16 slots, so the speedup at τ 5.18 is **4.55×** for every
format:

| format | plain | with DFlash |
|---|---|---|
| BF16 | 349.8 | 1,591 |
| FP8 | 686.1 | 3,122 |
| 3.5-bit | 1,494.6 | 6,800 |

Rates are tok/s. The minimum is 44,431 MAC lanes at BF16.

Requirements this adds to both designs:

* the lane multiplier;
* KV-shared verify attention (one K/V read serves 16 slots, with the causal
  mask per slot);
* slot-parallel non-weight work (one op over all slots on the stream unit's
  lanes, never 16 serial ops);
* 16 DYN banks and the CTL steps with the shared accept unit;
* a KV ring of at least 17 entries.

## 9. HBM comparator requirements

The weight stream never stalls. Weights are data-independent, so the stream
runs ahead across every dependency point:

* **Prefetch buffer.** It holds what the stacks deliver during the longest
  weight-free interval of the chain, 1,756 cycles: **8.63 MB** at 4,915
  B/cycle.
* **Sustained efficiency.** At least 0.90 of **raw peak**, measured with
  refresh on. That is how `technology.json`'s 0.90 was measured: GPU
  STREAM-class runs, with refresh.
  * Measured on the Qwen3 reduced vehicle, all-bank refresh (tRFC 350 ns every
    3.9 µs) reaches 0.904 at 1 pseudo-channel and 0.910 at 2. That is its
    ceiling of 91.0%.
  * A refresh-aware per-bank refresh (tRFCpb 200 ns) is required so that 0.90
    holds with margin. As currently modelled it reaches 0.914 at 1 channel and
    0.889 at 2, with a 512-beat queue. A model diagnostic is open, so this
    requirement is not yet met by a record.
* **Address map.** Refresh-aware: pseudo-channels interleaved at the stream's
  word size, refresh phases staggered.
* **Controller queue.** At least 512 beats per pseudo-channel (bandwidth ×
  tRFC ≈ 350 beats). On the V4.1 HBM vehicle, all-bank refresh with 64-beat
  queues cost up to 15% of a token: head-of-line blocking stalled the in-order
  stream for about tRFC.
* **Isolation.** A refreshing channel must not stall requests to the others.
* **Refresh policy.** Stated per design (REFab as modelled, or REFpb).
* **MAC rate.** Above the stream rate so the buffer drains: the lane minima
  above. DFlash raises the minimum to about 44 K lanes at BF16.

## 10. Physical rules for every block

These come from the full-chip effort at a 1.0 ns ASAP7 target:

* Every block boundary is registered, inputs and outputs.
  * A registered 512-bit output needs about 300 ps inside the block (router
    clock-to-pin about 270 ps).
  * Feed-through paths get their own budget.
* Clock-tree insertion on the matrix engine took about 540 ps.
* Repair needs a 40% slew margin and a 15 ps setup margin, for estimated
  against extracted wire delay.
* Routes must carry a real hold margin: the fix at 48fc68e6. Earlier routes
  had effectively none.

## 11. Implementation and evidence

Each block goes through the same five steps:

1. golden;
2. ISA and program, with the ISA model bit-exact;
3. RTL on the reduced vehicle (Verilator, `tools/rtl_hdc_decode_campaign.py`,
   bit-exact and oracle token);
4. a per-block performance testbench asserting the block's throughput and
   latency spec;
5. recalibration of `tools/hdc_timing.py` and a lower `RATCHET_2K` in
   `tests/test_arch_budget_qwen3.py`.

Place and route of the whole core follows the blocks.
