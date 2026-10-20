# KV embedding takeover terminal evidence, 2026-10-20

Captured from the immutable EMB6 gate snapshots based on source branch claude/kv-emb6-1020 027eeaead; original worktree and databases were not changed. No source edits, closure submissions, or adoption in this step.

| variant | gate verdict | mapped max loads | TT / FF pin-flop spread ps | GRT overflow | native PG CTS / GRT failed contacts |
|---|---|---|---|---|---|
| n32b | WARN, zero FAIL | 32 | 42.3 / 46.3 | 0 | 5466 / 5466 |
| n32c | WARN, zero FAIL | 32 | 25.2 / 26.5 | 0 | 6270 / 6270 |
| x2a parent | WARN, zero FAIL | 32 | 53.4 / 52.5 | 0 | 15638 / 16194 |

These results are pathfinding gates. The independent frozen-database PG audit FAIL makes every variant ineligible for adoption. Failures include unbound hold BUFx2 VDD/VSS contacts; all audit mapping_error fields are empty. audit_pg.py loads the snapshot's own canonical native_pg_binding.tcl and opens CTS/GRT databases read-only in the fleet container. It performs no connect_global, unprotect, or database-write operation. Full audit witnesses are retained under each variant's pg/ directory.

n32c is the provisional standalone child choice because its measured pin-flop spread is smallest. It still needs ROOT's canonical hold-buffer creation/PG transaction fix, a fresh gate from merged tools, frozen native PG PASS, source-pinned native boundary timing audit, and coordinator image review before submission. The gate report's root-based clock metric does not establish child-parent compatibility. n32c floorplan PNG personally viewed: one SRAM with surrounding standard-cell area and full-face pin distribution; detailed review remains required. x2a uses the old c1b STAND-IN, has the existing off-lattice child-origin warning, and lacks the final native32 parent full-view bench/witnesses. Its numerical clock result cannot qualify the child crossing.

The current RTL schedule costs remain +2 active parent edges and +6 parallel reset-release edges; child active delta 0 and reset-release +6. This evidence step adds no cycles. No new RTL, physical layout or model change is proposed.

KVATTN3 remains a separate progressing source-pinned hierarchical Verilator build on ep5, unit oth-ubuntu-2714517-1792488035, original source fafc28231. No measured attention result exists yet. Do not populate prices 1555/1816 with predicted values.
