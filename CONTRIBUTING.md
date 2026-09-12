# Contributing to OpenTallas

[Project home](README.md) · [Documentation](docs/README.md) ·
[Specification](spec/README.md) · [Current program report](docs/ABI3_PROGRAM_REPORT.md)

OpenTallas is an evidence-driven hardware research project. A good contribution
does more than make code pass: it keeps the implementation, specification,
generated artifacts, and public claim boundary aligned.

## Inbound license

By opening a pull request you agree that your contribution is licensed under the
same terms as this repository — the [MIT License](LICENSE) — and that you have the
right to license it that way. Please keep this in mind if any part of your change
derives from code, weights, or PDK material under other terms: say so in the pull
request, and see [`NOTICE`](NOTICE) for how third-party material is recorded here.

## Where the project needs help

<a id="areas"></a>
Start with [`STATUS.md`](STATUS.md) — it says what passes, what fails, and why.
Then pick an area below, or go straight to
[**`docs/CONTRIBUTOR_TASKS.md`**](docs/CONTRIBUTOR_TASKS.md), which lists 32
scoped tasks with a size estimate and the document that specifies each one.

Each area below is real, scoped work, not a wish.

### 1. Correct a number or an assumption

The highest-value contribution is showing that a figure is wrong. Every
quantitative claim in prose is bound by digest to the artifact that produced it,
so disagreements are checkable rather than rhetorical.

```sh
make check-figures          # every annotated figure vs its artifact
PYTHONPATH=. python3 tools/check_prose_figures.py --list   # see all bindings
```

Assumptions live in `configs/` — `configs/hardware/*.json` for device and vendor
figures (each with a source URL), `configs/models/*.json` for model geometry,
`configs/pdk/*.json` for process locks. `docs/ASSUMPTIONS.md` and
`docs/SOURCES.md` record where each came from.

**The open question worth attacking first:** gate **C3**. The analytical model
says ROM is 5.05× faster than the HBM comparator for Qwen3-8B at 8K; the cycle
model says 0.179×, i.e. 5.6× slower. The cycle model reproduces the *comparator*
to 1.5% and is 28.7× apart on the *subject*, and ~90% of the ROM cycle step is
unattributed. Either model could be the wrong one. See
`results/derived/qwen3_n5_design_target_reconciliation.json`.

### 2. Run more simulation, or close a verification rung

Six rungs gate end-to-end token correctness (G1a–G1f). `STATUS.md` lists each
blocker. Two concrete entry points:

- **G1e re-take** — the cheapest structural fix, ~10 min per store. Its evidence
  has drifted, so the only green G1 rung currently passes on stale sources.
- **`MAPPED_FAMILIES_WORD`** — one literal `0` in
  `tools/build_abi3_shipped_prefix_vectors.py` fail-stops the integrated vehicle
  at PC 32 and blocks **four** rungs (G1a–G1d). Flipping it is trivial;
  producing golden past it is the work.

Campaigns are single-threaded but independent, so they parallelise across cores.
Costs are recorded in the artifacts themselves — look for `wall_seconds` or
`verification_wall_seconds` before starting one. Needs Verilator 5.050 and Icarus
≥ 11.0; `tools/bootstrap_verilator_5_050.sh` installs the pinned build.

### 3. Port to another PDK, or add a constraint set

Physical results currently come from **ASAP7** (predictive, non-manufacturable),
with **SKY130** and **IHP SG13G2** used for circuit methodology. A port to
another open PDK — or a real foundry process, under whatever NDA terms apply —
would materially strengthen the physical claims, which are the weakest link.

Start at `docs/ROM_PHYSICAL_METHODOLOGY.md` and `docs/OPEN_PDK_SELECTION.md`.
Process locks are `configs/pdk/*_lock.json`; each pins tool versions and a
container image digest so a run is reproducible. `tools/bootstrap_sky130_pdk.sh`
and `tools/bootstrap_ihp_pdk.sh` show the expected shape of a new PDK bootstrap.

Constraint work is equally welcome and cheaper: the g2 cluster does not close
timing at 4.75 ns at any utilisation from 20 to 40 (slew bottoms at 3 violations
near util 35, then rises, and util 40 introduces the sweep's first hold
failures). The open question there is whether the **slew constraint itself** is
right — see `tools/audit_g2_cluster_operating_point.py`.

### 4. Improve performance

The design's own numbers are the target. `results/roofline/*/REPORT.md` and
`results/iso-node/*/REPORT.md` show where the model says time goes; the cycle
model in `runtime/cycle/` shows where it says the *implementation* spends it. The
~24× gap between them (area 1) is itself a performance question: if the cycle
model is right, the architecture is much slower than claimed and the reason is
not yet attributed.

### 5. Pay down the evidence backlog

**59 of 91** artifacts that pin source digests no longer bind current sources.
A drifted artifact is inadmissible, not wrong — its numbers were true of sources
that have since changed. Re-taking them is mechanical and parallelisable:

```sh
python3 tools/audit_source_currency_drift.py --output /tmp/drift.json
```

The worst single staler is `runtime/abi3/constants.py`, which alone invalidates
21 artifacts. Re-taking a family together is far cheaper than one at a time.

### 6. Fix the test-suite memory footprint

`tests/runtime` reports 64 failures as a group and 10 per-file. The gap is
**memory, not test isolation**: `tests/runtime/test_abi3_cycle.py` alone measures
72–84 GB peak RSS and a group run gets OOM-killed. Capping that footprint —
`pytest-forked`, per-file invocation, or reducing the fixture — would let the
group run in CI, which it currently cannot (a hosted runner has ~7 GB).

Pairwise runs already ruled out shared module-level state, so that is *not* where
to look.

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
