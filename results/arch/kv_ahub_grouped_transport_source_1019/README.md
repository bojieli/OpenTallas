# Private grouped AHUB transport source review

No compile or simulation yet. Exact predecessor4415ee6cf and model143642b6b are preserved in frozen files. New private module family has ENABLE=0 bypass with unchanged interface and default outputs; no production source changed.

3075 state bits =1344 genuine4-slot indexed payload +1731 other bits. There are43 banks (<=8bits), command groups8/8/8/8/2, return8/1. Both physical resets drive7 independent root pairs. Explicit raw AND supplies authority before reset propagation. Common-clock recurrence adds exactly2 startup/admission edges; accepted-history data interval remains4 edges. This experimental startup cost has no production calendar adoption.

EMITTED_SOURCE_REVIEW.json lists all nonclock source driver classes with four slot-mux data loads per group-valid/bank. Explicit shared one-hot phase decode feeds static slot writes and rotated indexed reads; no shift chain, initialized RAM, numeric arming or quiet-window delay. Raw fanout21, receiver-group18, ingress-valid32 are source equation counts. RTL keep attributes do not prove independent mapped roots. Constants require local <=32-pin tie realization; no actual tie cell/PG implementation exists, so the complete native all-driver audit remains HOLD.

Payload has no reset and is held in an indexed array. Receiver reset removes output authority immediately, discards receiver-owned words, and clears validity by actual recurrence; transmitter-only reset allows prior accepted receiver words to drain. Invalid output payload may be arbitrary. Prefrontier speculative internal activities have no authoritative accept/output.

Safe-design checklist: pins HOLD native registered face implementation; reach HOLD; fanout source bounded except unbound constant roots, mapped HOLD; depth explicit binary mux/decode shape only; storage indexed4slot but macro technology HOLD even at1344bits; floorplan HOLD; clock/reset pulse/glitch/native phases HOLD; schedule experimental+2 startup only, accepted latency4. No physical, arithmetic, retained-health, child/calendar or SU/MU qualification.
