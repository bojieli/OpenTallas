# QC R26 export8 — dry component build review

Picture `results/qc_clk_mesh3/r26_codex/geometry8/all_tree_geometry.png` viewed2026-10-27. Pinned model0a3c806f9 and exporterfe4b1b130 (integrated6d47355cb). Raw packet intel2:/srv/opentallas-scratch2/claude/codex-qc-export-1027/export8_rowpins_inset/.

Regular horizontal band drivers remain in free row corridors; the west feed now rises vertically in the west channel before crossing in free bands. No diagonal repeater clusters over opaque cores. Full cell bodies clear seams/die inset and core halos. Actual geometry report:33417groups50149cells33416stage nets,0errors, maxstage448.524um. Row parity now29177R0/20972MX,0parityerrors. Native actual LEF PG proof in qc-export-pg-proof/result.json shows adjacent correct R0/MX VDD rails coincide and opposite-net VSS does not; old all-R0 fault preserved.

PASS-COND for upstream clock/mesh DRY construction only. Actual wire/shield/PG/via census remains to build.360short entry deliveries and17staged west branches are separate incomplete work; local trees and final PHY M5 terminals are not qualified by this image. Per-type footprint identity still pending. No routing/STA/freeze approval.
