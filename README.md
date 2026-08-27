# OpenTallas

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

The simulator is model-general. DeepSeek V4 Flash, DeepSeek V4 Pro, and Kimi K3
are representative input profiles, not constants embedded in the equations.
The standard analysis covers 200k and 1M context; mandatory batch 1, 8, and 64
points; audit points at batch 32 and 128; and an exhaustive integer-batch search
through each architecture's capacity for latency-, throughput-, balanced-, and
partial-TCO operating points.

The checked-in RTL and SPICE are disposable feasibility scaffolding. They are
not an implementation baseline and must not grow into one until the architecture,
interfaces, numerical contract, RAS/repair/DFT plan, and verification closure
criteria pass the specification gate in the program plan.

## Quick start

```bash
python3 -m pip install -e .
python3 tools/profile_hf.py --all
python3 run.py --standard
python3 decide.py results/standard/analytical.json
python3 tornado.py --standard
make verify
```

No model checkpoint is downloaded. The profiler uses small HTTP range requests
to read safetensors metadata. A full standard run is intended to fit on a CPU
workstation.

## What a result means

The code can validate accounting, architecture trends, constraint interactions,
and sensitivity to hardware assumptions. It cannot establish leading-node ROM
density, read bandwidth, yield, price, or packaging feasibility; those remain
foundry/OSAT measurements. See `docs/` and the generated result report for the
precise boundary between demonstrated, simulated, and unknown claims.
