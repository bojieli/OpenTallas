# OpenTallas documentation

[Project home](../README.md) · [Specification](../spec/README.md) ·
[Compiler](../compiler/README.md) · [RTL](../rtl/README.md) ·
[Circuit evidence](../spice/README.md) · [Contributing](../CONTRIBUTING.md)

OpenTallas is a technical library, not a sequence of lab notes. It connects the
motivation for instant inference to architecture research, model compilation,
runtime semantics, digital implementation, physical methodology, and circuit
evidence. Use this page to choose the level of detail that matches your question.

Technical records keep stable paths so citations, checklists, and in-flight work
do not break. The library is organized through reading paths and explicit
document roles rather than by moving active working documents.

## Start with the question you have

| I want to… | Read first | Then continue with… |
|---|---|---|
| Understand why 10,000+ tokens/s matters | [Why instantaneous inference matters](VISION.md) | [OpenTallas in plain English](OVERVIEW.md) and the [root performance guide](../README.md#performance-comparison) |
| Understand the architecture | [OpenTallas in plain English](OVERVIEW.md) | [Compute-in-ROM mechanism](COMPUTE_IN_ROM_MECHANISM.md) and [first-principles memory design](FIRST_PRINCIPLES_MEMORY_DESIGN.md) |
| Audit the performance claim | [Root README performance guide](../README.md#performance-comparison) | [Methodology](METHODOLOGY.md), [assumptions](ASSUMPTIONS.md), and the [iso-node](../results/iso-node/) / [area-constrained](../results/roofline/) reports |
| Evaluate ROM for video/world models | [Recent-model landscape audit](../results/world-model-landscape/REPORT.md) | [Oasis causal-state and H3 study](../results/world-model/REPORT.md), [compute-in-ROM mechanism](COMPUTE_IN_ROM_MECHANISM.md), and the [source register](SOURCES.md) |
| Evaluate a newly released model (DeepSeek-V4.1-Flash) | [DeepSeek-V4.1-Flash feasibility study](DEEPSEEK_V41_FLASH_FEASIBILITY.md) — candidate profile from the official checkpoint headers, wafer and array results | [Methodology](METHODOLOGY.md) and the [iso-node](../results/iso-node/) / [candidate roofline](../results/roofline/candidates/) reports |
| **Find something to work on** | [Contributor tasks](CONTRIBUTOR_TASKS.md) — 32 scoped tasks, each naming the document that specifies it | [How to contribute](../CONTRIBUTING.md#areas) |
| **What works today, in prose** | [STATUS.md](../STATUS.md) — every gate, its blocker, and the contributor task attached | [How to contribute](../CONTRIBUTING.md#areas) |
| **See what works today** | `PYTHONPATH=. python3 tools/check_redesign_gates.py` — prints all 19 gate rungs in 0.47 s and exits 1 while any terminal gate fails | [Generated status](PROGRAM_STATUS.md), then [four-target progress report](FOUR_TARGET_PROGRESS_REPORT.md) for the narrative |
| **Know what you can reproduce** | [Reproducibility boundary](REPRODUCIBILITY.md) — three tiers, with measured timings | [Methodology](METHODOLOGY.md) and [source register](SOURCES.md) |
| Implement software or hardware | [Specification index](../spec/README.md) | [ABI architecture decision](TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md), [wire format](TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md), and [operator conventions](TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS.md) |
| Work on the compiler/runtime | [Compiler guide](../compiler/README.md) | [Execution plan](TENSOR_ACCELERATOR_EXECUTION_PLAN.md) and [independent numeric reference](../runtime/reference/README.md) |
| Review RTL | [RTL inventory](../rtl/README.md) | [Engine datapaths](ABI3_ENGINE_DATAPATH_RTL.md), [ROM service](ROM_SERVICE_RTL.md), and [RTL reports](../results/rtl/) |
| Review physical or circuit evidence | [ROM physical methodology](ROM_PHYSICAL_METHODOLOGY.md) | [Open-PDK selection](OPEN_PDK_SELECTION.md), [SPICE guide](../spice/README.md), and [physical views](ABI3_PHYSICAL_VIEWS.md) |
| Audit a number or source | [Methodology](METHODOLOGY.md) | [Source register](SOURCES.md), [evidence ledger](EVIDENCE_LEDGER.md), and [fairness audit](COMPARISON_FAIRNESS_AUDIT.md) |

## Reading by audience

69 documents is too many to scan. This is what each tier is for, and how much of
it you need.

| If you are… | Read | Skip |
|---|---|---|
| **evaluating the project** | [STATUS.md](../STATUS.md), [REPRODUCIBILITY.md](REPRODUCIBILITY.md), [OVERVIEW.md](OVERVIEW.md), [COMPARISON_FAIRNESS_AUDIT.md](COMPARISON_FAIRNESS_AUDIT.md) | everything else |
| **about to contribute** | [CONTRIBUTOR_TASKS.md](CONTRIBUTOR_TASKS.md), then the one document your task names | the other 60 |
| **auditing a specific number** | [METHODOLOGY.md](METHODOLOGY.md), [ASSUMPTIONS.md](ASSUMPTIONS.md), [SOURCES.md](SOURCES.md), then the figure annotation's own `src=` attribute in the prose | the plans |
| **implementing against the ABI** | [../spec/README.md](../spec/README.md), [TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md](TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md), [..._OPERATOR_CONVENTIONS.md](TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS.md) | the evidence logs |

A census of the corpus, so the shape is not a surprise:

| Kind | Count | What it means for you |
|---|---:|---|
| evidence-log | 29 | A record of one campaign: what was proven, on which vectors, and what it does **not** prove. Dense by design. Read the claim-boundary section, not the whole file. |
| reference | 17 | Specifications and input ledgers. Authoritative; cite these. |
| plan | 10 | Design and implementation plans. Several contain numbered work packages a contributor can take. |
| newcomer-facing | 9 | Prose explanations. Start here. |
| post-mortem | 5 | What went wrong and why, including *"how the accelerator came to be 44,000× too slow"*. Read at least one — they show the project's standard of self-criticism. |
| guide | 4 | How to run something. |
| working-notes | 3 | Author-oriented. Useful specifications inside, but not organised for a reader. |
| superseded | 1 | Retained for history. |

**The evidence logs are the bulk and the hardest to read.** They exist so a claim
can be audited rather than trusted, and they are deliberately explicit about their
own limits. If you want the finding without the derivation, most have a §1 or an
executive summary; the claim boundary is usually the last numbered section.

## How the documentation fits together

```text
README + VISION + OVERVIEW           motivation, orientation, and headline
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

The mechanical answer comes first. `tools/check_redesign_gates.py` needs nothing
but the standard library, runs in under half a second, prints all 19 rungs with
the reason each failing one reports, and exits non-zero while any terminal gate
fails. It is the only status source that cannot drift, because it re-evaluates
the gate predicates against the artifacts on disk every time it runs. The
narrative documents below explain and contextualise; the board decides.

- [Reproducibility boundary](REPRODUCIBILITY.md) — what a stranger can re-derive
  in seconds, what needs open EDA tools, and what nobody else can reproduce
  because it needs a PDK or vendor model weights.
- [Four-target progress report](FOUR_TARGET_PROGRESS_REPORT.md) — current
  implementation boundary, per-target readiness, and critical path to full
  Qwen/DeepSeek ROM-versus-HBM acceptance.
- [Why instantaneous inference matters](VISION.md) — economic and product
  reasons for high per-user throughput, future application directions, and
  system-level qualifications.
- [OpenTallas in plain English](OVERVIEW.md) — concept, one-token walkthrough,
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

- [Chip architecture design](CHIP_ARCHITECTURE_DESIGN.md) — revised implementation proposal.
- [Checked chip resource budgets](CHIP_RESOURCE_BUDGETS.md) — exact Qwen placement,
  memory reserves, networks, engine service limits and source-bound physical snapshot.
- [Architecture review handoff](CHIP_ARCHITECTURE_REVIEW_HANDOFF.md) — fixes,
  verification and acceptance tasks for ongoing RTL/compiler work.
- [ABI 3.0 architecture decision](TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md)
  — unified program, runtime, verifier, and RTL direction.
- [ABI 3.0 tensor-datapath decode-utilization decision](ABI3_TENSOR_DATAPATH_DECODE_UTILIZATION_ADR.md)
  — shared lane architecture, correctness-first token gate, production
  simulation tiers, and correctness-qualified TPOT plan.
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
- [DeepSeek-V4.1-Flash ROM machine plan](DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md)
  — two-wafer primary target, reticle-array controlled experiment and HBM
  comparator for the 2026-09-10 release; gates DS41-A0 to DS41-REL12.
- [Qwen3 ROM hardware plan](QWEN3_ROM_HARDWARE_IMPLEMENTATION_PLAN.md) — Qwen
  model-specific ROM target.
- [DeepSeek-V4-Flash ROM hardware plan](DEEPSEEK_V4_ROM_HARDWARE_IMPLEMENTATION_PLAN.md)
  — wafer-scale sparse-model ROM target.
- [DeepSeek-V4 ROM array implementation and evaluation plan](DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md)
  — N-node reticle-class ROM array on the TA-DS-HBM fabric for Flash and Pro;
  the controlled array-versus-wafer and ROM-versus-HBM experiment.

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
| [`results/world-model/`](../results/world-model/) | Oasis causal-state/KV and MiniMax-H3 ROM-attribution study |
| [`results/world-model-landscape/`](../results/world-model-landscape/) | Dated Atlas/RTFM source record plus commit-pinned recent open-world-model decode-shape/ROM screen |
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
