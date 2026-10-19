# GEN2e2 original-success verification

Read-only pickup, 2026-10-19 13:48 PT. All 39 distinct original successful synthesis rows have actual terminal Yosys, TT and FF ETM artifacts, exact wrapper/netlist top and port order/directions/bit ranges, ETM library/cell names and bus bit ranges, and SHA256 for source/input and result artifacts. 38 outputs are on ot-epyc6; gq_issue's successful fourth round is on ot-pve1. Its three failed rounds remain preserved; the ep6 failed output was not mistaken for the final output.

The proposal's 37 old successes plus three formerly live names overlap on tkm, so they represent 39 distinct cells. Selector, score quarter and tkm are now complete. Original jobs.tsv has 79 distinct cells: 22 prior reuse and 57 new synthesis rows, of which 39 succeeded and 18 failed. Original views.json has 142 entries. No claim here independently qualifies the 22 reused views.

All 85 unique non-wrapper input files match pinned commit 6f783d0a1 by exact SHA256. All 39 generated wrappers match original vplan_a/wrap bytes. The per-row receipt includes actual Yosys script, file manifest, netlist, log, stat and ETM hashes, rather than relying solely on successful driver metadata.

The seven-host inventory positively reaches ep4, ep5, ep6, ep8 and PVE1. No original /syn output has a live container on these hosts. Four corrected ETMs pv4/pv6/pv7/pv13 are live on ep6, independently distinguished by mounts and IDs. PVE2/PVE3 DNS failures leave those host inventories explicitly INCOMPLETE; do not infer process absence there. No compute was launched, stopped or duplicated. Failed-only controller PID2322853 was alive under PPID1. Never restart run_failed.py.

This artifact does not modify the active 18-row collector, proposal or frozen source. Final composed view manifest remains INCOMPLETE until all 18 corrected receipts and reused views receive ROOT review. SRAM macro area remains UNKNOWN, not zero; no fit, physical qualification, S3, GEN or GO claim.
