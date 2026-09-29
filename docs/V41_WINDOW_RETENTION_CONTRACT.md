# Opt-in L0 packed WINDOW retention

Root approved a single-L0 experiment. Default behavior remains refill; indexed
and compressed-KV reuse is excluded. The reference model is not integrated RTL.

## Exact descriptor difference and same content proof

In the bound113-PC program, QK isPC24 and PV isPC32:

| Field | QK | PV |
|---|---|---|
| ts |512|1|
| ks |1|32|
| k after T0 resolution |512|128|
| nout after T0 resolution |128|512|
| tiles after T0 resolution |4|16|
| wbase/js/hg/mmode |0/0/1/1|0/0/1/1|

Both consume the same128 physical FP8 rows. PC21/22 publish KT0/KR0 from the
same KVQ. PC25–31 write only VM/HCP/selection temporaries and softmax S/Z;
none writes KT0, KR0, KVQ or a SU KV destination. The executable contract checks
those actual instruction fields, not a manually assumed no-write interval.

Raw descriptor equality would miss reuse because transpose/geometry differs.
Conversely, equal position alone is unsafe. Normalize content identity to user,
layer, absolute position, firstrow/count/finalmask, format/layout, stack and region
base/count, step epoch and source-content epoch. Allow only validated L0 QK→PV
signatures. Current external runtime does not expose every generalized identity;
therefore remain L0-only, with explicit step/config invalidation.

## Minimal implementation and hazards

Retain existing stage payload after QK; no extra rows, no extra HBM queue. Add one
small metadata entry, comparator, valid/single-use bit and one registered lookup
stage. Budget320 metadata bits pending exact packing; compare latency1 cycle,
physical timing unproved. Arm only after all128 rows are valid, prior replay and
engine finish, all service queues drain and no fault occurs.

A hit starts a **new lifecycle generation**, publishes stage-ready only in that
new generation's STAGE phase, resets replay beatcount and emits fresh beat tags.
Never preserve READY, beat_count or old descriptor generation. It bypasses
prefetch requests themselves: existing BANKED_STAGE unconditionally invalidates
and refills on every accepted prefetch.

Invalidate on ANY accepted block write, host prime, external region write,
replacement prefetch, step/layer/config/layout/region change, reset or fault.
Invalidation is at write acceptance, before completion, even for a partial row.
Reject hit while writes/reads/replay responses remain outstanding. A mutation
coincident with a lookup wins. Mutations while streaming remain backpressured or
faulting, never silently accepted into reused data. Epoch wrap requires invalid
entry and quiescent drain; matching wrapped numbers do not authorize a hit.

The metadata is single-use: a missed PV falls back to ordinary refill; a hit
consumes the entry. No multiuser persistence is claimed. A later user request may
evict immediately; pinning must not stall single-user critical operations without
pricing that latency.

## Expected benefit and required verification

Avoid2176 sectors and one128-row refill, not probability preload or PV arithmetic.
The4608-cycle ideal-source refill is a standalone witness, not predicted shared
HBM savings. Exact integration must run QK, real intervening VM operations and
PV with identical numeric results, no second-refill traffic and new-generation
beats. Negative gates: user/position/layer/config/format changes, pending/partial
write, sourceepoch wrap, late old response, invalid rowmask, incomplete fill,
and backpressure across final QK/first PV. The Python contract covers identity
and hazard decisions; the connected numeric test belongs to the attention owner.

## Standalone control implementation

`ot_chip_v41x_window_retention` implements the opt-in metadata decision, default
ENABLE=0. A320-bit canonical identity is supplied by the integrating wrapper;
it must bind all fields above and exact QK/PV shape validation. Storage is320-bit
key plus two16-bit generation registers and three control bits (355 bits), not
extra KV payload. One registered response cycle is explicit. Concurrent or
response-cycle invalidation suppresses hits; wrap always misses. This conservative
module never reuses a descriptor generation and consumes each entry once.

The standalone RTL test flips every one of320 key bits and checks single-use,
write/prime/config invalidation, pending write, incomplete rows, wrong shape,
un-drained service, stale generation and wrap. These are controller tests;
**source-scheduler hookup and real QK→VM-ops→PV numerical replay remain pending**.
No prefetch/source file was changed; refill owner retains that scope.
