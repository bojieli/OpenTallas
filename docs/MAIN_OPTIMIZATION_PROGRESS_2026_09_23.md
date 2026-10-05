# Main optimization progress — 2026-09-23

The accumulated optimization work is integrated into `main`. Before this report,
local HEAD and freshly fetched GitHub main both pointed to `e5fc05f2`; no further
branch merge was necessary. Future work continues on `main`. Unrelated workspace
edits are excluded from this report's commit.

## Assessment and refined architecture

The accelerator has substantial demonstrated improvements, but significant
integrated performance work remains. It is not yet qualified as highly efficient
across all supported targets. The architectural direction is local scheduling,
retained weight reuse across output rows, bounded outstanding memory requests,
coalesced operand delivery, complete-operand issue, and ordered completion.
Attention uses exact-result reuse and an exponential-only specialization to
avoid implementing an unused sigmoid service. Arithmetic and control changes
are selected using containing-engine latency as well as routed block timing.

## Demonstrated progress compared with earlier versions

| Change | Before → after | Scope and qualification |
|---|---|---|
| Pass-first retained weight reuse | K160: 708,336 → 203,111 cycles; 207,336 → 34,556 weight bytes | Campaign result; same retained SRAM capacity |
| Pass width independent of adder depth | K342: 200,641.5 → 67,785.5 median cycles | Two-column residency; increased activation traffic accounted for |
| Four outstanding ordered weight reads | K344: 109,884 → 80,903.5 median cycles | Matched queue4/delay12 service; configurable, default remains one |
| Same-line gather coalescing | K2: 704.5 → 570.5 median cycles; 836 → 212 weight bytes | Current credit4 transport passes final extracted 1 ns block checks |
| Exact exponential-result reuse | Softmax: 1,115,880 → 767,158 cycles | 31.25% fewer softmax cycles; complete attention corpus improves 2.24% |
| Exponential-only softmax specialization | 12,050.452 → 10,895.162 µm² mapped area | 9.59% reduction; matched workspace-source synthesis, not routed closure |
| Balanced multiplier reduction tree | 1,745.660 → 1,714.480 µm² routed area; setup −0.312287 → +0.117856 ns | Matched 1 ns ASAP7 block routes; selected tree16 passes timing and physical checks, transaction cycles unchanged |
| KV live-prefix count encoding | 1,080.380 → 911.483 µm² routed area; setup −0.139148 → +0.145303 ns | Matched 1 ns routes; current block passes, no added cycles |
| Wide-divider shared storage | 626.633 → 546.518 µm² mapped area; 162 fewer sequential cells | Arithmetic regression passes; physical results remain separately source/configuration bound |

These percentages are independent and must not be added. Simulation cycles,
mapped area, final routed area and whole-model throughput are distinct metrics.
Standalone 1 ns passes do not establish a 1 GHz integrated accelerator or energy
savings. The specialization measurements retain the exact workspace source,
including pre-existing divisor tuning; they are not measurements of an otherwise
pristine committed tree.

## Latest validation and remaining bottlenecks

The integrated multiplier passes exact-product tests and the full 4,200-case
exp/sigmoid corpus with 6,637,132 checks. Real softmax passes nine numerical cases
and two refusals at unchanged latency. The specialized attention path passes
nine complete transactions at 2,388,699 active cycles.

The production state controller still fails the extracted 1 ns target with
−0.663333 ns setup slack. Its critical byte-accounting path combines selection,
multiplication and accumulation. An isolated candidate separates operand capture,
registered multiplication and retirement, adding two cycles per applied entry.
Directed tests pass in both simulators. The newly completed containing
microsequencer campaign also passes in Icarus and Verilator: 65 cases, 53 programs,
185 issues, 460 resolved views and 4,555 checks per simulator. All recorded source
hashes were verified against the workspace before retaining the result. This
campaign checks control/state behavior; engine datapath arithmetic is outside
its scope. Production state RTL remains unchanged pending physical and latency
qualification. No final apply-pipeline route record was available at this report.

The exponential-only softmax route likewise has no final record yet and predates
the multiplier-tree integration. Current integrated softmax must be physically
qualified. Smaller divider steps and larger multiplier chunks are not automatic
wins: the tested step3 divider increases softmax cycles by 76.79%, while tree32
costs 67.84% more routed area than tree16 and fails the tested physical acceptance.

## Next priorities

1. Finish source-bound physical qualification of the state pipeline and current
   containing attention/arithmetic engines; accept changes only when useful
   throughput, area and correctness support the tradeoff.
2. Qualify the integrated G2 path, including operand transport, output capacity,
   control fanout and the production scheduling policy.
3. Extend the architecture evaluation across dense, MoE, attention/KV, vector
   and distributed execution, supported precisions and target technologies.
4. Pipeline remaining measured critical paths after checking recurrence latency,
   memory service rate, buffering and complete-engine throughput.

The broader architecture-first objective remains incomplete.

## Evidence

- [Architecture-first plan](ARCHITECTURE_FIRST_OPTIMIZATION_PLAN.md)
- [Detailed architecture decisions and physical evidence](ARCHITECTURE_REVIEW_SUMMARY.md)
- [Original main integration report](MAIN_OPTIMIZATION_PROGRESS.md)
- [State-pipeline containing campaign](../results/rtl/state_apply_pipeline/containing_campaign.json)
- [Multiplier integration decision](../results/rtl/wide_mul_tree_integration/route_decision.json)
- [Softmax specialization comparison](../results/rtl/softmax_exp_only/comparison.json)
