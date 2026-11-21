"""WAVE-FLOW-R2 11-17 (FABLE-FLOW-1100 item 4): the ONE type cell limit.  A type whose estimated flat standard cells exceed SPLIT_CELLS is a
SPLIT-NEEDED finding at plan / compose time (type_bound.classify, kit_wave plan probe) and is never launched.  The one run-time stop is the in-kit
floorplan CELL-CAP (native_cell_cap.tcl, FLOW-OPS-0900 11-21: measured std cells over SPLIT_CELLS, opt-out OT_CELL_CAP_STOP=0); enqueue / classify / place only report."""
SPLIT_CELLS = 400_000
