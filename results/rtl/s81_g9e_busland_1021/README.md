# S81 G9e service-bus landing assemblies

Five real four-slot rings carry the complete 16-, 514-, 805-, 1077- and 2133-bit service bundles. RTL source is `96d428dee`; the wrapper-aware driver is `77607ae3b`. The actual remote input hashes and Icarus version are in `inputs.sha256.txt`.

EP5 unit `oth-ubuntu-810518-1792639411` ran all five exact wrapper tops and returned zero. Each positive passed all 36 phase/skew points and raised a fault for all four deliberate calendar slips. Both causal mutants failed all 36 normal points at every width: a naive register loses fixed latency across phase wrap; a shifted ring selector reads the wrong epoch. Original logs and JSON are preserved by width.

The assemblies accept one complete word each cycle without credits or backpressure. The direct-crossing model uses D=4, E=K=2 and a minimum three-cycle arrival age; equal-age bundles may require a larger K, recorded per link. Bind calendars align the source gate to the receiving reset release. The physical estimate follows the existing die model: (D+1)*W flops at 0.29 square micrometres per flop divided by 0.45 placement utilization. The generated land plan records total storage, payload, read-register bits and per-link ages before physical work.

These are unhardened RTL parents. They have no CLOSED view, and their source-bound reset-stage contract explicitly rejects a closed-view alias. Existing CLOSED landing tiles retain their strict reset-stage checks. Routing, clock spread, native fanout, final service calendar and production token qualification remain open. Die GEN carries those limits explicitly.
