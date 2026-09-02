# OpenTallas documentation

[Project home](../README.md) · [Specification](../spec/README.md) ·
[Compiler](../compiler/README.md) · [RTL](../rtl/README.md) ·
[Circuit evidence](../spice/README.md) · [Contributing](../CONTRIBUTING.md)

OpenTallas spans architecture research, model compilation, runtime semantics,
digital implementation, physical methodology, and circuit evidence. This page
is the map across those layers. Existing technical records keep stable paths so
that citations, checklists, and in-flight work do not break; organization is
provided through clear entry points and explicit document roles.

## Start with the question you have

| I want to… | Read first | Then continue with… |
|---|---|---|
| Understand the central idea | [OpenTallas in plain language](OVERVIEW.md) | [Compute-in-ROM mechanism](COMPUTE_IN_ROM_MECHANISM.md) and [first-principles memory design](FIRST_PRINCIPLES_MEMORY_DESIGN.md) |
| Understand the performance claim | [Root README performance guide](../README.md#performance-at-a-glance) | [Methodology](METHODOLOGY.md), [assumptions](ASSUMPTIONS.md), and the [iso-node](../results/iso-node/) / [area-constrained](../results/roofline/) reports |
| See what works today | [ABI 3.0 program report](ABI3_PROGRAM_REPORT.md) | [Generated status](PROGRAM_STATUS.md) and [execution checklist](UNIFIED_EXECUTION_CHECKLIST.md) |
| Implement software or hardware | [Specification index](../spec/README.md) | [ABI architecture decision](TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md), [wire format](TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md), and [operator conventions](TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS.md) |
| Work on the compiler/runtime | [Compiler guide](../compiler/README.md) | [Execution plan](TENSOR_ACCELERATOR_EXECUTION_PLAN.md) and [independent numeric reference](../runtime/reference/README.md) |
| Review RTL | [RTL inventory](../rtl/README.md) | [Engine datapaths](ABI3_ENGINE_DATAPATH_RTL.md), [ROM service](ROM_SERVICE_RTL.md), and [RTL reports](../results/rtl/) |
| Review physical or circuit evidence | [ROM physical methodology](ROM_PHYSICAL_METHODOLOGY.md) | [Open-PDK selection](OPEN_PDK_SELECTION.md), [SPICE guide](../spice/README.md), and [physical views](ABI3_PHYSICAL_VIEWS.md) |
| Audit a number or source | [Methodology](METHODOLOGY.md) | [Source register](SOURCES.md), [evidence ledger](EVIDENCE_LEDGER.md), and [fairness audit](COMPARISON_FAIRNESS_AUDIT.md) |

## How the documentation fits together

```text
README + OVERVIEW                    orientation and current headline
        │
        ├── spec/                    normative system and implementation contract
        ├── methodology + configs/   comparison rules and declared inputs
        ├── design records           rationale, decisions, and architecture details
        ├── evidence notes           bounded claims tied to reproducible artifacts
        ├── plans + checklists        delivery sequence and open work
        └── results/                 generated records and reports
```

There is no single document that owns every kind of truth. Use the source that
owns the question:

| Question | Authority |
|---|---|
| What behavior or interface is required? | [`spec/`](../spec/) and the frozen ABI documents |
| What assumptions make a comparison fair? | [Methodology](METHODOLOGY.md), [assumptions](ASSUMPTIONS.md), and versioned files under [`configs/`](../configs/) |
| What exact value did a run produce? | The machine-readable artifact and generated report under [`results/`](../results/) |
| What does that value permit us to claim? | The artifact's evidence grade, its scoped evidence note, and the [evidence ledger](EVIDENCE_LEDGER.md) |
| What is complete or still open? | [Generated status](PROGRAM_STATUS.md), the [program report](ABI3_PROGRAM_REPORT.md), and the [execution checklist](UNIFIED_EXECUTION_CHECKLIST.md) |
| What should be built next? | The applicable implementation plan; plans do not override specifications or result artifacts |

## Performance and research foundations

- [Architecture-comparison methodology](METHODOLOGY.md) — normative comparison,
  evidence, accounting, and interpretation rules.
- [Analytical assumptions and interpretation contract](ASSUMPTIONS.md) — model,
  precision, hardware-envelope, topology, efficiency, cost, and exclusion inputs.
- [Source and evidence register](SOURCES.md) — primary sources and unavailable
  evidence.
- [Research provenance](RESEARCH_PROVENANCE.md) — provenance and outcome of the
  multi-domain source review.
- [Evidence ledger](EVIDENCE_LEDGER.md) — load-bearing figures, producers, grades,
  and known blind spots.
- [Comparison fairness audit](COMPARISON_FAIRNESS_AUDIT.md) — artifacts,
  legitimate asymmetries, refuted concerns, and missing measurements.
- [First-principles memory design](FIRST_PRINCIPLES_MEMORY_DESIGN.md) — what
  weight/KV traffic and capacity imply for the hierarchy.
- [Compute-in-ROM mechanism](COMPUTE_IN_ROM_MECHANISM.md) — what the ROM cell
  operation means and does not mean.
- [Per-region compute-in-ROM design](PER_REGION_COMPUTE_IN_ROM_DESIGN.md) — the
  sparse-region alternative and its trade-offs.
- [Iso-area comparison and Taalas anchor](ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md)
  — area-normalized comparison and validation anchor.
- [Wafer versus array latency](WAFER_VERSUS_ARRAY_LATENCY.md) — topology choice
  through latency and communication budgets.
- [Technical direction recommendation](TECHNICAL_DIRECTION_RECOMMENDATION.md) —
  decision synthesis, corrections, and falsification conditions.

## Program orientation and status

- [OpenTallas in plain language](OVERVIEW.md) — concept, one-token walkthrough,
  performance derivation, evidence ladder, and suggested reading paths.
- [ABI 3.0 program report](ABI3_PROGRAM_REPORT.md) — current narrative across the
  unified executable program.
- [ABI 3.0 program status](PROGRAM_STATUS.md) — generated status snapshot. Do not
  edit it by hand; regenerate it with `make abi3-status` when intentionally
  refreshing status.
- [Unified execution checklist](UNIFIED_EXECUTION_CHECKLIST.md) — live gates,
  evidence requirements, and completion tracking.
- [Pre-NDA technology roadmap](PRE_NDA_TECHNOLOGY_ROADMAP.md) — external
  technology and validation path.

## ABI and architecture decisions

- [ABI 3.0 architecture decision](TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md)
  — unified program, runtime, verifier, and RTL direction.
- [ABI 3.0 wire format](TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md) — frozen binary
  records, descriptors, validation, and compatibility contract.
- [ABI 3.0 operator conventions](TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS.md)
  — operator operands, views, numeric behavior, and scheduling conventions.
- [TA-A3 architecture review and plan revision](TA_A3_ARCH_0_REVIEW_AND_PLAN_REVISION.md)
  — review disposition and amendments at the architecture freeze.
- [DeepSeek sparse-attention gate](DEEPSEEK_SPARSE_ATTENTION_GATE.md) — semantic
  and evidence gates for sparse attention.

The full normative system package lives in [`spec/`](../spec/README.md), including
requirements, architecture, microarchitecture, interfaces, numerics, clock/reset/
power, RAS/repair/DFT, firmware/compiler, floorplan/PPA, verification, traceability,
and change control.

## Implementation plans

These are delivery documents. They organize work and acceptance gates; they do
not promote planned behavior into implemented evidence.

- [Executable-system recovery plan](EXECUTABLE_SYSTEM_RECOVERY_PLAN.md) — governed
  path from analytical work to artifact-driven execution.
- [Four-target implementation master plan](FOUR_TARGET_IMPLEMENTATION_MASTER_PLAN.md)
  — coordination across the two models and two storage backends.
- [Tensor-accelerator execution plan](TENSOR_ACCELERATOR_EXECUTION_PLAN.md) —
  compiler, simulator, validation, and production execution program.
- [Shared HBM/SRAM implementation plan](HBM_SRAM_TENSOR_ACCELERATOR_IMPLEMENTATION_PLAN.md)
  — conventional accelerator backend and distributed dataflow work.
- [Qwen3 ROM hardware plan](QWEN3_ROM_HARDWARE_IMPLEMENTATION_PLAN.md) — Qwen
  model-specific ROM target.
- [DeepSeek-V4-Flash ROM hardware plan](DEEPSEEK_V4_ROM_HARDWARE_IMPLEMENTATION_PLAN.md)
  — wafer-scale sparse-model ROM target.

## Functional and model evidence

### Qwen3

- [Qwen3-8B 8K executable evidence](QWEN3_8B_EXECUTABLE.md) — bounded executable
  workload and reference boundary.

### DeepSeek V4

Each note below qualifies one deliberately bounded semantic surface. Together
they are a navigable evidence suite, not an assertion that the complete model is
implemented.

- [Lookup slice](DEEPSEEK_V4_LOOKUP_EVIDENCE.md)
- [Selected-row FP8 linear](DEEPSEEK_V4_FP8_LINEAR_EVIDENCE.md)
- [Complete-output FP8 linear](DEEPSEEK_V4_FP8_LINEAR_FULL_EVIDENCE.md)
- [Routed/shared SwiGLU](DEEPSEEK_V4_SWIGLU_EVIDENCE.md)
- [Grouped attention output](DEEPSEEK_V4_GROUPED_OUTPUT_EVIDENCE.md)
- [Attention KV view](DEEPSEEK_V4_ATTENTION_KV_VIEW_EVIDENCE.md)
- [Circular KV window](DEEPSEEK_V4_KV_WINDOW_EVIDENCE.md)
- [Sparse attention](DEEPSEEK_V4_SPARSE_ATTENTION_EVIDENCE.md)
- [Compressor](DEEPSEEK_V4_COMPRESSOR_EVIDENCE.md)
- [HC_PRE](DEEPSEEK_V4_HC_PRE_EVIDENCE.md)
- [Shared vocabulary head](DEEPSEEK_V4_LM_HEAD_EVIDENCE.md)
- [DSpark main projection](DEEPSEEK_V4_DSPARK_MAIN_PROJECT_EVIDENCE.md)
- [DSpark prefill KV](DEEPSEEK_V4_DSPARK_PREFILL_KV_EVIDENCE.md)
- [DSpark Markov loop](DEEPSEEK_V4_MARKOV_LOOP_EVIDENCE.md)
- [DSpark Markov microprogram](DEEPSEEK_V4_MARKOV_MICROPROGRAM_EVIDENCE.md)

## RTL, physical, and circuit evidence

- [ABI 3.0 engine datapaths in RTL](ABI3_ENGINE_DATAPATH_RTL.md) — implemented
  engine slices, correlation, and open gates.
- [ROM read service in RTL](ROM_SERVICE_RTL.md) — addressing, placement, repair,
  correlation, and explicit macro boundary.
- [ABI 3.0 physical implementation views](ABI3_PHYSICAL_VIEWS.md) — governed
  public physical proxies and their scope.
- [ASAP7 predictive physical campaign](ASAP7_PHYSICAL.md) — predictive-node
  routing methodology and limitations.
- [Open transistor PDK selection](OPEN_PDK_SELECTION.md) — selection criteria and
  public-process evidence matrix.
- [ROM physical methodology](ROM_PHYSICAL_METHODOLOGY.md) — bitcell, macro,
  energy, extraction, and node-transfer evidence chain.
- [ROM density node transfer](ROM_DENSITY_NODE_TRANSFER.md) — whether a measured
  ROM/SRAM area ratio transfers across processes.
- [Qwen RTL on IHP SG13G2](QWEN3_RTL_IHP_PHYSICAL.md) — public-PDK physical
  feasibility for a bounded accelerator block.

Subsystem entry points provide the source inventory and reproduction commands:

| Subsystem | Guide |
|---|---|
| Compiler and executable fixtures | [`compiler/README.md`](../compiler/README.md) |
| Tensor-accelerator vertical slice | [`compiler/tensor_accelerator/README.md`](../compiler/tensor_accelerator/README.md) |
| Independent numeric reference | [`runtime/reference/README.md`](../runtime/reference/README.md) |
| Public-reference RTL | [`rtl/README.md`](../rtl/README.md) |
| ROM circuit campaigns | [`spice/README.md`](../spice/README.md) |
| Visual assets and interpretation | [`docs/assets/README.md`](assets/README.md) |

## Generated results

Generated evidence belongs under [`results/`](../results/), separate from design
prose and plans:

| Result family | Contents |
|---|---|
| [`results/model-traffic/`](../results/model-traffic/) | Hardware-independent active-weight and mutable-KV traffic |
| [`results/iso-node/`](../results/iso-node/) | N7/A100 architecture attribution and N4-class/B300 market-generation studies |
| [`results/roofline/`](../results/roofline/) | Area-constrained N6/A100 and N5/B200 comparisons, plus declared variants |
| [`results/abi3/`](../results/abi3/) | Deployments, executions, comparisons, certificates, and ABI program records |
| [`results/rtl/`](../results/rtl/) | Static, formal, simulation, fault, coverage, implementation, and ABI campaigns |
| [`results/spice/`](../results/spice/) | Primitive, extracted-layout, PVT, mismatch, resistance, and macro experiments |
| [`results/asap7_physical/`](../results/asap7_physical/) | Predictive physical-design artifacts |
| [`results/noc/`](../results/noc/) | Network sweeps and reports |

The top-level [decision](../results/DECISION.md),
[pre-NDA readiness](../results/PRE_NDA_READINESS.md), and
[requirement audit](../results/REQUIREMENT_AUDIT.md) connect result families to
program decisions. `results/standard/` and the older sensitivity outputs are
retained for historical/exploratory context; use the current iso-node and
area-constrained pairs for headline comparisons.

## Background and program history

- [`rom-inference-brief.md`](../rom-inference-brief.md) — original concise
  problem framing.
- [`rom-inference-program-plan.md`](../rom-inference-program-plan.md) — original
  analytical and architecture program plan.

These remain useful context. For current requirements, status, and numerical
claims, follow the specification, program report, and generated result paths
above.

## Documentation contract

When adding or revising documentation:

1. **Name the document's role.** Orientation, specification, decision, evidence
   note, plan/checklist, and generated report have different authority.
2. **Keep volatile detail at its source.** Landing pages summarize; exact counts,
   hashes, and status belong in generated artifacts or scoped evidence notes.
3. **Attach important figures to producers.** Use the repository's machine-
   resolvable figure provenance annotations and run `make check-figures`; the
   annotation grammar is documented in `tools/check_prose_figures.py`.
4. **State the non-claim.** Simulation, RTL, synthesis, routed proxies, extracted
   circuits, and silicon are separate evidence levels.
5. **Preserve stable paths.** Add a navigation layer before moving a live plan,
   checklist, or evidence record. Coordinate any necessary rename with its owner.
6. **Update this index.** Every new durable technical document needs a home in a
   reading path or catalog above.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for setup, validation, generated-file,
and change-control guidance.
