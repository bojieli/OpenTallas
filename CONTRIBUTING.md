# Contributing to OpenTallas

[Project home](README.md) · [Documentation](docs/README.md) ·
[Specification](spec/README.md) · [Current program report](docs/ABI3_PROGRAM_REPORT.md)

OpenTallas is an evidence-driven hardware research project. A good contribution
does more than make code pass: it keeps the implementation, specification,
generated artifacts, and public claim boundary aligned.

## Before you begin

Read the entry point that owns the area you plan to change:

| Change | Required context |
|---|---|
| Analytical model or headline comparison | [Methodology](docs/METHODOLOGY.md), [assumptions](docs/ASSUMPTIONS.md), [sources](docs/SOURCES.md), and the affected generated report |
| ABI, interface, numeric, firmware, or hardware behavior | [Specification index](spec/README.md), [change control](spec/CHANGE_CONTROL.md), and the affected normative document |
| Compiler or runtime | [Compiler guide](compiler/README.md), ABI documents, and the relevant execution plan |
| RTL | [RTL inventory](rtl/README.md), verification plan, and the corresponding campaign report |
| Circuit or physical method | [SPICE guide](spice/README.md), [ROM physical methodology](docs/ROM_PHYSICAL_METHODOLOGY.md), and the relevant PDK boundary |
| Documentation or evidence claim | [Documentation hub](docs/README.md), [evidence ledger](docs/EVIDENCE_LEDGER.md), and the source artifact |

The worktree may contain experiments, generated evidence, or checklists being
updated by another contributor. Preserve unrelated edits. In particular, do not
rename, move, regenerate, or reformat a live plan/checklist merely to improve
navigation; add or improve an index first and coordinate structural changes with
the document's owner.

## Development setup

The core Python package requires Python 3.10 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[test,compiler]"
```

That combination is the minimum for collecting the repository's full Python
test suite. Install the other optional dependencies only when your work needs
them:

```bash
python3 -m pip install -e ".[plot]"           # rendered plots/assets
python3 -m pip install -e ".[qwen3]"          # local Qwen execution work
```

Pinned external RTL, physical-design, PDK, and circuit tools are documented in
the subsystem guides. They are intentionally not hidden behind the basic Python
installation.

## Make a focused change

1. Identify the source of truth before editing. A generated report should be
   changed through its producer; a behavioral contract should be changed in the
   specification before or with its implementation.
2. Keep the patch scoped. Do not fold unrelated generated artifacts, local build
   products, or another contributor's work into the change.
3. Add the narrowest test that would have caught the defect or proves the new
   behavior.
4. Regenerate only the artifacts owned by the changed producer.
5. Update the evidence boundary and documentation when the externally visible
   meaning changes—not only when a number changes.

## Validation

Run checks in proportion to the surface you changed.

### Documentation and evidence

```bash
make check-figures
make spec-check
```

`check-figures` verifies provenance annotations in prose against their committed
JSON, CSV, and Markdown producers. `spec-check` verifies the governed
specification inventory, requirements, budgets, and traceability contract.

### Python, compiler, and runtime

```bash
make test
make abi3-test
```

Use a focused `pytest` invocation while iterating, then run the owning suite
before handoff.

### RTL and circuit work

```bash
make -C rtl pre-synth-verify
make -C rtl verify
make -C spice verify
```

The full repository flow is intentionally heavier:

```bash
make verify
```

Do not report a check as passing when it was skipped because a required external
tool was unavailable. Record the skipped gate and the tool/version needed to run
it.

## Specifications and ABI changes

Externally visible behavior is controlled, even when the implementation change
looks small.

- Follow [`spec/CHANGE_CONTROL.md`](spec/CHANGE_CONTROL.md).
- Update normative prose and machine-readable records together.
- Preserve requirement IDs and traceability; do not silently repurpose them.
- Regenerate/check published ABI records with `make abi3-spec`.
- Include compatibility, migration, and fail-closed behavior in the change.
- Keep analytical product envelopes separate from public-reference RTL proxy
  parameters.

An implementation passing its local tests does not authorize a specification
change after the fact.

## Generated artifacts

Generated evidence is reviewable source material, not disposable output.

- Prefer the committed producer command over hand edits.
- Keep inputs, tool identity, command, hashes, evidence grade, and claim boundary
  with the result when the schema provides them.
- Review generated diffs for unexpected scope changes; do not commit an entire
  result tree because one file was intended to change.
- [`docs/PROGRAM_STATUS.md`](docs/PROGRAM_STATUS.md) is generated by
  `make abi3-status` and should not be edited manually.
- Visual assets under [`docs/assets/`](docs/assets/) are generated by
  `python3 tools/render_public_assets.py`; follow their
  [provenance contract](docs/assets/README.md).
- Avoid cleaning shared result directories while another campaign may be using
  them. `make clean-results` is broad and should be treated accordingly.

## Writing technical documentation

Write for a reader who did not participate in the experiment.

- Lead with the question, result, and boundary; put chronology and debugging
  detail later.
- Define the comparator. “Faster” is incomplete without workload, context, batch,
  technology, area/capacity rule, parallelism, and metric.
- Keep per-user latency, aggregate throughput, resident capacity, energy, cost,
  and throughput density separate.
- Call deterministic conservative/central/aggressive scenarios *envelopes*, not
  confidence intervals.
- Distinguish planned, implemented, executed, correlated, synthesized, routed,
  extracted, measured, and fabricated evidence.
- Link to the artifact that produces a headline value and add a machine-resolvable
  figure annotation where required.
- Put durable documents in the appropriate section of
  [`docs/README.md`](docs/README.md). Avoid creating another parallel status page.
- Preserve correction history in the owning technical record when it is needed
  for auditability; keep the project landing page focused on current results.

## Review checklist

Before handing off a change, confirm:

- [ ] The patch has one clear purpose and preserves unrelated work.
- [ ] Tests cover the changed behavior at the appropriate evidence level.
- [ ] Generated files came from their documented producer.
- [ ] Specifications, registries, schemas, and traceability agree.
- [ ] Every performance comparison identifies workload, context, batch, metric,
      technology, and comparator.
- [ ] Important prose figures resolve with `make check-figures`.
- [ ] The document or report states what the result does not prove.
- [ ] New durable documentation is linked from the documentation hub.
- [ ] No simulation, proxy, or public-PDK result is presented as product silicon.

OpenTallas values corrections and negative results. Finding that a benefit
disappears under a fairer comparator or a more conservative envelope is a useful
contribution when the evidence is reproducible and the boundary is clear.
