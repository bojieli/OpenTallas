# Default-off BIRA search popcount pipeline

Tested source: `65c28c175` (`POP_PIPE=1`); pinned BIRA, controller, shell and benches remain unchanged. Additive successors default to `POP_PIPE=0`.

The prescribed search uses registered 16-bit chunk counts, sums of four chunks and a final sum. It keeps subset/allocation order and queue/accepted-event processing. Search takes five rather than three cycles per subset: +128 cycles per E=6 analysis, at most +256 cycles across two SRAM banks. The unified model prices +213.248 ns at the target 0.833 ns; clean BIST and inference incur zero additional cycles. This is a model price, not a measured clock.

The existing element campaign passes functional exactness (two seeds), 22/22 fault cases and signatures `c3be36d94a11bdbd0082a2b5c029cd00`. Clean BIST remains 21,545 cycles. Matched fault-case deltas are 0 or +128 cycles. The shared controller campaign passes all 74/74 scenarios, its existing ECC checks and all lint gates. See `element.json`, `controller.json` and `latency.json`.

The first source attempt's overall controller verdict was FAIL due to lint width/filename warnings despite 74/74 functional scenarios. Its evidence remains in `../bira_pipe_v1_lint_FAIL/`. Explicit-width and scratch-filename corrections introduce no allocation/pipeline change.

The first physical launch failed before synthesis/P&R because the shared driver referenced an undefined `argv`; no ORFS artifacts were created. Its source/command/log are preserved in `route_v1_preflow_FAIL/`. The shared tool owner was notified; no duplicate run or custom driver workaround was used.

Routed SS60/FF25 closure at 0.833 ns, DRC/antenna/electrical checks and measured area remain pending. The pipeline is not adopted and no frequency or area headline is claimed. Inventory remains unchanged pending qualification.
