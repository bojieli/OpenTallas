# ROM redesign feasibility audit

Status: analytical review in progress; no new RTL or workload simulation.
The previous goal turn made progress by rejecting the unchanged sequential
recurrence. This checkpoint evaluates the proposed alternative without accepting
a new numerical contract.

## Blocked accumulation is a separate numerical design

The shipped Qwen ROM capability names `bf16_bf16_fp32_sequential_rne_v1`.
The existing RE8 endpoint implements adjacent-pair combination of block partials;
that implementation alone does not qualify replacing sequential accumulation.

A 256-element dot product supplies a simple counterexample. All entries are zero
except products at indices 0, 128 and 129: `2^24`, `1`, and `-2^24`. These are
exact BF16 products (4096×4096, 1×1 and −4096×4096). Sequential binary32 RNE
accumulation returns **0** because `2^24 + 1` rounds back to `2^24`. Independent
128-element block sums return `2^24` and `1−2^24`; their tree sum returns **1**.
No overflow, nonfinite input or approximate transcendental is involved.

Consequently a blocked implementation needs an explicitly qualified numerical
contract. Matching a reference changed to use the same blocked arithmetic is not
independent qualification. Preserve sequential execution; do not silently amend
the shipped capability. Even vendor token agreement on a corpus would establish
only that tested scope, not universal sequential bit equivalence.

## Work and recurrence bounds

Use the proposed 393,216 system lanes and 1 GHz clock. For each dependent operator,
charge the larger of total products divided by lanes and the longest block's
sequential recurrence. QKV and gate/up are fused optimistically. Accumulation
recurrence is one, two or three cycles; interleaving independent blocks may hide
pipeline latency but cannot shorten a block's own chain. Sum dependent operator
bounds. This is static arithmetic, not a scheduled latency prediction.

| Block size | Ideal one-cycle recurrence floor | Ideal three-cycle recurrence floor | One-cycle floor at 65% utilization cap | Three-cycle floor at 65% cap | Partial payload required within 32 µs |
|---|---:|---:|---:|---:|---:|
| 32 | 19.259 µs | 22.319 µs | 29.651 µs | 30.731 µs | 29,563 B/cycle |
| 64 | 20.015 µs | 31.535 µs | 29.651 µs | 37.535 µs | 14,781 B/cycle |
| 128 | 24.623 µs | 56.879 µs | 32.927 µs | 58.091 µs | 7,391 B/cycle |
| 256 | 38.447 µs | 112.175 µs | 44.267 µs | 113.027 µs | 3,695 B/cycle |

The utilization cap is the proposal's assumption, not a measurement. Reduction,
launch/drain, bank conflicts and communication remain excluded. The 128-element
variant already exceeds the 32 µs allocation at that cap with an ideal one-cycle
recurrence. Deeper pipelining makes the recurrence issue worse unless a mapping
has enough additional independent work and sufficient latency budget.

Smaller blocks trade recurrence length for reduction work. Block32 requires about
7,342 reduction adds/cycle across the system to fit that same budget; block128
requires about 1,799. The partial-byte figures count leaf payload only, not all
intermediate tree traffic or buffering. Neither can be equated to a global bus:
placement must keep most partials local and explicitly count cuts and upper trees.
The 24 mm²/die reduction allocation has no current proof of supporting those
rates. Block32 also changes the numerical association again.

## Decision and next feasibility gates

The 85/75 µs design remains rejected under the unchanged sequential contract.
The existing block128 alternative also fails the current linear budget under
its configured utilization assumption, before overhead. No proposed alternative
is accepted yet.

Continue feasibility in this order:

1. Establish the admissible numerical contract from specifications and existing
   qualification evidence; retain the exact counterexample as a guard against
   claiming universal equivalence.
2. Analyze placement and service for block32/64/128 alternatives, including active
   matrix stripes, finite local ports, tree depth and partial-buffer capacity.
   Require a feasible complete resource budget before selecting a candidate.
3. Compare exact sequential alternatives and revised latency targets against an
   independently optimized HBM design. A common numerical bottleneck on both
   machines can erase ROM's memory advantage.
4. Continue macro-density/port evidence, collective latency, numerical-function
   fallback and power checks. Resolving matrix recurrence does not resolve these.

Reproduce with `python3 tools/audit_blocked_rom_feasibility.py`.
The [calculation record](../results/architecture/blocked_rom_feasibility.json)
contains per-operator shapes, bounds, source hashes and the counterexample.
The [architecture proposal](ROM_FIRST_ARCHITECTURE_PROPOSAL.md) remains the design
candidate; this audit controls whether it is ready for implementation.
