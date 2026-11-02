# QC coll_ucie source floorplan review, 2026-11-01

Picture: `results/qc_die62_1101/codex_collect/coll_ucie_parent_repack.png` (personally viewed).

Current source: **FAIL**. The licensed PHY abstract spans the complete partition width. No west/east channel remains. The plan also selects an older physical interface than the native bound blackbox, and names the macro outside its actual `u_bound` hierarchy.

Proposed matching native metadata with an 803.52-um slot: **BLOCKED_PARENT_REPACK**. The picture shows a 25.92-um intrusion into both eastern peers, coll_f2 and coll_core. The added macro side channels clear the static 10.8-um rule, and the native M5 pin phase and actual instance path clear their static contract checks. Parent interfaces, data and reset reach, clock placement and PG must be regenerated and reviewed together. The current canonical coll_ucie plan remains unchanged.

This is a source geometry review only. No actual new GEN or placed view exists; no P&R, STA, equivalence or physical-release credit. The licensed PHY view remains an assumed abstract, with `physical_qualification_eligible=false` in its own metadata.
