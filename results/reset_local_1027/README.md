# Independent local reset delivery

`partition_types[T].reset.local_taps_um` adds explicit local reset/START terminal relay sites. Clock tap ports and clock topology are unchanged. The generated synchronous tree reaches every added site at the same type depth as the existing consumer taps and registered neighbor outputs. No asynchronous exception is added. These relays retain their nets through synthesis for placement-time sink assignment.

Bound native station reset selection reads the source-ordered `native_station_plan.json` copied by bind.py (f51684c55). FT station selection reads the plan's explicit `regs_um`. Physical hooks re-point control/epoch sinks to the nearest equal-depth reset terminal and retain the existing placed-hop gate.

The independent geometry package `codex/geom-0812-1027@d6844af1c` supplies the io_cor/hroot local grids, rendered and viewed against actual 3_place flops. All existing clock pins remain on y=21.6. Whole-outline nearest-grid coverage is 345.6 um; measured all-flop maxima are 340.821/337.959 um.

Planning-only comparison on immutable R26 hm_r26.json using R26 schema tap rules (38c1ed8519) is in r26_release_compare.json. io_cor adds 3 boot/START clocks after its input, hroot adds 2; no data-lane cycles. All per-partition wavefront offsets and compiler boot/START tables must regenerate in the one KV plan event. Both generated trees pass structural checks. This is not routed timing or sign-off evidence.

Validation: 54 focused reset/landing and binding tests pass, including generated RTL lockstep against the declared pipeline-depth specification and a direct reset/START bypass mutant; 3 relevant G2 tests pass. Existing default plans do not opt in to extra consumers. Native re-plan strips an old initialized leaf-reset wire before assigning the new local leaf, preventing two relay drivers on rst_n. Pipelined consumers preserve the same explicit terminal-net metadata. No P&R submitted.
