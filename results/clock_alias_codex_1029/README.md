# Actual ctree clock-master alias fix

netlist_tap_masters traced only direct cell Y(port) connections. Actual
ctree emits `assign tap = internal_net`, so the trace silently returned
no masters and spice_cell fell back to the tree's inverter master,
dropping BUFx24 tap pads. It now resolves output and intermediate input
aliases, rejects loops/undriven paths, and retains unknown masters so
cell_cal_factors fails closed instead of defaulting to the inverter.

Actual retained KV tree:1,920 ports traced,1,888 inverter-only and32
inverter+BUFx24 paths (the32 PHY taps), matching measured component
inventory. Five focused alias/unknown-master/loop/undriven controls and
the existing netlist-master test PASS. No route, STA, default calibration
or clock change. Base shared mixed-calibration helper7caabf04b.
