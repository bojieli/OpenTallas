# CLAUDE S81-PH svc tiles (dsfd_svc_pc, dsfd_svc_stn): appended after the calibrated margin IO SDC (core_clk = ck).
# rst = asynchronous die reset, synchronised in the tile.
set_false_path -from [get_ports {rst*}]
