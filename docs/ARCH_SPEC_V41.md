# DeepSeek-V4.1-Flash architecture specification: requirement, budget, block specs

Status: specification and budget, 2026-09-26. This document works top-down. It sets the performance
requirement first, derives a per-block specification from it, and records the gap to the RTL as built. It
covers the ROM array (packaging option (b)) and the HBM comparator.

- Budget model: `tools/arch_budget_v41.py`, recorded in `results/arch/arch_budget_v41.json`, tested by
  `tests/test_arch_budget_v41.py`.
- Shipped-shape program replay: `tools/hdc_replay_v41.py`, recorded in `results/arch/v41_replay.json`,
  tested by `tests/test_hdc_replay_v41.py`.

**Headline target (user decision, 2026-09-26).** The target context is **200K**; 1M is the secondary point.
200K gives the larger ROM:HBM advantage on every metric (§8.3). At batch 1 the ROM array must reach at least
**4,450 tokens/s per user without MTP**, which is the report's option-(b) figure. With DSpark MTP at the
default τ = 4.1, the budgeted design delivers **10,837 tokens/s per user**. The HBM comparator at equal total
logic area delivers 1,143 without MTP and 1,687 with it. Every figure below comes from the budget model at its
current spec, not from silicon.

## 1. Requirement

The requirement is the report's own headline. The report prices the array with the dependency DAG in
`tools/decode_critical_path.py` (`packaging_options`, option (b)): 188 reticle dies in 94 two-die packages,
tensor group 4 spanning a package pair, 28 layer groups, and the realistic links (UCIe inside a package,
209 ns board SerDes between packages). The silicon must deliver what that DAG publishes, or the report must
change.

| context | batch 1, tokens/s/user | batch 1, µs/token | batch 64, tokens/s/user |
|---|---|---|---|
| 8,192 | 4,522 | 221.1 | 4,522 |
| 200,000 (headline) | 4,450 | 224.7 | 4,450 |
| 1,048,576 | 4,249 | 235.4 | 4,249 |

The model re-prices that DAG node by node from a block spec. At the DAG's own assumptions it reproduces all
three figures exactly (`test_dag_spec_reproduces_the_headline_exactly`). So the budget and the headline share
one dependency structure, and the question is only whether each node can be priced at the widths and depths
the DAG assumed.

Speculation is reported with and without MTP, on both machines:

- τ, the accepted tokens per verify cycle including the bonus token, defaults to **4.1** (user decision).
- The band around it is 3.27 and 3.80 (derived from vLLM survival) and ~5 (LMSYS/SGLang, published), from
  `results/roofline/speculative/hdc_design_faithful.json`.
- DSpark's configured block is γ = 5, so a verify pass carries **6 positions**.

## 2. Workload: one token, from the model graph

The ops come from `ops_of_layer` in the budget model, which follows the operator order of
`tools/hdc_golden_v41.py` and the shipped `operator_config`: dim 5,120, 4 hyper-connection copies, 64 heads of
512, 32 index heads of 128, 384 experts with top-6, window 128, index top-512, and candidate blocks of 8 with
top-2,048 at layer 20.

| per token (whole model) | 8K | 200K | 1M |
|---|---|---|---|
| weight MACs, FP8 | 6.16 G | 6.16 G | 6.16 G |
| weight MACs, FP4 (6 routed experts) | 8.49 G | 8.49 G | 8.49 G |
| weight MACs, BF16 / FP32 (wo_a, compressor, router, index proj) | 1.44 G | 1.44 G | 1.44 G |
| attention MACs (q·k + p·v over 128 window + 512 selected rows) | 1.61 G | 1.61 G | 1.61 G |
| **indexer MACs** (32 × 128 over every compressed key) | 0.22 G | **2.32 G** | **11.0 G** |
| weight ROM bytes read | 14.06 GB | 14.06 GB | 14.06 GB |
| KV bytes (window rows + gathered compressed rows) | 13.9 MB | 13.9 MB | 13.9 MB |
| **index-key bytes** (68 B per key) | 3.6 MB | **38.5 MB** | **182.7 MB** |
| Engram table bytes (48 rows × 264 B) | 12.7 KB | 12.7 KB | 12.7 KB |
| stream element-ops (linear / transcendental / divide) | 18.4 / 2.2 / 1.5 M | 34.8 / 2.2 / 1.5 M | 102.7 / 2.2 / 1.5 M |
| collectives per token (payload per user) | 209 (2.06 MB) | 209 | 209 |

Per layer at 200K:

| layer | kind | MACs | ROM bytes | index bytes | stream element-ops | collectives |
|---|---|---|---|---|---|---|
| 0 | sliding window | 386 M | 324 MB | 0 | 440 K | 5 |
| 1 | window + Engram | 543 M | 486 MB | 0 | 563 K | 5 |
| 2 | ratio-2 source, scans 100K keys | 840 M | 341 MB | 6.8 MB | 3.72 M | 6 |
| 3 | ratio-2 reuse | 419 M | 324 MB | 0 | 506 K | 5 |
| 20 | ratio-1 source, scans 200K keys, candidates | 1,247 M | 335 MB | 13.6 MB | 6.92 M | 7 |
| 24 | reindex, scans 16,384 | 492 M | 330 MB | 1.1 MB | 1.04 M | 6 |

Three properties set the architecture.

1. **Context enters only through the indexer.** The lightning indexer scans every compressed key: 200K
   keys at layer 20, which has ratio 1, and 100K at layers 2, 8 and 14. Its cost is linear in context per
   token, so it grows quadratically over a sequence. At 1M the indexer's MACs exceed the routed experts'.
2. **The stream work is fixed, wide and replicated.** Every sublayer collapses, re-expands and normalises a
   4 × 5,120 residual, and every die of a tensor group repeats that work.
3. **The golden's summation orders are sequential at shipped shapes.**

| accumulation | terms in one sequential chain |
|---|---|
| hyper-connection mix, `HC_SPLIT` = 8 | 2,560 |
| wo_a, `WO_A_SPLIT` = 2 | 2,048 |
| p·v, over positions | 640 |
| q·k, over head_dim | 512 |
| the hyper-connection norm's sum of squares | 640 |
| linear_q blocks, sequential | 160 |

A dependent FP32 chain of n terms cannot finish in fewer than n × (add latency) cycles, however wide the
engine is (§4).

## 3. Three-layer reconciliation: report DAG, calibrated sequencer, RTL as built

`tools/hdc_replay_v41.py` builds shipped-shape programs for one die's share of a token in option (b), using
a shape-generic emitter. At the reduced shape the emitter reproduces the real `hdc_program_v41.Builder`
program instruction for instruction: 3,992 instructions, every field. `hdc_timing_v41.simulate` prices both
exactly the same at 4, 8, 16 and 64 stream lanes; at 8 lanes that is 344,131 cycles at pos 7. The shipped
replay then prices every layer kind with the RTL-calibrated sequencer and unit model.

Layers B and C below include the DAG's communication, 55.6 µs per token.

| context | A: report DAG | B: calibrated at the DAG's widths | B with lane-parallel reductions | C: as built |
|---|---|---|---|---|
| 8K | 4,522 tok/s (221 µs) | 1,118 (894 µs) | 2,824 | 39.7 (25.2 ms) |
| 200K | 4,450 (225 µs) | 1,099 (910 µs) | 2,703 | 29.6 (33.8 ms) |
| 1M | 4,249 (235 µs) | 1,025 (975 µs) | 2,298 | 14.5 (69.2 ms) |

- **A** is the report's DAG.
- **B** gives the as-built sequencer the DAG's widths: a 512-lane stream unit, and 276K MACs/cycle for every
  matvec and every KV-sourced op.
- **C** is the RTL as it is: an 8-lane stream unit, the ME at 64 MACs/cycle (it also runs attention and the
  indexer through head groups), the QE at 512 MACs/cycle, the HE at 3 × 8 lanes, a 1-element/cycle insertion
  select, and the routed Sinkhorn.

**The gap from C to A, attributed at 200K.** The per-token effect of each factor, one at a time:

| factor | C with this factor at the DAG's value | B with this factor as built |
|---|---|---|
| attention and indexer on the ME head-group path | −14,821 µs | +14,821 µs |
| weight matvec width (ME, QE, HE) | −13,931 µs | +14,206 µs |
| stream unit, 8 vs 512 lanes | −3,518 µs | +3,922 µs |
| select, 1 element/cycle vs a 64-lane tselect | −174 µs | +175 µs |
| Engram inline vs prefetched | −129 µs | 0 |

Two further factors are measured as what removing them saves inside one configuration:

| factor | removed from C | removed from B |
|---|---|---|
| ordered reductions (one lane per golden segment) | −210 µs | −540 µs |
| unit drains, replaced by a region scoreboard | −1,204 µs | −0.4 µs |

**Why B is still 4× slower than A.**

- **Reductions that keep the golden's segment order run one lane per segment.** That is 4 lanes for the
  hyper-connection norm and 8 for RMSNorm. So `hc_post` with its sum of squares takes 5,120 cycles even at
  512 lanes. Lifting this restriction is worth 540 µs.
- **The dependent-stage structure itself.** What remains is 707K cycles of stream-unit drains per token, 72K
  cycles of QE serialisation, and 34K cycles of stream class changes.
- **Neither a scoreboard nor a faster issue helps.** A scoreboard saves 0.4 µs and a 1-cycle issue gap
  saves 2.7 µs. The dependences are real. Only vector-granular chaining of producer into consumer, which the
  DAG assumes, closes this gap.

The DAG under-counts the sequential accumulation chains and assumes chaining. The RTL has neither the widths
nor the chaining.

## 4. The budget: fixed part, issue budget, and the arithmetic contract

The DAG is re-priced with every issue time set to zero. What remains is the fixed part of a token: unit
pipeline depths, sequencer control, link latencies, and sequential-chain floors. The rest of the target is
the **issue budget** that the block widths must fit into.

| 200K, µs | report DAG | required orders (chunks ≤ 8, fast FP) | golden orders | as built |
|---|---|---|---|---|
| compute-chain depths | 101.6 | 99.0 | 216.3 | 481.0 |
| sequential-chain floors (on the weight path) | 0 | 10.9 | 587.9 | 979.8 |
| KV gather and scan latency | 2.1 | 2.2 | 5.2 | 8.2 |
| collective latency + bytes | 43.6 | 43.6 | 24.2 | 24.2 |
| pipeline hops | 11.9 | 11.9 | 11.9 | 11.9 |
| control | 7.2 | 7.2 | 5.5 | 8.2 |
| **fixed part** | **166.5** | **175.0** | **851.0** | **1,513.4** |
| target | 224.7 | 224.7 | 224.7 | 224.7 |
| **issue budget** | 58.2 | **49.7** | **< 0: infeasible** | < 0 |

At 8K the issue budget is 47.2 µs; at 1M it is 52.4 µs.

**Finding 1: the latency floor is the requirement.** Of the 224.7 µs target:

- 175 µs is fixed.
- 44 µs of that is collectives: about 5 per layer, each ~220 ns across the package pair.
- About 99 µs is unit depth.

The widths therefore have only 50 µs, **22% of the token**, to spend.

**Finding 2: the golden's summation orders make the target unreachable at any width.** A 2,560-term
sequential FP32 chain costs 12,800 cycles at a 5-cycle add. Under the current orders the fixed part alone is
851 µs, which caps the design near 1,170 tokens/s per user (`ablations: golden_orders`).

**Requirement R-ARITH (the arithmetic contract at shipped shapes):**

- Every accumulation is cut into contiguous chunks of at most 8 terms, summed sequentially from +0, with the
  chunk sums added by a pairwise tree padded with +0. This is the golden's own `split_sum`, applied with the
  chunk length fixed instead of the chunk count.
- A tree level that crosses dies is the one-shot collective's fixed rank order.
- Where both operands are FP8/FP4 with 32-element block scales (the linear_q weights and the index dots), the
  chunk is the quantisation block: its dot is formed exactly and rounded once, as linear_q already does, and
  the block values combine by the same chunked tree. This is what makes a block-dot lane cost ~78 µm² per
  MAC instead of a full FP32 adder.
- A tree level that crosses dies is the one-shot collective's fixed rank order.
- The golden, the ISA and the RTL change together.
- Bit-exactness stays defined against the golden. The golden stays token-equal to the oracle, which must be
  re-checked on the reduced vehicle (§10).

**Status of R-ARITH.**

- **Golden:** `tools/hdc_golden_v41.py` carries it as a mode, `HDC_V41_ARITH=chunk8` (`csum`, `dots_q4`).
  `legacy` stays the default so the as-built core's records hold. The mode can also be a list of operator
  classes (`me, qe, he, att, idx, su`), so the re-specified units can be brought up one at a time against a
  golden that switches only their classes.
- **ISA:** the ISA-level simulator of the V4.1 program implements the same classes. Under `chunk8` it is bit-exact
  with the golden in every logit at position 7 and over the prompt plus 4 generated tokens from an empty
  state.
- **Numerics** (`tools/check_v41_arith_contract.py`, `results/arch/v41_arith_contract.json`; teacher-forced
  over the oracle's 24-token sequence):
  - Up to position 7 the two orders differ by at most **2.4 × 10⁻⁷** in any logit.
  - At position 8 a routed-expert selection flips at a near-tie of the reduced vehicle's 12-expert router,
    and every later difference (up to 0.34) follows such flips.
  - Against the oracle (the vendor model in BF16 on a GPU), neither order is closer: legacy matches 3 of 16
    teacher-forced steps, chunk8 matches 2, with mean oracle-token gaps of 0.345 and 0.341.
  - This is the reduced fixture's conditioning, not a precision loss: its top-1 margins are 0.001-0.25 while
    either golden sits ~0.34 from the oracle per step. Both orders reproduce the oracle's token 3118 at step
    0 with the same margin.

The other depth requirements:

| item | required | as built |
|---|---|---|
| FP32 add latency (`ot_hdc_fastfp`, routed 1,312 MHz, closed) | 3 cycles | 5 |
| exp depth | 49 cycles | 92: `ot_hdc_v41_stream` pads exp back to 92 |
| sigmoid path depth | 80 cycles | 128 |
| rsqrt depth | 37 cycles | 61 |
| producer → consumer | vector-granular chaining across ME/QE/SU/XU, with a credit per vector | drain barriers (wait masks) |

**How the widths are derived.** The issue budget is split across the critical-path resources by the
area-optimal rule for serial stages: t_r ∝ √(area_r × work_r), which minimises Σ area_r × work_r / t_r at a
fixed Σ t_r. The widths are then rounded to hardware granularity and re-verified on the DAG. A greedy repair
doubles the best width per area until the target holds; a shrink pass halves widths while it still holds.
This is done at 8K, 200K, 1M and at batch 64, 200K, and the spec takes the maximum of each width over the
four cases.

## 5. Per-block requirements and the gap table (per die)

| block | unit | required | as built | factor | as-built basis |
|---|---|---|---|---|---|
| weight engine (FP8/FP4 block-dot) | MACs/cycle | 231,936 | 512 | 453× | QE: 16 block-dot lanes × 32 |
| BF16/FP32 weight engine | MACs/cycle | 31,360 | 64 | 490× | ME: 4 groups × 16 lanes |
| weight ROM read | bytes/cycle | 301,904 | 528 | 572× | QE word 16 × 33 B |
| attention engine (q·k, p·v) | MACs/cycle | 34,176 | 64 | 534× | ME head groups |
| KV row staging buffer | bytes/cycle | 2,203 | 128 | 17× | KV SRAM |
| indexer engine (FP4 × FP4) | MACs/cycle | 228,864 | 64 | 3,576× | ME head groups |
| index-key stream (from HBM) | bytes/cycle | 3,800 | 128 | 30× | KV SRAM |
| stream unit, linear lanes | elements/cycle | 1,024 | 8 | 128× | 8 lanes |
| stream unit, SFU lanes (exp/sigmoid/silu/divide) | elements/cycle | 256 | 8 | 32× | rsqrt, sqrt, softplus and gate on lane 0 only |
| index top-512 select | scores/cycle | 64 (streaming filter) | 1 (insertion) | 64× | XU `ot_hdc_select` |
| hyper-connection projection | FP32 MACs/cycle | 2,048 | 24 | 85× | HE 3 lanes × 8 chunks |
| longest accumulation chain | terms | 17 (8 + log2 tree) | 2,560 | — | golden orders |
| FP32 add latency | cycles | 3 | 5 | — | `ot_fp32_add_rne_pipe` |
| exp / sigmoid depth | cycles | 49 / 80 | 92 / 128 | — | padded in the V4.1 stream unit |
| producer → consumer | — | vector chaining | unit drains | — | wait masks |
| Engram gather ingest | bytes/cycle | 13.7 (256-bit port) | 12,672 (flat) | 0.001× | 48 × 2,112-bit ports, 16,559 IO pins |

**Weight ROM read.** At 301,904 B/cycle the required read is 36% of the ROM macro array's sweep rate:
2.96 TB/s/mm² over 289 mm² of ROM is 828 KB/cycle (`docs/MEMORY_COMPILERS_AND_BIST.md`). ROM bandwidth is
not the constraint. MAC lanes and latency are.

**Area.** At ASAP7 unit areas the required blocks total **85 mm² per die**, against the analytical design's
329 mm² N5 compute envelope. The breakdown:

| block | mm² |
|---|---|
| weight engine | 18.2 |
| BF16 engine | 16.0 |
| attention | 17.4 |
| indexer | 18.0 |
| light stream lanes | 4.2 |
| SFU lanes | 8.8 |
| hyper-connection projection | 2.4 |
| select | 0.1 |

The source of each unit area:

- **Measured (routed or synthesised):** the blockdot at 78.5 µm² per FP8/FP4 MAC, the pipelined BF16 MAC at
  509 µm², the V4.1 stream lane at 34,451 µm², and `tselect_w16` at 1,130 µm² per lane.
- **Estimated (no routed block exists):** a light stream lane at 4,085 µm², taken as 1.5 × (2 FP32 mul + 3
  FP32 add).

The DAG assumed 276K BF16-class MACs per die for weights, attention and indexer alike, which is about 290 mm².
The top-down spec needs far fewer lanes. It spends them per class, and it pays for the latency floor instead.

What each requirement is worth, with that one requirement undone, at 200K and batch 1:

| undone | tokens/s/user |
|---|---|
| none (the spec) | 4,892 |
| golden summation orders | 1,165 |
| stream unit as built (8 lanes) | 1,442 |
| weight engines as built | 81 |
| attention on 64 lanes | 159 |
| indexer on 64 lanes | 112 (24 at 1M) |
| no chaining (drain barriers) | 4,646 |
| 5-cycle FP32 add | 4,812 |
| as-built SFU depths | 4,786 |
| two-pass select instead of the streaming filter | 4,799 (4,139 at 1M) |

## 6. Microarchitecture that meets the spec

Each block below is specified with its budget and its bench criterion. §10 gives the implementation order.
Every block boundary is registered. Physical inputs from the full-chip effort:

- Clock insertion is about 540 ps at 1.0 ns.
- A registered 512-bit output needs about 300 ps inside the block.
- Repair needs a 40% slew margin plus a 15 ps setup margin.
- The token-path clock stays at 1.034 GHz, set by softplus and the BF16 MAC, which close at 1.03-1.05 GHz.

1. **Arithmetic contract (R-ARITH).** Parameterise the golden's splits by a fixed chunk length c = 8
   (`split_sum` over n/8 segments with a padded pairwise tree) for:
   - every `linear_q` block accumulation, `dots` (q·k and p·v), `reduce_rows`, `HC_SPLIT`, `HC_SS_SPLIT`,
     `RMS_SPLIT` and `WO_A_SPLIT`;
   - the tensor-group K-splits, whose top level is the collective's rank order.

   The ISA carries the chunk length. The engines' K-split already implements a chunked sum (`me_split`);
   what changes is that the chunk length, not the lane count, sets the split.
   *Bench:* golden = ISA = RTL bit-exact on the reduced vehicle with c = 8, and the reduced token still equals
   the oracle's.

2. **Stream unit: one parameterised vector unit, shared with the Qwen core.** N light lanes (mul, add, max,
   BF16 rounding, reducer partials) plus M SFU lanes (exp, sigmoid/silu, divide), with rsqrt, sqrt, softplus
   and the Engram gate on a small scalar side-pipe.
   - **Reducer:** lane-parallel partials, one per lane, combined by the tree R-ARITH defines. This removes the
     "one lane per golden segment" restriction that cost B 540 µs.
   - **Chaining:** vector-granular chaining to and from the ME/QE output buffers.
   - **Depths:** the fast-FP set with no padding.
   - **Spec:** N = 1,024 and M = 256 elements/cycle at 1.034 GHz; linear-op latency ≤ 21 cycles, exp ≤ 49,
     sigmoid ≤ 80.
   - *Bench:* throughput N elements/cycle sustained on a 20,480-element hc_post; depth per class as above;
     bit-exact against the golden.
   - The Qwen agent (abf1bc09) gets the same parameterised unit; the Qwen core needs N and M of its own.

3. **Weight engines.** A pooled block-dot array: FP8 × FP8 and FP4 × FP8 with FP32 accumulation per 32-block
   and chunked accumulation per R-ARITH, fed from the ROM macros through a banked read network.
   - **Spec:** 231,936 MACs/cycle and 302 KB/cycle of ROM read. Every matrix is striped across enough macros
     to reach the read rate.
   - **BF16/FP32 engine:** 31,360 MACs/cycle, for wo_a, the compressor, the router and the index projection.
   - **MTP lane multiplier:** m MAC lanes per weight lane; m = 2 at the design point (§7).
   - *Bench:* a matvec of n rows × k in ⌈n·k / lanes⌉ + depth cycles, with depth ≤ 60 + 3·⌈log2(k/8)⌉.

4. **Attention engine.** A dynamic-operand engine, separate from the weight engines, because ROM-stationary
   lanes cannot take KV operands. The KV is single-head MQA with 512-dim rows shared by all heads, so one row
   read feeds 16 heads × 512 MACs on a die.
   - **Spec:** 34,176 BF16 × FP8 MACs/cycle and a 2.2 KB/cycle row staging buffer: one 528-B row per cycle
     feeds 8,192 MACs. The buffer holds 640 rows, 338 KB per die per layer.
   - The 64-position blocks of the release's online softmax fit in the buffer.

5. **Indexer engine and key stream (KV in HBM, user decision).** Index keys stay in their model precision:
   FP4 E2M1 codes plus one UE8M0 scale per 32, **68 B per key**. The golden quantises every key to FP4 before
   use, so this is lossless and 3.8× smaller than BF16.
   - **Spec:** 228,864 FP4 × FP4 MACs/cycle, which is about 56 keys/cycle, streaming keys from the die's HBM
     at up to 3.8 KB/cycle.
   - The fused ReLU·weight head-sum runs on the stream unit's light lanes, at 32 heads per key.
   - At 1M, layer 20's scan is 17.8 MB per die, about 4.4 µs at the 4.5 TB/s the die's five HBM3E stacks
     sustain. That scan is the HBM term that grows with context (§9).

6. **Select.** A **streaming exact filter** plus a threshold select over the survivors.
   - While scores arrive, keep a running lower bound on the k-th largest score and discard every score below
     it. The filter is exact because nothing it discards can enter the top-k.
   - About k·(1 + ln(n/k)) scores survive: 2,858 of 50,000 at 200K, 3,707 of 262,144 at 1M. The tselect's
     two passes then run over the survivors.
   - **Spec:** 64 scores/cycle ingest, matching the indexer. As one unit that is 4 × 16 quartered, because
     the 64-lane tselect fails global routing and `tselect_w16` routes at 1.05-1.09 GHz. Tail ≤ 181 cycles
     after the last score at 1M, against 8,257 for the two-pass tselect. Position-order output. On survivor
     overflow, fall back to a full second pass.
   - **Candidate top-2,048** (layer 20): the mask is consumed ≥ 4 layers later, so its latency budget is
     ~4 layer times. Its width follows the ingest: 64 score lanes and 8 block-max lanes. That replaces the
     64 × 64 array that hit the 6 h P&R ceiling at 283K cells.

7. **Hyper-connection projection.** 24 outputs × 20,480 FP32 terms, with chunks of 8 per R-ARITH, on
   **2,048 FP32 MAC lanes**. It runs as the sublayer's side branch and must finish within the sublayer body,
   and it must keep doing so under MTP's 6 positions, which needs 2,048 lanes. The Sinkhorn unit's 297 core
   cycles already fit the body: no change.

8. **Engram gather.** The bandwidth is **13.7 B/cycle**: 48 rows × 264 B within a quarter of the ≥ 3.57 µs
   slack at batch 1, because the hash reads only token ids and the gather issues at embed time.
   - **Spec:** a per-bank slice at each column bank, one 264-B row per bank per token, and a 256-bit beat
     stream to the consuming die: 12,672 B in about 400 cycles.
   - This replaces the as-built 48 × 2,112-bit flat port, whose 16,559 IO pins forced a 460 µm die routed at
     841 MHz.

9. **Collectives.** The one-shot fixed-rank-order engine, as measured by agent a6df6a56. Each die broadcasts
   its partial once and folds all N in rank order, so latency after the last partial is 2 + (N − 1) × the
   add latency.
   - Six collectives per layer cost ~220 ns each, set by the 209-ns package link. That is **44 µs per token,
     the largest single fixed term**.
   - **Spec:** a receive FIFO of 32 words per source, which removes link hold, and 1 GHz.

10. **Sequencer.** ≤ 5 cycles per issue, and a vector-credit chaining protocol between units in place of
    wait-mask drains. The replay counts ~3,840 instructions per token per die, so issue is 1.9% of the token.

11. **KV state and HBM controller on the ROM die (user decision).**
    - **Stacks:** five HBM3E stacks per die, beachfront-limited: 60% of the perimeter at 12 mm per stack.
    - **Bandwidth:** 4.5 TB/s sustained at 90%, measured with refresh on.
    - **Controller:** refresh-aware per-bank refresh (REFpb, tRFCpb 200 ns): refresh the not-yet-refreshed
      bank that the fewest queued bursts need, never the head burst's bank. At least 64 beats of queue per
      pseudo-channel (256 if a design falls back to all-bank refresh), and no head-of-line blocking across
      channels. Agent a8c77c67 measured this in RTL on the reduced vehicle: 0.965-0.993 of the refresh-free
      rate, against 0.85-0.95 for all-bank refresh behind 64-beat queues.
    - **Prefetch:** window rows and reuse-layer selections have static addresses, so they are prefetched one
      layer ahead.
    - **Gathers:** an index-source layer's gather is exposed, and its first row is budgeted at 250 ns.
    - **Capacity:** per-user state at 1M is 93.5 MB on the busiest die, so the stacks hold **1,203 users at
      1M and 6,272 at 200K**. Batch is not capacity-limited below that, and the old 8,192-context admission
      limit from on-die KV does not apply.

12. **Power (requirement).** Per-die power must stay at or below the die's cooling limit, 0.5 W/mm² × 815 mm²
    = **407.5 W** (`technology.json` thermal), at every batch, with stage clock gating: an idle stage's clock
    tree gated at its block boundaries, and its ROM macros and engines quiescent. From
    `results/arch/arch_budget_v41.json` `power`, at 200K:

    | per die | m = 1 | m = 2 (MTP) |
    |---|---|---|
    | block area (ASAP7) | 85 mm² | 170 mm² |
    | active clock of the blocks | 7.5 W | 14.9 W |
    | dynamic while its stage holds the token, batch 1 | 23.2 W | 30.7 W |
    | dynamic at the saturated batch (every die busy) | 27.4 W | 42.3 W |

    With static leakage (33.5 W, the analytical N5 estimate) and the HBM interfaces (14 W), the worst case is
    **~90 W per die, 4.5× under the limit**. Without gating, the analytical design charges a 48 W/die clock
    term on all 525 mm² of logic, which is the upper bound if nothing gates. Stage gating is also what keeps
    batch-1 energy at 19 mJ per token instead of 300 mJ (§8).

## 7. MTP (DSpark): per-operator speculation analysis

The verify pass carries B = 6 positions. The same `price()` as the plain token applies, with MACs and stream
elements × B, dense weights read once per pass, routed experts at the union U(B) = 384·(1 − (1 − 6/384)^B),
which is 34.6 at B = 6, KV rows and index keys read once per user, and fixed latencies once per pass.

Cost ratio verify / plain per operator class, at 200K. "Busy" is the class's total unit time per token on
one die; "path" is its share of the critical path.

| operator class | ROM, AR-sized lanes (m = 1) | ROM, m = 6 core | HBM, m = 1 | HBM, m = 6 | binding resource |
|---|---|---|---|---|---|
| dense GEMVs (projections, shared expert, head) | 5.1× (MAC-bound) | **1.0×** (weight read shared) | **1.0×** (bytes shared) | 1.0× | ROM: MAC lanes; HBM: bytes |
| routed experts | 6.0× | **5.35×** | **5.3×** | 5.3× | ROM: weight lanes (the union); HBM: bytes (the union) |
| hyper-connection projection | 6.0× (then on the path) | 4.7× (off the path) | 3.2× | 1.0× | FP32 lanes |
| attention (q·k, p·v, softmax) | 5.6× | 2.2× | 5.6× | 2.2× | MAC lanes; KV rows shared |
| indexer (scan + select) | 6.0× | 1.7× | 6.0× | 1.7× | MAC lanes; keys read once per pass |
| stream unit | 3.2× | 1.5× | 3.2× | 1.5× | lanes |
| fixed (depths, control, collectives, hops) | 1.33× | 1.2× | 1.21× | 1.18× | latency, once per pass |
| **whole verify pass** | **2.33×** (476.5 µs) | **1.45×** (283.5 µs) | **2.53×** (2,212 µs) | **2.43×** (2,108 µs) | |

**Does "speculation trades MACs for bandwidth" hold for sparse V4.1?** Only for the dense part.

- **Dense GEMVs.** The claim holds. HBM reads the dense weights once per pass, and the ROM die does the same
  once it has an m-way lane multiplier.
- **Routed experts.** The claim fails on both machines. Six positions touch 34.6 distinct experts, not 6, so
  HBM streams 5.3× the expert bytes. The ROM die holds each expert striped over its four-die group, with a
  pooled weight engine, so it streams the same union through its weight lanes at 5.35× the lane time. An
  m-way multiplier cannot help, because only positions that share an expert share a weight read.
- **"Idle expert dies" do not exist in this placement.** Striping puts every die on every expert. The
  alternative, expert-parallel placement, leaves dies idle at batch 1 only because it is *worse* balanced
  there. What the ROM die does have idle is macro read bandwidth: 828 KB/cycle available against 302 KB/cycle
  used, so 2.7× headroom. Harvesting it takes more weight lanes (area), not more positions.
- **Correlated routing.** If adjacent tokens share experts, the union shrinks. At an overlap of 25% (50%) of
  the union's excess, the ROM m = 6 verify drops 283 → 273 (263) µs and the HBM verify 2,107 → 1,808
  (1,510) µs. No measurement of adjacent-token routing on real prompts with the shipped router exists here;
  the reduced vehicle has 12 experts, which is not representative. Independent draws are the conservative
  case.
- **Sparse attention.** The KV rows of adjacent positions overlap: the window fully, the selected rows mostly.
  Bytes are shared and MACs grow B×.
- **Indexer.** Keys are read once per pass while MACs grow B×. At 8K and 200K the scan is MAC-bound on both
  machines at the spec's lanes. At 1M layer 20 streams 17.8 MB per die, and with m = 6 lanes it becomes
  HBM-bound on both machines.

**Correction to the existing remodel.** `tools/hdc_speculative_model.py` (`Pass`) charges every matvec,
routed experts included, ⌈positions/m⌉ sweeps of its share. It uses the expert union only for energy. At
m ≥ B it therefore charges routed experts one sweep. That assumes the m MAC lanes of a weight lane can serve
positions that use *different* experts, which they cannot. The routed term should be (U/k) × max(1, share/m)
sweeps, as `price()` does here. At m = 1 the two agree: the remodel charges 6 sweeps, this model 6.0×.

**The MTP design point** at 200K, B = 6, τ = 4.1. An m-way core makes every engine m times wider; the ROM read
width does not change.

| m | block area, mm² | verify, µs | draft, µs | tok/s at τ = 4.1 (band 3.27 – 3.8 – 5.0) |
|---|---|---|---|---|
| 1 | 85 | 476.5 | 27.6 | 8,134 |
| **2 (design)** | **170** | **356.2** | **22.2** | **10,837** (8,633 – 10,044 – 13,216) |
| 3 | 255 | 319.7 | 20.1 | 12,066 |
| 4 | 340 (exceeds 329) | 309.3 | 19.6 | 12,464 |
| 6 | 510 | 283.5 | 18.1 | 13,596 |

m = 2 is the knee: m = 3 buys 11% for 50% more area. The draft chain is 3 DSpark stages over a 5-row block
plus 5 dependent argmax steps over the 129,280-row vocabulary (lm_head row, rank-256 Markov bias, argmax,
219-ns collective). At m = 2 it is **22.2 µs, 6% of the cycle**.

With and without MTP, both machines, at τ = 4.1:

| | 200K, no MTP | 200K, with MTP | 1M, no MTP | 1M, with MTP |
|---|---|---|---|---|
| ROM array (option b; m = 2) | 4,892 | **10,837** | 4,510 | 9,535 |
| HBM comparator (iso logic area; m = 6) | 1,143 | 1,687 | 1,121 | 1,675 |
| ROM : HBM | 4.28× | **6.4×** | 4.02× | 5.7× |

## 8. Batch: rate per user, throughput and energy (one model with §7)

Batching uses the same `price()` as speculation. Users × positions share weight reads, routed experts cost
their union across users and positions, and KV and index keys are per user.

- **Batch policy (pipeline fill):** with 28 layer-group stages, b < 28 users ride one per stage, and b ≥ 28
  share each stage in microbatches of b/28.
- **Energy:** `configs/hardware/technology.json` per-format op energies, ROM read plus operand delivery or
  HBM at 104.9 pJ/B, the clock at 8.5 × 10⁻¹¹ J/mm²/cycle on the spec's block area, and assumed link energy.
  "Gated" clocks only the stage holding the token, which makes stage clock gating a power requirement.

### 8.1 200K (headline)

| batch | ROM tok/s/user | ROM array tok/s | ROM mJ/token (gated) | ROM + MTP tok/s/user | HBM tok/s/user | HBM array tok/s | HBM mJ/token (gated) | HBM + MTP tok/s/user |
|---|---|---|---|---|---|---|---|---|
| 1 | 4,892 | 4,892 | 19.0 | 10,837 | 1,143 | 1,143 | 1,509 | 1,658 |
| 8 | 4,892 | 39,135 | 13.6 | 10,837 | 1,143 | 9,146 | 1,486 | 1,658 |
| 28 | 4,892 | 136,972 | 13.1 | 10,837 | 1,143 | 32,012 | 1,484 | 1,658 |
| 64 | 3,538 | 226,427 | 11.2 | 6,377 | 864 | 55,279 | 858 | 945 |
| 128 | 2,473 | 316,562 | 10.7 | 3,747 | 516 | 65,990 | 730 | 583 |
| 256 | 1,477 | 378,057 | 10.2 | 1,951 | 333 | 85,151 | 556 | 355 |
| 1,024 | 377 | 386,338 | 9.8 | 515 | 105 | 107,653 | 402 | 180 |

The HBM MTP column uses m = 2 here, the batch model's single design point; §7 gives HBM at m = 6.

### 8.2 1M

| batch | ROM tok/s/user | ROM array tok/s | ROM mJ/token (gated) | HBM tok/s/user | HBM array tok/s | HBM mJ/token (gated) |
|---|---|---|---|---|---|---|
| 1 | 4,510 | 4,510 | 35.3 | 1,121 | 1,121 | 1,525 |
| 64 | 3,105 | 198,725 | 26.9 | 835 | 53,460 | 874 |
| 1,024 | 304 | 310,870 | 25.5 | 98 | 100,832 | 418 |

Batch-1 energy per token without gating: ROM 300 mJ (clock 287 mJ), HBM 2,143 mJ (weights 1,474 mJ). Every
die clocks every cycle while only one layer group works, so **idle-stage clock gating is a requirement**.
Gated, the ROM token at batch 1 is 19 mJ, **79.5× below HBM**.

The pipeline keeps the batch-1 per-user rate up to 28 users. The array then saturates at 386K tokens/s at
200K; the HBM comparator reaches 108K at 1,024 users. Per-user MTP gains shrink with batch, because the
verify pass's extra positions compete for the lanes that other users' tokens use.

### 8.3 Target context: 200K

| ROM : HBM | 200K | 1M |
|---|---|---|
| per-user rate, with MTP (τ = 4.1) | **6.54×** | 5.87× |
| per-user rate, without MTP | **4.28×** | 4.02× |
| energy per token, batch 1, gated | **79.5×** | 43.3× |
| array throughput, batch 64 | **4.10×** | 3.72× |
| array throughput, saturated | **3.59×** | 3.08× |

200K wins on every metric. The reason is that the context-dependent cost is the indexer's key scan plus its
KV. Both machines hold it in HBM, stream it at the same per-die bandwidth, and pay for it equally. The ROM
advantage is in the weight path, which does not grow with context, so a longer context dilutes it. 200K is
the headline and 1M is the secondary point.

## 9. HBM comparator specification (equal total logic area)

**Configuration.** The ROM array spends 188 dies × 328.9 mm² = 61,836 mm² on compute. The comparator spends
the same on logic-only dies: the same 815 mm² die with the ROM area freed, keeping interconnect and overhead,
with 5 HBM3E stacks per die (beachfront-limited) and 618.3 mm² of logic.

- **101 dies** in about 25 tensor groups of 4.
- 11.4 TB of HBM, against 510 GB of weights.
- **4.5 TB/s sustained per die**: a 90% efficiency requirement, measured with refresh on.

At 200K the comparator gives 1,143 tokens/s per user. Its weight sweep is 679 µs of the 875 µs token.

| sustained efficiency | 75% | 85% | 90% | 95% |
|---|---|---|---|---|
| tokens/s/user | 990 | 1,093 | 1,143 | 1,192 |

Requirements:

- **Prefetch window.** 4.5 MB per die, which is latency × bandwidth at 1 µs first access. Every static-address
  stream (dense weights, window rows) is issued that far ahead across every dependency point.
- **Routed-expert fetch.** The hard part. The expert ids exist only after the router's top-6, so a layer's
  28.2 MB per die of expert bytes is exposed: first access plus bytes, **7.3 µs per layer on the critical
  path**. With MTP the fetch is the union (34.6 experts at B = 6), which caps HBM's speculative gain at 1.5×
  (γ = 5, τ = 4.1).
- **Controller.** Refresh-aware REFpb with at least 64-beat queues per pseudo-channel (256 under all-bank
  refresh), and request issue that never lets a refreshing channel stall words that do not touch it (agent
  a8c77c67).
- **KV and index keys.** Same format and prefetch as the ROM die. They compete with weights for the same
  stacks.

## 10. Implementation order and status

The priority is set by what each item is worth on the budget (§5):

1. **R-ARITH and the vector unit.** Golden/ISA splits at c = 8; the parameterised stream unit (N light lanes,
   M SFU lanes, lane-parallel reducer, fast-FP depths, no padding); the vector-credit chaining protocol.
   Shared with the Qwen core. Before touching `ot_hdc_core_v41` / `ot_hdc_v41_stream`, coordinate with the
   MTP agent (adbe13f5).
2. **Attention engine and indexer engine**, which are the dynamic-operand arrays, plus the HBM key stream.
3. **Weight engine width.** A parameter sweep of the block-dot and ME arrays, with the chunked accumulate.
4. **Streaming-filter select**, the 4 × 16 quartered tselect behind it, and the candidate select at the
   ingest width.
5. **Hyper-connection projection** at 2,048 lanes, and the **Engram per-bank gather** at a 256-bit port.
6. **MTP m = 2 lane multiplier** across the engines.

Each block ships with a performance testbench that asserts its spec row (throughput, depth, bit-exactness).
Each is re-checked with the bit-exact V4.1 token campaign (`tools/rtl_hdc_v41_decode_campaign.py`) and routed
on ASAP7 at 0.97 ns with registered boundaries.

**Status at this commit.** The spec, the budget model and the replay are committed. No RTL block of this spec
has been implemented yet.

## 11. Assumptions and limits

- **One dependency structure.** The budget re-prices the report's DAG. The replay (§3) shows that the as-built
  sequencer adds drains and ordered reductions that this DAG does not have; the spec requires them removed.
  The spec is verified on the DAG, not on a replay of a respecified ISA. Doing that is the first
  implementation milestone.
- **Areas.** Unit areas are ASAP7, compared against the analytical design's N5 compute envelope, which is
  conservative. The light stream lane's area is an estimate; no routed block exists.
- **Routing.** Uniform routing: the router trace is synthetic. Correlated routing is a sensitivity (§7), not
  a measurement.
- **Draft cost.** Priced as three sliding-window layer spans at a 5-row block, plus 5 Markov steps. The
  drafter's own KV and experts use the main layers' unit models.
- **Energy.** Link energy (0.5 pJ/bit UCIe, 5 pJ/bit board SerDes) is assumed. The clock term is
  `technology.json`'s, charged on the spec's block area.
- **Batch policy.** Beyond 28 users, "pipeline fill" is a policy the array controller must implement:
  microbatches per stage.
