# OpenTallas

**Open research toward instant, affordable AI inference.**

**[What works today](STATUS.md)** · [What you can reproduce](docs/REPRODUCIBILITY.md) ·
[How to contribute](CONTRIBUTING.md#areas) · [Why speed matters](docs/VISION.md) ·
[Plain-English overview](docs/OVERVIEW.md) · [Documentation](docs/README.md) ·
[Specification](spec/README.md) · [Results](results/)

More than 10,000 tokens per second per user is now a publicly reported silicon
result. [Taalas](https://taalas.com/products/) reports **16,960 tokens/s** <!-- figure: 16,960 src="configs/hardware/technology.json#reference_parts.taalas_hc1.published_tokens_s_per_user.value" name="Taalas HC1 published per-user rate, README" -->
per user for its fabricated HC1 accelerator running Llama 3.1 8B at batch one.
That result changes the conversation: model-specific inference is no longer
only a paper architecture. It is a credible path toward AI systems that respond
at interactive timescales.

OpenTallas asks what it would take to make that architectural direction open,
inspectable, and extensible to larger models and longer contexts. The repository
connects model accounting, architecture simulation, a shared compiler/runtime
ABI, public-reference RTL, and open-PDK circuit experiments in one evidence
chain. It is independent of Taalas and does not claim to reproduce HC1.

For implementation work, use the [revised chip architecture](docs/CHIP_ARCHITECTURE_DESIGN.md),
[checked resource budgets](docs/CHIP_RESOURCE_BUDGETS.md), and
[review handoff](docs/CHIP_ARCHITECTURE_REVIEW_HANDOFF.md). These correct physical
placement and service assumptions; the historical analytical studies below
remain separate from a correctness-qualified chip throughput result.

![Conceptual OpenTallas model-specific decode architecture](docs/assets/architecture-overview.svg)

## The headline—and the evidence behind it

| Signal | Result | Evidence class |
|---|---:|---|
| Public model-specific silicon reference | **16,960 tokens/s per user** on Taalas HC1 | Fabricated product; first-party Taalas run, publicly documented, not an independent benchmark | <!-- figure: 16,960 src="configs/hardware/technology.json#reference_parts.taalas_hc1.published_tokens_s_per_user.value" name="Taalas HC1 public reference rate, README" -->
| OpenTallas redesigned ROM array, DeepSeek-V4.1-Flash, 200K context | **4,176 tokens/s per user** at batch 1; **3,402** with 64 concurrent users | Deterministic analytical result on the [analytical report](docs/ANALYTICAL_REPORT.md) framework, with the serial path priced from the per-token operator graph; not measured silicon | <!-- figure: 4,176 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x176,batch_size=1].rom_per_user_tokens_s" name="README V4.1 ROM batch-1 rate" --> <!-- figure: 3,402 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x132,batch_size=64].rom_per_user_tokens_s" name="README V4.1 ROM batch-64 rate" -->
| Same ROM array versus B200 on NVLink/NVL72 at the same silicon | **5.99×** per user at batch 1, **7.22×** at 64 users | Modeled; the GPU picks its own best layout, including NVL72 and expert parallelism, and pays a published launch gap per dependent kernel | <!-- figure: 5.99 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x176,batch_size=1].per_user_speed_ratio" name="README V4.1 batch-1 ratio" --> <!-- figure: 7.22 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x132,batch_size=64].per_user_speed_ratio" name="README V4.1 batch-64 ratio" -->
| Each side at its best | **4.22×** throughput, **12.32×** tokens per joule | Best design and batch on each side at the same silicon | <!-- figure: 4.22 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4.1-Flash,silicon_area_mm2=554700.0].aggregate_ratio" name="README V4.1 best throughput ratio" --> <!-- figure: 12.32 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4.1-Flash,silicon_area_mm2=554700.0].tokens_per_joule_ratio" name="README V4.1 best energy ratio" -->

The Taalas and OpenTallas rates are **not** an apples-to-apples benchmark. They
use different models, contexts, systems, and evidence classes. The Taalas number
is useful because it is a public proof point from fabricated hardware; the
OpenTallas number is useful because its assumptions and derivation are open to
inspection. Taalas publishes a product page, a [public
chatbot](https://chatjimmy.ai/), and [API documentation](https://api.taalas.com/),
but the benchmark itself was run by Taalas Labs rather than MLPerf or an
independent laboratory. The exact source boundary is recorded in the
[source register](docs/SOURCES.md#the-shipping-mask-rom-part-the-anchor-the-model-is-gated-against).

> **Research status**
>
> OpenTallas is an active hardware research program, not a fabricated product.
> Its headline performance and cost figures are deterministic model outputs.
> Bounded functional executions, RTL campaigns, public-PDK layouts, and extracted
> circuit experiments exist only at their documented scopes. A complete target
> implementation, foundry signoff, packaged system, and OpenTallas silicon do not.
> Current source-locked and retained historical execution horizons are separated
> explicitly in the [execution checklist](docs/UNIFIED_EXECUTION_CHECKLIST.md).
> A cycle result that depends on assumed machine values is correctness evidence,
> not a performance measurement or projection.

## Where this program actually stands

Every figure below is a model output. Whether the design *works* is tracked
separately, by a gate board of 19 rungs that is deliberately mostly red. Run it
yourself on a bare checkout — no install, no EDA tools, under half a second:

```
PYTHONPATH=. python3 tools/check_redesign_gates.py
```

At the time of writing it prints **9 of 19 rungs passing and 1 of 4 terminal
gates**, and exits non-zero:

```
TERMINAL GATES FAILING: G1, G3, G4 -- the release criteria of
docs/OPENTALLAS_REDESIGN_PLAN.md are not met
```

What those failures mean, in plain terms:

- **G1** — the integrated RTL does not yet produce the reference model's tokens.
  End-to-end token correctness is not demonstrated.
- **G3** — no correctness-qualified time-per-output-token measurement exists.
- **G4** — the cycle model is ~10x off the measured RTL control plane, with 32 of
  32 ratios outside the acceptance band.
- **C3** — the cycle model and the analytical model do **not** agree on the
  binding constraint. This one bears directly on the headline numbers; see
  [the disagreement](#the-cycle-model-disagrees-with-the-analytical-model) below.

Two further facts a reader should have before quoting anything here:

- **64 of 96** artifacts that pin source digests no longer bind the current tree
  (`results/derived/source_currency_drift.json`). A drifted artifact is
  inadmissible as evidence until re-taken.
- The analytical layer **is** byte-reproducible: `python3 tools/run_roofline_studies.py --force`
  regenerates every figure in the [analytical report](docs/ANALYTICAL_REPORT.md).

[**STATUS.md**](STATUS.md) explains every failing gate in plain language and
names the contributor task attached to it.
[**What you can and cannot reproduce**](docs/REPRODUCIBILITY.md) states the full
boundary in three tiers.

## Why 10,000 tokens per second matters

High token rates are not valuable simply because a benchmark number is large.
They change both the economics of inference and the kinds of products that can
be built.

### 1. More useful work from every dollar of infrastructure

When a system produces more useful tokens during each paid second of hardware,
its capital and operating costs are amortized across more output. That does not
make lower cost automatic: utilization, yield, power, lifetime, model quality,
and non-recurring engineering all matter. It does make throughput a powerful
economic lever.

The [analytical report](docs/ANALYTICAL_REPORT.md) prices energy per delivered
token rather than cost: at each side's best, the redesigned ROM machine uses
3–5× less energy per token than B200 on DeepSeek models and 13× less on
Qwen3-8B. The earlier partial-TCO scenarios came from the retired iso-node
analytical model and are no longer published. A cost model would add mask and
NRE amortisation, which falls on the ROM side, and model-refresh risk.

Here, **stock** does not mean a measured off-the-shelf server run. It means an
allowed conventional GPU or GPU cluster assembled from the published device
characteristics and compatibility rules in the study configuration. The
performance comparator is the GPU layout that is best at each metric, at
approximately equal silicon area.

The executable stack keeps this architecture choice explicit:

```text
checkpoint + workload
        │
        ▼
canonical model graph ──► backend-neutral IR ──► ABI 3.0 program
                                                    │
                              ┌─────────────────────┴─────────────────────┐
                              ▼                                           ▼
                    HBM/SRAM deployment                         ROM deployment
                              │                                           │
                              └──────── verifier + device + counters ─────┘
                                                    │
                                      functional / cycle / RTL evidence
```

Qwen3-8B and DeepSeek-V4-Flash both use this shared compiler/runtime path. The
analytical studies also use DeepSeek-V4-Pro as a scaling workload; it is not a
third executable ABI target. See the [architecture specification](spec/ARCHITECTURE.md),
[ABI decision](docs/TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md), and
[wire format](docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md) for the contract.

## Performance comparison

The [analytical report](docs/ANALYTICAL_REPORT.md) is the single source for
performance. It compares a redesigned model-specific ROM machine with a
general-purpose HBM machine at best shipping practice, at equal silicon area.

The ROM machine keeps weights in ROM, packages four dies over UCIe-class links,
connects packages over direct SerDes, stripes experts across banks, and pipelines
layers across packages. The HBM machine is B200 or A100 on NVLink (HGX and NVL72)
and may use tensor, pipeline, hybrid or expert parallelism.

Summary at N5 against B200, per user:

- **DeepSeek MoE models:** 2.3–5× at batch 1 and 2.8–8.5× from tens to about a
  thousand concurrent users.
- **Qwen3-8B:** about 19× for a single user.
- **At each side's best:** throughput is about 3×, and tokens per joule 3–5× on
  DeepSeek (13× on Qwen).

Specialisation, not weights-in-ROM alone, produces most of the large-model
single-user gain. With the GPU's own links, a ROM array only ties B200 on NVL72
for one user.

## What is implemented—and what is not

| Evidence layer | Present in the repository | Claim boundary |
|---|---|---|
| Model and architecture analysis | Checked traffic, iso-node, area-constrained, NoC, routing, cost, and sensitivity studies | Deterministic model output; not measured hardware |
| Compiler and runtime | Canonical model ingestion, backend-neutral IR, ABI 3.0 deployments, independent verification, functional and cycle devices | Bounded workloads and declared token-agreement horizons; not unrestricted model correctness |
| Digital implementation | Synthesizable public-reference RTL, formal/static/simulation/fault campaigns, and open-library implementation proxies | Qualified blocks and correlated deployments only; not a complete target chip or wafer |
| Circuit and physical methods | SKY130A and IHP controlled-via ROM slices, extracted simulations, and predictive/open-library routed blocks | Local methodology evidence; not leading-node ROM density, yield, or product signoff |
| Product silicon | **Not present** | No tapeout, fabricated OpenTallas device, package, full-chip P&R, foundry DRC/LVS, or silicon benchmark |

The [evidence ladder](docs/assets/README.md) defines how conceptual diagrams,
simulated results, routed geometry, and extracted circuits may be interpreted.
Functional, cycle, RTL, synthesis, place-and-route, SPICE, published, measured,
and assumed evidence are intentionally not interchangeable. Start with the
[current program report](docs/ABI3_PROGRAM_REPORT.md), [generated
status](docs/PROGRAM_STATUS.md), and [evidence methodology](docs/METHODOLOGY.md)
before extending a claim.

## Start exploring

| If you want to… | Start here |
|---|---|
| Understand why instant inference matters | [Vision and product implications](docs/VISION.md) |
| Learn the architecture without a hardware background | [OpenTallas in plain English](docs/OVERVIEW.md) |
| Navigate the full technical library | [Documentation hub](docs/README.md) |
| Audit the performance comparison | [Methodology](docs/METHODOLOGY.md), [assumptions](docs/ASSUMPTIONS.md), and [sources](docs/SOURCES.md) |
| Inspect the executable program | [ABI 3.0 program report](docs/ABI3_PROGRAM_REPORT.md) and [compiler guide](compiler/README.md) |
| Implement against the contract | [Specification index](spec/README.md), [wire format](docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md), and [operator conventions](docs/TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS.md) |
| Review digital hardware evidence | [RTL inventory](rtl/README.md) and [RTL result reports](results/rtl/) |
| Review ROM circuit evidence | [SPICE guide](spice/README.md) and [physical methodology](docs/ROM_PHYSICAL_METHODOLOGY.md) |
| Track active work | [Unified execution checklist](docs/UNIFIED_EXECUTION_CHECKLIST.md) |
| **See what passes today** | `PYTHONPATH=. python3 tools/check_redesign_gates.py` — 19 rungs in 0.47 s |
| **Know what you can reproduce** | [Reproducibility boundary](docs/REPRODUCIBILITY.md) |

## Quick start

The core Python analyses and tests run on a CPU workstation with Python 3.10 or
newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[test,compiler]"

make model-traffic
make spec-check
make test
```

Rebuild the headline studies and verify every annotated prose figure with:

```bash
make iso-node
make roofline
make check-figures
```

The complete `make verify` flow additionally needs RTL synthesis and simulation
tools. Its `spice` step checks circuit topology and source invariants; the
optional device, physical, and extracted-layout campaigns are separate and
require pinned SKY130A or IHP SG13G2 PDK/tool installations. See
[spice/README.md](spice/README.md). Model profiling reads checkpoint metadata
with range requests and does not download full checkpoints by default.

## Repository map

| Path | Purpose |
|---|---|
| [`src/opentallas/`](src/opentallas/) | Analytical architecture and performance models |
| [`compiler/`](compiler/) | Model ingestion, canonical IR, ABI lowering, and deployment construction |
| [`runtime/`](runtime/) | Independent checks, functional device, cycle model, and reference numerics |
| [`spec/`](spec/) | Governed system, microarchitecture, interface, numeric, RAS, firmware, and verification contracts |
| [`rtl/`](rtl/) | Public-reference SystemVerilog, benches, formal harnesses, and campaigns |
| [`spice/`](spice/) and [`physical/`](physical/) | Circuit and physical-methodology vehicles |
| [`configs/`](configs/) | Explicit model, hardware, benchmark, and PDK inputs |
| [`results/`](results/) | Generated, reviewable evidence artifacts and reports |
| [`docs/`](docs/) | Vision, orientation, methodology, decisions, evidence notes, plans, and status |
| [`tests/`](tests/) | Unit, differential, integration, ABI, runtime, and simulation tests |
| [`tools/`](tools/) | Reproduction, checking, reporting, and campaign entry points |

## Contributing

OpenTallas welcomes work that makes an assumption more explicit, a result more
reproducible, an implementation more complete, or a claim easier to audit. Read
[CONTRIBUTING.md](CONTRIBUTING.md) before changing a specification, generated
report, evidence grade, or headline figure. Add new documents to the
[documentation hub](docs/README.md), and coordinate with current owners before
renaming or moving an active plan or checklist.

The most valuable contribution is often not a larger number. It is a clearer
boundary between what the repository demonstrates, what it models, and what
still has to be measured in silicon.

## License

OpenTallas is released under the [MIT License](LICENSE).

See also [`CONTRIBUTING.md`](CONTRIBUTING.md), the
[code of conduct](CODE_OF_CONDUCT.md), and the [security policy](SECURITY.md) —
which distinguishes a security report (crafted input to the toolchain, a broken
tool pin) from a correctness report (a wrong number, a drifted artifact, a
failing gate). Correctness reports are welcome as ordinary issues; this project
is deliberately public about them.

[`NOTICE`](NOTICE) lists third-party material that is redistributed inside this
repository under its own terms and is **not** covered by MIT — notably ASAP7
standard-cell geometry embedded in three routed GDSII files, and one weight
tensor from a third-party model checkpoint committed as RTL test data. Read it
before redistributing.

Vendor comparator figures are quoted from published sources and remain the
property of their publishers. OpenTallas is independent of Taalas and of every
other vendor named here.
