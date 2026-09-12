# What you can reproduce, and what you cannot

This repository's claims are backed by artifacts under `results/`, each pinning
the SHA-256 of the sources it was produced from. This page states plainly which
of those you can re-derive on your own machine and which you cannot, so that
nobody has to discover the boundary by hitting it.

Timings below were measured on a 32-core x86-64 Linux host on 2026-09-12 at
commit `764c57d`. They are wall-clock for a warm filesystem.

---

## Tier 1 — a bare checkout, Python 3.10+, and numpy

Nothing else. No EDA tools, no PDK, no model weights, no `pip install -e .`
(most tools insert their own `sys.path`).

| Command | Time | What it establishes |
|---|---|---|
| `PYTHONPATH=. python3 tools/check_redesign_gates.py` | **0.47 s** | Prints all 19 gate rungs with pass/fail and the reason each failing rung reports. Exits 1 while any terminal gate fails. **Start here.** |
| `make spec-check` | **0.06 s** | Schema, interface, traceability and budget consistency across the specification |
| `make model-traffic` | **0.03 s** | Regenerates `results/model-traffic/REPORT.md` |
| `make iso-node` | **2.97 s** | Regenerates both technology studies, including the per-user figures the README quotes |
| `make check-figures` | **1.66 s** | Verifies every annotated figure in prose against the artifact that produced it |
| `python3 infersim.py --model configs/models/qwen3-8b.json --context 8192 --batch 1` | **0.04 s** | One analytical operating point from first principles |

**The property worth checking first.** Run the regenerating targets, then:

```
git status --porcelain
```

It returns nothing. The analytical artifacts are byte-identical on
regeneration, so the numbers in the documents are checkable rather than
asserted. If that ever stops being true, treat every figure in this repository
as suspect until it is true again.

Tier 1 covers the **analytical** layer only: a roofline/first-principles model
of both the ROM design and its HBM/GPU comparator. It is a projection, not a
measurement of hardware.

---

## Tier 2 — with open EDA tools installed

Adds functional simulation and RTL equivalence work. You need pinned tool
versions; `tools/bootstrap_verilator_5_050.sh` installs the one this
repository characterises against, and other requirements are listed in
`docs/ABI3_PHYSICAL_VIEWS.md`.

| Requires | Gets you |
|---|---|
| Verilator 5.050, Icarus ≥ 11.0 | The RTL campaigns under `results/rtl/`, including the operator-equivalence and control-plane evidence the G1 rungs read |
| Yosys 0.68 | Synthesis-frontend checks |
| `pytest` plus the `test` extra | 7,445 tests collect in ~6.5 s. Tests needing a tool absent from `PATH` skip rather than fail |

Costs here are hours, not seconds, and the artifacts record their own: several
campaigns carry `verification_wall_seconds` near 16,500 s per store. Read the
cost field before starting one.

**Known issue:** run `tests/runtime` as a group and it reports 64 failures;
run the same files individually and 10 remain. 54 are order-dependent, from
shared module-level state, and three files pass completely alone. Until that is
fixed, triage per-file and quote failure counts with the execution mode
attached.

---

## Tier 3 — what you cannot reproduce without more than tools

These are the honest limits. Each needs an input this repository does not and
should not ship.

**Physical design results** (`results/physical_abi3/**`, `results/asap7_physical/**`)
need an installed ASAP7 PDK and the pinned OpenROAD/ORFS container image. ASAP7
is a *predictive, non-manufacturable academic* PDK — every frequency, area and
power figure derived from it is a projection in a research process node, **not a
silicon result and not a foundry claim.** No number in this repository has been
measured on fabricated hardware.

**Anything reading real model weights** needs the checkpoints from their
upstream sources under their own licences: Qwen/Qwen3-8B,
deepseek-ai/DeepSeek-V4-Flash-0731, deepseek-ai/DeepSeek-V4-Pro-0813. Expect
tens of GB of download and disk. `compiler/qwen3/README.md` documents the exact
revision and free-space requirement. One tensor is committed as test data; see
`NOTICE`.

**Vendor comparator figures** (NVIDIA, Cerebras, Taalas and others) are quoted
from published sources, cited by URL in `configs/hardware/*.json`. They were not
measured here, and no GPU was run.

**Long campaigns** — some individual runs are hours, and the artifacts record
it. A few record more than a day of simulated work.

---

## The state of the evidence

Two facts a reader should have before trusting any figure:

1. **The gate board is mostly red, on purpose.** 9 of 19 rungs pass and 1 of 4
   terminal gates. `tools/check_redesign_gates.py` prints the current state in
   under half a second and exits non-zero while terminal gates fail. Absence of
   evidence is recorded as failure, never as "not evaluable".

2. **Source-currency drift is real and measured.** 64 of 96 artifacts that pin
   source digests no longer bind the current tree
   (`results/derived/source_currency_drift.json`). A drifted artifact is
   inadmissible as evidence: its numbers were true of sources that have since
   changed. Drift is not wrongness, but it is not currency either, and the
   regeneration backlog is not yet paid down.

If a number matters to you, check the gate rung that covers it and whether its
artifact still binds current sources. Both are mechanical checks, and both are
in Tier 1.
