# CLAUDE S81-PH coll v2 core tile (dsfd_coll_core): appended after the calibrated margin IO SDC (core_clk = ck).
# rs = asynchronous stream reset (synchronised in the tile).
set_false_path -from [get_ports {rs*}]
