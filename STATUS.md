# Status: what is done, what is not

This page is the honest answer to "does it work yet?". It is written for someone
deciding whether to trust, use, or contribute to this project.

**One command supersedes this page.** It needs nothing but Python 3.10 and the
standard library, and it re-evaluates every gate against the artifacts on disk:

```sh
PYTHONPATH=. python3 tools/check_redesign_gates.py
```

If this page and that command ever disagree, the command is right. It exits
non-zero while any terminal gate fails.

---

## The headline

**9 of 19 rungs pass. 1 of 4 terminal gates passes.**

The project has a working analytical model, a working compiler and runtime, a
cycle model, synthesizable RTL, and routed physical blocks. It does **not** yet
have end-to-end token correctness in RTL, a time-per-output-token measurement, or
agreement between its two performance models. Nothing has been fabricated.

---

## The gate board, in plain language

### Terminal gates — the release criteria

| Gate | State | What it means |
|---|---|---|
| **G1** | ❌ fail | The integrated RTL does not yet reproduce the reference model's tokens. 8 of 10 requirements unmet. |
| **G2** | ✅ pass | One routed netlist exists containing the microsequencer and datapath array, DRC 0, antenna 0. *See the caveat below.* |
| **G3** | ❌ fail | No correctness-qualified time-per-output-token measurement exists. `results/tpot/` is empty. |
| **G4** | ❌ fail | The cycle model is ~10× off the measured RTL control plane; 32 of 32 ratios outside the acceptance band. |

> **G2's caveat, stated plainly.** G2's evaluator checks tree-cleanliness,
> `flow_completed`, macro count, DRC and antenna. It does **not** read
> `design.closed`, the clock period, or f<sub>max</sub> — and the record it cites
> reports `closed: false` with one max-slew violation, at a 16 ns period the
> artifact itself labels a characterisation probe. G2 passing does not mean the
> cluster closes timing. Fixing this is [a contributor task](#g2-semantics).

### Verification rungs (G1a–G1f)

| Rung | State | Blocker |
|---|---|---|
| G1a | ❌ | 4 operator-equivalence classes uncovered on ROM (`DMA.GATHER` + 3 `TENSOR.MATMUL`), 3 on HBM. 0 mismatched words across 86,789 compared — this is a coverage gap, not a wrongness gap. |
| G1b | ❌ | 11 of the layer's 19 operators never execute; all 11 marked `blocked_only_by_the_boundary`. |
| G1c | ❌ | The RTL→RTL handoff half is unmeasured. The loop half already passes (36 of 36 invocations). |
| G1d | ❌ | No token emitted; the run fetches 33 instructions and never reaches the five head sites. |
| G1e | ✅ | Passes — but 11 of its 54 pinned sources have drifted, 10 of them the RTL under test. [Re-take needed](#re-take-g1e) (~10 min per store). |
| G1f | ❌ | One blocker left: the reduced program exists on both stores and all three probed engines admit its geometry, but no vehicle runs it end to end. |

**G1a–G1d share one physical cause.** `tools/build_abi3_shipped_prefix_vectors.py`
emits case-record word 59 (`MAPPED_FAMILIES_WORD`) as a literal `0`, so the six
mapped families are never admitted and the vehicle fail-stops at PC 32,
`DMA.SCATTER`, trap class 4. One word blocks four rungs.

### Design gates (D1–D5) — all pass

Bit-identity, MAC-per-lane-cycle, lane count verified in the netlist, per-MAC
area and period against baseline, and distinct failure modes. `D4`'s *baseline*
record carries `worktree_dirty: true`, which by this project's own rule makes it
inadmissible — the candidate is clean. [Contributor task](#d4-baseline).

### Comparison gates (C1–C4) — the apple-to-apple fairness gates

| Gate | State | Note |
|---|---|---|
| C1 | ✅ | `derive_cycle_machine.py --check` exits 0. Self-contained, reads no drifted artifact. |
| C2 | ❌ | 8 of 15 machine pairs fail `comparable`. **6 of 15 cells are `unbuildable`, so `require_all` cannot go green regardless.** |
| C3 | ❌ | The cycle model and the analytical model disagree on the binding constraint — by ~24×, in the direction that reverses the headline. See below. |
| C4 | ✅ | Worst total-over-binding-floor 8.22×, under the 100× ceiling. Only 2 records exist and both are Qwen3; no DeepSeek derived-run record exists at all. |

---

## The disagreement that matters most

`README.md` publishes **5.05×** ROM-over-GPU for Qwen3-8B at 8K, from the
analytical model. For the identical design pair, the cycle model records
`cycle_ratio: 0.179` — ROM **5.6× slower**.

The asymmetry is what makes this load-bearing rather than a tolerance question:

| Side | cycle ÷ analytical |
|---|---:|
| HBM comparator | **1.0148** — reproduces to within 1.5% |
| ROM subject | **28.686** |

A cross-check that validates the comparator and fails only the subject is
evidence about the subject. About 90% of the ROM cycle step is not attributed to
any measured term. This is gate **C3**, and it is unresolved. Until it is, read
the analytical advantage as an upper bound from a roofline projection whose own
higher-fidelity cross-check does not reproduce it.

**This is the single most valuable thing a contributor could work on.**

---

## Evidence health

| Measure | Value |
|---|---|
| Artifacts pinning source digests | 91 |
| ...that no longer bind current sources | **59 (65%)** |
| Worst single staler | `runtime/abi3/constants.py` — 21 artifacts |
| Test groups fully green | `tests/abi3`, `tests/qwen3`, `tests/sim` |
| `tests/runtime` real failures | 10 (per-file); 64 as a group, which is a memory artefact |
| `tests/compiler` failures | 67, dominated by the drift above |

A drifted artifact is **inadmissible**, not wrong: its numbers were true of
sources that have since changed. Re-taking them is mechanical, parallelisable
contributor work — see [Correct or refresh evidence](CONTRIBUTING.md#areas).

---

## What does not exist

State this plainly so nobody has to infer it:

- No tapeout, no fabricated device, no packaged system, no silicon benchmark.
- No foundry signoff and no foundry PDK. Physical results use **ASAP7**, a
  predictive, non-manufacturable academic PDK, and **SKY130**/**IHP SG13G2** for
  circuit methodology.
- No GPU was run. Comparator figures are quoted from vendors' published sources,
  cited by URL in `configs/hardware/*.json`.
- No full-chip place-and-route, and no DRC/LVS against a manufacturable process.
- No TPOT measurement (gate G3).

---

## Where to help

[`docs/CONTRIBUTOR_TASKS.md`](docs/CONTRIBUTOR_TASKS.md) lists 32 scoped tasks
with sizes and the document specifying each; `CONTRIBUTING.md` explains how to
submit. The tasks this page refers to:

<a id="g2-semantics"></a>
**G2 semantics** — decide whether G2's evaluator should read `design.closed`, or
whether the claim should be reworded to say what it actually checks. Currently a
reader could reasonably believe G2 means the cluster closes timing. It does not.

<a id="re-take-g1e"></a>
**Re-take G1e** — the cheapest structural fix on the board. The rung's own
`cost_measurement` block records `end_to_end_seconds` 586.08 per store and
`measured_all_stores_seconds` 1169.01, so about 20 minutes for both. It converts
the only green G1 rung from passing-on-stale-evidence to actually passing, and it
feeds G1c and the composition certificate, which both read it.

<a id="d4-baseline"></a>
**D4 baseline** — `results/physical_abi3/asap7/matmul_bf16_sram_engine/pnr.json`
carries `worktree_dirty: true` and one drifted source. By the project's own
admissibility rule it should not be used as a baseline; it is never tested
against that rule.

**The `MAPPED_FAMILIES_WORD` boundary** — flipping the word is trivial;
producing golden past it is costed in MACs, not hours (the LM head alone is
622,329,856 MACs, ~5.7 h whole or ~1.4 h sharded), and the head is separately
refused above 4,096 weight rows.

**Close C3** — attribute the unexplained ~90% of the ROM cycle step, or
establish which of the two models is wrong.
