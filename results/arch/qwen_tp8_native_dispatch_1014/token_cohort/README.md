The functional `ot_qwen_tp8_token_cohort` reserves the sole allocator's actually
accepted stage-0/segment-0 TAG59 and original generation. It then accepts one
genuine credited endpoint request event per native rank. Each event must carry
that full identity. A registered credit pulse returns the consumed endpoint
request slot. Only the complete eight-rank acceptance mask permits the held
dispatch handshake. Neither offered HC packets nor seven-copy transmission
counts substitute for endpoint acceptance.

Execution starts and initial collective delivery must use the accepted cohort
dispatch. If ranks arrive through different clocks, their event stations require
real CDC/credits before these synchronous inputs; the component does not provide
an implicit CDC. Peer-7 delay is supported without launching the other ranks.

The component retains its allocation and acceptance mask across `warm_ready=0`.
Only POR resets identity. Warm-service ingress must hold endpoint events in real
stations while warm readiness is absent. Duplicates, any TAG59 or generation
disagreement, and stale terminals fault the cohort and suppress dispatch. Faults
are sticky until a matching drained fault terminal releases the allocation and
genuine link drain/reset/retraining permits recovery. Normal terminals require
actual prior dispatch. Terminal identity is the same allocation with stage 37,
segment 0; terminal acknowledgement is qualified by that full identity and
generation. A held terminal is consumed once and rearms only after valid falls.

The authoritative `v3` gate passed 1,056 checks with a 1,000-edge genuine delayed-rank input,
normal terminal drain withholding, registered held-terminal rearming, duplicate
and all six identity field errors, warm retention, drained cancellation, failed
retraining, and stale terminal rejection. Four actual source mutants failed the
strict observer. Unit `2510323-1791975477` ran via ot-run on EPYC1 and exited 0.
It additionally proves that a simultaneous invalid begin and recovery fence
cannot erase an identity fault. The source requires no asserted begin during
recovery and blocks dispatch on the same edge as an invalid begin. The earlier
`v2` positive and mutants remain preserved under their original source identity.
`v1` preserves the failed observer run: the bench cleared a pulse without
reevaluating combinational signals, so its immediate post-pulse observation was
stale. The RTL was unchanged between these runs.

This is standalone functional control evidence. Actual HOST endpoint admission,
continuous collector reset/credit fence, core launch, all-rank terminal assembly,
and whole-token checkpoint execution remain integration obligations. No physical
view, rate, or price acceptance follows from this component.
