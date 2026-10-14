# Native TAG59 functional transport

This distinct candidate preserves the legacy TAG32 sources and their CLOSED views. It has no qualified physical views or accepted area/cycle cost.

Identity is `{epoch16, stage6, token18, position13, segment6}`: bits 58:43, 42:37, 36:19, 18:6, 5:0. Stage is the explicit 38-stage native manifest ID. The allocator, not this transport, must allocate epoch on actual accepted whole-token admission, retain it across warm reset, and fence epoch FFFF reuse with actual drain/link reset/retraining. Untagged credits still require that coherent system fence.

Modules are `ot_rom_oneshot_die_native59`, `ot_coll_tp8_die_native59`, and `qfd_coll_xfifo_native59`. Ingress, package partial and cross-package records are 573 bits `{tag59, mode, last, data512}`. Peer results are 573 bits `{tag59, err, last, data512}`. Local returns are 576 bits `{tag59, err, rank3, last, data512}`; low517 preserves the original native return map. Collector scalar outputs add `out_tag[58:0]`.

The engine records the identity and agreement result of actual accepted operand groups. Existing arbitration drains older reduces before gathering, preserving arithmetic/result order. Each gather group emits four returns with the same recorded identity. The collective retains identity on its peer and local return queues and rejects a selected return whose identity differs from its active message. A participant-tag disagreement poisons the corresponding engine result, and protocol/engine/poison faults suppress collector output. Native sequencer validation is a separate source owned by the service integration stream.

This prototype uses CT0, MEMM0, WT0 and QMEM0 functional storage. Changed-width records cannot reuse the old fixed-width SRAM macros or physical WT1 column views. The FIFO retains the original accepted-strobe credit/reservation behavior with wider opaque payloads and functional storage.

`build_provider.sh OUT` builds the actual eight-die RTL observer. `runtime.py` accepts eight actual-produced rank files and one source-accepted identity dictionary per message. Rank order is native `4*DIE+PKG`; the bench index is `2*PKG+DIE`. CHECK0 requires an identity file and never reads a golden output file. Optional golden data is observer-only. The runtime validates output count, error and exact identity, and preserves actual data outputs for downstream comparison. This API does not turn caller-offered metadata into an allocator acceptance receipt.

`generate_vectors.py OUT` reproduces the independent component pair-fold fixture from pinned commit414c13ff1. This fixture is a component arithmetic/transport test, not actual checkpoint weights or a whole-token execution proof. Fresh tests preserve send gaps, source skew, full-vocabulary token bits, position8191, and actual stale-peer identity rejection. The guard-removal mutation demonstrates that the stale identity reaches outputs if the new join check is removed.
