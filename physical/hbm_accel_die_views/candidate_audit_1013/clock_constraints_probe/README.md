# Retained OpenSTA clock-constraint probe

Raw source and output copied byte-for-byte from the HBM lead's already-run
four-cell probe. Run in OpenSTA with this directory mounted at `/probe`.
`output.log` shows both common-to-early and early-to-common paths with
-0.2100 ns inter-clock uncertainty. `result.sdc` retains source early/late
latencies 0.1900/0.2100 ns at b versus physical base entry 0.1500 ns,
and retains asynchronous exceptions only for the serial domain.

The miniature Liberty has no min/max_clock_tree_path arcs. This probe proves
execution of the generated compensation constraints; it does not independently
prove OpenSTA's ETM normalization semantics on a real ETM. The per-pin parser
and reference corrections are covered by the focused Python/Tcl tests.
