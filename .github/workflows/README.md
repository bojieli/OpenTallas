# CI scope

`ci.yml` runs only what is demonstrably green on a bare checkout, so that a red
badge always means a regression rather than a known gap. Three jobs:

| Job | Needs | Measured cost | Fails the build? |
|---|---|---|---|
| `evidence-checks` | Python 3.10 + numpy | ~5 s | yes |
| `fast-tests` | `pip install -e '.[test]'` | ~45 s | yes |
| `gate-board` | standard library only | ~0.5 s | no — informational |

All timings were measured at `b0f92a9` in a fresh virtualenv containing nothing
but the declared dependencies, not estimated.

## Memory budget

A hosted `ubuntu-latest` runner has ~7 GB. Peak RSS of everything in `ci.yml`,
measured with `/usr/bin/time -v`:

| Job step | Peak RSS |
|---|---:|
| `tests/sim` | 1.29 GB |
| `make check-figures` | 0.54 GB |
| `tests/abi3` | 0.13 GB |
| `make iso-node` | 0.07 GB |
| `tests/qwen3` | 0.05 GB |
| `make check-chip-architecture` | 0.01 GB |

Nothing is within 5× of the limit. **Measure peak RSS before adding any job**:

```sh
/usr/bin/time -v python3 -m pytest <target> 2>&1 | grep 'Maximum resident'
```

The excluded suites are not merely slow — they cannot physically run on a hosted
runner. `tests/runtime/test_abi3_cycle.py` alone measures 72–84 GB and has been
OOM-killed on a 250 GB machine.

## Why the gate board does not fail the build

`tools/check_redesign_gates.py` exits 1 while any terminal gate fails, and three
of four currently do. That is the honest state of the program, not a build break,
so the job prints the board into the run summary and exits 0. When the terminal
gates pass, this job should start enforcing its exit code.

## What is deliberately excluded

| Excluded | Why |
|---|---|
| `tests/runtime` | 64 failures as a group, 10 per-file, and only **4** when the three worst files run together. The gap is **memory, not test pollution**: `test_abi3_cycle.py` exceeds 70 GB RSS and a group run is OOM-killed (measured rc=137, `anon-rss:72208572kB`, zero failures recorded before the kill). A GitHub runner has ~7 GB, so this cannot run in CI at all until the footprint is fixed. |
| `tests/compiler` | 67 failures at HEAD, dominated by source-currency drift (64 of 96 pinning artifacts drifted). A backlog, not a regression. |
| RTL, synthesis, ORFS | Need pinned Verilator 5.050, Icarus, Yosys 0.68, OpenROAD and a PDK. See [`docs/REPRODUCIBILITY.md`](../../docs/REPRODUCIBILITY.md) tiers 2–3. |
| Long campaigns | Several artifacts record `verification_wall_seconds` near 16,500 s per store. |

Each exclusion is a tracked debt, not a permanent decision. Capping
`tests/runtime`'s memory footprint should add it as its own job; paying down the
drift backlog should add `tests/compiler`.

Note the correction: an earlier version of this file attributed the
`tests/runtime` gap to an "isolation bug" and order-dependent shared state. That
was inferred from solo-clean-plus-group-red without reproducing it, and it is
wrong — three pairwise runs show no file poisoning another, and the group run is
simply OOM-killed. Anyone hunting module-level caches here is looking in the
wrong place.

## The determinism gate

`evidence-checks` regenerates the analytical artifacts and then requires
`git status --porcelain` to be empty. This is the property the entire evidence
chain rests on: figures in prose are checkable only because the artifacts behind
them reproduce byte-for-byte. If that step ever fails, treat it as the most
serious signal in CI — not a flake.

It has already earned its place. A doc edit in `ae2bcde` changed
`CHIP_RESOURCE_BUDGETS.md` without regenerating the prose-figure census; the
`check-figures` step catches that class of mistake in under two seconds.

## Running the same checks locally

```sh
make spec-check check-figures check-evidence-grades check-chip-architecture
PYTHONPATH=. python3 -m pytest tests/abi3 tests/qwen3 tests/sim -q
PYTHONPATH=. python3 tools/check_redesign_gates.py   # exits 1 by design
```
