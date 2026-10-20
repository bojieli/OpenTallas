# MU host turnaround measurement

The exact existing four-user/three-round MU peer bench passes on Verilator 5.050. Timestamp-only observers measure the coordinator engine RESULT edge to the next native request at die-0 endpoint output: 26, 43, 44, 27, 27, 44, 3026, 27 edges. The 3026 case contains the bench's deliberate 3000-edge user3 delay. Other cases max at 44 edges. This measures an actual RTL service chain, with host stimulus waiting for POST.

This does **not** admit the final kind-12 slot: record_port/pin wrappers, physical die/CDC links, and the real host turnaround are absent. The old placeholder max(3,21+H) therefore still needs the complete bound transport H. The ideal-router native-request component alone would contribute 44 edges to that ledger; do not promote 65 to a production slot without adding the missing pieces and replaying its static calendar.

The prior source monitor also measured RESULT->POST <=33, cmd->local request 9..54, cmd->all-eight requests <=70, and RESULT->all endpoint retire 5. These maxima come from different events and must not be treated as one measured complete latency.

record.json pins every source hash and the executed bench commit. The raw log includes duplicate HLAT_NEXT prints from both unchanged observer sites; identical timestamp tuples are deduplicated in record.json. No production RTL or schedule changes.
