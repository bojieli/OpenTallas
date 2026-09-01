# OpenTallas

![Conceptual OpenTallas fixed-model decode architecture](docs/assets/architecture-overview.svg)

> **Research status:** OpenTallas is a unified ABI 3.0 accelerator program. One
> wire format, one verifier, one functional device, one counter registry and one
> backend-neutral IR serve all four model/backend targets, so a target is a set
> of descriptors rather than a separate code path. **The Qwen3-8B accelerator
> produces output token-identical to an independent reference over the pinned
> chat workload — 24 generated tokens** — executed entirely from compiled
> artifacts through the microsequencer and engines with on-device token
> selection. **That claim has a horizon and the horizon is part of the claim:**
> at 192 tokens on the longer `TA-QW-8K-1` workload the HBM lane diverges from
> the oracle at index **137** <!-- figure: 137 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution_192.json#record.notes.first_divergence_index" name="TA-QW-8K-1 HBM-vs-oracle divergence index at 192 tokens" -->
> ([`results/abi3/qwen3_hbm_ta-qw-8k-1_execution_192.json`](results/abi3/qwen3_hbm_ta-qw-8k-1_execution_192.json),
> `status: "diverged"`, `notes.first_divergence_index: 137`), and on the agentic
> workload the accelerator-versus-oracle divergence is at index **286** <!-- figure: 286 src="results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json#turns[turn=0].oracle_comparison.first_generated_divergence_index" name="TA-QW-AGENT-2 divergence index, turn 0" -->
> ([`results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json`](results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json),
> `oracle_comparison.first_generated_divergence_index`). The 24-token identity is
> `results/abi3/comparison_qwen_rom_vs_hbm.json` →
> `token_agreement {identical: true, common_prefix_length: 24}`. Both real models <!-- figure: 24 src="results/abi3/comparison_qwen_rom_vs_hbm.json#token_agreement.common_prefix_length" name="ROM-vs-HBM token identity horizon" -->
> compile, and all four deployments are admitted by an independent verifier.
> **DeepSeek-V4-Flash now has governed four-token captures on both backends**
> for the 32-token `TA-DS-CHAT-1-P32` prompt. HBM generates **4** tokens <!-- figure: 4 src="results/abi3/accelerator_tokens/deepseek_v4_flash_hbm_p32.json#generated_token_count" name="DeepSeek HBM governed generated tokens, README" -->
> — `[13806, 345, 7472, 55560]` — identical to the external oracle. ROM now
> generates the same **4** tokens <!-- figure: 4 src="results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32.json#generated_token_count" name="DeepSeek ROM governed generated tokens, README" -->,
> and the governed pairwise report records a common prefix of **4** <!-- figure: 4 src="results/abi3/comparison_deepseek_rom_vs_hbm.json#token_agreement.common_prefix_length" name="DeepSeek ROM-vs-HBM token identity horizon, README" -->
> with no divergence.
> Both records come from the committed `tools/run_accelerator_tokens.py`, and
> every recorded transaction returns `SUCCESS` with trap `NONE`. All four
> model/backend targets have therefore produced a reference-validated
> continuation. DeepSeek's established cross-backend and oracle-identity
> horizon is four tokens; behavior beyond that horizon is not established.
> The artifacts and their claim boundary are in
> [`results/abi3/accelerator_tokens/`](results/abi3/accelerator_tokens/).
>
> **Two things that are separately true and must not be blurred.** The above is
> the functional-simulator path. Whether the *RTL* runs a given shipped
> deployment is a different question with its own artifact:
> `results/rtl/abi3_deployment_campaign.json` → `correlated_cases` lists the
> deployments the ABI 3.0 microsequencer RTL is known to reproduce exactly, and
> **any routed area, timing or power number resting on that RTL may claim those
> deployments and no others.** A validated token from the golden model is not
> evidence that the RTL runs the same design.
>
> It does **not** yet have accelerator results at the mandatory contexts, a
> fabricated chip or wafer, a
> full-chip placed-and-routed netlist, or foundry signoff DRC/LVS. Progress is
> tracked in
> [`docs/UNIFIED_EXECUTION_CHECKLIST.md`](docs/UNIFIED_EXECUTION_CHECKLIST.md),
> the narrative and judgements in
> [`docs/ABI3_PROGRAM_REPORT.md`](docs/ABI3_PROGRAM_REPORT.md), and every
> load-bearing figure's provenance rule in
> [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) §0.
>
> [`docs/PROGRAM_STATUS.md`](docs/PROGRAM_STATUS.md) is the only generated file
> in `docs/`. Regenerate it with `make abi3-status` before citing it: it is
> written by a tool and will silently lag whatever it counts.

## ABI 3.0 at a glance

The four targets are one conventional HBM/SRAM accelerator chip used as one node
for Qwen and 32 identical nodes for DeepSeek, plus a Qwen-specific ROM chip and a
DeepSeek-specific wafer-scale ROM accelerator.

Counts are the `record.notes.verification` block of each admitted execution
record in [`results/abi3/`](results/abi3/). **The previous version of this table
read 69/204, 29/197, 913/2,149 and 322/2,205; every one of those is stale**, and
the 69 contradicted a figure of 75 stated 25 lines further down this same file.

| Target | Instructions | Descriptors | Weights bound | Execution record |
|---|---:|---:|---:|---|
| Qwen3-8B HBM | **75** | **218** | 16.38 GB | `qwen3_hbm_ta-qw-chat-1_execution.json` | <!-- figure: 75 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.notes.verification.instruction_count" name="Qwen HBM instructions" --> <!-- figure: 218 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.notes.verification.descriptor_count" name="Qwen HBM descriptors" -->
| Qwen3-8B ROM | **75** | **239** | 16.38 GB | `qwen3_rom_ta-qw-chat-1_execution.json` | <!-- figure: 75 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.notes.verification.instruction_count" name="Qwen ROM instructions" --> <!-- figure: 239 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.notes.verification.descriptor_count" name="Qwen ROM descriptors" -->
| DeepSeek-V4-Flash HBM | **11,049** | **23,297** | 156.0 GB | `deepseek_v4_hbm_ta-ds-chat-1_execution.json` | <!-- figure: 11,049 src="results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json#record.notes.verification.instruction_count" name="DeepSeek HBM instructions" --> <!-- figure: 23,297 src="results/abi3/deepseek_v4_hbm_ta-ds-chat-1_execution.json#record.notes.verification.descriptor_count" name="DeepSeek HBM descriptors" -->
| DeepSeek-V4-Flash ROM | **881** | **2,883** | 156.0 GB | `deepseek_v4_rom_ta-ds-chat-1_execution.json` | <!-- figure: 881 src="results/abi3/deepseek_v4_rom_ta-ds-chat-1_execution.json#record.notes.verification.instruction_count" name="DeepSeek ROM instructions" --> <!-- figure: 2,883 src="results/abi3/deepseek_v4_rom_ta-ds-chat-1_execution.json#record.notes.verification.descriptor_count" name="DeepSeek ROM descriptors" -->

Weights bound are `results/abi3/program_status.json` →
`neutral_ir.<model>.bound_weight_bytes` = 16,381,470,720 and 156,015,698,140, <!-- figure: 16,381,470,720 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.bound_weight_bytes" name="Qwen bound weight bytes" --> <!-- figure: 156,015,698,140 src="results/abi3/program_status.json#neutral_ir.deepseek-v4-flash-0731.bound_weight_bytes" name="DeepSeek bound weight bytes" -->
both unchanged by the corrections. The two DeepSeek records currently carry
`status: "failed"`; they are the admitted programs, not passing executions, and
the counts are the verifier's, not a completed run's.

A *different* build — the same graph lowered twice through one backend, varying
only where the immutable weights live — reports smaller and equal counts, and
those two must not be confused:
[`results/abi3/storage_class_equivalence_qwen3.json`](results/abi3/storage_class_equivalence_qwen3.json)
gives `instruction_count {hbm: 31, rom: 31}` and `descriptor_count {hbm: 210, <!-- figure: 31 src="results/abi3/storage_class_equivalence_qwen3.json#instruction_count.hbm" name="Qwen storage-class-equivalent instructions" --> <!-- figure: 210 src="results/abi3/storage_class_equivalence_qwen3.json#descriptor_count.hbm" name="Qwen storage-class-equivalent descriptors" -->
rom: 210}`, and its DeepSeek twin gives 322 and 2,206. **The 322 in the old table
above was that number, filed in the wrong row.**

The backend-neutral IR behind them
([`build/ir-v3/`](build/ir-v3/), also summarised in `program_status.json`):
Qwen3-8B **728 kernels / 1,165 tensors / 36 states**, graph <!-- figure: 728 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.kernels" name="Qwen IR kernels" --> <!-- figure: 1,165 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.tensors" name="Qwen IR tensors" --> <!-- figure: 36 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.states" name="Qwen IR states" -->
`88496d70b772…`; DeepSeek-V4-Flash **3,956 kernels / 7,047 tensors / 229 <!-- figure: "88496d70b772…" src="results/abi3/program_status.json#neutral_ir.qwen3-8b.graph_id" name="Qwen IR graph id" --> <!-- figure: 3,956 src="results/abi3/program_status.json#neutral_ir.deepseek-v4-flash-0731.kernels" name="DeepSeek IR kernels" --> <!-- figure: 7,047 src="results/abi3/program_status.json#neutral_ir.deepseek-v4-flash-0731.tensors" name="DeepSeek IR tensors" -->
states**, graph `9ef6c3248d23…`. **`build/` is not committed**, so <!-- figure: "9ef6c3248d23…" src="results/abi3/program_status.json#neutral_ir.deepseek-v4-flash-0731.graph_id" name="DeepSeek IR graph id" -->
`results/abi3/program_status.json` is the only committed record of these
numbers, and it is regenerated by hand: run `make abi3-status` before quoting
them. The DeepSeek row moved three times while earlier versions of this
paragraph stood — `3,003 / 71,278 / 572431f15e65`, then `3,976 / 7,066 /
e9b960ffcb19`, then `3,956 / 7,047 / fa785d3fd7e3` — and nothing noticed until
a figure checker was pointed at it.

Three properties are worth stating plainly because the program exists to
establish them:

**Loop compression.** One Qwen forward step is **75 instructions** against
924,386 flat commands under the previous ABI 2.5. Programs describe loop nests
over layers and token blocks; tile mapping lives in schedule descriptors, where
the cycle model reads it. (The 924,386 has **no producer** in this repository —
ABI 2.5 no longer exists to re-emit it — and is retained as a historical
statement, not a reproducible one.)

**Zero-copy weights.** No image file is written anywhere. A memory object
references authenticated byte ranges of the locked checkpoint, and tiling is
expressed by view strides, for 16.38 GB and 156.0 GB of weights respectively.
(**The bundle sizes previously stated here — 223 KB and 30.9 MB — have no
producer this repository can point at.** `build/abi3/qwen3-8b-single-chip/` is
409 KB across five files and predates several commits, and no DeepSeek bundle is
present at all. The two figures are withdrawn rather than replaced; a bundle-size
claim needs an artifact that records it.)

**A deployment's storage class is separable from its program.** Building the
same graph twice through the ROM backend, changing only where the immutable
weights live, yields a byte-identical instruction stream and identical operator,
view, numeric and schedule descriptors; only the memory object's storage class
and permissions differ. This is checked mechanically
(`tools/prove_storage_class_equivalence.py`).

Note what that proof does *not* yet cover. It varies storage class **within one
backend**. The stronger property the ROM-versus-HBM comparison actually needs —
that the `rom_qwen3` and `hbm_sram` backends emit the *same* program for the
same graph — is not proven, and at the moment it does not hold: the HBM lowering
emits 75 instructions and 218 descriptors where the ROM lowering emits 31 and
210. Until the two agree, a measured ROM-versus-HBM gap is partly a measurement
of the compiler. Tracked as OI-19.

Evidence boundaries are declared, never inferred: functional, cycle, RTL,
synthesis, place-and-route, SPICE, external-reference and assumed are distinct
classes, and `runtime/evidence.py` refuses to mix them, refuses a pair that did
not share a prompt or a technology view, and refuses any comparison whose two
targets produced different tokens.

## Start here

- **New to the project?** Read
  [`docs/OVERVIEW.md`](docs/OVERVIEW.md) for the plain-language rationale, a
  one-token walkthrough, architecture and layout views, simulation results, the
  exact **8,050-tokens/s** derivation, and a clear “built versus not built”
  boundary. (**The 9,399 tok/s this line used to point at is retracted**: one of
  the derivation's five inputs, the HBM KV service term, was 3.20× low. The
  corrected value is
  [`results/iso-node/n7_architecture_attribution/REPORT.md`](results/iso-node/n7_architecture_attribution/REPORT.md)
  → "Central-envelope 200K results", column `ROM user tok/s` = 8,050.1, against <!-- figure: 8,050.1 src="results/iso-node/n7_architecture_attribution/REPORT.md#ROM user tok/s" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="N7 central ROM user tok/s" -->
  614.4 for the same-batch A100 point, a ratio of 13.10×.) <!-- figure: 614.4 src="results/iso-node/n7_architecture_attribution/REPORT.md#GPU user tok/s" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="N7 same-batch A100 user tok/s" --> <!-- figure: 13.10 src="results/iso-node/n7_architecture_attribution/REPORT.md#Same-B ratio" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="N7 same-batch ratio" -->
- **Using a figure?** Read the
  [`visual asset provenance contract`](docs/assets/README.md). It labels each
  image as conceptual, simulation-derived, or rendered from archived physical
  geometry and records the forbidden interpretations.
- **Reviewing the headline studies?** Use the N7/HBM2e/A100
  [`architecture-attribution report`](results/iso-node/n7_architecture_attribution/REPORT.md)
  and the N4-class/HBM3e/B300
  [`market report`](results/iso-node/leading_node_market/REPORT.md), then the
  **area-constrained roofline pair**, which is where the project's current
  headline figures are produced and where its retractions are stated:
  [`n6_vs_a100`](results/roofline/n6_vs_a100/REPORT.md) and
  [`n5_vs_b200`](results/roofline/n5_vs_b200/REPORT.md). Each opens with a
  numbered "What the model says" list; findings 2 and 8 of each carry the two
  largest corrections (per-user latency separated from aggregate throughput, and
  the retraction of the on-wafer tensor-parallel rates of 116,278 and 81,966
  tok/s per user).
- **Checking a number against its source?** [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md)
  §0 states the provenance rule every document in `docs/` is held to, and §7a
  requires every modelled power or energy figure to carry both power gates:
  A100 passes at 1.15× of TDP, while HC1 fails at 0.35–0.44× of its published
  card-power band and its throughput reconstruction is capacity-infeasible.
- **Implementing or auditing the design?** Start at the governed
  [`executable-system recovery plan`](docs/EXECUTABLE_SYSTEM_RECOVERY_PLAN.md)
  and [`specification index`](spec/README.md), then consult the
  [`methodology`](docs/METHODOLOGY.md), [`sources`](docs/SOURCES.md), and
  [`assumptions`](docs/ASSUMPTIONS.md).
- **Running the executable fixture?** See the compiler/runtime scope and commands
  in [`compiler/README.md`](compiler/README.md). It is unit-test evidence, not a
  transformer or DeepSeek validation.

OpenTallas is a reproducible, CPU-capable evaluation of model-specific inference
silicon whose weights live in mask ROM.  It implements the analytical and
architecture-simulation work described in
[`rom-inference-program-plan.md`](rom-inference-program-plan.md).

The project is deliberately evidence graded:

- `measured` values come from official configs or safetensors headers;
- `published` values come from an official model report or hardware source;
- `assumed` values are explicit sweep inputs, never silently presented as facts;
- `synthetic` traces exercise the design but are not substitutes for production
  router traces.

The normative comparison method is in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md),
the primary-source register is in [`docs/SOURCES.md`](docs/SOURCES.md), and every
runtime/cost convention is recorded in [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md).
Reported cost is explicitly partial
TCO (hardware/NRE amortization plus active electricity), not a complete business
case or cloud price.

The authoritative generated comparisons are deliberately separated by technology
generation, and there are **four** of them in two pairs:

- [`results/iso-node/n7_architecture_attribution/REPORT.md`](results/iso-node/n7_architecture_attribution/REPORT.md): N6/N7-class ROM plus HBM2e-era interfaces versus A100 80 GB, with WSE-2 only as a wafer-feasibility anchor;
- [`results/iso-node/leading_node_market/REPORT.md`](results/iso-node/leading_node_market/REPORT.md): N4-class ROM plus HBM3e versus B300 4NP/HBM3e, with WSE-3 only as a physical-feasibility anchor;
- [`results/roofline/n6_vs_a100/REPORT.md`](results/roofline/n6_vs_a100/REPORT.md) and
  [`results/roofline/n5_vs_b200/REPORT.md`](results/roofline/n5_vs_b200/REPORT.md):
  the area-constrained pair, in which silicon area is the primary input on both
  sides and each side chooses its own parallelism. Both are gated against a
  shipping mask-ROM part — **Taalas HC1, 16,960 tok/s per user published against <!-- figure: 16,960 src="results/roofline/n6_vs_a100/REPORT.md#Published" table="Validation gates" where="Gate=Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user" name="Taalas HC1 published anchor (input echo)" -->
  an infeasible 0.0 tok/s model reconstruction, ratio 0.00×** <!-- figure: 0.0 src="results/roofline/n6_vs_a100/REPORT.md#Modelled" table="Validation gates" where="Gate=Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user" name="HC1 gate modelled rate" --> <!-- figure: 0.00 src="results/roofline/n6_vs_a100/REPORT.md#Ratio" table="Validation gates" where="Gate=Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user" name="HC1 gate ratio" --> — and against A100 at 1.00×
  (each report's "Validation gates" table). The anchor is registered at
  `SRC-TAALAS-HC1` in [`docs/SOURCES.md`](docs/SOURCES.md). The HC1 failure is
  intentionally not tuned away: with the corrected ROM density the reconstructed
  checkpoint does not fit in the published die, so at least one physical input
  remains wrong for the shipping part.

The hardware-independent weight/KV matrix is in
[`results/model-traffic/REPORT.md`](results/model-traffic/REPORT.md), and the
phase/gate disposition is in
[`results/PRE_NDA_READINESS.md`](results/PRE_NDA_READINESS.md). The direct mapping
from the requested re-baseline and the eight public program deliverables to
repository evidence is in
[`results/REQUIREMENT_AUDIT.md`](results/REQUIREMENT_AUDIT.md).

The custom-transistor methodology vehicle is documented in
[`docs/OPEN_PDK_SELECTION.md`](docs/OPEN_PDK_SELECTION.md). The governed SKY130A
run now has zero Magic DRC errors, a unique Netgen LVS match, an audited
one-via programming difference, capacitance extraction, and 33/33 deterministic
extracted-layout PVT/load cases. A separate fixed-seed campaign enables the
installed per-instance mismatch equations at nominal TT: 256/256 local modeled
samples pass, the same seed replays exactly, and cross-seed variation is
observed. A complementary full-RC campaign preserves all extracted resistor
segments across five declared Magic interconnect styles: 165/165 deterministic
electrical cases and all five fresh-directory semantic extraction replays pass.
The nominal local delay is 0.0412 ns versus 0.0354 ns for the capacitance-only
baseline; this is a local methodology comparison, not a product timing value. See
[`results/spice/sky130_physical/REPORT.md`](results/spice/sky130_physical/REPORT.md)
and
[`results/spice/SKY130_EXTRACTED_PVT_REPORT.md`](results/spice/SKY130_EXTRACTED_PVT_REPORT.md),
plus
[`results/spice/SKY130_EXTRACTED_MISMATCH_REPORT.md`](results/spice/SKY130_EXTRACTED_MISMATCH_REPORT.md)
and
[`results/spice/sky130_resistance/REPORT.md`](results/spice/sky130_resistance/REPORT.md).
The independent IHP SG13G2 replication is governed end to end. The pinned
v0.3.0 checkout is semantically locked, all four official Verilog-A modules
compile twice byte-identically for generic x86-64, and the official 1.2-V
device smoke passes. The separately implemented controlled-via slice then
closes zero-error DRC, unique ten-port LVS, the exact 6-versus-5 via invariant,
capacitance PEX, and 33/33 deterministic PVT/load cases. Its five-style
detailed-RC campaign preserves 10 MOS, 41 resistor, and 68 capacitor elements,
passes all five fresh-directory semantic replays, retains all six extracted
NMOS body-resistance paths, and closes 165/165 electrical cases. See the
[`IHP device-smoke`](results/spice/ihp_device_smoke/REPORT.md),
[`physical`](results/spice/ihp_sg13g2_physical/REPORT.md),
[`capacitance-PVT`](results/spice/IHP_SG13G2_EXTRACTED_PVT_REPORT.md), and
[`detailed-RC`](results/spice/ihp_sg13g2_resistance/REPORT.md) reports. These
are local open-PDK circuit results, not silicon-yield evidence, a compact ROM
macro, or N7/N4 scaling anchors.

`results/standard/` and `results/sensitivity/` are retained as legacy exploratory
artifacts. Their B200/B300-versus-single-midpoint figures are superseded and must
not be quoted as the current comparison. The focused Qwen3-8B control remains in
[`results/standard/QWEN3_8B_ADDENDUM.md`](results/standard/QWEN3_8B_ADDENDUM.md)
as a legacy architecture-control study, not a product result.

The simulator is model-general. The authoritative iso-node studies currently use
DeepSeek V4 Flash and Pro at 8K, 32K, 200K, and 1M resident context and batch 1,
8, 32, and 64. They inventory released tensors and exact operator shapes, retain
DeepSeek's official FP8/MXFP4/BF16/FP32 roles, keep immutable ROM weights separate
from mutable SRAM/HBM KV state, and expose weight, KV, compute, communication,
pipeline, capacity, and thermal terms. Kimi K3 and Qwen3-8B remain useful controls
in the legacy/general simulator but are not part of the two current comparator
matrices.

The reported compute interval prices format-specific tensor contractions only.
Selected normalization, nonlinear, softmax/index-score, compressor, top-k, and
Sinkhorn work is now stage-partitioned and reported as break-even service-rate
requirements without inventing a vector roof. Those paths—and the still-incomplete
auxiliary operator ledger—do not yet contribute modeled time or energy, so all
token rates and ROM/GPU ratios remain conditional under `COMP-01`.

The architecture/specification gate has passed for public-reference RTL only. The
checked `ot_*` hierarchy is now a controlled implementation baseline with strict
static/CDC/RDC, formal, dual-simulator, and source-hashed evidence. A warning-clean,
source-checked campaign also closes 87 enumerated public RTL fault/containment sites
under both Icarus and pinned Verilator 5.050; this is not physical or ATPG coverage.
The governed seven-case Nangate45 implementation campaign also closes from an
isolated clean baseline: mapped synthesis and complete proxy STA cover 7/7 cases,
with 2/2 generic equivalence, 1/1 actual mapped equivalence, 2/2 physical proxies,
2/2 post-route equivalence, and 386 hash-verified referenced artifacts. See the
[`implementation report`](results/rtl/IMPLEMENTATION_REPORT.md) and
[`clean replay`](results/rtl/CLEAN_BASELINE_REPLAY.md). The small legacy tile,
open-library implementation, and open-PDK transistor experiments remain
methodology/feasibility proxies. None authorizes product silicon: target numerical
qualification, target macros/PDK, full-chip or wafer physical design, package,
manufacturing, and foundry signoff remain mandatory gates.

## Quick start

```bash
python3 -m pip install -e .
python3 tools/profile_hf.py --all

make model-traffic     # results/model-traffic/
make iso-node          # results/iso-node/
make roofline          # results/roofline/
make abi3-status       # regenerates docs/PROGRAM_STATUS.md

PYTHONPATH=src pytest -q tests/test_iso_node_studies.py tests/test_roofline.py
make fault-campaign
make verify
```

The rendered figures under `docs/assets/` are generated by
`python3 tools/render_public_assets.py`, which reads the current artifacts.
Nothing checks that they have been re-rendered, so run it after any change to
`results/` — three of them silently carried retracted values for two days
before anyone looked.

The optional custom-transistor campaign requires the pinned public SKY130A and
IHP SG13G2 PDKs, Magic, VLSI Netgen, ngspice 43 with OSDI, and the pinned patched
OpenVAF compiler. It is deliberately outside the generic `make verify`
dependency set:

```bash
tools/bootstrap_sky130_pdk.sh
tools/bootstrap_sky130_physical_tools.sh
tools/bootstrap_ihp_pdk.sh
tools/bootstrap_ihp_model_tools.sh
make spice-pdk
```

The fault plan is machine-readable in
[`spec/fault_campaign.json`](spec/fault_campaign.json); canonical evidence is in
[`results/rtl/FAULT_REPORT.md`](results/rtl/FAULT_REPORT.md). Rebuild the pinned
timed-bench simulator with `tools/bootstrap_verilator_5_050.sh` when it is absent.
The controlled source and bench inventory is documented in
[`rtl/README.md`](rtl/README.md).

No model checkpoint is downloaded. The profiler uses small HTTP range requests
to read safetensors metadata. A full standard run is intended to fit on a CPU
workstation.

## What a result means

The code can validate accounting, architecture trends, constraint interactions,
and sensitivity to hardware assumptions. It cannot establish leading-node ROM
density, read bandwidth, yield, price, or packaging feasibility; those remain
foundry/OSAT measurements. See `docs/` and the generated result report for the
precise boundary between demonstrated, simulated, and unknown claims.
