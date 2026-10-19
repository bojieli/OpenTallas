# Qwen forwarded corridor and phase diagnostics, 2026-10-19

The original `forward1` diagnostic failed after all765 regional roots:
`no clock route (1940,854) -> (1691,877)`. Its complete failure log is
`physical/build_tt.log`. It produced neither a clock ODB nor a timing verdict.
Source is `codex/qwen-dieclk2-recovery-1019@42d93c5d8`, using GEN
`1075e50e2dcc1c25d15ab8232757bac665f11a1a` (dv2f16), not the live dv2f18dh2 GEN.

The actual adjacent hard blocks span y5529.600..10756.776um:
`c16_E0_1` x16951.680..19396.776 and `c16_E1_1`
x19414.080..21859.176. Their17.304um corridor contains12.960x6.480um
reset repeater blocks at10.800um ypitch. The10um conservative grid hides the
4.320um physical bays. No macro relocation or reach relaxation is justified.

`physical/corridor_occupied_geometry.json` replays the exact failed pair with
all hard rectangles and18333 placed standard cells. Actual ODB confirms
BUFx24=1.620x0.270um and BUFx12f=.972x.270um. Whole-footprint exact bays restore
26637 coarse cells; a670-step route has station bounds at most404.540um.
This proves the corridor representation change; the full new spine remains
unqualified until replayed after all765 new region trees have been placed.

The opt-in `spine.exact_footprint_bays` source fix takes that post-region ODB
occupancy, reserves every whole footprint, and checks routed length using
actual placed library pin coordinates. It keeps strict380um blocked runs,
405um stage reach and fanout2. `--geometry-only` writes a geometry manifest
before STA; it never produces a timing/admission claim. The recorded script
and exact spec replay the entire required spine before any new timing build.
Ten focused fleet tests pass. `reach_mutant.log` is the required independent
410um rejection witness; occupied bays, newly placed region trees and partial
footprint overlaps are tested.

Immutable inputs are on epyc4:
`/srv/opentallas-scratch/claude/codex-qwen-dieclk2-1019`.
Floorplan ODB SHA256:
`793ab8aedba4e0f7c8a0706ece9a776ff00c7ca09e9e7b3df175762ee563e53c`.
Hard rectangles SHA256:
`efeda305ec8b150318215cfe0197f23f68f1ae43586f24157f46e9406fdd3f81`.
Occupancy JSON SHA256:
`e5a6e1aa0a4b8d31726d2a87db17df38103a0bba41ef98cf57bbcd16a2bad810`.
Own replay/collector outputs:
`/srv/opentallas-scratch/claude/qwen-clock-phase-1019/baseline_measure`.

`qwen_qphase.py` binds actual GEN endpoint/relay/native clock pins and collects
single-corner TT/FF/SS raw pin arrivals. The old completed DME ODB was used only
as a collector runtime control, not as the failed forward1 candidate. Its
receipt remains BLOCKED: GEN mismatch, missing SAFE2 clock ports, assumed native
references, and unresolved propagated pin-clock tags. No prefetch advance or
production phase is admitted. Production still owes a source-bound programme,
512 Q writes/all32 requests and an actual per-endpoint phase replay.
