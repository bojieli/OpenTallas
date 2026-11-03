# Frozen native START ancestor source

SOURCE PREP only. Extracts genuine retained provider RTL for W5 CTL, SU-c, both four-lane producer partitions and STREAM. 76 virtual stage instances, their real bounded reset relays, five actual pst outputs,81 total selected/native ancestor regions. No alternative origin, synthetic frame or clock alias.

Frozen source: bd55b15b452761be8ceefeae7b97abdf4a915bd4 provenance plan_qc52 and results/qc_die57_1031/bind/sidecar.json. Retained provider: results/token_pass/qc_functional_0845/inputs/start_stages.{sv,json.gz}, recoverable from the frozen Git tree even though the sparse worktree omits them. All3266 retained stages match selected graph region/parent/pad/edgefall and provider ID/clock-port/module/flop-count; node_cell matches selected geometric clock_node. Retained rects differ from plan placement, so no old physical view is transferred.

The retained actual_clock_driver is not semantically the same field as geometric clock_node: for an inverting node, the provider clock uses the true-polarity A-side driver net rather than the node Y output (start_stage_emit contract). Clock-port names stay explicit; actual selected driver/polarity join remains required. No all-ports dummy clock is permitted.

Run prepare_native_start_cone.py with --source retainedSV --stages uncompressedRetainedJSON --cone selected_cone.json --out aNewDirectory. Source emission and all referenced START/reset wire declarations checked; no EDA or runtime gate launched. Exact native origin and producer command/operand/write cone plus selected clocks must be composed before phase qualification. Full physical provider remains separate; pruning unrelated branches does not qualify reverse/control START paths or global clock/reset.
