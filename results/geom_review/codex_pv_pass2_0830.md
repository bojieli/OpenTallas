# KV pv_join R0 pass2 planned entry trunk

Image personally viewed: results/codex_pv_pass2_0830/pv_trunk_plan.png.
Verdict PASS for CTS trial: the approved single BUFx4 occupies the reserved centre-entry island with no fixed tap overlap; root origin86.238,86.4um remains between M5 PG stripes. Clock entry86.424,86.4 and reset entry86.808,86.4 are unchanged. The short clock stub fits without a PG crossing. No new macro, datapath hop, IO pin or latency cycle is introduced. One CTS-open leaf domain contains all15763 sequential clock sinks from the placed netlist. The data placement already passed independent geometry and GRT review; route remains pending actual CTS geometry and timing.

The predecessor slice predicts250.0TT/201.1FFps after one BUFx4. These are PLAN MODEL UNCHECKED values, not a timing PASS. Actual propagated timing remains to measure. The pass1 island reservation will be consumed only where the trunk cell is fixed; all other island sites stay reserved, and every tap is retained.
