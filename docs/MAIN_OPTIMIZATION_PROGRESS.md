# Architecture and optimization progress at main integration

The optimization branch through `6944da8f` has been fast-forwarded into local
`main`; ongoing work now uses `main`. The prior remote main was `c7093ba5`, an
ancestor of the branch, so no conflict resolution or history rewrite was needed.
The integration includes 539 commits of accumulated branch work. Pre-existing
uncommitted changes remain in the workspace; they are not part of the merge.
This report summarizes the architecture-first optimization work, not every
historical change in that branch.

## Assessment

The implemented accelerator path has materially improved, particularly in weight
reuse and memory-latency handling. It is **not yet qualified as a well-optimized
accelerator across all targets**. Strongest evidence covers optional G2/LQ8
runtime execution and bounded attention/control experiments. Current integrated
physical closure, broader engine balance and deployment-wide validation remain
unfinished. A target of 1 ns on ASAP7 is not an achieved whole-chip clock.

## Implemented architecture and demonstrated gains

The runtime path combines checked descriptors, local scheduling, tagged weight
banks, activation/scale windows, bounded read concurrency, complete-operand issue,
arithmetic, reserved output capacity and ordered write acknowledgement. Generation
ownership and fault drain cover the complete operation lifetime.

| Improvement | Matched evidence | Qualification |
|---|---|---|
| Pass-first weight reuse across output rows | K160 campaign cycles 708,336 → 203,111; weight bytes 207,336 → 34,556 | 71.33% fewer campaign cycles and 83.33% less weight traffic |
| Pass width independent of adder stages | K342 median successful-operation cycles 200,641.5 → 67,785.5 | Two-column pass fits the same SRAM; 66.22% fewer cycles, with increased activation traffic included |
| Deeper one-column residency | K513 median cycles 300,448.5 → 143,226.5 | 52.33% fewer cycles; no added SRAM or accumulator spill for resident whole-K passes |
| Configuration-time capacity policy | K343 median cycles 201,466.5 → 68,181.5 | Runner heuristic; not production runtime adaptation or global optimality |
| Four outstanding ordered weight reads | K344 median cycles 109,884 → 80,903.5 | 26.37% fewer cycles under matched queue4/delay12 service; default remains one |
| Same-line gather coalescing | K2 median cycles 704.5 → 570.5; weight bytes 836 → 212 | 19.02% fewer cycles, 74.64% fewer bytes; mapped transport area +1.06% |
| Exact exponential-result reuse | Softmax corpus cycles 1,115,880 → 767,158; physical evaluations 397 → 276 | Complete attention corpus improves 2.24%; duplicate-index fixture improves 58.64%; several cases unchanged |
| Shared dividend/quotient shift storage | Small-divider mapped area 330.457 → 251.898 µm²; flops 500 → 347 | 23.77% area reduction at unchanged transaction cycles; pre-layout timing still fails 1 ns |
| State modulo, payload capture and parallel admission | Mapped state area 3,919.979 → 3,573.645 → 3,492.799 → 3,448.841 µm² | Synthesis checkpoints; general modulo adds 34 apply cycles, later changes add none |
| Sparse-attention prefix count | Removes population-count arithmetic from admission | Same one-cycle interface; functional equivalence and containing operator pass; final timing pending |

These are separate source-bound experiments. Percentages are not additive.
Campaign cycles include fault/recovery work; successful-operation cycles use
modeled external service. Neither establishes whole-model inference speed or
silicon energy. Area measurements distinguish synthesis from final routing.

A subsequent widened-subtraction/borrow divider experiment was rejected: its
pre-layout worst slack worsened from about −1.7225 to −1.7994 ns at the same
1 ns target, with negligible area change. The shared-shift implementation was
restored and the experiment retained for review.

## Correctness and physical status

Loaded G2 campaigns check 2,234 exact outputs and 295 writes/acknowledgements,
including stalls, bounds, abort/restart and faults. Credit and coalescing tests
cover ownership during concurrent and stalled requests. State verification
includes 10,800 multi-slot equivalence cycles per simulator and full control
campaigns with 4,555 checks each. Sparse-attention reference checks cover nine
complete transactions. Divider checks cover 354 arguments at six step sizes in
both Icarus and Verilator; containing softmax results and cycle counts match.

The partial-replay scheduler has a passing extracted 1 ns block route, with
+0.033745 ns setup slack and 1,393.780 µm² standard-cell area. Recorded writer
closure is also at 1 ns; recorded Sinkhorn closure is at 2 ns. These do not
qualify the integrated chip.

The historical sequential-modulo state controller completed routing at 1 ns
with **−0.843259 ns setup slack and 1,895 setup violations**, despite clean
hold and reported physical checks. Its source predates later admission fixes.
Those fixes, current transport, integrated G2 and other candidates still need
final source-bound qualification. KV-index candidate and baseline first failed
IO-pin capacity; both retries use a matched larger floorplan at 22% utilization.
No pin-placement failure is reported as a timing verdict.

## Next priorities

1. Finish current physical jobs, audit retained artifacts and exact elaborated
   configurations, and optimize the measured remaining critical paths.
2. Improve general exact-exponential service capacity. Profiling attributes
   92% of the baseline attention corpus's active cycles to softmax exponential
   wait; the one-entry cache only helps repeated arguments.
3. Select divider step width from complete latency, area and routed timing,
   then qualify the containing exponential and softmax engines.
4. Complete production schedule selection, deeper tiling and descriptor-driven
   activation/format transport with explicit bandwidth and storage budgets.
5. Extend architecture and service-rate qualification across dense decode and
   prefill, MoE, attention/KV, vector/reduction and distributed execution, then
   validate every supported deployment and technology configuration.

The detailed evidence index and historical limitations remain in
[Architecture review summary](ARCHITECTURE_REVIEW_SUMMARY.md), with full-scope
acceptance in [Architecture-first plan](ARCHITECTURE_FIRST_OPTIMIZATION_PLAN.md).
The integration itself does not constitute a fresh full-repository regression;
reported validations belong to their recorded sources and configurations.
