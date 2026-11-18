"""WAVE-FLOW-R2 11-17 (FABLE-FLOW-1100 item 4): the ONE type cell limit.  A type whose estimated flat standard cells exceed SPLIT_CELLS is a
SPLIT-NEEDED finding at plan / compose time (type_bound.classify, kit_wave plan probe) and is never launched.  No run-time stop exists any more
(autopilot enqueue / classify, kit_wave place, prebuild_gate, native_cell_cap.tcl only report)."""
SPLIT_CELLS = 400_000
