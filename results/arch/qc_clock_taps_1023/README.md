Qwen compute clock-tap declarations (COORD 10-23 08:34)

The existing generator clock_taps() reproduces all 51 type records in the
previous plan_notes.clock_taps.types exactly. Its schema-supported fields are
now copied into partition_types.<type>.clock.taps[] by declare_clock_taps(),
called from the normal generator. The 134 type taps produce 1,941 placed tap
instances. All 388 partition clock.tap_um roots remain unchanged. Removing
only the newly added clock.taps fields yields the exact previous plan object:
no port, lane, topology, latency or other plan field changed. Region/reach
annotations remain in plan_notes because they are not clock.taps schema fields.

G2 die generation adds these declarations as terminals on the same existing
virtual clk_spine diagnostic net. It preserves the partition roots and reset
spine, and applies only the partition orientation to the already type-frame
coordinates (a0_ck already applied core orientation). Diagnostic metadata
records all declaration fields and transformed coordinates. Tap names use safe
indexed terminal IDs rather than Tcl-interpreting arbitrary declared names.
Plans with no extra taps generate all four probe files byte-identically to
main55e0ec7fa. Tests cover that default and the partition/core orientation case.

These are virtual connectivity/PG/reach diagnostics. Insertion fields remain
existing declared estimates, not measurements. Hard-core source pin binding,
actual insertion, regional clock trees and STA remain open. G0's zero hard-core
count is absence of hard-core entries, not 0/0 qualification. No RTL, clocks,
clock-domain topology, budgets or hard-core pins were invented.

G0 PASS: zero errors, 84 warnings, 134 declared type taps, 54 types/388
partitions. Complete die-plan suite: 46 passed. The source and render require
independent G1 re-review before any new probe run. Earlier root-only G2 results
are preserved and do not qualify the newly represented taps. No G2 or P&R run
was launched for this change.
