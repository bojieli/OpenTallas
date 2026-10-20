# KV embedding takeover terminal evidence, 2026-10-20

Captured from the immutable EMB6 gate snapshots launched by source branch claude/kv-emb6-1020 027eeaead (the gate manifests, including working-tree and daemon overlays, are authoritative; n32c records start_commit 44190484115f8f5e3440882c6858bb99020efa7e); original worktree and databases were not changed. No source edits, closure submissions, or adoption in this step.

| variant | gate verdict | mapped max loads | TT / FF pin-flop spread ps | GRT overflow | native PG CTS / GRT failed contacts |
|---|---|---|---|---|---|
| n32b | WARN, zero FAIL | 32 | 42.3 / 46.3 | 0 | 5466 / 5466 |
| n32c | WARN, zero FAIL | 32 | 25.2 / 26.5 | 0 | 6270 / 6270 |
| x2a parent | WARN, zero FAIL | 32 | 53.4 / 52.5 | 0 | 15638 / 16194 |

These results are pathfinding gates. The final-binding audit run on these intermediate CTS/GRT databases reports unbound contacts. This alone does not establish a flow defect: unprotected and nonfixed cells may bind normally during final global_connect. The exact protected/fixed census is collected separately; final 6_final PG PASS remains mandatory. Failures include unbound hold BUFx2 VDD/VSS contacts; all audit mapping_error fields are empty. audit_pg.py loads the snapshot's own canonical native_pg_binding.tcl and opens CTS/GRT databases read-only in the fleet container. It performs no connect_global, unprotect, or database-write operation. Full audit witnesses are retained under each variant's pg/ directory.

n32c is the provisional standalone child choice because its measured pin-flop spread is smallest. It still needs ROOT's canonical hold-buffer creation/PG transaction fix, a fresh gate from merged tools, final native PG PASS, source-pinned native boundary timing audit, and coordinator image review before submission. The gate report's root-based clock metric does not establish child-parent compatibility. n32c floorplan PNG personally viewed: one SRAM with surrounding standard-cell area and full-face pin distribution; detailed review remains required. x2a uses the old c1b STAND-IN, has the existing off-lattice child-origin warning, and lacks the final native32 parent full-view bench/witnesses. Its numerical clock result cannot qualify the child crossing.

The current RTL schedule costs remain +2 active parent edges and +6 parallel reset-release edges; child active delta 0 and reset-release +6. This evidence step adds no cycles. No new RTL, physical layout or model change is proposed.

KVATTN3 remains a separate progressing source-pinned hierarchical Verilator build on ep5, unit oth-ubuntu-2714517-1792488035, original source fafc28231. No measured attention result exists yet. Do not populate prices 1555/1816 with predicted values.

Exact state correction: n32b and n32c have ZERO protected-unbound or fixed-unbound contacts in both CTS/GRT databases. Their intermediate unbound contacts alone do not block progression. Parent x2a has 3910 protected-unbound contacts in each CTS/GRT database (zero fixed-unbound), establishing the protected-bind concern for the parent. See pg_state/summary.json and full per-contact TSV witnesses. Child final routed PG and boundary audits remain owed.

Boundary diagnostic: n32c fails one native launch pin row_open at 223.89729 ps against 220 ps, capture82.48839 ps against190, no combinational pins, TT/FF spread25.2/26.5. This independent boundary concern prevents qualification at the current reference. Probe uses CTS placement RC; no routed timing claim. Existing n32b snapshot diagnostic is being compared before deciding on structural repair.
