# Fully pipelined token decode on ASAP7: review and optimization plan

Date: 2026-09-23. Scope: an end-to-end RTL decode of one token, datapath and
control, simulated at token level and implemented on the ASAP7 PDK at a high
clock. This document records the review of the current designs, the plan, and,
in its log section, each iteration's measurements.

## 1. Review of the current designs

### Targets and what decodes a token today

| Target | Token-level RTL today | Clock evidence |
|---|---|---|
| Qwen3 reduced, ROM (ABI 3.0) | `ot_a3_shipped_prefix_top` runs the full reduced decode program: 248/248 instructions, 7,901,003 cycles | Slowest instantiated blocks route at 58 MHz (`matmul_bf16_sram_engine`), 70 MHz (`a3_qwen_gqa`), 75 MHz (`a3_microsequencer_dep_depth`) |
| DeepSeek V4.1 reduced, ROM array/wafer (ABI 3.0) | Deployment builds; engines partly integrated; no end-to-end token in RTL | Supporting engines 190–520 MHz |
| ROM redesign mechanisms | Striped banks, package link, layer pipeline (functional, `rtl/rom/`) | Link endpoint routes at 1,339 MHz |
| Prototype compute tile | `ot_compute_unit` (16 lanes) | 1,290 MHz closed, but shares no module with the token path |

The ABI 3.0 machine is a general programmable accelerator. It has a descriptor
control plane, a microsequencer, an admission bridge and engines with IEEE
arithmetic. Its measured problems are structural:

1. **One MAC per cycle.** `ot_a3_engine_array` retires one multiply-accumulate
   per cycle; a 64-lane tile is written but not instantiated.
2. **Unpipelined arithmetic.** A single combinational FP32 add is a ~6.25 ns path
   on ASAP7, capping a block near 160 MHz. Several engines still contain them.
3. **General control costs clock.** The same 16 lanes route at 1,290 MHz alone
   and 226 MHz inside the G2 cluster with its control plane: 5.7× of clock.
4. **Cycle count.** 7.9 M cycles for a 1.28 M-MAC reduced token: about six cycles
   of control and service per MAC.

At its 58 MHz limiter, the reduced Qwen3 token takes ~136 ms in the ABI 3.0 RTL.
The fast pieces already exist in isolation: FP32 add and multiply pipes (1.4 GHz),
the MAC tile (1.2 GHz), a square root (1.36 GHz), the block-max unit (1.7 GHz).

## 2. Design decision

Build a **model-specific, fully pipelined decode core** for the ROM machine, the
design the [analytical report](ANALYTICAL_REPORT.md) recommends. The ABI 3.0
machine remains the general HBM-side vehicle.

- **Datapath.** W parallel MAC lanes. Each lane is a pipelined FP32 multiply
  followed by a pipelined FP32 add, and interleaves I ≥ adder latency + 1
  outputs. Every lane therefore retires one MAC per cycle, while each output
  still accumulates its K products in order (sequential FP32 RNE per output).
  Weights stream from ROM, W per cycle; activations broadcast.
- **Special functions.** Exponential, reciprocal and reciprocal square root are
  fixed pipelines of FP32 multiply/add stages: range reduction plus a
  polynomial, and Newton-Raphson from a bit-level seed. No combinational IEEE
  operation and no iterative divider sits on any path.
- **Reductions.** Sums of squares, softmax sums and maxima use a fixed
  interleaved-partial-plus-tree order, so they are deterministic and pipelined.
- **Control.** A static schedule of macro-operations (matrix-vector, norm, RoPE,
  attention head, activation, residual, argmax) in a small ROM. Registered
  address generators and a single-issue sequencer: no descriptors, no
  admission, no microcode interpretation on the critical path.
- **Memory.** Weight ROM and KV SRAM sit behind simple ports. The simulation
  top supplies behavioural arrays; the physical top leaves them as ports or
  macros.
- **Numerics.** Stated, not inherited:
  - BF16 weights, activations rounded to BF16 at matrix inputs (exact FP32
    products), FP32 accumulation and FP32 elementwise work;
  - the special-function algorithms above;
  - a Python golden model emulating every operation in the same order with
    NumPy float32, so the RTL must match it bit for bit.

  The decoded token is also compared with the project's torch reference oracle.

## 3. Plan

| Step | Deliverable | Gate |
|---|---|---|
| P1 | Golden model of the reduced Qwen3 decode step in the RTL's arithmetic order; prefill KV for the oracle's 16-token prompt | Golden decodes the oracle's first token (1073) |
| P2 | Pipelined arithmetic units: MAC lane, exponential, reciprocal, reciprocal square root, max/argmax | Bit-exact against the golden per unit; each routes at or above 1 GHz on ASAP7 |
| P3 | Matrix-vector engine (W lanes × interleave) and vector/norm/RoPE/softmax units | Bit-exact on real layer data |
| P4 | Static control sequencer and core top; simulation top with weight ROM and KV SRAM | One-token decode in Verilator bit-exact with the golden; token 1073 |
| P5 | ASAP7 synthesis and place-and-route of the core, clock sweep | Routed Fmax, area, cycles per token, tokens/s |
| P6 | Iterate on the measured limiter: lane count, overlap of vector work with matrix work, control fan-out, critical paths | Each change re-verified at P4 and re-measured at P5 |

## 4. Iteration log

Entries are appended as measurements land.

**P1 (done).** `tools/hdc_golden.py` specifies the arithmetic. With the
oracle's 16-token prompt it decodes 1073, 382, 93: the torch oracle's three
tokens. The first token's logit margin is 0.865 against 0.830. Exponential,
reciprocal and reciprocal square root are within 2.4×10⁻⁷ relative error
(≈2 ulp). Test: `tests/test_hdc_golden.py`.

The golden now composes every operation from `add` and `mul`, the qualified
pipes' semantics: IEEE RNE with gradual underflow, and every zero result
canonical +0. It still decodes 1073.

**P2.** `rtl/hdc/ot_hdc_sfu.sv` holds three pipelines built from the
qualified FP32 pipes: exponential (depth 92), reciprocal (46) and reciprocal
square root (61). Each accepts one operand per cycle. Golden vectors checked: 18,010. <!-- figure: 18010 src="results/rtl/hdc_iterations/iter1_baseline.json#sfu.vectors" name="HDC special-function vectors checked" -->
All match bit for bit, fed with random bubbles.

Routed alone at a 1 ns target, the SFU units land just under 1 GHz. The path
is always the multiplier's single-stage full significand product, which iteration 3
rebalances.

- reciprocal: 988 MHz; <!-- figure: 988 src="results/physical_abi3/asap7/hdc/ot_hdc_recip/physical.json#place_and_route.metrics.fmax_hz" scale="1e-6" name="HDC reciprocal routed fmax" -->
- rsqrt: 949 MHz. <!-- figure: 949 src="results/physical_abi3/asap7/hdc/ot_hdc_rsqrt/physical.json#place_and_route.metrics.fmax_hz" scale="1e-6" name="HDC rsqrt routed fmax" -->

With iteration 3's rebalanced multiplier, re-routed at 0.8 ns:

- exp: 1,196 MHz; <!-- figure: 1196 src="results/physical_abi3/asap7/hdc/ot_hdc_exp_rebalanced_mul/physical.json#place_and_route.metrics.fmax_hz" scale="1e-6" name="HDC exp routed fmax, rebalanced multiplier" -->
- reciprocal: 1,223 MHz; <!-- figure: 1223 src="results/physical_abi3/asap7/hdc/ot_hdc_recip_rebalanced_mul/physical.json#place_and_route.metrics.fmax_hz" scale="1e-6" name="HDC reciprocal routed fmax, rebalanced multiplier" -->
- rsqrt: 1,210 MHz. <!-- figure: 1210 src="results/physical_abi3/asap7/hdc/ot_hdc_rsqrt_rebalanced_mul/physical.json#place_and_route.metrics.fmax_hz" scale="1e-6" name="HDC rsqrt routed fmax, rebalanced multiplier" -->

**P3–P4 (done).** The core has four parts:

- `ot_hdc_matvec`: 16 lanes × 8 interleaved outputs; the sum circulates in the
  adder pipeline;
- `ot_hdc_stream`: a 2-D element loop through a fixed
  multiply/add/special-function/multiply pipeline, plus a segmented reducer;
- `ot_hdc_core`: the sequencer;
- a program from `tools/hdc_program.py`, with the format in `tools/hdc_isa.py`:
  178 instructions. <!-- figure: 178 src="results/rtl/hdc_iterations/iter1_baseline.json#parameters.program_instructions" name="HDC program length" -->

The program is first run on an ISA-level model, which is bit-exact with the
golden. In Verilator the RTL decodes token 1073 at position 15.

- Cycles per token: **107,228**. <!-- figure: 107228 src="results/rtl/hdc_iterations/iter1_baseline.json#single_step.cycles" name="HDC cycles per token, first iteration" -->
- Every logit, the whole vector memory and the whole KV cache match bit for bit.
- From an empty KV cache it consumes the 16-token prompt, writing its own KV
  rows, and generates 1073, 382, 93: the torch oracle's tokens.
- Cycles on which the matrix engine issues: 90,112. <!-- figure: 90112 src="results/rtl/hdc_iterations/iter1_baseline.json#single_step.me_issue_cycles" name="HDC matrix-engine issue cycles" -->
- Cycles on which the stream unit issues: 11,729. <!-- figure: 11729 src="results/rtl/hdc_iterations/iter1_baseline.json#single_step.su_issue_cycles" name="HDC stream-unit issue cycles" -->
- Cycles on which neither issues: 5,387. <!-- figure: 5387 src="results/rtl/hdc_iterations/iter1_baseline.json#single_step.both_units_idle_cycles" name="HDC cycles with neither unit issuing" -->

Record: `results/rtl/hdc_decode_campaign.json`, from
`tools/rtl_hdc_decode_campaign.py`.

Each iteration's campaign record is kept in `results/rtl/hdc_iterations/`.
`results/rtl/hdc_decode_campaign.json` is the current one.

**Iteration 2: attention batching, fused sums of squares, chaining.** None of
these changes alters the arithmetic.

- *Attention.* The matrix engine now takes an x element per slot
  (`xbase + k*xks + j*xjs`), a slot-shifted weight stride (`(j >> jsh)*js`),
  output strides and a lane-mask mode. All eight heads of a layer are one
  scores op and one weighted-sum op: each slot is a head, and it shares the KV
  words of its group. That replaces 16 ops of 128+ cycles each.
- *Norms.* The op that produces x (embedding, residual add) also reduces
  x·x through a squaring stage in front of the reducer. The separate
  sum-of-squares pass of every hidden-size norm is gone.
- *Chaining.* A matrix-vector op whose only hazard is the preceding stream
  op's output starts when that op writes its first element, not when it
  drains. It reads x[k] no sooner than k·8 cycles after starting, so it cannot
  overtake the writer.

Results:

- program: 113 instructions, 13 of them chained; <!-- figure: 113 src="results/rtl/hdc_iterations/iter2_attention_batch_chaining.json#parameters.program_instructions" name="HDC program length, iteration 2" -->
- cycles per token: **95,590**; <!-- figure: 95590 src="results/rtl/hdc_iterations/iter2_attention_batch_chaining.json#single_step.cycles" name="HDC cycles per token, iteration 2" -->
  every logit, the vector memory and the KV cache are still bit-exact;
- matrix-engine issue cycles: 82,944; <!-- figure: 82944 src="results/rtl/hdc_iterations/iter2_attention_batch_chaining.json#single_step.me_issue_cycles" name="HDC matrix-engine issue cycles, iteration 2" -->
  the weight matrices account for about 82K of them.

The limiter is now the 16-lane matrix engine, and only more lanes move it. At
hidden size 128, a lane count above 16 needs outputs × 8 interleave ≥ lanes × 8,
which the 128-row matrices cannot supply. Iteration 3 therefore splits K for
narrow matrices: a deterministic change to the accumulation order, specified in
the golden.

**Iteration 3: four lane groups, K-split, exact BF16 lanes, rebalanced
multiplier.**

*Lane groups.* The matrix engine now has four groups of 16 lanes, 64
multiply-accumulates per cycle. A matrix with few rows cannot fill every
output slot, so its K range is cut into S contiguous chunks. Each chunk is
summed in order in its own group, and a pipelined pairwise tree adds the chunk
sums. The split is chosen per matrix for the fewest cycles (`split_for`):
S = 2 for QKV and gate/up, 4 for o_proj and down, 1 for lm_head.

*Numerics.* The split changes the accumulation order. The golden specifies it
(`matvec(w, x, split)`), and the golden still decodes the oracle's tokens.

*Multipliers.*

- Group 0 keeps full binary32 multipliers and alone serves the FP32 attention
  ops.
- Groups 1–3 use `ot_hdc_bmul`, an exact BF16 × BF16 multiplier. It equals the
  qualified pipe wherever it does not refuse; it refuses (fails closed) only
  where a product would need rounding or is nonfinite.
- The FP32 multiplier is a stage-rebalanced copy of the qualified pipe. Three
  byte-wide partial products and both exponent decisions sit in stage 2; the
  sum and a two-way select sit in stage 3. Edge-biased vectors on which it is
  cycle-equivalent: 20,000,000. <!-- figure: 20000000 src="results/rtl/hdc_iterations/iter3_groups_ksplit.json#multipliers.vectors" name="multiplier equivalence vectors" -->
  Routed alone on ASAP7 at a 0.7 ns target:
  - rebalanced FP32 multiplier: 1,275 MHz; <!-- figure: 1275 src="results/physical_abi3/asap7/hdc/ot_hdc_fp32_mul_pipe/physical.json#place_and_route.metrics.fmax_hz" scale="1e-6" name="rebalanced FP32 multiplier routed fmax" -->
  - qualified FP32 multiplier: 1,052 MHz; <!-- figure: 1052 src="results/physical_abi3/asap7/hdc/ot_fp32_mul_rne_pipe/physical.json#place_and_route.metrics.fmax_hz" scale="1e-6" name="qualified FP32 multiplier routed fmax" -->
  - FP32 adder: 1,447 MHz. <!-- figure: 1447 src="results/physical_abi3/asap7/hdc/ot_fp32_add_rne_pipe/physical.json#place_and_route.metrics.fmax_hz" scale="1e-6" name="FP32 adder routed fmax" -->

*Chaining.* A split matrix does not chase its producer, because chunk c reads
x[c·kc] on its first step.

Results:

- cycles per token: **36,950**; <!-- figure: 36950 src="results/rtl/hdc_iterations/iter3_groups_ksplit.json#single_step.cycles" name="HDC cycles per token, iteration 3" -->
  bit-exact, and 1073, 382, 93 are still generated end to end;
- matrix-engine issue cycles: 21,504; <!-- figure: 21504 src="results/rtl/hdc_iterations/iter3_groups_ksplit.json#single_step.me_issue_cycles" name="HDC matrix-engine issue cycles, iteration 3" -->
- stream-unit issue cycles: 10,577; <!-- figure: 10577 src="results/rtl/hdc_iterations/iter3_groups_ksplit.json#single_step.su_issue_cycles" name="HDC stream-unit issue cycles, iteration 3" -->
- cycles with neither unit issuing: 4,972. <!-- figure: 4972 src="results/rtl/hdc_iterations/iter3_groups_ksplit.json#single_step.both_units_idle_cycles" name="HDC idle cycles, iteration 3" -->

The stream unit and the drains now take about as many cycles as the matrix
engine. Iteration 4 targets them.

**Iteration 4: fused SiLU·up, progress-threshold chaining.**

- *Fused SiLU·up.* A sigmoid SFU class computes 1/(exp(R)+1), chaining the
  exponential, one adder and the reciprocal (depth 143). A final multiply
  stage takes B, so `(g · sigmoid(g)) · up` is one stream op instead of three.
- *Chaining by progress.* Both units now report the progress of their latest
  op: elements written, or result slots produced. Any op whose only hazards
  are reads of the other unit's in-flight main writes waits for a threshold,
  not a barrier. The program generator derives the threshold from the
  producer's write order and the consumer's read order, so no read overtakes
  its write:
  - a split matrix op starts once its producer has written far enough;
  - the down projection starts after 33 elements of the last SiLU op;
  - stream ops that read engine results start when the slots they need exist.
- *Overlap of SiLU with gate/up.* Gate and up rows are interleaved by output
  tile, so each engine round yields matching gate/up rows. SiLU runs on round
  r while the engine computes round r+1.

Results:

- cycles per token: **32,212**; <!-- figure: 32212 src="results/rtl/hdc_iterations/iter4_sigmoid_progress_chaining.json#single_step.cycles" name="HDC cycles per token, iteration 4" -->
  bit-exact, and 1073, 382, 93 are still generated end to end;
- stream-unit issue cycles: 7,505. <!-- figure: 7505 src="results/rtl/hdc_iterations/iter4_sigmoid_progress_chaining.json#single_step.su_issue_cycles" name="HDC stream-unit issue cycles, iteration 4" -->

The matrix engine is now compute-bound at 64 multiply-accumulates per cycle,
and lm_head is the largest single op.

**Iteration 5: region refinement; a negative result; lane scaling.**

- *RoPE regions.* The RoPE halves write disjoint halves of the query and key
  rows. Tracking them as separate regions removes two barriers per layer, and
  the V row now goes to the cache right after the QKV op.
  Cycles per token: 32,084. <!-- figure: 32084 src="results/rtl/hdc_iterations/iter5_rope_regions_g8_scaling.json#single_step.cycles" name="HDC cycles per token, iteration 5" -->
- *Negative result: prefetching sequencer.* A sequencer that fetches and
  decodes the next instruction during the current one's wait was built,
  verified, measured and reverted. It saved no cycles: every wait it could
  hide is already a pipeline drain longer than the fetch.
- *Scaling point: 8 lane groups (128 lanes).* The split plan becomes 4/8/4/8/1,
  and the golden still decodes the oracle's tokens. The token is bit-exact
  against its own ISA-level model.
  - cycles per token: **22,418**; <!-- figure: 22418 src="results/rtl/hdc_iterations/iter5_rope_regions_g8_scaling.json#scaling_8_groups.cycles" name="HDC cycles per token, 8 groups" -->
  - matrix-engine issue cycles: 11,264. <!-- figure: 11264 src="results/rtl/hdc_iterations/iter5_rope_regions_g8_scaling.json#scaling_8_groups.me_issue_cycles" name="HDC matrix-engine issue cycles, 8 groups" -->

  Four groups stay the default: they are the configuration being routed.
  Beyond eight groups the stream unit and the short-vector latency chains
  (norms, head norms, softmax) dominate this hidden-size-128 vehicle.

**P5: stream unit on ASAP7.** Routed alone at a 1 ns target, the stream unit
(iteration 4) met every register-to-register path; the worst had +32.85 ps of
slack. The only violation was its combinational fault OR into an output port.
Fault is a sticky status bit, so both units now register it in two levels.
Re-routed at a 0.85 ns target:

- routed Fmax: **1,111 MHz**; <!-- figure: 1111 src="results/physical_abi3/asap7/hdc/ot_hdc_stream/physical.json#place_and_route.metrics.fmax_hz" scale="1e-6" name="HDC stream unit routed fmax" -->
- cell area: 35,300 µm². <!-- figure: 35300 src="results/physical_abi3/asap7/hdc/ot_hdc_stream/physical.json#synthesis.cell_area_um2" name="HDC stream unit cell area" -->

It routed with no DRC or design-rule violations. The critical path is stage 3
of the rebalanced multiplier (the partial-product sum and select), so the two
product stages are now close to balanced.

**ROM array: a layer-per-package pipeline of decode cores.** This is the
array the analytical report proposes, now as token-level RTL
(`rtl/test/tb_hdc_array.sv`, `tools/rtl_hdc_array_campaign.py`).

- *Packages.* Package n is an `ot_hdc_core` running only layer n's program
  (`hdc_program.py --stages`). It has its own vector memory and a KV SRAM
  slice per user. Package 0 also does the embedding.
- *Links.* The 128-float hidden state crosses `ot_rom_pkg_link` (a 60-cycle
  stand-in for the PHY) as one header and 8 data flits. They land in the next
  package's vector memory as they arrive. The last package returns the token.
- *Control.* Each package's control is the synthesizable `ot_rom_pkg_ctrl`
  (docs/ROM_ARRAY_FABRIC_RTL.md), not testbench code: message framing, core
  start/done, per-user context, the argmax reduction and token feedback at
  package 0. Only the memories stay behavioural.
- *Exactness.* Splitting the program at layer boundaries is exact. A package
  that receives X opens with its sum of squares, the same arithmetic the fused
  residual performed.

Every user starts from an empty KV cache, runs the oracle's prompt through the
array and generates 1073, 382, 93. The links never stalled.

| Packages / users | Cycles per token-step | Busy per step (layer packages / last) |
|---|---|---|
| 4 / 4 (lm_head on layer 3's package) | 14,510 | 5,911 / 14,264 |
| 5 / 5 (lm_head alone) | 8,809 | 5,911 / 8,547 |
| 6 / 6 (lm_head split by vocabulary) | 6,174 | 5,911 / 4,451 and 4,140 |
| 10 / 10 (layers split into attention and MLP packages) | 4,616 | 2,962 and 3,143 / 4,451 and 4,140 |
| 12 / 12 (as 10, lm_head split over four packages) | 3,306 | 2,962 and 3,143 / 2,403, then 2,092 each |

- 4 / 4 aggregate speed-up over one core: 2.219× <!-- figure: 2.219 src="results/rtl/hdc_array_campaign.json#configurations[packages=4,users=4].aggregate_speedup_vs_single_core" name="HDC array 4-package aggregate speed-up" -->
- 5 / 5 aggregate speed-up over one core: 3.655× <!-- figure: 3.655 src="results/rtl/hdc_array_campaign.json#configurations[packages=5,fabric=p2p].aggregate_speedup_vs_single_core" name="HDC array 5-package aggregate speed-up" -->
- 5 / 5 cycles per token-step: 8,809. <!-- figure: 8808.8 src="results/rtl/hdc_array_campaign.json#configurations[packages=5,fabric=p2p].cycles_per_token_step" name="HDC array 5-package cycles per token step" -->

- 6 / 6 aggregate speed-up over one core: 5.214× <!-- figure: 5.214 src="results/rtl/hdc_array_campaign.json#configurations[packages=6,users=6,fabric=p2p].aggregate_speedup_vs_single_core" name="HDC array 6-package aggregate speed-up" -->

In the 6-package array lm_head is split by vocabulary:

- The first lm_head package does the final norm and rows 0–2047. It sends the
  normalised state with its best {row, logit}.
- The second does rows 2048–4095 and keeps its own best only when it is
  strictly greater, so a tie keeps the lower row, as numpy's argmax does.

- 10 / 10 aggregate speed-up over one core: 6.975× <!-- figure: 6.975 src="results/rtl/hdc_array_campaign.json#configurations[packages=10,fabric=p2p].aggregate_speedup_vs_single_core" name="HDC array 10-package aggregate speed-up" -->

The 10-package array also splits every layer at the residual after o_proj,
into an attention package and an MLP package. That cut is as exact as a layer
boundary: the MLP package opens with the sum of squares of the X it receives.

- 12 / 12 aggregate speed-up over one core: 9.739× <!-- figure: 9.739 src="results/rtl/hdc_array_campaign.json#configurations[packages=12,users=12,fabric=p2p].aggregate_speedup_vs_single_core" name="HDC array 12-package aggregate speed-up" -->

With more than two lm_head packages, each one carries the running best
{row, logit} forward and replaces it only when strictly greater.

Per-user latency stays near one core's, as a layer pipeline should.
Throughput is set by the slowest package. At 12 packages the pipeline is
balanced: the MLP half-layer package (about 3.1K cycles) limits.

Through a switch (`ot_rom_fabric_router`), the last body package can instead
multicast its hidden state to every lm_head package at once. Each part then
applies the final norm and its rows in parallel, and package 0 reduces their
results. That shortens one user's token step, from 34,045 to 27,529 cycles at
12 packages, but barely changes the throughput of a full pipeline, which the
MLP package still limits. See docs/ROM_ARRAY_FABRIC_RTL.md.

## 5. Toward a single-reticle Qwen3-8B chip

`tools/hdc_timing.py` is a cycle model of the core. It covers the sequencer,
the two units, barriers, chases, class drains and the reducer tail. Its
constants were fitted to the RTL's issue trace. It matches the RTL's token
within 0.5% (a test enforces this) and every issue time within a few cycles.
It needs only the program's shapes, so it can price Qwen3-8B (hidden 4096,
36 layers, 32/8 heads of 128, FFN 12288, vocabulary 151,936), which the RTL
simulator cannot reach. The attention op now batches heads 8 at a time, one
per slot, for models with more heads than slots.

At position 1,024 the as-built core scales poorly with lanes. At 16,384 lanes
attention takes 77% of the token and the stream unit 21%. Attention runs only
on group 0's 16 FP32 lanes, and the stream unit retires one element per cycle.
The timing model's projection options price the two fixes the chip needs:

| Qwen3-8B, 16,384 lanes, position 1,024 | Cycles per token |
|---|---|
| as built | 24.7 M |
| stream unit 16 elements per cycle | 19.9 M |
| attention spread over all groups | 7.0 M |
| both | 2.18 M |

The weight work alone is about 0.46 M cycles at that width. The Qwen3-8B
reticle therefore needs three things:

1. KV-sourced ops that give every lane group its own heads and KV words;
2. a vector-wide stream unit (reductions then need a wider partial order,
   specified in the golden);
3. several engines on the die in a layer pipeline, with users in flight, as
   the array already proves.

Those are the next RTL iterations for that target.

**Iteration 6: BF16 KV cache, attention on every lane group, one lane type.**

- *Numerics* (a spec change, in the golden). The KV cache holds BF16, and q
  and the softmax probabilities are rounded to BF16 before their products.
  That is the common serving choice, and the golden still decodes the oracle's
  tokens. It makes every matrix-engine product an exact BF16 × BF16 product.
- *Lanes.* All 64 lanes now use the small exact BF16 multiplier. Group 0's
  FP32 multipliers are gone.
- *Attention.* KV-sourced ops spread over all groups: group g takes context
  tile r·G + g through its own KV port. At the vehicle's position 15 the
  context is one tile, so the token is unchanged (32,196 cycles).
- *Long-context check.* The prompt cycled to 60 tokens exercises all four
  groups. The RTL is bit-exact against the ISA model in every logit, the
  vector memory and the KV cache.
  That token took 37,828 cycles. <!-- figure: 37828 src="results/rtl/hdc_iterations/iter6_bf16_kv_attention_all_groups.json#long_context.cycles" name="HDC cycles at position 59" -->
- *Effect on Qwen3-8B* (timing model, re-checked against the RTL on the
  vehicle). At 16,384 lanes and position 1,024, 24.7 M cycles per token become
  8.2 M. The next limits are the weighted sum over positions, whose K is the
  whole context, and the one-element stream unit.
