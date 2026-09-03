# ABI 3.0 engine datapaths in RTL

**Checklist item:** W8.3
**Status:** eleven `(family, subopcode)` pairs are implemented and correlated,
including six bounded VECTOR additions; the rest of the engine surface is not,
and none of these datapaths is wired to the microsequencer
**Evidence class:** `public_open_tool_rtl_simulation` (functional), plus a
separate open-PDK physical view that carries its own boundary
**Primary artifacts:**
`results/rtl/abi3_engine_campaign.json` (functional correlation),
`testdata/compiler/abi3_engine/abi3_engine_vectors.json` (the vector set),
`results/physical_abi3/sky130hd/{a3_selection_argmax,a3_vector_add,a3_dma_index_mover}/physical.json`
(routed), `results/physical_abi3/sky130hd/a3_mac_lane/prelayout.json`,
`results/physical_abi3/sky130hd/a3_numeric_probes/*.json`

---

## 1. Why this exists, and what it is not

W8.1 and W8.2 built the ABI 3.0 control plane — microsequencer, loop stack,
view resolver, event scoreboard, state controller — and W8.6 correlated it
against the functional simulator over 64 generated programs on two simulators.
W8.8 then re-ran the same control plane on the **shipped deployment images**
(`results/rtl/abi3_deployment_campaign.json`), where both Qwen3-8B deployments,
the DeepSeek-V4-Flash ROM wafer deployment, and the DeepSeek-V4-Flash HBM
32-node cluster deployment correlate exactly at whole-transaction depth; which
shipped deployments that campaign covers is its own `correlated_cases` field.
Both campaigns bind **every engine to a recording no-op**, on purpose, and say
so in their own limitations: *no engine arithmetic is modelled on either side.*
So the sequence is verified — on all four shipped deployments, at
whole-transaction depth — and the arithmetic is not.

This item is the other half. It does not replace the control-plane campaign and
it is not wired to it: the two are correlated separately, and **nothing here
shows that a resolved operand view drives the addresses these datapaths read.**
That integration is still open, and the deployment campaign measures how far
apart the two halves are: the shipped programs issue 38 distinct
`(family, subopcode)` pairs, and only a handful of those have datapath RTL here
at all — none of it driven by the sequencer. That campaign's `engine_coverage`
field carries the current split.

**What the routed numbers in §7 may and may not claim.** They are the
implementation cost of these datapath blocks in an open 130-nm PDK, and nothing
about the sequencer, which has never been synthesised or routed
(`docs/UNIFIED_EXECUTION_CHECKLIST.md`, [OI-43]). And a number resting on ABI
3.0 RTL may be presented as the cost of hardware that runs exactly the
deployments `results/rtl/abi3_deployment_campaign.json` → `correlated_cases`
records, and no others. The current artifact records both Qwen3-8B deployments,
the DeepSeek-V4-Flash ROM wafer deployment, and the DeepSeek-V4-Flash HBM
32-node cluster deployment; at commit `518260f` it recorded only the Qwen
builds. That is a restriction on the sentence a number may
appear in, not on the number: every measurement below stands exactly as
recorded.

## 2. Which datapaths, and why these

The selection criterion was: *which datapath, if it were wrong, would change a
published result rather than a cycle count* — and *which is not already covered
by an existing evidence class*.

| Datapath | Why it carries weight |
|---|---|
| `TENSOR.MATMUL` | Every contraction in both models. It is the arithmetic the whole program is about, and the ASAP7 physical run that exists synthesised blocks whose own boundary says they implement *signed integer datapaths only* — not this |
| `DMA.GATHER` / `DMA.SCATTER` | Every weight byte and every KV byte that moves. The executed simulator's strongest evidence is **byte counts**; this is the block that produces them, and its two failure modes — a clamped index and a lost read-back — are both silent |
| `SELECTION.ARGMAX` | The token itself. `[OI-33]` is a single argmax flip at generated index 137 that ended the 8,000-token run's oracle identity. The tie rule — *lowest token ID among the maxima* — is a property of one comparison, and getting it backwards still looks like a maximum |
| `VECTOR.ADD` | The residual, at every layer boundary, with the closed-form `bf16_add_rne_v1` contract |
| bounded `VECTOR.CONVERT`, `SCALE` and `HADAMARD` | Storage conversion, scalar/elementwise scaling and the released DeepSeek normalized 128-point transform, without inventing transcendental approximations |
| bounded `VECTOR.INDEX_SCORE`, `COMPRESS` and `MHC` | The released DeepSeek learned-index, projection and hyper-connection forms, including their packing and matrix-orientation contracts |

Seven of the thirteen VECTOR subopcodes now dispatch in this engine array:
`ADD` plus the following six explicitly bounded forms. The exact same scope is
machine-readable as `correlation.vector_rtl_scope` in the retained campaign;
an out-of-bound or unsupported sub-case is refused with `ERR_SHAPE`.

| opcode | correlated form and bound | explicitly not correlated |
|---|---|---|
| `CONVERT` | Unscaled, one input and one output, 1–512 elements; supported identity copies or finite numeric input converted to BF16/FP32 | Block dequantization; two-output block quantization |
| `SCALE` | BF16-to-BF16, 1–512 elements; constant (`aux0=0`) or same-shape elementwise (`aux0=1`) | Logistic sigmoid (`aux0=2`); general trailing-axis broadcasting |
| `HADAMARD` | Normalized 128-point BF16 transform, 1–4 rows | Widths other than 128 or more than four rows |
| `INDEX_SCORE` | BF16 learned-index score, batch one, exactly four heads, scale exactly 1.0, 1–4 sites, 1–8 candidates and 1–16 head channels | Non-unit scale; other head counts; batches greater than one |
| `COMPRESS` | `COMPRESS_PROJECT` (`aux0=0`), 1–8 flattened rows, 1–16 outputs and 1–64 reduction channels; packed KV-then-gate FP32 output | `COMPRESS_POOL`; `COMPRESS_STATE_UPDATE` |
| `MHC` | `HYPER_CONNECT_POST` (`aux0=1`), 1–4 flattened sites, 1–32 hidden channels and exactly four streams | `HYPER_CONNECT_PRE`; `HYPER_CONNECT_HEAD`; multipliers other than four |

The boundary is still substantial. `SILU_MUL`, `SOFTMAX` and
`SQRT_SOFTPLUS` are wholly deferred because correctly rounded
exponential/logarithm/square-root RTL does not exist here; no approximation is
substituted. Standalone `RMS_NORM`, `HEAD_RMS_NORM` and `ROPE` RTL exists but
remains outside this engine array and this correlation. ATTENTION, ROUTE,
REDUCTION, LINK and STATE have no datapath here. Within otherwise covered
families, `TENSOR.GROUPED_MATMUL`, `ROUTED_MATMUL` and `EMBED_LOOKUP`,
`DMA.TRANSFER` and `FILL`, and `SELECTION.TOKEN_APPEND` are also absent.
`SELECTION.SAMPLE` has no governed contract on either side.

## 3. What the correlation actually compares

Every vector is a **real ABI 3.0 program**: built with
`runtime.abi3.builder.DeploymentBuilder`, admitted by `runtime.abi3.verifier`,
and executed by `runtime.sim.device.Device` with the **real** engines in
`runtime.sim.engines` — `tensor`, `dma`, `vector`, `selection`. Nothing is
stubbed. The operand images are the bytes each resolved operand view held at
the issue, read back out of device memory; the expected image is the bytes the
engine wrote. Generator: `tools/build_abi3_engine_vectors.py`.

Two independently written checkers replay the same images through the same RTL:
`rtl/test/tb_a3_engine.sv` under Icarus and `rtl/test/a3_engine_harness.cpp`
under Verilator. Neither reads the other's expectations. Each counts what it
actually compared and refuses to print the marker unless its own counts equal
the totals the image declares, so the marker is not an echo of the image.

The marker both simulators print, identically:

```
PASS: ABI3 RTL engine datapaths cases=135 families=11 results=14468 macs=59868 faults=92 decodes=2576 arith=5200
```

Its parts, each re-readable from the campaign artifact:

| quantity | value |
|---|---:|
| cases replayed | 135 <!-- figure: 135 src="results/rtl/abi3_engine_campaign.json#correlation.case_count" name="engine RTL cases" --> |
| of which refusals | 92 <!-- figure: 92 src="results/rtl/abi3_engine_campaign.json#correlation.fault_case_count" name="engine RTL fault cases" --> |
| distinct (family, subopcode) pairs | 11 <!-- figure: 11 src="results/rtl/abi3_engine_campaign.json#correlation.family_count" name="engine RTL families" --> |
| result words compared, per simulator | 14468 <!-- figure: 14468 src="results/rtl/abi3_engine_campaign.json#correlation.result_word_count" name="engine RTL result words" --> |
| multiply-accumulates the correlated contractions perform | 59868 <!-- figure: 59868 src="results/rtl/abi3_engine_campaign.json#correlation.mac_count" name="engine RTL MACs" --> |
| storage-format decode probes | 2576 <!-- figure: 2576 src="results/rtl/abi3_engine_campaign.json#correlation.decode_probe_count" name="engine RTL decode probes" --> |
| binary32 arithmetic probes | 5200 <!-- figure: 5200 src="results/rtl/abi3_engine_campaign.json#correlation.arith_probe_count" name="engine RTL arithmetic probes" --> |
| checks per simulator | 40878 <!-- figure: 40878 src="results/rtl/abi3_engine_campaign.json#checks_per_simulator.iverilog" name="engine RTL checks per simulator" --> |

The campaign fails if the two simulators print the same marker after a
different number of comparisons, because that is not two checks of one thing.

Compared, per case: every element the engine wrote **word for word**; the
engine's own result, work and saturation counters, including the distinct
site-by-head-by-candidate-by-depth work count for `INDEX_SCORE`; the packed
KV-then-gate order of `COMPRESS_PROJECT`; the source/destination matrix
orientation of `HYPER_CONNECT_POST`; selection vocabulary and tie counts; DMA
movement counts; the selected token; and, for a refusal, the fault class *and*
that the whole destination window still holds the unwritten sentinel — so **a
partial result is a failure, not a pass.**

### Coverage that is worth naming

* **Contraction contract.** `bf16_bf16_fp32_sequential_rne_v1` — exact
  products, strictly ascending-K binary32 accumulation, one RNE output
  rounding — reproduced for **BF16 × BF16**, **FP8 E4M3FN × FP8 E4M3FN**, and
  the block-scaled **MXFP4 E2M1 × FP8 E4M3FN** pair the released DeepSeek MoE
  ships. Amendment A15's two-dimensional scale block (one E8M0 code per 4 × 32
  weight tile) is a case of its own, because an A8-only reader addresses it
  wrongly and every shape still agrees.
* **The reduction order itself.** Two cases are built so their *BF16 output*
  distinguishes ascending-K from any other association — see 4.3, which is why
  they exist. One is on the frozen BF16 kernel's path and one on
  `runtime.sim.backend`'s, because those are two separate implementations of
  one contract.
* **Both reference schedules.** `runtime.sim.backend` switches the sequential
  contraction from its K-last schedule to its K-major one at 8,192 output
  elements. One case sits exactly at that tile, so the RTL checks the contract's
  claim that the two schedules agree bit for bit against the *other* schedule.
* **Storage-format decode, exhaustively.** All 256 E4M3FN codes, all 16 E2M1
  nibbles, all 256 E8M0 codes, and every BF16 exponent with four significands
  and both signs — 2,576 probes against `runtime.sim.formats`, whose tables are
  enumerated at import from the exact `fractions.Fraction` decoders in
  `runtime/reference/formats.py`.
* **The six newly integrated VECTOR forms.** Directed and seeded cases cover
  conversion identities and rounding, constant and same-shape scaling,
  Hadamard normalization, `INDEX_SCORE`'s ReLU/reduction tree,
  `COMPRESS_PROJECT`'s KV-then-gate packing, and `HYPER_CONNECT_POST`'s
  combination-matrix orientation. Each form also has an explicit late-poison
  case; the complete destination must remain unwritten even when the bad value
  is in the final operand position.
* **The binary32 arithmetic, on the distribution that breaks it.** The 135
  engine cases exercise the adder and the multiplier on the values real
  operands produce — normals of moderate exponent, mostly of one magnitude —
  which is where a rounding or normalisation defect is least likely to show. A
  separate sweep of 5,200 cases walks the other distribution: the full cross
  product of a 36-code corner set (both zeros, both smallest subnormals, the
  largest subnormal, the smallest normal, 2²⁴ where a unit ulp disappears, the
  largest finite, both signs of each) plus a seeded spread over BF16-widened
  codes, general binary32 including the nonfinite band, and the subnormal
  range. The authority is `runtime.reference.formats.binary32_add`,
  `binary32_multiply`, `binary32_bits_to_bf16_rne` and
  `binary32_product_add`, which compute with `fractions.Fraction` and round
  once, so **no host floating-point mode participates on the reference side.**
* **The tie rule, three ways.** A unique maximum; three logits sharing the
  maximum (the token must be 17, not 201, and the multiplicity 3); and a
  maximum that appears as both `+0` and `−0`, which compare equal in binary32
  and must therefore key equal.
* **Scatter read-back.** The destination starts from real bytes, seeded by a
  `DMA.TRANSFER` the same program issues, so a scatter that never read the
  destination back cannot pass. A repeated index resolves to the later slot.
* **Ninety-two refusals**: 17 Device faults <!-- figure: 17 src="results/rtl/abi3_engine_campaign.json#correlation.refusal_count_by_expectation_source.device_fault" name="engine RTL Device refusals" --> whose classes are derived from the functional
  engine's actual `EngineError`; 18 one-above-bound or unsupported-form
  refusals <!-- figure: 18 src="results/rtl/abi3_engine_campaign.json#correlation.refusal_count_by_expectation_source.rtl_bounded_profile" name="engine RTL bounded-profile refusals" -->; and 57 independently corrupted descriptor-admission cases <!-- figure: 57 src="results/rtl/abi3_engine_campaign.json#correlation.refusal_count_by_expectation_source.rtl_descriptor_admission" name="engine RTL descriptor-admission refusals" -->.
  The latter two groups start from programs the general Device successfully
  executes and require the bounded RTL to return `ERR_SHAPE` before any operand
  read or destination write. All 92 cases prove the entire destination remains
  untouched.

## 4. Four things this found

### 4.1 One simulator silently disagreed with the other

Under **Icarus 11**, a wildcard-imported package identifier that appears *only*
inside a module-instance port-connection expression is not resolved against the
import. Icarus creates an implicit one-bit net of that name instead, and that
net then shadows the constant **for the whole module**. `DMA_SCATTER` read as
`z`, every `DMA.SCATTER` dispatched as unimplemented, and `DMA_GATHER` — which
never appears in a port connection — kept working. Three of the twenty-nine cases the set held
at the time failed and twenty-six passed. **Verilator resolved the constant correctly**, so
the two simulators disagreed about the same source text, and the two-simulator
rule is the only reason it was visible at all.

Every engine RTL file now refers to package members as `pkg::name` and carries
no `import`. `tests/compiler/test_rtl_abi3_engine.py::test_engine_rtl_carries_no_wildcard_package_import`
pins that shut. The same change is what makes these blocks synthesisable: the
pinned Yosys 0.68 Verilog frontend rejects `import` in a module header and in a
module body alike, so a wildcard import is a block that cannot be routed at all.

### 4.2 The binary32 *adder* is the critical path, not the multiplier

Each operation was synthesised alone as one combinational cloud between an
input port and one register — `rtl/test/ot_a3_numeric_probes.sv` — and run
through the governed physical driver on SKY130 HD `tt_025C_1v80` with the
pinned Yosys 0.68 + ABC mapping and OpenSTA. Artifacts:
`results/physical_abi3/sky130hd/a3_numeric_probes/*.json`.

| operation | cells | cell area (µm²) | min clock period (ns) | Fmax (MHz) |
|---|---:|---:|---:|---:|
| `ot_fp32_rne_pkg::fp32_add_rne` | 2014 <!-- figure: 2014 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_add.json#synthesis.cell_count" name="fp32 add cells" --> | 13868.7 <!-- figure: 13868.7 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_add.json#synthesis.cell_area_um2" name="fp32 add cell area" --> | **66.97** <!-- figure: 66.97 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_add.json#static_timing.fmax_search.min_clock_period_ns" name="fp32 add min period" --> | 14.93 <!-- figure: 14.93 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_add.json#static_timing.fmax_search.fmax_hz" scale="1e-6" name="fp32 add fmax" --> |
| `ot_fp32_rne_pkg::fp32_mul_rne` | 5165 <!-- figure: 5165 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_mul.json#synthesis.cell_count" name="fp32 mul cells" --> | 33660.4 <!-- figure: 33660.4 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_mul.json#synthesis.cell_area_um2" name="fp32 mul cell area" --> | 29.385 <!-- figure: 29.385 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_mul.json#static_timing.fmax_search.min_clock_period_ns" name="fp32 mul min period" --> | 34.03 <!-- figure: 34.03 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_mul.json#static_timing.fmax_search.fmax_hz" scale="1e-6" name="fp32 mul fmax" --> |
| `ot_fp32_rne_pkg::fp32_to_bf16_rne` | 129 <!-- figure: 129 src="results/physical_abi3/sky130hd/a3_numeric_probes/bf16_round.json#synthesis.cell_count" name="bf16 round cells" --> | 1224.9 <!-- figure: 1224.9 src="results/physical_abi3/sky130hd/a3_numeric_probes/bf16_round.json#synthesis.cell_area_um2" name="bf16 round cell area" --> | 3.84 <!-- figure: 3.84 src="results/physical_abi3/sky130hd/a3_numeric_probes/bf16_round.json#static_timing.fmax_search.min_clock_period_ns" name="bf16 round min period" --> | 260.31 <!-- figure: 260.31 src="results/physical_abi3/sky130hd/a3_numeric_probes/bf16_round.json#static_timing.fmax_search.fmax_hz" scale="1e-6" name="bf16 round fmax" --> |
| `ot_a3_format_pkg::decode_element` (all formats) | 145 <!-- figure: 145 src="results/physical_abi3/sky130hd/a3_numeric_probes/format_decode.json#synthesis.cell_count" name="decode cells" --> | 1531.5 <!-- figure: 1531.5 src="results/physical_abi3/sky130hd/a3_numeric_probes/format_decode.json#synthesis.cell_area_um2" name="decode cell area" --> | 2.62 <!-- figure: 2.62 src="results/physical_abi3/sky130hd/a3_numeric_probes/format_decode.json#static_timing.fmax_search.min_clock_period_ns" name="decode min period" --> | 381.38 <!-- figure: 381.38 src="results/physical_abi3/sky130hd/a3_numeric_probes/format_decode.json#static_timing.fmax_search.fmax_hz" scale="1e-6" name="decode fmax" --> |

The period is not the raw logic delay: the driver's SDC charges 20% of the
clock period as input delay and 20% as output delay, so a probe's period
carries that overhead too. What the comparison rests on is the *ratio* under an
identical SDC, corner and mapping — **the adder needs 2.28× the multiplier's
period while costing 41% of its cell area.** The adder is much cheaper to build
and much slower to run, and it is what sets the MAC lane's period.

The cause is structural, not technological: `fp32_add_rne` normalises a
cancellation with a 27-iteration loop whose iterations are *dependent* —

```verilog
for (shift_count = 0; shift_count < 27; shift_count = shift_count + 1)
    if (!arithmetic_extended[26] && (large_exponent > 1)) begin
        arithmetic_extended = arithmetic_extended << 1;
        large_exponent      = large_exponent - 1'b1;
    end
```

which synthesises to twenty-seven conditional one-bit shifts and twenty-seven
exponent decrements in series. A leading-zero count followed by a single barrel
shift is functionally identical and far shorter. `shift_right_jam_28`'s
28-iteration sticky reduction has the same shape.

**This has not been changed here.** `rtl/ot_fp32_rne_pkg.sv` is shared with the
ABI 2.5 production blocks, and physical campaigns over those blocks were in
flight while this was measured; editing a shared numeric package under another
campaign's feet is how a correlated artifact quietly stops matching its
sources. It is reported, with the measurement, for whoever owns that file. Any
rewrite must re-run this campaign, which is exactly the check that would catch
a rewrite that changed a result bit.

### 4.3 The mutation that shaped the vectors, and the retained mutation gate

A campaign that passes proves nothing until something makes it fail. During the
original exploratory pass, five deliberate defects were injected into the RTL
and replayed against the vector set:

| injected defect | caught |
|---|---|
| `SELECTION.ARGMAX` replaces its running best on an *equal* key, so the highest tied ID wins instead of the lowest | yes — token 40 where 9 is required |
| The MAC lane stops canonicalising an exact-zero product before accumulation | **no** |
| `DMA.SCATTER` stops reading the destination back, so unnamed rows are lost | yes — a row left unwritten |
| The MAC lane ignores amendment A15's `scale_block_rows`, reading scales as an A8 one-dimensional block | yes |
| The reduction runs descending in K instead of ascending | **no**, until two cases were added |

**The missed zero-canonicalisation is a true no-op**, checked rather than
waved away: the only consumer of `product` is `fp32_add_rne`, that function
canonicalises every zero *result*, and `x + (−0.0)` and `x + (+0.0)` agree for
every `x` it can produce. So no vector can distinguish it, and the
canonicalisation is kept for fidelity to the written contract rather than
because a test demands it.

**The missed reduction order was a real gap and it is the important one.**
Reordering a binary32 reduction perturbs the accumulator by about one part in
2²⁴, and the output rounds to BF16, which resolves one part in 2⁸. On ordinary
operands the two orders therefore produce the *same BF16 code at every output*:
in `matmul_bf16_tile_edge`, 147 of 585 accumulators differ in binary32 and
**none** of them differ after the output rounding. The campaign was checking
the products, the accumulation width and the output rounding of
`bf16_bf16_fp32_sequential_rne_v1` — and not the ordering the contract is named
for.

`matmul_bf16_reduction_order` and `matmul_fp8_reduction_order` close it, one on
each reference code path. Both are catastrophic cancellation with a small
leading term — products `(2ʲ, 2³⁰, −2³⁰)` — so ascending absorbs the small term
into the large one and returns exactly zero, while any order that cancels first
returns it whole. With them, the descending-K mutation fails at case 5.

That historical exercise explains the vector design, but it is not merely a
prose recollection now. Every forced campaign run also makes seven exact source
mutations, compiles each changed design independently under both simulators,
and requires checker failure with no PASS marker:

| retained source mutation | first behavior it corrupts |
|---|---|
| flip the low bit of every narrowed `CONVERT` result | BF16 conversion rounding |
| replace the `SCALE` product with binary32 addition | scale arithmetic |
| replace the Hadamard normalization constant with 1.0 | normalized transform |
| propagate negative rounded head scores past the ReLU | `INDEX_SCORE` activation |
| swap the compressor's KV and gate output planes | `COMPRESS_PROJECT` packing |
| split the compressor's exact product-add into separately rounded multiply and add | `COMPRESS_PROJECT` numeric contract |
| transpose the hyper-connection combination lookup | `HYPER_CONNECT_POST` matrix orientation |

All seven compile and are caught by both Icarus and Verilator in the retained
artifact. `mutation_sensitivity.mutations[]` records the exact before/after
text, source digest, compile result, missing marker and first mismatch for each
simulator; `all_caught_by_both_simulators` is true. This is seven real corrupted
RTL builds, not a Python-level perturbation of expected data.

### 4.4 Regeneration caught two functional-engine contract defects

Schema-v2 generation does not blindly bless the Device's output for governed
DeepSeek VECTOR forms. It independently recomputes `INDEX_SCORE`,
`COMPRESS_PROJECT` and `HYPER_CONNECT_POST` with the exact rational references
in `runtime/reference/` and refuses to emit vectors on the first mismatch.

The first source-current regeneration stopped at
`vector_index_score_exact_product_add`: the Device wrote BF16 `0x02be`, while
`runtime.reference.index_score.index_score_bf16` required `0x02bf`. The Device
formed a binary32 product and then added it, rounding twice, although the ABI
3.0 numeric contract requires one correctly rounded `acc + x*w` step. The
engine now shares the compressor's exact-product product-add path. The same
audit found that `INDEX_SCORE` discarded its four BF16 saturation counts and
`HYPER_CONNECT_POST` discarded its output saturation count; both now publish
the existing architectural `vector.saturations` counter. Focused Device tests
pin the one-ulp distinguisher and every saturation boundary.

This is an ABI 3.0 semantic repair, not an ABI extension. It adds no
instruction, descriptor, persistent state, retry or recovery mechanism. It can
change a DeepSeek learned-index score by one BF16 ulp and therefore can change
sparse-KV selection and a downstream token. Accelerator DeepSeek token records
made with the earlier functional source are consequently prior-build evidence
until rerun. Qwen does not issue `INDEX_SCORE` and is not affected by this
numeric correction.

## 5. Physical characterisation

### 5.1 Pre-layout, `ot_a3_mac_lane`

SKY130 HD (`sky130A`, `sky130_fd_sc_hd`, `tt_025C_1v80`), pinned Yosys 0.68 +
ABC + OpenSTA through `tools/run_abi3_physical.py`. Artifact:
`results/physical_abi3/sky130hd/a3_mac_lane/prelayout.json`.

| quantity | value |
|---|---:|
| standard cells | 24224 <!-- figure: 24224 src="results/physical_abi3/sky130hd/a3_mac_lane/prelayout.json#synthesis.cell_count" name="MAC lane cells" --> |
| of which sequential | 462 <!-- figure: 462 src="results/physical_abi3/sky130hd/a3_mac_lane/prelayout.json#synthesis.sequential_cell_count" name="MAC lane flops" --> |
| macros | 0 <!-- figure: 0 src="results/physical_abi3/sky130hd/a3_mac_lane/prelayout.json#synthesis.macro_count" name="MAC lane macros" --> |
| cell area (µm²) | 160516.1 <!-- figure: 160516.1 src="results/physical_abi3/sky130hd/a3_mac_lane/prelayout.json#synthesis.cell_area_um2" name="MAC lane cell area" --> |
| minimum clock period (ns) | 57.39 <!-- figure: 57.39 src="results/physical_abi3/sky130hd/a3_mac_lane/prelayout.json#static_timing.fmax_search.min_clock_period_ns" name="MAC lane min period" --> |
| Fmax (MHz) | 17.42 <!-- figure: 17.42 src="results/physical_abi3/sky130hd/a3_mac_lane/prelayout.json#static_timing.fmax_search.fmax_hz" scale="1e-6" name="MAC lane fmax" --> |
| hold worst slack (ns) | 0.366 <!-- figure: 0.366 src="results/physical_abi3/sky130hd/a3_mac_lane/prelayout.json#static_timing.hold_wns_ns" name="MAC lane hold slack" --> |

**Which path that is, read back rather than inferred.** At a 30 ns target the
worst setup path in the mapped netlist runs from the flop holding `acc[25]`,
through combinational logic, to the flop holding `acc[23]` — the accumulator
register through `fp32_add_rne` and back — with a 56.97 ns arrival and a
−27.10 ns slack. The path's cell composition is a ripple carry chain
(15 `maj3_1`, 15 `xnor2_1`). So the lane's period is the `S_ACC` stage, and
section 4.2 is a measurement of the operation in it, not a guess about which
one binds.


### 5.2 Routed

Full ORFS place-and-route in the pinned container, same view and corner, one
target period each. Every one of the three met setup and hold with **zero DRC
errors and zero antenna violations**.

| | `selection_argmax` | `vector_add` | `dma_index_mover` |
|---|---:|---:|---:|
| target period (ns) | 12 | 100 | 25 |
| status | "pass" <!-- figure: "pass" src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#acceptance.status" name="selection routed status" --> | "pass" <!-- figure: "pass" src="results/physical_abi3/sky130hd/a3_vector_add/physical.json#acceptance.status" name="vector add routed status" --> | "pass" <!-- figure: "pass" src="results/physical_abi3/sky130hd/a3_dma_index_mover/physical.json#acceptance.status" name="dma routed status" --> |
| setup worst slack (ns) | 3.348 <!-- figure: 3.348 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.setup_wns_ns" name="selection routed setup slack" --> | 14.61 <!-- figure: 14.61 src="results/physical_abi3/sky130hd/a3_vector_add/physical.json#place_and_route.metrics.setup_wns_ns" name="vector add routed setup slack" --> | 9.240 <!-- figure: 9.240 src="results/physical_abi3/sky130hd/a3_dma_index_mover/physical.json#place_and_route.metrics.setup_wns_ns" name="dma routed setup slack" --> |
| hold worst slack (ns) | 0.403 <!-- figure: 0.403 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.hold_wns_ns" name="selection routed hold slack" --> | 0.431 <!-- figure: 0.431 src="results/physical_abi3/sky130hd/a3_vector_add/physical.json#place_and_route.metrics.hold_wns_ns" name="vector add routed hold slack" --> | 0.478 <!-- figure: 0.478 src="results/physical_abi3/sky130hd/a3_dma_index_mover/physical.json#place_and_route.metrics.hold_wns_ns" name="dma routed hold slack" --> |
| DRC errors | 0 <!-- figure: 0 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.drc_errors" name="selection DRC errors" --> | 0 <!-- figure: 0 src="results/physical_abi3/sky130hd/a3_vector_add/physical.json#place_and_route.metrics.drc_errors" name="vector add DRC errors" --> | 0 <!-- figure: 0 src="results/physical_abi3/sky130hd/a3_dma_index_mover/physical.json#place_and_route.metrics.drc_errors" name="dma DRC errors" --> |
| antenna violations | 0 <!-- figure: 0 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.antenna_violating_nets" name="selection antenna" --> | 0 <!-- figure: 0 src="results/physical_abi3/sky130hd/a3_vector_add/physical.json#place_and_route.metrics.antenna_violating_nets" name="vector add antenna" --> | 0 <!-- figure: 0 src="results/physical_abi3/sky130hd/a3_dma_index_mover/physical.json#place_and_route.metrics.antenna_violating_nets" name="dma antenna" --> |
| die area (µm²) | 47430.3 <!-- figure: 47430.3 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.die_area_um2" name="selection die area" --> | 122766 <!-- figure: 122766 src="results/physical_abi3/sky130hd/a3_vector_add/physical.json#place_and_route.metrics.die_area_um2" name="vector add die area" --> | 268200 <!-- figure: 268200 src="results/physical_abi3/sky130hd/a3_dma_index_mover/physical.json#place_and_route.metrics.die_area_um2" name="dma die area" --> |
| routed wirelength (µm) | 52983 <!-- figure: 52983 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.routed_wirelength_um" name="selection wirelength" --> | 155596 <!-- figure: 155596 src="results/physical_abi3/sky130hd/a3_vector_add/physical.json#place_and_route.metrics.routed_wirelength_um" name="vector add wirelength" --> | 369697 <!-- figure: 369697 src="results/physical_abi3/sky130hd/a3_dma_index_mover/physical.json#place_and_route.metrics.routed_wirelength_um" name="dma wirelength" --> |
| vias | 13932 <!-- figure: 13932 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.vias" name="selection vias" --> | 44021 <!-- figure: 44021 src="results/physical_abi3/sky130hd/a3_vector_add/physical.json#place_and_route.metrics.vias" name="vector add vias" --> | 71295 <!-- figure: 71295 src="results/physical_abi3/sky130hd/a3_dma_index_mover/physical.json#place_and_route.metrics.vias" name="dma vias" --> |
| total power (mW) | 2.54 <!-- figure: 2.54 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.power_total_w" scale="1000" name="selection routed power" --> | 2.06 <!-- figure: 2.06 src="results/physical_abi3/sky130hd/a3_vector_add/physical.json#place_and_route.metrics.power_total_w" scale="1000" name="vector add routed power" --> | 45.3 <!-- figure: 45.3 src="results/physical_abi3/sky130hd/a3_dma_index_mover/physical.json#place_and_route.metrics.power_total_w" scale="1000" name="dma routed power" --> |

Three things in that table are worth saying out loud.

**The routed Fmax a flow reports is not the pre-layout one improved.**
Place-and-route may resize and buffer for the target period, and it does: the
selection block's 1387 mapped cells <!-- figure: 1387 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#synthesis.cell_count" name="selection mapped cells" --> become 2641 placed instances <!-- figure: 2641 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.standard_cell_count" name="selection placed cells" -->.
What each routed run establishes is that the block closes at *its* target with
real wire parasitics, at the area, wirelength and power shown — not a frequency
comparable to section 4.2's.

**The residual adder is far cheaper in context than in isolation, and that is
not a contradiction.** `ot_a3_vector_add`'s whole pre-layout minimum period is
29.932 ns <!-- figure: 29.932 src="results/physical_abi3/sky130hd/a3_vector_add/physical.json#static_timing.fmax_search.min_clock_period_ns" name="vector add prelayout min period" --> against the standalone `fp32_add_rne` probe's 66.97 ns, and the whole
block is 2291 cells <!-- figure: 2291 src="results/physical_abi3/sky130hd/a3_vector_add/physical.json#synthesis.cell_count" name="vector add mapped cells" --> against the probe's 2014. Both addends here are *widened
BF16*, so their low sixteen bits are constant zero and synthesis specialises
the adder around that. The MAC lane gets no such specialisation, because its
accumulator is a general binary32 value — which is why its period sits near the
general adder's and not near this one's.

**The index mover is the largest of the three**, at 12133 mapped cells <!-- figure: 12133 src="results/physical_abi3/sky130hd/a3_dma_index_mover/physical.json#synthesis.cell_count" name="dma mapped cells" --> and
94481.2 µm² <!-- figure: 94481.2 src="results/physical_abi3/sky130hd/a3_dma_index_mover/physical.json#synthesis.cell_area_um2" name="dma cell area" --> of cells before layout, for a block that moves codes and does no
arithmetic on them. That is the general 32-bit `slot * trailing` and
`row * trailing` address multiplies, and it is the same lesson as 5.4's
dividers: writing an address expression in full generality buys area and delay
for shapes no deployment uses.

### 5.3 The contraction lane's routed run did not produce an artifact

`ot_a3_mac_lane` — 24224 standard cells, by far the largest of the four — was
started through the same flow at a 60 ns target. It completed synthesis,
floorplan, placement and clock-tree synthesis and reached **global routing**;
its driver process was then terminated by the session's task supervisor, so
`run_abi3_physical.py` never wrote its record and no routed artifact exists.

That is not a convergence failure and is not reported as one. What the flow had
established by the time it stopped is that the block does **not** close at
60 ns: the post-CTS repair plateaued at a setup WNS of about −57 ns with the
scale-address register `t_rd_addr[31]` as its endpoint, which is the divider
path of section 5.4 rather than the accumulator path of section 5.1. **The
routed area, wirelength and power of the contraction lane remain unmeasured**,
and a re-run at a period it can meet — 120 ns or more, on the evidence above —
is the outstanding piece of this item.

### 5.4 Two weaknesses of this RTL that the physical run exposes

Neither changes a result bit, and neither is hidden:

* **`scale_index` divides.** The A15 scale address is
  `(row / block_rows) * (depth / block) + (column / block)`, written as integer
  division so that any block size is legal. Two 32-bit dividers is what that
  synthesises to, and at a relaxed ABC delay target they become the block's
  critical path — the routed flow's worst endpoint is the scale-address
  register `t_rd_addr[31]`, not the accumulator. Every block size the two
  models actually ship is a power of two (MXFP4's 32, A15's 4 × 32), so a shift
  is exactly equivalent for every shape that exists and the generality is
  bought at the cost of the period. A future version should require a
  power-of-two block and refuse anything else, which is also the more
  fail-closed reading of the amendment.
* **The lane is five cycles per multiply-accumulate.** One binary32 operation
  per pipeline stage was chosen to keep the timing attributable; it is not a
  throughput target and no cycle count here feeds any model. A design meant to
  perform would pipeline the accumulator recurrence, which is the one stage
  that cannot simply be widened.

### 5.5 What none of section 5 may be used for

**SKY130 is a 130 nm open foundry PDK and is the primary *methodology*
vehicle, not a node proxy.** `docs/OPEN_PDK_SELECTION.md` forbids feature-size
scaling from it, so **no number in this section may be scaled to N6, N5 or N4,
and none of it retires `power.fabric_clock_hz = 1e9` in
`configs/hardware/technology.json`** — that constant stays graded `assumed`.
Nor is any cycle count here a rate: the lane's five-cycle multiply-accumulate is
a sequencing choice, and feeding it to an `engine.<family>.work_per_lane_cycle`
would turn a verification convenience into a performance figure.

What does survive the change of node is the *structure*: the contraction
lane's period is set by one unpipelined binary32 addition written as a serial
shift chain, its scale address by two integer dividers, and the index mover's
area by two general 32-bit multiplies. Those are statements about the design,
and they are true wherever it is built.

## 6. Hard claim boundary

A passing campaign establishes:

* the eleven integrated `(family, subopcode)` pairs in `rtl/abi3/` produce
  **bit-identical** results to the functional simulator's engines on every case
  of this vector set, under two independently written checkers on two
  simulators making the same number of comparisons;
* bounded `CONVERT`, `SCALE`, `HADAMARD`, `INDEX_SCORE`, `COMPRESS_PROJECT` and
  `HYPER_CONNECT_POST` agree in output, fault class and architectural counters
  within the exact scope in section 2;
* seven independent source mutations of those six new datapaths all compile and
  are rejected by both simulators;
* the storage-format decoders are exhaustively correct over E4M3FN, E2M1 and
  E8M0 against the exact `Fraction` reference;
* the binary32 add, multiply and BF16 rounding the datapaths are built from
  agree with `runtime.reference.formats` — exact `Fraction` arithmetic, one
  rounding, no host floating point on the reference side — over a corner
  cross-product and a seeded spread reaching signed zero, both smallest
  subnormals, the largest finite and the nonfinite band;
* refusals agree in class and leave **no** partial result;
* an operation the array does not implement is refused rather than routed to
  whichever datapath happened to be wired up.

It does **not** establish any of the following:

* **the blocked contraction contract.** Only
  `bf16_bf16_fp32_sequential_rne_v1` is correlated. `bf16_bf16_fp32_blocked_rne_v1`'s
  association is the executing implementation's *declared* one, so "bit-exact
  against it" is not a well-posed statement about a different implementation,
  and it is not made;
* **IEEE conformance of the arithmetic package.** The directed sweep samples
  5,200 arithmetic cases from the binary32 and BF16-product-add domains,
  chosen where a rounding or
  normalisation defect is most likely to live. It is directed evidence, not a
  proof;
* **late fault position in the legacy arithmetic blocks.** The six newly
  integrated VECTOR blocks preflight their operands or buffer the complete
  bounded result, and their final-position poison cases prove whole-destination
  atomicity. `TENSOR.MATMUL` and `VECTOR.ADD` still stop at the first faulting
  output; their fault vectors put the first offender in the first output.
  **Atomicity after a later MATMUL or ADD fault is not established** and remains
  a known divergence from the functional engine's validate-before-write order;
* **throughput or latency.** The lane computes one multiply-accumulate every
  five cycles by construction, to keep one binary32 operation per pipeline
  stage. No cycle count here is a performance claim and none feeds any timing
  model;
* **the rest of the engine surface and the unsupported forms within otherwise
  routed VECTOR subopcodes** — see section 2;
* **the contraction lane's routed area, timing or power, or physical
  characterisation of the six new VECTOR blocks.** Three legacy blocks are
  routed; `ot_a3_mac_lane` and all six additions are not — see 5.3;
* **integration with the control plane.** The sequencer of W8.6 and these
  datapaths are correlated separately and are not wired together;
* **memory macros.** Operand and result memories are behavioural arrays in the
  verification top. No SRAM or ROM macro, no bank conflict, no ECC, no
  arbitration, no backpressure from a real memory;
* **target-node area, timing, power or realisability.** See section 5.

## 7. Reproducing

```sh
python3 tools/build_abi3_engine_vectors.py           # regenerate the vectors
python3 tools/rtl_abi3_engine_campaign.py --force    # replay on both simulators
python3 -m pytest tests/compiler/test_rtl_abi3_engine.py
```

The campaign artifact records the SHA-256 of every RTL source, testbench,
vector image and *frozen contract* it depends on — including
`runtime/sim/engines/tensor.py`, `runtime/sim/backend.py`,
`runtime/tensor_accelerator/bf16.py` and `runtime/reference/formats.py`. A
change to any of them invalidates the artifact rather than silently outdating
it, and `test_retained_campaign_artifact_is_bound_to_these_sources` fails until
the campaign is re-run.
