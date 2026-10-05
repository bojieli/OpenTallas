# DeepSeek-V4.1-Flash architecture specification: requirement, budget, block specs

Status: specification and budget, 2026-09-28 (re-derived on the unified budget model; MTP at the measured
V4.1-Flash τ, liquid cooling baseline). This document works
top-down. It sets the performance requirement first, derives a per-block specification from it, and records the
gap to the RTL as built. It covers the ROM array (packaging option (b)) and the HBM comparator.

- Budget model: `tools/arch_budget_v41.py`, the single V4.1 budget model (the former design-point base
  `tools/arch_budget_v41_dp.py` is retired into it), recorded in `results/arch/arch_budget_v41.json`, tested by
  `tests/test_arch_budget_v41.py` and `tests/test_v41_dag_basis.py`. It prices every weight at the official
  checkpoint's precision (FP8 E4M3 with one UE8M0 scale per 32 × 32 block, FP4 routed experts, BF16 lm_head /
  router / compressor), adopts online softmax (norm folding is rejected), uses the measured hyper-connection depth
  (126 cycles) and the pinned pre-pipeline RTL timing constants of `tools/decode_critical_path.py` (e6ba1efc).
- Shipped-shape program replay: `tools/hdc_replay_v41.py`, recorded in `results/arch/v41_replay.json`,
  tested by `tests/test_hdc_replay_v41.py`.

**Headline target (user decisions, 2026-09-26 and 2026-09-27).** The baseline is the best shippable option:
packaging option (b), plus a light-FEC package link (130 ns hop instead of 209 ns, the same bandwidth), plus
overlapped reductions (a collective's bytes stream behind its producer). Plain option (b) stays as a secondary
row. The target context is **1M** (user decision 2026-09-27: the default of most agent APIs); 200K is the
secondary point and 8K the tertiary one (§8.3). At batch 1 the ROM array must reach at least **4,599 tokens/s per
user without MTP at 1M** (4,837 at 200K), which is the report's DAG re-priced at the baseline. The budgeted design
delivers **4,933 without MTP and 9,500 with DSpark MTP at 1M** (5,418 and 10,904 at 200K) at the headline
τ = 3.65, the value measured on V4.1-Flash itself. The HBM comparator at equal total logic area delivers 926
without MTP and 1,221 with it at 1M (942 and 1,228 at 200K). Every figure below comes from the budget model at its current spec, not from silicon; the
adopted design point built on this spec is in `docs/ARCH_V41_RACK.md` and the atlas.

**One occupancy basis (2026-09-28).** Every operating point here is bound by the busiest pipeline stage, the
same bound the adopted design point uses. §8.4 is the record-bound ladder from this specification (4,933 at 1M)
to the design point (7,049).

## 1. Requirement

The requirement is the report's own dependency DAG (`tools/decode_critical_path.py`, `packaging_options`,
option (b)): 188 reticle dies in 94 two-die packages, tensor group 4 spanning a package pair, and 28 layer
groups. It uses the realistic links: UCIe inside a package, and a board SerDes between packages. The
baseline re-prices that DAG with the light-FEC package link (130 ns, band 100-170) for collectives, stage hops on the rack-cable tier (209 ns, full RS(544,514); `technology.json` links.rom_rack_cable_serdes), 4 HBM3E stacks per die and with collectives
chasing their producers. The silicon must deliver what that DAG gives, or the report must change.

| context | baseline, batch 1, tokens/s/user (µs/token) | plain (b), batch 1 (µs/token) |
|---|---|---|
| 8,192 | 4,922 (203.2) | 4,522 (221.1) |
| 200,000 | 4,837 (206.7) | 4,450 (224.7) |
| 1,048,576 (headline) | **4,599** (217.4) | 4,249 (235.4) |

The model re-prices that DAG node by node from a block spec. At plain (b) and the DAG's own assumptions it
reproduces the published figures exactly (`test_dag_spec_reproduces_the_headline_exactly`). So the budget and
the headline share one dependency structure, and the question is only whether each node can be priced at the
widths and depths the DAG assumed. The baseline's two changes cut the collective latency on the critical path
from 40.3 to 26.4 µs per token and hide the collectives' 3.3 µs of bytes.

Speculation is reported with and without MTP, on both machines:

- τ, the accepted tokens per verify cycle including the bonus token, headlines at **3.65** (user decision
  2026-09-28): the measured V4.1-Flash τ = 3.65 (DSpark at γ = 5, greedy, on-policy exact replay on the model's own output, 95% CI 3.50–3.84; `results/speculative/v41_flash_dspark_onpolicy_greedy.json`), read by `tools/arch_budget_v41.py` (`TAU_HEADLINE`) from that record.
  It replaces the earlier 5.0 (LMSYS/SGLang, DeepSeek-V4-Pro, workload not stated).
- The sensitivity band is the published V4.1-Flash range **3.5–4.1** (InferenceX 3.51 / 4.07, vLLM PR #57432
  GSM8K greedy 3.82–3.89; `results/speculative/acceptance_tau.json`); the V4-Pro-derived 3.27 / 3.80 (vLLM
  survival, `results/roofline/speculative/hdc_design_faithful.json`) are kept as further points.
- DSpark's configured block is γ = 5, so a verify pass carries **6 positions**.

## 2. Workload: one token, from the model graph

The ops come from `ops_of_layer` in the budget model, which follows the operator order of
`tools/hdc_golden_v41.py` and the shipped `operator_config`: dim 5,120, 4 hyper-connection copies, 64 heads of
512, 32 index heads of 128, 384 experts with top-6, window 128, index top-512, and candidate blocks of 8 with
top-2,048 at layer 20.

| per token (whole model) | 8K | 200K | 1M |
|---|---|---|---|
| weight MACs, FP8 | 5.49 G | 5.49 G | 5.49 G |
| weight MACs, FP4 (6 routed experts) | 8.49 G | 8.49 G | 8.49 G |
| weight MACs, BF16 activations (wo_a on its FP8 weights; lm_head, compressor, router, index proj in BF16) | 2.10 G | 2.10 G | 2.10 G |
| attention MACs (q·k + p·v over 128 window + 512 selected rows) | 1.61 G | 1.61 G | 1.61 G |
| **indexer MACs** (32 × 128 over every compressed key) | 0.22 G | **2.32 G** | **11.0 G** |
| weight ROM bytes read | 13.03 GB | 13.03 GB | 13.03 GB |
| KV bytes (window rows + gathered compressed rows) | 13.9 MB | 13.9 MB | 13.9 MB |
| **index-key bytes** (68 B per key) | 3.6 MB | **38.5 MB** | **182.7 MB** |
| Engram table bytes (48 rows × 264 B) | 12.7 KB | 12.7 KB | 12.7 KB |
| stream element-ops (linear / transcendental / divide) | 18.4 / 2.2 / 1.5 M | 34.8 / 2.2 / 1.5 M | 102.7 / 2.2 / 1.5 M |
| collectives per token (payload per user) | 209 (2.06 MB) | 209 | 209 |

Per layer at 200K:

| layer | kind | MACs | ROM bytes | index bytes | stream element-ops | collectives |
|---|---|---|---|---|---|---|
| 0 | sliding window | 386 M | 283 MB | 0 | 440 K | 5 |
| 1 | window + Engram | 543 M | 440 MB | 0 | 563 K | 5 |
| 2 | ratio-2 source, scans 100K keys | 840 M | 299 MB | 6.8 MB | 3.72 M | 6 |
| 3 | ratio-2 reuse | 419 M | 283 MB | 0 | 506 K | 5 |
| 20 | ratio-1 source, scans 200K keys, candidates | 1,247 M | 294 MB | 13.6 MB | 6.92 M | 7 |
| 24 | reindex, scans 16,384 | 492 M | 288 MB | 1.1 MB | 1.04 M | 6 |

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
| compute-chain depths | 101.6 | 99.0 | 218.9 | 483.7 |
| sequential-chain floors (on the weight path) | 0 | 10.9 | 587.9 | 979.8 |
| KV gather and scan latency | 2.7 | 2.8 | 5.4 | 8.4 |
| collective latency + bytes | 26.6 | 26.4 | 14.4 | 16.6 |
| pipeline hops | 11.9 | 11.9 | 11.9 | 11.9 |
| control | 6.4 | 6.4 | 5.1 | 8.2 |
| **fixed part** | **149.1** | **157.4** | **843.5** | **1,508.6** |
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
844 µs, which caps the design near 1,170 tokens/s per user (`ablations: golden_orders`).

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
| weight engine (FP8/FP4 block-dot) | MACs/cycle | 264,960 | 512 | 518× | QE: 16 block-dot lanes × 32 |
| BF16/FP32 weight engine | MACs/cycle | 41,664 | 64 | 651× | ME: 4 groups × 16 lanes |
| weight ROM read | bytes/cycle | 348,547 | 528 | 660× | QE word 16 × 33 B |
| attention engine (q·k, p·v) | MACs/cycle | 37,184 | 64 | 581× | ME head groups |
| KV row staging buffer | bytes/cycle | 2,397 | 128 | 19× | KV SRAM |
| indexer engine (FP4 × FP4) | MACs/cycle | 248,832 | 64 | 3,888× | ME head groups |
| index-key stream (from HBM) | bytes/cycle | 3,482 | 128 | 27× | KV SRAM |
| stream unit, linear lanes | elements/cycle | 1,024 | 8 | 128× | 8 lanes |
| stream unit, SFU lanes (exp/sigmoid/silu/divide) | elements/cycle | 256 | 8 | 32× | rsqrt, sqrt, softplus and gate on lane 0 only |
| index top-512 select | scores/cycle | 64 (streaming filter) | 1 (insertion) | 64× | XU `ot_hdc_select` |
| hyper-connection projection | FP32 MACs/cycle | 5,120 | 24 | 213× | HE 3 lanes × 8 chunks |
| longest accumulation chain | terms | 17 (8 + log2 tree) | 2,560 | — | golden orders |
| FP32 add latency | cycles | 3 | 5 | — | `ot_fp32_add_rne_pipe` |
| exp / sigmoid depth | cycles | 49 / 80 | 92 / 128 | — | padded in the V4.1 stream unit |
| producer → consumer | — | vector chaining | unit drains | — | wait masks |
| Engram gather ingest | bytes/cycle | 13.7 (256-bit port) | 12,672 (flat) | 0.001× | 48 × 2,112-bit ports, 16,559 IO pins |

The hyper-connection projection's requirement is 5,120 FP32 lanes per weight lane: at the measured 126-cycle
projection depth (`results/rtl/hdc_v41x_hcp_campaign.json`), 2 × 4,096 lanes leave 45 of 80 projections on the
MTP verify's critical path and 2 × 5,120 take them off at the batch-1 spec (`hc_mtp_sizing`). The quantised
weight engine's ROM read counts the checkpoint's own layout: FP8 at one UE8M0 scale per 32 × 32 block (1 + 1/1024
B per weight) and FP4 routed experts at one scale per 32. The weight-engine agent measured a 365 KB/cycle peak
when the router's weights streamed concurrently as FP32; the checkpoint's router is BF16, so that peak is an
upper bound, 44% of the ROM macros' sweep rate.

**Weight ROM read.** At 348,547 B/cycle the required read is 42% of the ROM macro array's sweep rate:
2.96 TB/s/mm² over 289 mm² of ROM is 828 KB/cycle (`docs/MEMORY_COMPILERS_AND_BIST.md`). ROM bandwidth is
not the constraint. MAC lanes and latency are.

**Area.** At ASAP7 unit areas the required blocks total **99.5 mm² per die**, against the analytical design's
329 mm² N5 compute envelope. The breakdown:

| block | mm² |
|---|---|
| weight engine | 20.8 |
| BF16 engine | 21.2 |
| attention | 18.9 |
| indexer | 19.5 |
| light stream lanes | 4.2 |
| SFU lanes | 8.8 |
| hyper-connection projection | 6.0 |
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
| none (the spec) | 5,418 |
| golden summation orders | 1,171 |
| stream unit as built (8 lanes) | 1,487 |
| weight engines as built | 69 |
| attention on 64 lanes | 160 |
| indexer on 64 lanes | 112 (24 at 1M) |
| no chaining (drain barriers) | 5,000 |
| 5-cycle FP32 add | 5,309 |
| as-built SFU depths | 5,275 |
| two-pass select instead of the streaming filter | 5,304 (4,493 at 1M) |

On plain (b) the same spec gives 5,028 / 4,933 / 4,528 tokens/s per user at 8K / 200K / 1M, all above plain
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
   - **Spec:** 264,960 MACs/cycle and 349 KB/cycle of ROM read. Every matrix is striped across enough macros
     to reach the read rate.
   - **BF16/FP32 engine:** 41,664 MACs/cycle, for wo_a (its FP8 codes and block scales dequantised exactly at
     the lane input), the lm_head, the compressor, the router and the index projection.
   - **MTP lane multiplier:** m MAC lanes per weight lane; m = 2 at the design point (§7).
   - *Bench:* a matvec of n rows × k in ⌈n·k / lanes⌉ + depth cycles, with depth ≤ 60 + 3·⌈log2(k/8)⌉.

4. **Attention engine.** A dynamic-operand engine, separate from the weight engines, because ROM-stationary
   lanes cannot take KV operands. The KV is single-head MQA with 512-dim rows shared by all heads, so one row
   read feeds 16 heads × 512 MACs on a die.
   - **Spec:** 37,184 BF16 × FP8 MACs/cycle and a 2.4 KB/cycle row staging buffer: one 528-B row per cycle
     feeds 8,192 MACs. The buffer holds 640 rows, 338 KB per die per layer.
   - The 64-position blocks of the release's online softmax fit in the buffer.

5. **Indexer engine and key stream (KV in HBM, user decision).** Index keys stay in their model precision:
   FP4 E2M1 codes plus one UE8M0 scale per 32, **68 B per key**. The golden quantises every key to FP4 before
   use, so this is lossless and 3.8× smaller than BF16.
   - **Spec:** 248,832 FP4 × FP4 MACs/cycle, which is about 61 keys/cycle, streaming keys from the die's HBM
     at up to 3.5 KB/cycle.
   - The fused ReLU·weight head-sum runs on the stream unit's light lanes, at 32 heads per key.
   - At 1M, layer 20's scan is 17.8 MB per die, about 5.0 µs at the 3.6 TB/s the die's four HBM3E stacks
     sustain. That scan is the HBM term that grows with context (§9); at the spec's indexer width it wants 4.7 stacks' bandwidth, so on four the 1M scan is bandwidth-bound.

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
   **5,120 FP32 MAC lanes per weight lane** (sized for the MTP verify at the measured 126-cycle projection depth:
   the smallest width that keeps the chain-attacked MTP rate within 0.2% of unlimited lanes, `hc_mtp_sizing`).
   It runs as the sublayer's side branch and must finish within the sublayer body, also under MTP's 6
   positions. The block agent measured 2,048 lanes at 328 cycles for one position and 1,578
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
    - **Stacks:** four HBM3E stacks per die, 4 <!-- figure: 4 src="results/arch/arch_budget_v41.json#requirement.headline.hbm_stacks_per_die" name="V4.1 HBM stacks per ROM die" --> per layer die and 8 <!-- figure: 8 src="results/arch/arch_budget_v41.json#requirement.headline.hbm_stacks_per_package" name="V4.1 HBM stacks per layer package" --> per two-die layer package. This is a standing user decision: it is what today's interposers carry. The beachfront rule, 60% of the perimeter at 12 mm per stack, would allow five per die, and 10 per package is the report DAG's superseded figure.
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
    - **Capacity:** per-user state at 1M is 93.5 MB on the busiest die. After the 0.9 capacity reserve for
      runtime workspace, allocator and safety (`technology.json` `efficiencies.hbm_capacity`, the reserve the
      Qwen3 budget applies), the stacks hold **866 users at 1M and 4,516 at 200K** (962 and 5,018 without
      it). A saturated operating point runs at most that many users (`arch_budget_v41.point_batch`); the old
      8,192-context admission limit from on-die KV does not apply.

12. **Power (requirement).** Per-die power must stay at or below the die's cooling limit at every batch, with
    stage clock gating: an idle stage's clock tree gated at its block boundaries, and its ROM macros and engines
    quiescent. The limit is the per-class limit of a die in a two-die package (`configs/hardware/
    power_scenarios.json` cooling classes: a shipping package's rating less its own stacks, per die): **474.6 W
    liquid, the V4.1 baseline** (user decision 2026-09-28), with 374.6 W air as the sensitivity. The former 0.5 W/mm² × 815 mm² rule (407.5 W, an A100 module rating over its die) is
    withdrawn. **The check is the hottest die, not the average:** the placement cuts the layers at equal ROM
    bytes, so the stages that hold the uncapped index scans carry far more than the mean. With the adopted stage
    rebalancing (layer 20's keys split over S14, S13 and S12; `tools/v41_stage_rebalance.py`) the hottest die is
    S9, layer 14's scan: 3.8× the mean layer die's work at batch 1 and 4.0× at saturation
    (`power_scenarios.v41_hottest_die`; 6.9× and 7.4× on S14 before the split). From
    `results/arch/arch_budget_v41.json` `power`, at 1M (hottest die; the array average in parentheses):

    | per die | m = 1 | m = 2 (MTP) |
    |---|---|---|
    | block area (ASAP7) | 99.5 mm² | 199.1 mm² |
    | active clock of the blocks | 8.7 W | 17.5 W |
    | dynamic while its stage holds the token, batch 1 | 145.7 W (44.4) | 154.4 W (53.2) |
    | dynamic at the saturated batch (busiest-stage bound) | 81.8 W (20.5) | 99.3 W (38.0) |

    Static power on the validated inputs is 98.8 W per die: leakage 54.5 W (0.10 W/mm² of logic, 0.0067 W/mm² of
    ROM array; `technology.json` power.static_leakage_w_per_mm2), HBM idle 11.2 W (4 stacks), always-on SerDes
    30.6 W and UCIe idle 2.5 W. On the busiest-stage basis the spec's saturated rate is held down by S14 (layer
    20's unsplit scan), so the saturated average falls below the active power. The worst point is therefore the
    pipeline fill, where every stage holds a token and every die runs at its batch-1 active power. With the HBM
    interface at its worst-case traffic (34.2 W), the worst case is **276.3 W for the hottest die, within liquid
    (0.58× of 474.6 W) and within air (0.74× of 374.6 W)**. Provisioned at 1.2 × worst case through the wall
    chain, it is 411.2 W. Before 2026-09-28 the saturated rate used the stage mean, which gave 373.8 W and
    556.4 W. These are specification-width figures and do not bound the design point, which is faster. At the
    adopted design point, whose operating points are bound by the busiest stage, the hottest die draws 383 W at batch 1 and the fill, 455 W
    at batch 1 with MTP (a head die, the draft), 426 W at the fill with MTP and 461 / 471 W saturated without /
    with MTP at 1M (production lane, `results/arch/power_scenarios.json`): **within liquid at every operating
    point over 200K–1M, over air at every 1M point** (`results/arch/v41_stage_rebalance.json`
    `cooling_sweep`). That is the placement balanced in time, not bytes, that this requirement asks for: the
    index scans are spread by the stage rebalancing (the ratio-2 scans of layers 2, 8 and 14 only in MTP
    verify passes, where their home dies would otherwise exceed liquid). Without gating, the analytical design charges a 48 W/die clock term on all
    525 mm² of logic, which is the upper bound if nothing gates. Stage gating is also what keeps batch-1 energy
    at 36.0 mJ per token at 1M instead of 362 mJ (19.6 against 317 mJ at 200K; §8).

## 7. MTP (DSpark): per-operator speculation analysis

The verify pass carries B = 6 positions. The same `price()` as the plain token applies, with MACs and stream
elements × B, dense weights read once per pass, routed experts at the union U(B) = 384·(1 − (1 − 6/384)^B),
which is 34.6 at B = 6, KV rows and index keys read once per user, and fixed latencies once per pass.

Cost ratio verify / plain per operator class, at 200K. "Busy" is the class's total unit time per token on
one die; "path" is its share of the critical path.

| operator class | ROM, AR-sized lanes (m = 1) | ROM, m = 6 core | HBM, m = 1 | HBM, m = 6 | binding resource |
|---|---|---|---|---|---|
| dense GEMVs (projections, shared expert, head) | 5.0× (MAC-bound) | **1.0×** (weight read shared) | **1.0×** (bytes shared) | 1.0× | ROM: MAC lanes; HBM: bytes |
| routed experts | 6.0× | **5.35×** | **5.3×** | 5.3× | ROM: weight lanes (the union); HBM: bytes (the union) |
| hyper-connection projection | 6.0× | 1.9× | 1.0× | 1.0× | FP32 lanes |
| attention (q·k, p·v, softmax) | 5.6× | 2.1× | 5.6× | 2.1× | MAC lanes; KV rows shared |
| indexer (scan + select) | 5.5× | 1.6× | 5.5× | 1.6× | MAC lanes; keys read once per pass |
| stream unit | 3.2× | 1.5× | 3.2× | 1.5× | lanes |
| fixed (depths, control, collectives, hops) | 1.17× | 1.16× | 1.15× | 1.12× | latency, once per pass |
| **whole verify pass** | **2.30×** (424.9 µs) | **1.41×** (248.6 µs) | **2.52×** (2,679 µs) | **2.45×** (2,581 µs) | |

**Does "speculation trades MACs for bandwidth" hold for sparse V4.1?** Only for the dense part.

- **Dense GEMVs.** The claim holds. HBM reads the dense weights once per pass, and the ROM die does the same
  once it has an m-way lane multiplier.
- **Routed experts.** The claim fails on both machines. Six positions touch 34.6 distinct experts, not 6, so
  HBM streams 5.3× the expert bytes. The ROM die holds each expert striped over its four-die group, with a
  pooled weight engine, so it streams the same union through its weight lanes at 5.35× the lane time. An
  m-way multiplier cannot help, because only positions that share an expert share a weight read.
- **"Idle expert dies" do not exist in this placement.** Striping puts every die on every expert. The
  alternative, expert-parallel placement, leaves dies idle at batch 1 only because it is *worse* balanced
  there. What the ROM die does have idle is macro read bandwidth: 828 KB/cycle available against 349 KB/cycle
  used, so 2.4× headroom. Harvesting it takes more weight lanes (area), not more positions.
- **Correlated routing.** If adjacent tokens share experts, the union shrinks. At an overlap of 25% (50%) of
  the union's excess, the ROM m = 6 verify drops 249 → 240 (235) µs and the HBM verify 2,581 → 2,207
  (1,834) µs. No measurement of adjacent-token routing on real prompts with the shipped router exists here;
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

**The MTP design point** at 200K, B = 6, τ = 3.65 (measured). An m-way core makes every engine m times wider;
the ROM read width does not change.

| m | block area, mm² | verify, µs | draft, µs | tok/s at τ = 3.65 (published band 3.5 – 4.1) |
|---|---|---|---|---|
| 1 | 99.5 | 424.9 | 23.5 | 8,139 |
| **2 (design)** | **199** | **315.8** | **19.0** | **10,904** (10,456 – 12,248) |
| 3 | 298.5 | 281.7 | 17.2 | 12,209 |
| 4 | 398 (exceeds 329) | 271.9 | 16.8 | 12,642 |
| 6 | 597 | 248.6 | 15.7 | 13,810 |

m = 2 is the knee: m = 3 buys 12% for 50% more area. The draft chain is 3 DSpark stages over a 5-row block
plus 5 dependent argmax steps over the 129,280-row vocabulary (lm_head row, rank-256 Markov bias, argmax, one
group collective). At m = 2 it is **19.0 µs, 6% of the cycle**.

With and without MTP, both machines, at τ = 3.65 (baseline; plain (b) in the last row):

| | 200K, no MTP | 200K, with MTP | 1M, no MTP | 1M, with MTP |
|---|---|---|---|---|
| ROM array (baseline; m = 2) | 5,418 | 10,904 | 4,933 | **9,500** |
| HBM comparator (iso logic area; m = 6) | 942 | 1,228 | 926 | 1,221 |
| ROM : HBM | 5.75× | 8.9× | 5.33× | **7.8×** |
| ROM array, plain (b) (m = 2) | 4,933 | 9,982 | 4,528 | 8,793 |

## 8. Batch: rate per user, throughput and energy (one model with §7)

Batching uses the same `price()` as speculation. Users × positions share weight reads, routed experts cost
their union across users and positions, and KV and index keys are per user.

- **Batch policy (pipeline fill):** with 28 layer-group stages, b < 28 users ride one per stage, and b ≥ 28
  share each stage in microbatches of b/28.
- **Energy:** `configs/hardware/technology.json` per-format op energies, ROM read plus operand delivery or
  HBM at 104.9 pJ/B, the clock at 8.5 × 10⁻¹¹ J/mm²/cycle on the spec's block area, and the validated link
  energy (`technology.json` energy.link_j_per_bit).
  "Gated" clocks only the stage holding the token, which makes stage clock gating a power requirement.

### 8.1 1M (headline)

| batch | ROM tok/s/user | ROM array tok/s | ROM mJ/token (gated) | ROM + MTP tok/s/user | HBM tok/s/user | HBM array tok/s | HBM mJ/token (gated) | HBM + MTP tok/s/user |
|---|---|---|---|---|---|---|---|---|
| 1 | 4,933 | 4,933 | 36.0 | 9,500 | 926 | 926 | 1,430 | 1,192 |
| 8 | 4,933 | 39,465 | 29.8 | 9,500 | 926 | 7,408 | 1,397 | 1,192 |
| 16 | 4,933 | 78,930 | 29.4 | 6,443 | 679 | 10,867 | 1,395 | 1,192 |
| 28 | 2,867 | 80,272 | 29.4 | 3,736 | 388 | 10,867 | 1,395 | 967 |
| 64 | 1,282 | 82,061 | 27.7 | 1,665 | 388 | 24,819 | 828 | 522 |
| 128 | 653 | 83,591 | 27.4 | 842 | 276 | 35,384 | 723 | 306 |
| 256 | 328 | 84,036 | 26.9 | 425 | 163 | 41,792 | 561 | 177 |
| 512 | 165 | 84,385 | 26.6 | 215 | 89 | 45,399 | 483 | 109 |
| 1,024 | 83 | 84,525 | 26.4 | 107 | 48 | 48,857 | 416 | 69 |

The HBM MTP column uses m = 2 here, the batch model's single design point; §7 gives HBM at m = 6.

### 8.2 200K

| batch | ROM tok/s/user | ROM array tok/s | ROM mJ/token (gated) | ROM + MTP tok/s/user | HBM tok/s/user | HBM array tok/s | HBM mJ/token (gated) | HBM + MTP tok/s/user |
|---|---|---|---|---|---|---|---|---|
| 1 | 5,418 | 5,418 | 19.6 | 10,904 | 942 | 942 | 1,413 | 1,212 |
| 28 | 5,418 | 151,695 | 13.4 | 9,347 | 388 | 10,867 | 1,379 | 1,064 |
| 64 | 3,056 | 195,577 | 11.7 | 4,286 | 388 | 24,819 | 812 | 629 |
| 256 | 911 | 233,278 | 10.9 | 1,130 | 234 | 59,993 | 545 | 239 |
| 1,024 | 232 | 237,086 | 10.4 | 292 | 76 | 77,791 | 400 | 116 |

Batch-1 energy per token without gating at 1M: ROM 362 mJ (clock 333 mJ), HBM 2,327 mJ (weights 1,367 mJ); at
200K 317 mJ (clock 304) and 2,296 mJ. Every die clocks every cycle while only one layer group works, so
**idle-stage clock gating is a requirement**. Gated, the ROM token at batch 1 is 36.0 mJ at 1M, **39.7× below
HBM** (19.6 mJ and 72.0× at 200K).

These rows are bound by the busiest pipeline stage (`arch_budget_v41.stage_bound`), the same basis the design
point uses. At the specification's widths, with no split scan, the busiest stage is S14, which holds layer 20's
whole index scan: 4.5× the mean stage's work at 1M saturated and 2.1× at 200K.

- **Where the batch-1 rate stops.** At 1M it holds up to 16 users. At 200K it holds up to the 28-user fill.
- **Where the array saturates.** At 1M it saturates at 84K tokens/s with 512 users. The 1,024-user row, 85K, is
  beyond the 866 users the HBM holds after the 0.9 capacity reserve, so it is flagged `fits_capacity: false`.
  At 200K the array saturates at 237K with 1,024 users.
- **The HBM comparator** reaches 49K (78K at 200K) at 1,024 users.
- **MTP gains shrink with batch,** because the verify pass's extra positions compete for the lanes that other
  users' tokens use.

These are the specification's widths. The adopted design point relieves S14 by the split scan and the stage
rebalancing, and it saturates higher: 273K at 1M and 436K at 200K. §8.4 gives the record-bound ladder from these
rows to the design point. Before 2026-09-28 these rows used the stage mean (359K at 1M, 473K at 200K), which is
why they used to sit above the design point's.

### 8.3 Target context: 1M

| ROM : HBM | 200K | 1M |
|---|---|---|
| per-user rate, with MTP (τ = 3.65) | 9.00× | **7.97×** |
| per-user rate, without MTP | 5.75× | **5.33×** |
| energy per token, batch 1, gated | 72.0× | **39.7×** |
| array throughput, batch 64 (busiest stage) | 7.88× | **3.31×** |
| array throughput, saturated (busiest stage) | 3.05× | **1.86×** |

The two throughput ratios are specification-width ratios with both machines bound by the busiest stage. At 1M
the ROM array's S14 is bound by layer 20's unsplit HBM key stream, which both machines stream at the same
per-die bandwidth. The adopted design point splits that scan (§8.4).

1M is the headline by user decision (2026-09-27: the default context of most agent APIs). The ratio rule the
spec used before, the largest ROM:HBM per-user rate with MTP, then without, would still pick 200K
(`target_context.ratio_rule_pick`): the context-dependent cost is the indexer's key scan plus its KV, both
machines hold it in HBM, stream it at the same per-die bandwidth and pay for it equally, and the ROM advantage
is in the weight path, which does not grow with context, so a longer context dilutes it.

### 8.4 From the specification to the adopted design point (record-bound ladder)

The specification (§1-§6, this record) and the adopted design point (`results/arch/v41_lanes.json`
`design_point`, the atlas headline) are one machine at two stages of the same ladder, priced by the same
`price()` and on the same occupancy basis (the busiest pipeline stage). Each row adds its lever to the row above;
batch 1, autoregressive, tokens/s per user. Every cell is bound to the record that produces it.

| # | step (cumulative) | record | 1M | 200K |
|---|---|---|---|---|
| 0 | required spec: 264,960 <!-- figure: 264,960 src="results/arch/arch_budget_v41.json#required_spec.weight_macs" name="V4.1 spec weight MAC lanes" --> weight MAC lanes, 41,664 <!-- figure: 41,664 src="results/arch/arch_budget_v41.json#required_spec.bf16_macs" name="V4.1 spec BF16 MAC lanes" --> BF16, 1,024 <!-- figure: 1,024 src="results/arch/arch_budget_v41.json#required_spec.su_lanes" name="V4.1 spec stream-unit lanes" --> stream-unit lanes, sequencer gap 5 <!-- figure: 5 src="results/arch/arch_budget_v41.json#required_spec.seq_gap" name="V4.1 spec sequencer gap" -->, 1.0339 GHz <!-- figure: 1.0339 src="results/arch/arch_budget_v41.json#clock_hz" scale="1e-9" name="V4.1 spec clock" -->, m = 1 | `arch_budget_v41.json` `required_priced` | 4,933 <!-- figure: 4,933 src="results/arch/arch_budget_v41.json#required_priced.1048576.tokens_s_per_user" name="V4.1 spec rate 1M" --> | 5,418 <!-- figure: 5,418 src="results/arch/arch_budget_v41.json#required_priced.200000.tokens_s_per_user" name="V4.1 spec rate 200K" --> |
| 1 | + chain levers L1-L3 (online softmax, chaining for every unit, shorter stages), spec widths | `arch_budget_v41.json` `chain_ladder[4]` | 6,555 <!-- figure: 6,555 src="results/arch/arch_budget_v41.json#chain_ladder[4].1048576.tokens_s_per_user" name="V4.1 chain ladder step 3, 1M" --> | 6,992 <!-- figure: 6,992 src="results/arch/arch_budget_v41.json#chain_ladder[4].200000.tokens_s_per_user" name="V4.1 chain ladder step 3, 200K" --> |
| 2 | + pooled engines and the adopted communication levers (R-U2..R-U8), HC 5,120 lanes per weight lane: the latency ladder's start | `v41_latency_ladder.json` `ladder[key=start]` | 7,038 <!-- figure: 7,038 src="results/arch/v41_latency_ladder.json#ladder[key=start].1048576.rom.ar" name="V4.1 ladder start 1M" --> | 7,548 <!-- figure: 7,548 src="results/arch/v41_latency_ladder.json#ladder[key=start].200000.rom.ar" name="V4.1 ladder start 200K" --> |
| 3 | + four-wide lm_head BF16 engine | `ladder[key=wide_head]` | 7,184 <!-- figure: 7,184 src="results/arch/v41_latency_ladder.json#ladder[key=wide_head].1048576.rom.ar" name="V4.1 ladder wide head 1M" --> | 7,715 <!-- figure: 7,715 src="results/arch/v41_latency_ladder.json#ladder[key=wide_head].200000.rom.ar" name="V4.1 ladder wide head 200K" --> |
| 4 | + uncapped index scans split over 8 dies | `ladder[key=idx_split]` | 7,420 <!-- figure: 7,420 src="results/arch/v41_latency_ladder.json#ladder[key=idx_split].1048576.rom.ar" name="V4.1 ladder idx split 1M" --> | 7,717 <!-- figure: 7,717 src="results/arch/v41_latency_ladder.json#ladder[key=idx_split].200000.rom.ar" name="V4.1 ladder idx split 200K" --> |
| 5 | + sequencer gap 5 → 2 cycles | `ladder[key=seq_gap2]` | 7,576 <!-- figure: 7,576 src="results/arch/v41_latency_ladder.json#ladder[key=seq_gap2].1048576.rom.ar" name="V4.1 ladder seq gap 1M" --> | 7,886 <!-- figure: 7,886 src="results/arch/v41_latency_ladder.json#ladder[key=seq_gap2].200000.rom.ar" name="V4.1 ladder seq gap 200K" --> |
| 6 | + fast-FP formulas, matrix-engine tree on the 3-cycle add, radix-4 divider (three rungs); one Sinkhorn unit per verified position (MTP only) | `ladder[key=sinkhorn_per_position]` | 7,784 <!-- figure: 7,784 src="results/arch/v41_latency_ladder.json#ladder[key=sinkhorn_per_position].1048576.rom.ar" name="V4.1 ladder fast-FP rungs 1M" --> | 8,118 <!-- figure: 8,118 src="results/arch/v41_latency_ladder.json#ladder[key=sinkhorn_per_position].200000.rom.ar" name="V4.1 ladder fast-FP rungs 200K" --> |
| 7 | + core clock 1.034 → 1.087 GHz | `ladder[key=clock_1087]` | 8,068 <!-- figure: 8,068 src="results/arch/v41_latency_ladder.json#ladder[key=clock_1087].1048576.rom.ar" name="V4.1 ladder clock 1M" --> | 8,434 <!-- figure: 8,434 src="results/arch/v41_latency_ladder.json#ladder[key=clock_1087].200000.rom.ar" name="V4.1 ladder clock 200K" --> |
| 8 | + pooled engines ×2 inside the envelope (R-L8): the ladder's top | `ladder[key=widths_x2]` | 8,635 <!-- figure: 8,635 src="results/arch/v41_latency_ladder.json#ladder[key=widths_x2].1048576.rom.ar" name="V4.1 ladder top 1M" --> | 9,055 <!-- figure: 9,055 src="results/arch/v41_latency_ladder.json#ladder[key=widths_x2].200000.rom.ar" name="V4.1 ladder top 200K" --> |
| 9 | + the layer die's registered on-die wire (ASAP7 routed-wire model) and the adopted stage rebalancing (layer 20's keys over S14, S13, S12), collectives' bytes still overlap-assumed | `v41_lanes.json` `ladder_top_overlap_assumed` | 7,362 <!-- figure: 7,362 src="results/arch/v41_lanes.json#ladder_top_overlap_assumed.1048576.ar" name="V4.1 ladder top with wire, 1M" --> | 7,610 <!-- figure: 7,610 src="results/arch/v41_lanes.json#ladder_top_overlap_assumed.200000.ar" name="V4.1 ladder top with wire, 200K" --> |
| 10 | + the package's 112G lanes split TP 52 <!-- figure: 52 src="results/arch/v41_lanes.json#best_split.tp" name="V4.1 TP lanes per package" --> / stage 14 <!-- figure: 14 src="results/arch/v41_lanes.json#best_split.stage" name="V4.1 stage lanes each way" -->, every collective's bytes priced per link | `v41_lanes.json` `best_split` | 7,374 <!-- figure: 7,374 src="results/arch/v41_lanes.json#best_split.1048576.ar" name="V4.1 best lane split 1M" --> | 7,623 <!-- figure: 7,623 src="results/arch/v41_lanes.json#best_split.200000.ar" name="V4.1 best lane split 200K" --> |
| 11 | + the collective tails measured in the RTL stage bench (gate C7), no collective levers | `v41_lanes.json` `design_point_no_levers` | 6,592 <!-- figure: 6,592 src="results/arch/v41_lanes.json#design_point_no_levers.1048576.ar" name="V4.1 measured tails no levers 1M" --> | 6,803 <!-- figure: 6,803 src="results/arch/v41_lanes.json#design_point_no_levers.200000.ar" name="V4.1 measured tails no levers 200K" --> |
| 12 | + the adopted collective levers: **the design point** | `v41_lanes.json` `design_point` | **7,049** <!-- figure: 7,049 src="results/arch/v41_lanes.json#design_point.1048576.ar" name="V4.1 design point 1M" --> | **7,286** <!-- figure: 7,286 src="results/arch/v41_lanes.json#design_point.200000.ar" name="V4.1 design point 200K" --> |

Two single-lever ablations of row 12 separate what row 9 adds together. Without the on-die wire the design point
would run at 8,246 <!-- figure: 8,246 src="results/arch/v41_lanes.json#on_die_wire.design_point_pre_wire.1048576.ar" name="V4.1 design point without wire 1M" -->
(8,568 <!-- figure: 8,568 src="results/arch/v41_lanes.json#on_die_wire.design_point_pre_wire.200000.ar" name="V4.1 design point without wire 200K" --> at 200K),
so the wire costs about 15%. Without the stage rebalancing it runs at 7,009 <!-- figure: 7,009 src="results/arch/v41_stage_rebalance.json#scenarios.baseline.batch1.1048576.ar" name="V4.1 design point without rebalance 1M" -->
at 1M. At 200K the rebalancing costs nothing (7,286 <!-- figure: 7,286 src="results/arch/v41_stage_rebalance.json#scenarios.baseline.batch1.200000.ar" name="V4.1 design point without rebalance 200K" -->),
because its helper groups engage only from position 400,000. At batch 1 the rebalancing is a small latency
term. Its purpose is the busiest stage: it takes that stage down to a level the liquid limit holds at every
operating point (§6 item 12).

**The saturated aggregates on one basis.** The specification and the design point now both bound every operating
point by the busiest pipeline stage (`arch_budget_v41.stage_bound`; the record's `occupancy_basis`). The two
saturated aggregates therefore order as the ladder does:

- **Specification (§8.1-§8.2).** No split scan and no rebalancing, so its busiest stage is S14, which holds layer
  20's whole index scan. That stage carries 4.5× the mean stage's work at 1M saturated and 2.1× at 200K. The
  spec saturates at 84K tokens/s at 1M with 512 users and at 237K at 200K with 1,024 users.
- **Design point.** It saturates at 273K <!-- figure: 273 src="results/arch/v41_lanes.json#energy.1048576.sat1024.rom.aggregate_tokens_s" scale="0.001" name="V4.1 design point saturated aggregate 1M" -->
  at 1M with the 866 users the HBM holds, and 436K <!-- figure: 436 src="results/arch/v41_lanes.json#energy.200000.sat1024.rom.aggregate_tokens_s" scale="0.001" name="V4.1 design point saturated aggregate 200K" -->
  at 200K.

Before this change the specification's rows used the stage mean, which gave 359K (1M) and 473K (200K). Those
figures were higher than the design point's, and a reader had to be told why. That difference was a difference
of basis, not of machine.

One step of the specification still uses the stage mean: the batch-64 width derivation (`budget.*_b64`, and
`requirement.headline.tokens_s_per_user_b64` as its target). On the busiest-stage basis, the 1M batch-64
requirement is bound by S14's unsplit HBM key stream, and no engine width relieves that. Widening every engine to
about 318 mm² still misses the target. The design point relieves S14 by the split scan (row 4) and the
rebalancing (row 9), not by width. That is why the widths in row 0 stay the stage-mean derivation's.

## 9. HBM comparator specification (equal total logic area)

**Configuration.** The ROM array spends 188 dies × 328.9 mm² = 61,836 mm² on compute. The comparator spends
the same on logic-only dies: the same 815 mm² die with the ROM area freed, keeping interconnect and overhead,
with 4 HBM3E stacks per die (the ROM die's package limit; the beachfront allows five) and 628.3 mm² of logic.

- **99 dies** in about 24 tensor groups of 4.
- 8.9 TB of HBM, against 510 GB of weights.
- **3.6 TB/s sustained per die**: a 90% efficiency requirement, measured with refresh on.

At 1M the comparator gives 926 tokens/s per user on the baseline links (942 at 200K; 914 / 929 on plain (b);
arch_budget_v41.json plain_b.hbm_ar). Its weight sweep is 881 µs of the 1,080 µs token (1,062 µs at 200K).

| sustained efficiency | 75% | 85% | 90% | 95% |
|---|---|---|---|---|
| tokens/s/user, 1M | 794 | 883 | 926 | 968 |
| tokens/s/user, 200K | 807 | 898 | 942 | 985 |

Requirements:

- **Prefetch window.** 3.6 MB per die, which is latency × bandwidth at 1 µs first access. Every static-address
  stream (dense weights, window rows) is issued that far ahead across every dependency point.
- **Routed-expert fetch.** The hard part. The expert ids exist only after the router's top-6, so a layer's
  28.2 MB per die of expert bytes is exposed: first access plus bytes, **8.8 µs per layer on the critical
  path**. With MTP the fetch is the union (34.6 experts at B = 6), which caps HBM's speculative gain at 1.3×
  (γ = 5, τ = 3.65, m = 6).
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
5. **Hyper-connection projection** at 5,120 lanes per weight lane, and the **Engram per-bank gather** at a 256-bit port.
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
/ 160.8 µs at 8K / 200K / 1M. The replay record is at the spec widths it was run with
(`v41x_replay.json` `spec`: an earlier derivation, 231,936 / 31,360 / 34,176 weight / BF16 / attention MACs,
2,048 HC lanes); it has not been re-run on the unified spec, so its columns are not re-derived here.

| context | replayed spec, baseline links (38.5 µs comm) | budget, baseline | target, baseline | replayed, plain (b) (55.6 µs) | target, plain (b) |
|---|---|---|---|---|---|
| 8K | 5,789 | 5,532 | 4,922 | 5,270 | 4,522 |
| 200K | 5,616 | 5,418 | 4,837 | 5,126 | 4,450 |
| 1M | 5,015 | 4,933 | 4,599 | 4,621 | 4,249 |

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
- **Energy.** Link energy is `technology.json` energy.link_j_per_bit (0.5 pJ/bit UCIe, 6.5 pJ/bit 112G board
  SerDes; validated 2026-09-27, `results/arch/power_assumptions.json`). The clock term is `technology.json`'s,
  charged on the spec's block area.
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
| 0 | the spec on the baseline links | 184.6 | 5,532 / 5,418 / 4,933 | 99.5 mm² |
| 1 | reductions off the critical path: online softmax | 179.9 | 5,680 / 5,560 / 5,051 | 99.5 mm² |
| 1x | norm folding as well (REJECTED) | 162.1 | 6,288 / 6,168 / 5,547 | 99.5 mm² |
| 2 | + tile/row chaining for every unit (on step 1) | 157.1 | 6,440 / 6,367 / 6,011 | 99.5 mm² |
| 3 | + shorter stages | **143.0** | **7,083 / 6,992 / 6,555** | 99.5 mm² |
| 4a | + attention on one package, spec widths | 144.5 | 7,114 / 6,922 / 6,086 | 99.5 mm² |
| 4b | + attention on one package, attention/indexer/weight engines ×2 | 126.7 | 8,151 / 7,893 / 6,824 | 180 mm² |
| 4c | the same engines ×2, attention kept on the four-die group | 132.9 | 7,629 / 7,524 / 7,020 | 180 mm² |
| 5 | MTP m = 2, τ = 3.65, on step 3 | 267.0 per cycle | **13,963 / 13,672 / 12,516** | 199 mm² |

1. **Reductions off the critical path (−4.7 µs).** The attention softmax becomes online: exp streams behind
   the scores with a running-max rescale, as the release's own sparse-attention kernel does in 64-row blocks
   (`hdc_golden_v41` `vendor_blocks`). Fused SiLU·mul and the hyper-connection/Sinkhorn side branch are
   already in the graph. **This is a contract change:** the golden must adopt it (an R-ARITH v2), and the ISA
   and RTL follow, with the token re-checked against the oracle as in §4. **Norm folding is rejected**
   (row 1x, user decision 2026-09-27): scaling the next matvec's outputs by an RMSNorm's rstd instead of its
   input would take the sum of squares and the rsqrt off the path (−22 µs), but it moves the point where the
   activation is quantised to FP8, so it is not the checkpoint's arithmetic.
2. **Chaining for every unit (−22.8 µs).** Matvecs, the attention and indexer scans and the local selects start
   on their producer's first tile or row instead of its last element. This extends the vector unit's
   per-vector credits to the ME/QE, attention, indexer and select outputs. The weight sweep on the path
   falls from 26 to 14 µs because each matvec now overlaps its producer.
3. **Shorter stages (−14.1 µs).** The stream unit's base depth drops to 21 cycles (29 in the DAG) and its reducer
   tail to 25 (32). Beyond the spec's exp and sigmoid, rsqrt goes to 58 cycles (90) and sqrt(softplus) to 161
   (259); the vector-unit agent measured these depths. The chain floor is already chunk-of-8 plus the tree,
   on 3-cycle adds.
4. **Collectives and hops: fewer tensor-parallel boundaries (not adopted).** Keeping attention and its
   projections on the two dies of one package halves the attention collectives' latency on the path (26 →
   13 µs). But it doubles each die's attention, indexer and projection work.
   - At the spec's widths this is a net loss: 6,922 against 6,992 tok/s at 200K, and 6,086 against 6,555
     at 1M.
   - With those engines doubled it gains 7% at 8K and 5% at 200K over spending the same area without the
     move (step 4c), and loses 3% at 1M, the headline context, where the doubled index scan dominates.
   - The attention stays on the four-die group.
   - What remains of the collective term (26 µs) is link latency after the last partial. In-package
     reduction is already the one-shot engine's first level. The next lever is in-network reduction, which
     removes the package-pair round trip, or a shorter pair link. The substrate module is +12.5% but not
     shippable (the packaging agent's study).
5. **MTP on top (×1.9).** On step 3 the m = 2 core verifies 6 positions in 248.0 µs plus a 19.0 µs draft per
   cycle. At the measured τ = 3.65 that is **12,516 tok/s per user at 1M** (13,672 at 200K), against 9,500
   (10,904) with MTP on the spec alone.

Levers 1-3 are the integration requirements for `ot_hdc_core_v41x`:
- lever 1 is a golden/ISA/RTL contract change;
- lever 2 is the chaining protocol on every unit boundary;
- lever 3 is the vector unit's measured depths.

Doubling the engines (step 4c, +8% at 200K and +7% at 1M for +80 mm²) stays inside the 329 mm² envelope. It is the next
width lever if the silicon falls short. Every number in this section is the model's, on the report's DAG,
not silicon.
