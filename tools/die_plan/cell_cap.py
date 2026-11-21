"""WAVE-FLOW-R2 11-17 (FABLE-FLOW-1100 item 4): the ONE type cell limit.  A type whose estimated flat standard cells exceed SPLIT_CELLS is a
SPLIT-NEEDED finding at plan / compose time (type_bound.classify, kit_wave plan probe) and is never launched.  No run-time stop by default: the in-kit
floorplan CELL-CAP (native_cell_cap.tcl, FLOW-OPS-0900 11-21) REPORTS a measured count over SPLIT_CELLS and the wave posts it once per type (stop only with
OT_CELL_CAP_STOP=1, COORD r703 ruling); enqueue / classify / place only report."""
SPLIT_CELLS = 400_000
