# OpenTallas

![Conceptual OpenTallas fixed-model decode architecture](docs/assets/architecture-overview.svg)

> **Research status:** OpenTallas has checked analytical studies, synthesizable
> public-reference RTL, open-tool verification, local open-PDK ROM methodology
> slices, and a partial predictive-PDK digital physical proxy. It does **not**
> have a target-node ROM macro, a full placed-and-routed chip or wafer, or
> fabricated OpenTallas silicon.

## Start here

- **New to the project?** Read
  [`docs/OVERVIEW.md`](docs/OVERVIEW.md) for the plain-language rationale, a
  one-token walkthrough, architecture and layout views, simulation results, the
  exact 9,399-tokens/s derivation, and a clear “built versus not built” boundary.
- **Using a figure?** Read the
  [`visual asset provenance contract`](docs/assets/README.md). It labels each
  image as conceptual, simulation-derived, or rendered from archived physical
  geometry and records the forbidden interpretations.
- **Reviewing the headline studies?** Use the N7/HBM2e/A100
  [`architecture-attribution report`](results/iso-node/n7_architecture_attribution/REPORT.md)
  and the N4-class/HBM3e/B300
  [`market report`](results/iso-node/leading_node_market/REPORT.md).
- **Implementing or auditing the design?** Start at the governed
  [`specification index`](spec/README.md), then consult the
  [`methodology`](docs/METHODOLOGY.md), [`sources`](docs/SOURCES.md), and
  [`assumptions`](docs/ASSUMPTIONS.md).

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

The primary-source register is in [`docs/SOURCES.md`](docs/SOURCES.md), and every
midpoint/runtime/cost convention is recorded in
[`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md). Reported cost is explicitly partial
TCO (hardware/NRE amortization plus active electricity), not a complete business
case or cloud price.

The generated standard report is in
[`results/standard/REPORT.md`](results/standard/REPORT.md); the focused Qwen3-8B
control analysis is in
[`results/standard/QWEN3_8B_ADDENDUM.md`](results/standard/QWEN3_8B_ADDENDUM.md).

The simulator is model-general. DeepSeek V4 Flash and DeepSeek V4 Pro are target
hypotheses; Kimi K3 is a long-context/MoE stress control; and Qwen3-8B is a small
dense control. The long-context models run at 200k and 1M resident tokens, while
Qwen3-8B runs at the requested 8K context. Every model covers mandatory batch 1,
8, and 64 points, audit points at batch 32 and 128, and an exhaustive integer-batch
search through each architecture's capacity for latency-, throughput-, balanced-,
and partial-TCO operating points. GPU candidates span B200/B300 x1, x2, x4, x8,
and x16 analytical configurations so the dense control is not forced onto an
inappropriately large cluster.

The architecture/specification gate has passed for public-reference RTL only. The
checked `ot_*` hierarchy is now a controlled implementation baseline with strict
static/CDC/RDC, formal, dual-simulator, and source-hashed evidence. A warning-clean,
source-checked campaign also closes 87 enumerated public RTL fault/containment sites
under both Icarus and pinned Verilator 5.050; this is not physical or ATPG coverage.
The small legacy tile and open-PDK SPICE remain feasibility proxies. Neither baseline
authorizes product silicon: target numerical qualification, stage/reticle/pipeline
fault and degradation coverage, code/functional coverage closure, verified-baseline
synthesis, target macros/PDK, package, and foundry signoff remain mandatory gates.

## Quick start

```bash
python3 -m pip install -e .
python3 tools/profile_hf.py --all
python3 run.py --standard
python3 decide.py results/standard/analytical.json
python3 tornado.py --standard
make fault-campaign
make verify
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
