# DeepSeek-V4.1-Flash architecture specification: requirement, budget, block specs

Status: specification and budget, 2026-09-26. This document works top-down. It sets the performance
requirement first, derives a per-block specification from it, and records the gap to the RTL as built. It
covers the ROM array (packaging option (b)) and the HBM comparator.

- Budget model: `tools/arch_budget_v41.py`, recorded in `results/arch/arch_budget_v41.json`, tested by
  `tests/test_arch_budget_v41.py`.
- Shipped-shape program replay: `tools/hdc_replay_v41.py`, recorded in `results/arch/v41_replay.json`,
  tested by `tests/test_hdc_replay_v41.py`.

**Headline target (user decisions, 2026-09-26 and 2026-09-27).** The baseline is the best shippable option:
packaging option (b), plus a light-FEC package link (130 ns hop instead of 209 ns, the same bandwidth), plus
overlapped reductions (a collective's bytes stream behind its producer). Plain option (b) stays as a secondary
row. The target context is **200K**; 1M is the secondary point, because 200K gives the larger ROM:HBM
advantage on every metric (§8.3). At batch 1 the ROM array must reach at least **4,837 tokens/s per user
without MTP**, which is the report's DAG re-priced at the baseline. The budgeted design delivers **5,393 without
MTP and 12,002 with DSpark MTP** at the default τ = 4.1. The HBM comparator at equal total logic area delivers
972 without MTP and 1,391 with it. Every figure below comes from the budget model at its current spec, not
from silicon.

## 1. Requirement

The requirement is the report's own dependency DAG (`tools/decode_critical_path.py`, `packaging_options`,
option (b)): 188 reticle dies in 94 two-die packages, tensor group 4 spanning a package pair, and 28 layer
groups. It uses the realistic links: UCIe inside a package, and a board SerDes between packages. The
baseline re-prices that DAG with the light-FEC package link (130 ns, band 100-170) for collectives, stage hops on the rack-cable tier (209 ns, full RS(544,514); `technology.json` links.rom_rack_cable_serdes), 4 HBM3E stacks per die and with collectives
chasing their producers. The silicon must deliver what that DAG gives, or the report must change.

| context | baseline, batch 1, tokens/s/user (µs/token) | plain (b), batch 1 (µs/token) |
|---|---|---|
| 8,192 | 4,922 (203.2) | 4,522 (221.1) |
| 200,000 (headline) | **4,837** (206.7) | 4,450 (224.7) |
| 1,048,576 | 4,599 (217.4) | 4,249 (235.4) |

The model re-prices that DAG node by node from a block spec. At plain (b) and the DAG's own assumptions it
reproduces the published figures exactly (`test_dag_spec_reproduces_the_headline_exactly`). So the budget and
the headline share one dependency structure, and the question is only whether each node can be priced at the
widths and depths the DAG assumed. The baseline's two changes cut the collective latency on the critical path
from 40.3 to 26.4 µs per token and hide the collectives' 3.3 µs of bytes.

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

This reconciliation is on plain (b), the report as published, so layers B and C include that DAG's
communication, 55.6 µs per token; the baseline's links take 17 µs off every column.

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

| 200K, µs (baseline) | report DAG | required orders (chunks ≤ 8, fast FP) | golden orders | as built |
|---|---|---|---|---|
| compute-chain depths | 101.6 | 99.0 | 216.3 | 481.0 |
| sequential-chain floors (on the weight path) | 0 | 10.9 | 587.9 | 979.8 |
| KV gather and scan latency | 2.7 | 2.8 | 5.4 | 8.4 |
| collective latency + bytes | 26.6 | 26.4 | 14.4 | 16.6 |
| pipeline hops | 11.9 | 11.9 | 11.9 | 11.9 |
| control | 6.4 | 6.4 | 5.1 | 8.2 |
| **fixed part** | **149.1** | **157.4** | **840.9** | **1,505.9** |
| target | 206.7 | 206.7 | 206.7 | 206.7 |
| **issue budget** | 57.7 | **49.4** | **< 0: infeasible** | < 0 |

At 8K the issue budget is 47.3 µs; at 1M it is 50.0 µs. Plain (b)'s fixed part was 175.0 µs against a
224.7 µs target (issue budget 49.7 µs): the baseline removes 18 µs of link latency from both, so the widths
get the same budget against a faster target.

**Finding 1: the latency floor is the requirement.** Of the 206.7 µs target:

- 157 µs is fixed.
- 26 µs of that is collectives: about 5 per layer, each ~135 ns across the package pair with the light-FEC
  link, their bytes hidden behind the producers.
- About 99 µs is unit depth.

The widths therefore have only 49 µs, **24% of the token**, to spend.

**Finding 2: the golden's summation orders make the target unreachable at any width.** A 2,560-term
sequential FP32 chain costs 12,800 cycles at a 5-cycle add. Under the current orders the fixed part alone is
841 µs, which caps the design near 1,180 tokens/s per user (`ablations: golden_orders`).

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
| weight engine (FP8/FP4 block-dot) | MACs/cycle | 233,472 | 512 | 456× | QE: 16 block-dot lanes × 32 |
| BF16/FP32 weight engine | MACs/cycle | 32,896 | 64 | 514× | ME: 4 groups × 16 lanes |
| weight ROM read | bytes/cycle | 306,560 | 528 | 581× | QE word 16 × 33 B |
| attention engine (q·k, p·v) | MACs/cycle | 35,840 | 64 | 560× | ME head groups |
| KV row staging buffer | bytes/cycle | 2,310 | 128 | 18× | KV SRAM |
| indexer engine (FP4 × FP4) | MACs/cycle | 239,616 | 64 | 3,744× | ME head groups |
| index-key stream (from HBM) | bytes/cycle | 3,482 | 128 | 27× | KV SRAM |
| stream unit, linear lanes | elements/cycle | 1,024 | 8 | 128× | 8 lanes |
| stream unit, SFU lanes (exp/sigmoid/silu/divide) | elements/cycle | 256 | 8 | 32× | rsqrt, sqrt, softplus and gate on lane 0 only |
| index top-512 select | scores/cycle | 64 (streaming filter) | 1 (insertion) | 64× | XU `ot_hdc_select` |
| hyper-connection projection | FP32 MACs/cycle | 4,096 | 24 | 171× | HE 3 lanes × 8 chunks |
| longest accumulation chain | terms | 17 (8 + log2 tree) | 2,560 | — | golden orders |
| FP32 add latency | cycles | 3 | 5 | — | `ot_fp32_add_rne_pipe` |
| exp / sigmoid depth | cycles | 49 / 80 | 92 / 128 | — | padded in the V4.1 stream unit |
| producer → consumer | — | vector chaining | unit drains | — | wait masks |
| Engram gather ingest | bytes/cycle | 13.7 (256-bit port) | 12,672 (flat) | 0.001× | 48 × 2,112-bit ports, 16,559 IO pins |

The hyper-connection projection's requirement rose from 2,048 to 4,096 lanes at the baseline: with the link
latency cut, its side branch surfaced on the batch-64 critical path. The quantised weight engine's ROM read
counts FP8 at 33 B per 32-weight block. The weight-engine agent measured a 365 KB/cycle peak when the router's
FP32 weights (4 B each) stream concurrently; that is still 44% of the ROM macros' sweep rate.

**Weight ROM read.** At 306,560 B/cycle the required read is 37% of the ROM macro array's sweep rate:
2.96 TB/s/mm² over 289 mm² of ROM is 828 KB/cycle (`docs/MEMORY_COMPILERS_AND_BIST.md`). ROM bandwidth is
not the constraint. MAC lanes and latency are.

**Area.** At ASAP7 unit areas the required blocks total **90 mm² per die**, against the analytical design's
329 mm² N5 compute envelope. The breakdown:

| block | mm² |
|---|---|
| weight engine | 18.3 |
| BF16 engine | 16.8 |
| attention | 18.3 |
| indexer | 18.8 |
| light stream lanes | 4.2 |
| SFU lanes | 8.8 |
| hyper-connection projection | 4.8 |
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
| none (the spec) | 5,393 |
| golden summation orders | 1,179 |
| stream unit as built (8 lanes) | 1,482 |
| weight engines as built | 81 |
| attention on 64 lanes | 160 |
| indexer on 64 lanes | 112 (24 at 1M) |
| no chaining (drain barriers) | 4,984 |
| 5-cycle FP32 add | 5,296 |
| as-built SFU depths | 5,257 |
| two-pass select instead of the streaming filter | 5,280 (4,476 at 1M) |

On plain (b) the same spec gives 5,007 / 4,913 / 4,511 tokens/s per user at 8K / 200K / 1M, all above plain
(b)'s own target.

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
   - **Spec:** 239,616 FP4 × FP4 MACs/cycle, which is about 58 keys/cycle, streaming keys from the die's HBM
     at up to 3.5 KB/cycle.
   - The fused ReLU·weight head-sum runs on the stream unit's light lanes, at 32 heads per key.
   - At 1M, layer 20's scan is 17.8 MB per die, about 5.0 µs at the 3.6 TB/s the die's four HBM3E stacks
     sustain. That scan is the HBM term that grows with context (§9); at the spec's indexer width it wants 4.6 stacks' bandwidth, so on four the 1M scan is bandwidth-bound.

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
   **4,096 FP32 MAC lanes** (2,048 sufficed on plain (b); the faster baseline brings the side branch onto the
   batch-64 critical path). It runs as the sublayer's side branch and must finish within the sublayer body,
   also under MTP's 6 positions. The block agent measured 2,048 lanes at 328 cycles for one position and 1,578
   for six, bit-exact (`results/rtl/hdc_v41x_hcp_campaign.json`). The Sinkhorn unit's 297 core cycles already
   fit the body: no change.

8. **Engram gather.** The bandwidth is **13.7 B/cycle**: 48 rows × 264 B within a quarter of the ≥ 3.57 µs
   slack at batch 1, because the hash reads only token ids and the gather issues at embed time.
   - **Spec:** a per-bank slice at each column bank, one 264-B row per bank per token, and a 256-bit beat
     stream to the consuming die: 12,672 B in about 400 cycles.
   - This replaces the as-built 48 × 2,112-bit flat port, whose 16,559 IO pins forced a 460 µm die routed at
     841 MHz.

9. **Collectives.** The one-shot fixed-rank-order engine, as measured by agent a6df6a56. Each die broadcasts
   its partial once and folds all N in rank order, so latency after the last partial is 2 + (N − 1) × the
   add latency.
   - About five collectives per layer cost ~135 ns each with the baseline's light-FEC package link (130 ns
     hop; ~220 ns with plain (b)'s 209 ns). Their bytes stream behind the producers (overlapped reductions),
     so only the latency after the last partial remains: **26 µs per token, still the largest single fixed
     term** (44 µs on plain (b)).
   - **Spec:** a receive FIFO of 32 words per source, which removes link hold, and 1 GHz.

10. **Sequencer.** ≤ 5 cycles per issue, and a vector-credit chaining protocol between units in place of
    wait-mask drains. The replay counts ~3,840 instructions per token per die, so issue is 1.9% of the token.

11. **KV state and HBM controller on the ROM die (user decision).**
    - **Stacks:** four HBM3E stacks per die (standing user decision: what today's interposers carry; the beachfront rule, 60% of the perimeter at 12 mm per stack, would allow five).
    - **Bandwidth:** 3.6 TB/s sustained at 90%, measured with refresh on.
    - **Controller:** refresh-aware per-bank refresh (REFpb, tRFCpb 200 ns: refresh the not-yet-refreshed
      bank that the fewest queued bursts need, never the head burst's bank) with at least 64 beats of queue
      per pseudo-channel, OR all-bank refresh with at least 512 beats; no head-of-line blocking across
      channels. The record is `results/rtl/hdc_hbm_campaign.json` `refresh_study`, commit be30614a on the HBM
      comparator branch (RTL, reduced vehicle, every run bit-exact). It gives, at 4 / 8 / 16 / 32
      pseudo-channels:
      - aware REFpb: 0.965 / 0.989 / 0.993 / 0.992 of the refresh-free rate;
      - all-bank refresh with 512-beat queues: 0.979 / 0.973 / 0.972 / 0.964;
      - all-bank refresh with 64-beat queues: 0.933 / 0.852 / 0.949 / 0.952 (fails the 90% floor at 8).

      A scratch run (not in the record) at the worst-case tRFCpb of 350 ns gives aware REFpb 0.864 at 4
      pseudo-channels. The die therefore uses at least 8 pseudo-channels per stream, or the all-bank-512
      option, to keep the 90% margin against tRFCpb uncertainty.

      The tie-break among equally eligible banks depends on the workload. The index-key scan is one long
      sequential stream, so it breaks ties toward the MOST RECENTLY ACTIVATED bank, the set the stream has
      just left. The record's closed-bank-first tie-break was measured on the QE weight streams; on a
      sequential scan it refreshes the next bank set just before the stream needs it. The indexer agent
      (ac9ca93f; its campaign record will carry these) measured, per stack, 64-beat queues, 1M keys:
      - MRU tie-break: 0.956 of peak;
      - closed-first tie-break: 0.851;
      - all-bank refresh with 512-beat queues: 0.901, the fallback;
      - refresh-free: 0.998.

      Measured on five stacks (the campaign predates the four-stack decision; re-run on four pending), layer 20's 1M scan (262,144 keys) takes 4.08 µs with MRU, 0.989 of refresh-free,
      against 5.09 µs with closed-first.
    - **Prefetch:** window rows and reuse-layer selections have static addresses, so they are prefetched one
      layer ahead.
    - **Gathers:** an index-source layer's gather is exposed, and its first row is budgeted at 250 ns.
    - **Capacity:** per-user state at 1M is 93.5 MB on the busiest die, so the stacks hold **962 users at
      1M and 5,018 at 200K**. Batch is not capacity-limited below that, and the old 8,192-context admission
      limit from on-die KV does not apply.

12. **Power (requirement).** Per-die power must stay at or below the die's cooling limit, 0.5 W/mm² × 815 mm²
    = **407.5 W** (`technology.json` thermal), at every batch, with stage clock gating: an idle stage's clock
    tree gated at its block boundaries, and its ROM macros and engines quiescent. From
    `results/arch/arch_budget_v41.json` `power`, at 200K:

    | per die | m = 1 | m = 2 (MTP) |
    |---|---|---|
    | block area (ASAP7) | 90 mm² | 180 mm² |
    | active clock of the blocks | 7.9 W | 15.8 W |
    | dynamic while its stage holds the token, batch 1 | 25.3 W | 33.2 W |
    | dynamic at the saturated batch (every die busy) | 31.0 W | 46.9 W |

    With static leakage (33.5 W, the analytical N5 estimate) and the HBM interfaces (11.2 W), the worst case is
    **~92 W per die, 4.5× under the limit**. Without gating, the analytical design charges a 48 W/die clock
    term on all 525 mm² of logic, which is the upper bound if nothing gates. Stage gating is also what keeps
    batch-1 energy at 18.7 mJ per token instead of 289 mJ (§8).

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
| hyper-connection projection | 6.0× | 2.4× | 1.3× | 1.0× | FP32 lanes |
| attention (q·k, p·v, softmax) | 5.6× | 2.1× | 5.6× | 2.1× | MAC lanes; KV rows shared |
| indexer (scan + select) | 5.6× | 1.6× | 5.6× | 1.6× | MAC lanes; keys read once per pass |
| stream unit | 3.2× | 1.5× | 3.2× | 1.5× | lanes |
| fixed (depths, control, collectives, hops) | 1.17× | 1.16× | 1.15× | 1.12× | latency, once per pass |
| **whole verify pass** | **2.33×** (431.7 µs) | **1.43×** (253.9 µs) | **2.57×** (2,649 µs) | **2.50×** (2,548 µs) | |

**Does "speculation trades MACs for bandwidth" hold for sparse V4.1?** Only for the dense part.

- **Dense GEMVs.** The claim holds. HBM reads the dense weights once per pass, and the ROM die does the same
  once it has an m-way lane multiplier.
- **Routed experts.** The claim fails on both machines. Six positions touch 34.6 distinct experts, not 6, so
  HBM streams 5.3× the expert bytes. The ROM die holds each expert striped over its four-die group, with a
  pooled weight engine, so it streams the same union through its weight lanes at 5.35× the lane time. An
  m-way multiplier cannot help, because only positions that share an expert share a weight read.
- **"Idle expert dies" do not exist in this placement.** Striping puts every die on every expert. The
  alternative, expert-parallel placement, leaves dies idle at batch 1 only because it is *worse* balanced
  there. What the ROM die does have idle is macro read bandwidth: 828 KB/cycle available against 301 KB/cycle
  used, so 2.7× headroom. Harvesting it takes more weight lanes (area), not more positions.
- **Correlated routing.** If adjacent tokens share experts, the union shrinks. At an overlap of 25% (50%) of
  the union's excess, the ROM m = 6 verify drops 254 → 244 (234) µs and the HBM verify 2,548 → 2,175
  (1,801) µs. No measurement of adjacent-token routing on real prompts with the shipped router exists here;
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
| 1 | 90 | 431.7 | 25.4 | 8,969 |
| **2 (design)** | **180** | **321.5** | **20.2** | **12,002** (9,561 – 11,124 – 14,637) |
| 3 | 270 | 287.0 | 18.1 | 13,437 |
| 4 | 360 (exceeds 329) | 277.0 | 17.7 | 13,917 |
| 6 | 540 | 253.9 | 16.3 | 15,175 |

m = 2 is the knee: m = 3 buys 12% for 50% more area. The draft chain is 3 DSpark stages over a 5-row block
plus 5 dependent argmax steps over the 129,280-row vocabulary (lm_head row, rank-256 Markov bias, argmax, one
group collective). At m = 2 it is **20.2 µs, 6% of the cycle**.

With and without MTP, both machines, at τ = 4.1 (baseline; plain (b) in the last row):

| | 200K, no MTP | 200K, with MTP | 1M, no MTP | 1M, with MTP |
|---|---|---|---|---|
| ROM array (baseline; m = 2) | 5,393 | **12,002** | 4,913 | 10,458 |
| HBM comparator (iso logic area; m = 6) | 972 | 1,391 | 955 | 1,382 |
| ROM : HBM | 5.55× | **8.6×** | 5.15× | 7.6× |
| ROM array, plain (b) (m = 2) | 4,913 | 11,006 | 4,511 | 9,693 |

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
| 1 | 5,393 | 5,393 | 18.7 | 12,002 | 972 | 972 | 1,515 | 1,372 |
| 8 | 5,393 | 43,144 | 13.6 | 12,002 | 972 | 7,772 | 1,487 | 1,372 |
| 28 | 5,393 | 151,003 | 13.1 | 12,002 | 972 | 27,202 | 1,484 | 1,372 |
| 64 | 3,874 | 247,962 | 11.1 | 7,029 | 730 | 46,725 | 858 | 779 |
| 128 | 2,685 | 343,734 | 10.7 | 4,141 | 430 | 55,054 | 730 | 483 |
| 256 | 1,652 | 422,815 | 10.2 | 2,266 | 280 | 71,634 | 556 | 298 |
| 1,024 | 439 | 449,707 | 9.7 | 602 | 91 | 93,067 | 402 | 160 |

The HBM MTP column uses m = 2 here, the batch model's single design point; §7 gives HBM at m = 6.

### 8.2 1M

| batch | ROM tok/s/user | ROM array tok/s | ROM mJ/token (gated) | HBM tok/s/user | HBM array tok/s | HBM mJ/token (gated) |
|---|---|---|---|---|---|---|
| 1 | 4,913 | 4,913 | 35.1 | 955 | 955 | 1,532 |
| 64 | 3,340 | 213,748 | 26.9 | 709 | 45,357 | 874 |
| 1,024 | 339 | 346,988 | 25.5 | 86 | 87,694 | 418 |

Batch-1 energy per token without gating: ROM 289 mJ (clock 276 mJ), HBM 2,289 mJ (weights 1,474 mJ). Every
die clocks every cycle while only one layer group works, so **idle-stage clock gating is a requirement**.
Gated, the ROM token at batch 1 is 18.7 mJ, **80.9× below HBM**.

The pipeline keeps the batch-1 per-user rate up to 28 users. The array then saturates at 450K tokens/s at
200K; the HBM comparator reaches 93K at 1,024 users. Per-user MTP gains shrink with batch, because the
verify pass's extra positions compete for the lanes that other users' tokens use.

### 8.3 Target context: 200K

| ROM : HBM | 200K | 1M |
|---|---|---|
| per-user rate, with MTP (τ = 4.1) | **8.75×** | 7.75× |
| per-user rate, without MTP | **5.55×** | 5.15× |
| energy per token, batch 1, gated | **80.9×** | 43.7× |
| array throughput, batch 64 | **5.31×** | 4.71× |
| array throughput, saturated | **4.83×** | 3.96× |

200K wins on every metric, on the baseline as on plain (b). The reason is that the context-dependent cost is
the indexer's key scan plus its KV. Both machines hold it in HBM, stream it at the same per-die bandwidth,
and pay for it equally. The ROM advantage is in the weight path, which does not grow with context, so a
longer context dilutes it. 200K is the headline and 1M is the secondary point.

## 9. HBM comparator specification (equal total logic area)

**Configuration.** The ROM array spends 188 dies × 328.9 mm² = 61,836 mm² on compute. The comparator spends
the same on logic-only dies: the same 815 mm² die with the ROM area freed, keeping interconnect and overhead,
with 4 HBM3E stacks per die (the ROM die's package limit; the beachfront allows five) and 628.3 mm² of logic.

- **99 dies** in about 24 tensor groups of 4.
- 8.9 TB of HBM, against 510 GB of weights.
- **3.6 TB/s sustained per die**: a 90% efficiency requirement, measured with refresh on.

At 200K the comparator gives 972 tokens/s per user on the baseline links (1,143 on plain (b)). Its weight
sweep is 848 µs of the 1029 µs token.

| sustained efficiency | 75% | 85% | 90% | 95% |
|---|---|---|---|---|
| tokens/s/user | 834 | 926 | 972 | 1,016 |

Requirements:

- **Prefetch window.** 3.6 MB per die, which is latency × bandwidth at 1 µs first access. Every static-address
  stream (dense weights, window rows) is issued that far ahead across every dependency point.
- **Routed-expert fetch.** The hard part. The expert ids exist only after the router's top-6, so a layer's
  28.2 MB per die of expert bytes is exposed: first access plus bytes, **7.3 µs per layer on the critical
  path**. With MTP the fetch is the union (34.6 experts at B = 6), which caps HBM's speculative gain at 1.4×
  (γ = 5, τ = 4.1).
- **Controller.** Refresh-aware REFpb with at least 64-beat queues per pseudo-channel, or all-bank refresh
  with at least 512 beats. Request issue must never let a refreshing channel stall words that do not touch
  it, and each stream uses at least 8 pseudo-channels (§6 item 11; `results/rtl/hdc_hbm_campaign.json`
  `refresh_study`).
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
5. **Hyper-connection projection** at 4,096 lanes, and the **Engram per-bank gather** at a 256-bit port.
6. **MTP m = 2 lane multiplier** across the engines.

Each block ships with a performance testbench that asserts its spec row (throughput, depth, bit-exactness).
Each is re-checked with the bit-exact V4.1 token campaign (`tools/rtl_hdc_v41_decode_campaign.py`) and routed
on ASAP7 at 0.97 ns with registered boundaries.

**Status.** The spec, the budget model, the replay and R-ARITH in the golden and the ISA simulator are
committed. The six blocks are merged into this branch as they stand; their campaigns are being refreshed
against the current golden, and an integration agent is building `ot_hdc_core_v41x` (a copy of the MTP core
with each unit behind an adapter), brought up one arithmetic class at a time. Committed so far:
- **Engram gather:** bit-exact (600 shipped-geometry + 436 reduced-vehicle tokens), 32.9 B/cycle against 13.7
  required, slice routed closed at 1,656 MHz and assembler at 1,179 MHz.
- **HC projection:** 2,048 lanes bit-exact at shipped K; 328 cycles for one position, 1,578 for six.
- **Weight engines:** 7 tile configurations bit-exact, one beat per cycle, latencies within the spec.
- **Select:** 1M tails of 99-144 cycles against 181, no ingest stalls; its routes are still short of 1.034 GHz.
- **Indexer:** engine and HBM key stream committed; output tree routed closed at 1.153 GHz.

**The spec replayed on the program (`tools/hdc_timing_v41x.py`, `results/arch/v41x_replay.json`).** The
shipped-shape instruction stream of one die (about 3,840 instructions per token) runs on an event model of
the re-specified core. Every op runs on its new unit at the spec widths, with region dependences and vector
chaining, and the DAG's communication is added. At the reduced shape, with the as-built widths and drains,
its engine reproduces `hdc_timing_v41.simulate` exactly (344,131 cycles). Compute per token is 134.2 / 139.5
/ 160.8 µs at 8K / 200K / 1M.

| context | replayed spec, baseline links (38.5 µs comm) | budget, baseline | target, baseline | replayed, plain (b) (55.6 µs) | target, plain (b) |
|---|---|---|---|---|---|
| 8K | 5,789 | 5,507 | 4,922 | 5,270 | 4,522 |
| 200K | 5,616 | 5,393 | 4,837 | 5,126 | 4,450 |
| 1M | 5,015 | 4,913 | 4,599 | 4,621 | 4,249 |

- The spec therefore meets the target on the program itself, not only on the DAG.
- With chaining, dependent-stage depth dominates the 140 µs of compute at 200K: stream-unit depth 27 µs,
  the scalar side pipe (rsqrt 58 cycles per norm, softplus 280 per router) 21 µs, the BF16 weight engine 16 µs,
  transcendental depth 15 µs.
- Chaining off (drains), plain (b): 4,274 at 200K, still above that target but not at 1M (3,917).
- Stream-unit width saturates near 1,024 lanes. Softplus depth is the next latency lever.

## 11. Assumptions and limits

- **One dependency structure.** The budget re-prices the report's DAG. The replay (§3) shows that the as-built
  sequencer adds drains and ordered reductions that this DAG does not have; the spec requires them removed.
  The spec is also verified on the program by the replay above (§10), which keeps the as-built instruction
  stream and changes only the units and the sequencing.
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

## 12. Attacking the dependency chain (user-approved order)

V4.1 on this array is dependency-chain-bound, not weight-bound. On the plain-(b) DAG the token is ~176 of
225 µs of dependent latency: compute chain 117, collectives 40 (about 210 on-path collectives), hops 12,
control 7, and weights only 43. The spec above (§4-§6) already takes the chain from the widths' side. This
section prices the further levers, each added to the previous, on the spec's widths at batch 1
(`tools/arch_budget_v41.py` `chain_ladder`, `results/arch/arch_budget_v41.json` `chain_ladder`):

| step | levers | µs/token at 200K | tok/s/user 8K / 200K / 1M | block area |
|---|---|---|---|---|
| 0 | the spec on the baseline links | 185.4 | 5,507 / 5,393 / 4,913 | 90 mm² |
| 1 | reductions off the critical path | 162.8 | 6,262 / 6,142 / 5,526 | 90 mm² |
| 2 | + tile/row chaining for every unit | 146.8 | 6,900 / 6,810 / 6,407 | 90 mm² |
| 3 | + shorter stages | **133.5** | **7,600 / 7,488 / 6,991** | 90 mm² |
| 4a | + attention on one package, spec widths | 138.2 | 7,464 / 7,235 / 6,323 | 90 mm² |
| 4b | + attention on one package, attention/indexer/weight engines ×2 | 119.1 | 8,702 / 8,395 / 7,196 | 162 mm² |
| 4c | the same engines ×2, attention kept on the four-die group | 121.9 | 8,336 / 8,202 / 7,609 | 162 mm² |
| 5 | MTP m = 2, τ = 4.1, on step 3 | 240.1 per cycle | **16,129 / 15,756 / 14,335** | 180 mm² |

1. **Reductions off the critical path (−23 µs).** An RMSNorm's rstd scales the next matvec's outputs instead
   of its input, so the sum of squares and the rsqrt run beside the weight sweep. The attention softmax
   becomes online: exp streams behind the scores with a running-max rescale, as the release's own
   sparse-attention kernel does in 64-row blocks (`hdc_golden_v41` `vendor_blocks`). Fused SiLU·mul and the
   hyper-connection/Sinkhorn side branch are already in the graph. **Both are contract changes:** the golden
   must adopt them (an R-ARITH v2), and the ISA and RTL follow, with the token re-checked against the oracle
   as in §4.
2. **Chaining for every unit (−16 µs).** Matvecs, the attention and indexer scans and the local selects start
   on their producer's first tile or row instead of its last element. This extends the vector unit's
   per-vector credits to the ME/QE, attention, indexer and select outputs. The weight sweep on the path
   falls from 23 to 13 µs because each matvec now overlaps its producer.
3. **Shorter stages (−13 µs).** The stream unit's base depth drops to 21 cycles (29 in the DAG) and its reducer
   tail to 25 (32). Beyond the spec's exp and sigmoid, rsqrt goes to 58 cycles (90) and sqrt(softplus) to 161
   (259); the vector-unit agent measured these depths. The chain floor is already chunk-of-8 plus the tree,
   on 3-cycle adds.
4. **Collectives and hops: fewer tensor-parallel boundaries (not adopted).** Keeping attention and its
   projections on the two dies of one package halves the attention collectives' latency on the path (26 →
   13 µs). But it doubles each die's attention, indexer and projection work.
   - At the spec's widths this is a net loss: 7,235 against 7,488 tok/s at 200K, and 6,323 against 6,991
     at 1M.
   - With those engines doubled it gains only 2-3% at 8K and 200K over spending the same area without the
     move (step 4c), and loses 4% at 1M, where the doubled index scan dominates.
   - The attention stays on the four-die group.
   - What remains of the collective term (26 µs) is link latency after the last partial. In-package
     reduction is already the one-shot engine's first level. The next lever is in-network reduction, which
     removes the package-pair round trip, or a shorter pair link. The substrate module is +12.5% but not
     shippable (the packaging agent's study).
5. **MTP on top (×2.1).** On step 3 the m = 2 core verifies 6 positions in 240.1 µs per cycle with its draft.
   At τ = 4.1 that is **15,756 tok/s per user at 200K**, against 12,002 with MTP on the spec alone.

Levers 1-3 are the integration requirements for `ot_hdc_core_v41x`:
- lever 1 is a golden/ISA/RTL contract change;
- lever 2 is the chaining protocol on every unit boundary;
- lever 3 is the vector unit's measured depths.

Doubling the engines (step 4c, +8% at 200K for +72 mm²) stays inside the 329 mm² envelope. It is the next
width lever if the silicon falls short. Every number in this section is the model's, on the report's DAG,
not silicon.
