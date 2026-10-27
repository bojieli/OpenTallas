# Declared QC entry delivery planning

Planner: cf7cf0e32 (`qc_entry_delivery.py`); exact candidate d6a9f226fe:physical/die_plan/qwen_compute/candidate_guard51_native100_io.json and committed R6 `geometry6/inputs/clock_spec.json.gz` mesh geometry. R6 cells fail PG orientation; this receipt uses only its unchanged mesh conductor coordinates.

360 direct entries have at most86.4um of actual metal from their nearest strap to the declared entry. All360 declare M9.17 entries need staged branches, including four newly corrected PHY coordinates. The exact d6a9 candidate still declares those four terminal layers M9 despite their real LEF M5 clock pins; parent plan owner notified and preparing successor. Do not infer M5 or silently substitute coordinates in this receipt.

`direct_d6a9.json` is a plan delta: actual terminal coordinates, nearest strap anchors, direct wire length and pending staged branches. It adds no cell or delay. It does not qualify local trees, PG, extraction or timing. New opt-in terminal stack support (268d805ee +17e7bab50) encodes explicit M4..M9 terminal layer transitions as real vias and includes lower access in cross-net census. Native terminal-stack coupon remains required before adopting that option in the complete physical vehicle.
